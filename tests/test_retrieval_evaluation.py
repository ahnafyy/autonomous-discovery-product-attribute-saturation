import pytest

from study.adapters.base import RelevanceRecord
from study.attribute_saturation.evaluation import evaluate_run, mean_metrics, query_metrics


def test_query_metrics_uses_binary_relevance_rank() -> None:
    metrics = query_metrics(["wrong", "target", "other"], {"target"})

    assert metrics["recall@1"] == 0.0
    assert metrics["recall@5"] == 1.0
    assert metrics["mrr"] == 0.5
    assert metrics["ndcg@5"] == pytest.approx(1 / 1.584962500721156)


def test_evaluate_run_preserves_query_level_pairs_and_aggregates() -> None:
    run = [
        {"query_id": "1", "hits": [{"product_id": "p1"}]},
        {"query_id": "2", "hits": [{"product_id": "wrong"}]},
    ]
    qrels = [RelevanceRecord("1", "p1"), RelevanceRecord("2", "p2")]

    rows = evaluate_run(run, qrels)
    aggregate = mean_metrics(rows)

    assert [row["query_id"] for row in rows] == ["1", "2"]
    assert aggregate["recall@1"] == 0.5
    assert aggregate["mrr"] == 0.5
