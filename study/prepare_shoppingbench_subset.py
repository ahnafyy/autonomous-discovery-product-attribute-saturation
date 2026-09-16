"""Deterministic engineering pilot subset: all qrel targets plus hash-sampled distractors.

This changes corpus difficulty; it is not the full benchmark or a random query sample.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

from study.adapters.shoppingbench import ShoppingBenchAdapter
from study.run_shoppingbench_pilot import _json, _sha256


def prepare_subset(
    documents: Path, queries: Path, output: Path, *, divisor: int = 256, seed: int = 20260903
) -> None:
    if divisor < 1:
        raise ValueError("divisor must be positive")
    if output.exists():
        raise FileExistsError(output)
    adapter = ShoppingBenchAdapter(documents, queries)
    if not list(adapter.queries()):
        raise ValueError("Empty query set")
    targets = {row.product_id for row in adapter.qrels()}
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".subset-", dir=output.parent))
    seen = set()
    total = kept = 0
    try:
        with (staging / "documents.jsonl").open("w", encoding="utf-8") as stream:
            for product in adapter.products():
                total += 1
                digest = hashlib.sha256(f"{seed}:{product.product_id}".encode()).digest()
                if product.product_id in targets or int.from_bytes(digest, "big") % divisor == 0:
                    kept += 1
                    seen.add(product.product_id)
                    stream.write(
                        json.dumps(
                            {"id": product.product_id, "product": product.fields},
                            sort_keys=True,
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
        if not targets <= seen:
            raise ValueError(f"Missing {len(targets - seen)} target products")
        shutil.copyfile(queries, staging / "queries.jsonl")
        _json(
            staging / "selection.json",
            {
                "method": "all target products plus SHA256(seed:product_id) mod divisor == 0",
                "seed": seed,
                "divisor": divisor,
                "source_products": total,
                "selected_products": kept,
                "target_products": len(targets),
                "source_sha256": {"documents": _sha256(documents), "queries": _sha256(queries)},
                "selected_sha256": _sha256(staging / "documents.jsonl"),
                "evidence_boundary": "Engineering pilot only; target-enriched reduced corpus. "
                "Do not interpret as full-corpus benchmark performance.",
            },
        )
        staging.rename(output)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--documents", type=Path, required=True)
    parser.add_argument("--queries", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--divisor", type=int, default=256)
    parser.add_argument("--seed", type=int, default=20260903)
    args = parser.parse_args()
    prepare_subset(args.documents, args.queries, args.output, divisor=args.divisor, seed=args.seed)


if __name__ == "__main__":
    main()
