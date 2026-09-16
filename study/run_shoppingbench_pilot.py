from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import shutil
import subprocess
import tempfile
from contextlib import ExitStack
from pathlib import Path

import yaml

from study.adapters.shoppingbench import (
    SHOPPINGBENCH_GROUPS,
    ShoppingBenchAdapter,
    render_document,
)
from study.attribute_saturation.analysis import paired_analysis
from study.attribute_saturation.evaluation import evaluate_run, mean_metrics
from study.attribute_saturation.representation import GROUP_ORDER

DEFAULT_CONFIG = Path(__file__).parent / "configs" / "pilot-shoppingbench.yml"


def _sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n")


def load_config(path: Path) -> dict:
    config = yaml.safe_load(path.read_text())["experiment"]
    if config["benchmark"] != "shoppingbench" or config["retrieval"] != "bm25":
        raise ValueError("Only ShoppingBench BM25 is supported")
    if config["representation_levels"] != [level.value for level in GROUP_ORDER]:
        raise ValueError("Pilot requires the five registered levels in order")
    if config.get("random_order_seeds") or config.get("llm", {}).get("enabled") is not False:
        raise ValueError("This pilot does not implement random ordering or LLM inference")
    if not isinstance(config["seed"], int) or isinstance(config["seed"], bool):
        raise ValueError("seed must be an integer")
    if not isinstance(config["bootstrap_samples"], int) or config["bootstrap_samples"] < 1:
        raise ValueError("bootstrap_samples must be positive")
    targets = config["saturation_targets"]
    if not targets or any(not 0 < value <= 1 for value in targets):
        raise ValueError("saturation_targets must be in (0, 1]")
    expected = {"recall@1", "recall@5", "recall@10", "mrr", "ndcg@5", "ndcg@10"}
    if set(config["metrics"]) != expected:
        raise ValueError("Unsupported metric selection")
    return config


def run_pilot(
    documents: Path,
    queries: Path,
    output: Path,
    *,
    config_path: Path = DEFAULT_CONFIG,
    top_k: int = 10,
) -> Path:
    """Publish a complete run atomically; never overwrite inputs or a previous run."""
    config = load_config(config_path)
    adapter = ShoppingBenchAdapter(documents, queries, top_k)
    if output.exists():
        raise FileExistsError(f"Use a new output directory: {output}")
    query_records = list(adapter.queries())
    qrels = list(adapter.qrels())
    if not query_records or not qrels:
        raise ValueError("No queries/qrels")
    input_hashes = {"documents": _sha256(documents), "queries": _sha256(queries)}
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".pilot-", dir=output.parent))
    try:
        levels = list(GROUP_ORDER)
        stats = {
            level.value: {"field_count": 0, "whitespace_tokens": 0, "utf8_bytes": 0}
            for level in levels
        }
        targets = {record.product_id for record in qrels}
        matched = set()
        count = 0
        # Decompress the potentially multi-GB corpus once, not once per treatment.
        with ExitStack() as stack:
            streams = {}
            for level in levels:
                path = staging / "corpora" / level.value / "documents.jsonl"
                path.parent.mkdir(parents=True)
                streams[level] = stack.enter_context(path.open("w", encoding="utf-8"))
            for record in adapter.products():
                count += 1
                if record.product_id in targets:
                    matched.add(record.product_id)
                for level in levels:
                    rendered = render_document(record.fields, level)
                    streams[level].write(
                        json.dumps(rendered, sort_keys=True, ensure_ascii=False) + "\n"
                    )
                    stats[level.value]["field_count"] += len(rendered["product"])
                    stats[level.value]["whitespace_tokens"] += len(rendered["contents"].split())
                    stats[level.value]["utf8_bytes"] += len(rendered["contents"].encode("utf-8"))
        if not count or matched != targets:
            raise ValueError(f"Corpus is empty or missing {len(targets - matched)} qrel products")
        _json(staging / "qrels.json", [record.__dict__ for record in qrels])
        _json(staging / "queries.json", [record.__dict__ for record in query_records])
        rows_by_level = {}
        summary = {}
        for level in levels:
            print(f"Indexing/retrieving {level.value}: {count} products", flush=True)
            corpus = staging / "corpora" / level.value / "documents.jsonl"
            index = staging / "indexes" / level.value
            run = staging / "runs" / f"{level.value}.jsonl"
            adapter.build_index(corpus, index)
            adapter.run_retrieval(index, run, expected_documents=count)
            with run.open() as stream:
                rows = evaluate_run((json.loads(line) for line in stream), qrels)
            rows_by_level[level.value] = rows
            summary[level.value] = mean_metrics(rows)
            path = staging / "metrics" / f"{level.value}.jsonl"
            path.parent.mkdir(exist_ok=True)
            path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))
        _json(staging / "summary.json", summary)
        _json(
            staging / "analysis.json",
            paired_analysis(
                rows_by_level,
                seed=config["seed"],
                samples=config["bootstrap_samples"],
                targets=config["saturation_targets"],
            ),
        )
        _json(staging / "representation-stats.json", stats)
        # Detect inputs modified during a run before publishing a misleading manifest.
        if input_hashes != {"documents": _sha256(documents), "queries": _sha256(queries)}:
            raise ValueError("Input files changed during the run")
        _json(
            staging / "manifest.json",
            {
                "schema_version": 1,
                "config": config,
                "input_sha256": input_hashes,
                "config_sha256": _sha256(config_path),
                "product_count": count,
                "query_count": len(query_records),
                "top_k": top_k,
                "mrr_scope": f"MRR truncated at {top_k}; not unbounded MRR",
                "field_groups": SHOPPINGBENCH_GROUPS,
                "renderer": "shoppingbench-values-v1",
                "bm25": {"k1": 0.9, "b": 0.4},
                "python": platform.python_version(),
                "dependencies": {
                    name: importlib.metadata.version(name) for name in ("pyserini", "numpy")
                },
                "java": subprocess.run(
                    ["java", "-version"], capture_output=True, text=True, check=True
                ).stderr.strip(),
                "source_sha256": {
                    path.relative_to(Path(__file__).parent).as_posix(): _sha256(path)
                    for path in sorted(Path(__file__).parent.rglob("*.py"))
                },
                "files": {
                    path.relative_to(staging).as_posix(): _sha256(path)
                    for path in sorted(staging.rglob("*"))
                    if path.is_file() and "indexes" not in path.relative_to(staging).parts
                },
                "evidence_boundary": "Observed subset/corpus only; no LLM or full-agent claims. "
                "Qrels identify a target product, not every acceptable substitute. "
                "Bootstrap intervals are pointwise, conditional on this corpus and group order.",
            },
        )
        staging.rename(output)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the deterministic ShoppingBench BM25 pilot")
    parser.add_argument("--documents", type=Path, required=True)
    parser.add_argument("--queries", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--top-k", type=int, default=10)
    args = parser.parse_args()
    run_pilot(args.documents, args.queries, args.output, config_path=args.config, top_k=args.top_k)


if __name__ == "__main__":
    main()
