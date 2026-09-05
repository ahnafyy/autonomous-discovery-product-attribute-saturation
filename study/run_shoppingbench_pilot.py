from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from study.adapters.shoppingbench import ShoppingBenchAdapter
from study.attribute_saturation.evaluation import evaluate_run, mean_metrics
from study.attribute_saturation.representation import GROUP_ORDER


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the deterministic ShoppingBench BM25 pilot")
    parser.add_argument("--documents", type=Path, required=True)
    parser.add_argument("--queries", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--top-k", type=int, default=10)
    args = parser.parse_args()

    adapter = ShoppingBenchAdapter(args.documents, args.queries, args.top_k)
    args.output.mkdir(parents=True, exist_ok=True)
    qrel_records = list(adapter.qrels())
    qrels = [record.__dict__ for record in qrel_records]
    (args.output / "qrels.json").write_text(
        json.dumps(qrels, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    summary: dict[str, dict[str, float]] = {}
    for level in GROUP_ORDER:
        corpus_dir = args.output / "corpora" / level.value
        documents = corpus_dir / "documents.jsonl"
        index = args.output / "indexes" / level.value
        run = args.output / "runs" / f"{level.value}.jsonl"
        adapter.render_documents(level, documents)
        adapter.build_index(documents, index)
        adapter.run_retrieval(index, run)
        query_results = evaluate_run(_read_jsonl(run), qrel_records)
        _write_jsonl(args.output / "metrics" / f"{level.value}.jsonl", query_results)
        summary[level.value] = mean_metrics(query_results)

    (args.output / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
