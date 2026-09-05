from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence

from study.adapters.base import RelevanceRecord


def query_metrics(
    ranked_product_ids: Sequence[str], relevant_product_ids: set[str]
) -> dict[str, float]:
    """Compute binary-relevance metrics for one ranked product list."""
    relevant_ranks = [
        rank
        for rank, product_id in enumerate(ranked_product_ids, start=1)
        if product_id in relevant_product_ids
    ]
    first_rank = min(relevant_ranks, default=None)
    denominator = len(relevant_product_ids)

    metrics = {
        f"recall@{cutoff}": (
            sum(rank <= cutoff for rank in relevant_ranks) / denominator if denominator else 0.0
        )
        for cutoff in (1, 5, 10)
    }
    metrics["mrr"] = 1.0 / first_rank if first_rank else 0.0
    for cutoff in (5, 10):
        dcg = sum(1.0 / math.log2(rank + 1) for rank in relevant_ranks if rank <= cutoff)
        ideal_hits = min(denominator, cutoff)
        idcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_hits + 1))
        metrics[f"ndcg@{cutoff}"] = dcg / idcg if idcg else 0.0
    return metrics


def evaluate_run(
    run: Iterable[Mapping[str, object]], qrels: Iterable[RelevanceRecord]
) -> list[dict[str, object]]:
    """Return query-level metrics in run order for paired treatment analysis."""
    relevant: dict[str, set[str]] = {}
    for qrel in qrels:
        if qrel.relevance > 0:
            relevant.setdefault(qrel.query_id, set()).add(qrel.product_id)

    results = []
    for row in run:
        query_id = str(row["query_id"])
        hits = row.get("hits", [])
        if not isinstance(hits, list):
            raise ValueError(f"run row {query_id} has a non-list 'hits' field")
        ranked_ids = [str(hit["product_id"]) for hit in hits if isinstance(hit, dict)]
        results.append(
            {
                "query_id": query_id,
                "metrics": query_metrics(ranked_ids, relevant.get(query_id, set())),
            }
        )
    return results


def mean_metrics(rows: Iterable[Mapping[str, object]]) -> dict[str, float]:
    totals: dict[str, float] = {}
    count = 0
    for row in rows:
        metrics = row.get("metrics")
        if not isinstance(metrics, Mapping):
            raise ValueError("query-metric row is missing object field 'metrics'")
        count += 1
        for name, value in metrics.items():
            totals[str(name)] = totals.get(str(name), 0.0) + float(value)
    return {name: total / count for name, total in sorted(totals.items())} if count else {}
