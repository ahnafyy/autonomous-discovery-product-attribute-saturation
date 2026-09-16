from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
import yaml

from paperkit.publication import render_project_metadata
from study.adapters.shoppingbench import ShoppingBenchAdapter
from study.attribute_saturation.analysis import paired_analysis
from study.attribute_saturation.evaluation import evaluate_run, query_metrics
from study.attribute_saturation.metrics import saturation_point
from study.run_shoppingbench_pilot import DEFAULT_CONFIG, load_config, run_pilot


def _write(path, rows):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))


def _inputs(tmp_path):
    documents, queries = tmp_path / "documents.jsonl", tmp_path / "queries.jsonl"
    products = [
        {
            "product_id": "target",
            "title": "coffee grinder",
            "brand": "BurrCo",
            "category": "coffee",
            "sku_options": {"1": {"color": "cobalt"}},
            "attributes": {"mechanism": ["conical"]},
            "description": "hand crank portable",
        },
        {"product_id": "other", "title": "tea kettle", "brand": "TeaCo"},
    ]
    products += [
        {"product_id": f"d{i}", "title": f"coffee grinder accessory {i}"} for i in range(12)
    ]
    _write(documents, [{"id": p["product_id"], "product": p} for p in products])
    _write(
        queries,
        [
            {"query": "cobalt conical", "reward": {"product_id": "target"}},
            {"query": "tea kettle", "reward": {"product_id": "other"}},
        ],
    )
    return documents, queries


def test_empty_affiliations_render_without_inventing_affiliation():
    result = render_project_metadata(Path(__file__).parents[1] / "project.yml")
    assert r"\newcommand{\PaperAuthors}{Khondoker Ahnaf Prio}" in result


@pytest.mark.parametrize(
    "rows",
    [
        [{"query_id": "1", "hits": []}, {"query_id": "1", "hits": []}],
        [{"query_id": "unjudged", "hits": []}],
        [],
        [{"query_id": "1", "hits": [None]}],
    ],
)
def test_invalid_run_cannot_silently_change_query_denominator(rows):
    from study.adapters.base import RelevanceRecord

    with pytest.raises(ValueError):
        evaluate_run(rows, [RelevanceRecord("1", "target")])


def test_duplicate_hits_cannot_inflate_recall():
    with pytest.raises(ValueError, match="Duplicate"):
        query_metrics(["target", "target"], {"target"})


def test_zero_quality_is_not_saturation():
    assert saturation_point({"a": 0, "b": 0}, ["a", "b"]) is None
    with pytest.raises(ValueError):
        saturation_point({"a": float("nan")}, ["a"])
    with pytest.raises(ValueError):
        saturation_point({"a": 1, "unobserved": 2}, ["a"])


def test_bootstrap_is_paired_and_retains_nonmonotone_curve():
    rows = [{"query_id": str(i), "metrics": {"recall@1": float(i % 2)}} for i in range(8)]
    zero = [{"query_id": str(i), "metrics": {"recall@1": 0.0}} for i in range(8)]
    args = {"seed": 42, "samples": 200, "targets": [0.95]}
    result = paired_analysis({"a": rows, "b": rows[::-1], "c": zero}, **args)
    assert result == paired_analysis({"a": rows, "b": rows[::-1], "c": zero}, **args)
    metrics = result["metrics"]["recall@1"]
    assert metrics["adjacent_marginal_value"][0]["ci95"] == [0.0, 0.0]
    assert metrics["adjacent_marginal_value"][1]["mean"] == -0.5
    assert metrics["saturation"]["k_star_95"]["level"] == "a"
    with pytest.raises(ValueError, match="identical unique query ids"):
        paired_analysis({"a": rows, "b": rows[:-1]}, **args)


def test_missing_target_and_existing_output_fail_without_partial_output(tmp_path):
    documents, queries = _inputs(tmp_path)
    _write(queries, [{"query": "missing", "reward": {"product_id": "absent"}}])
    output = tmp_path / "result"
    with pytest.raises(ValueError, match="missing 1 qrel"):
        run_pilot(documents, queries, output)
    assert not output.exists()
    assert not list(tmp_path.glob(".pilot-*"))
    output.mkdir()
    with pytest.raises(FileExistsError):
        run_pilot(documents, queries, output)
    assert documents.is_file()


def test_duplicate_products_are_rejected(tmp_path):
    documents, queries = _inputs(tmp_path)
    with documents.open("a") as stream:
        stream.write(
            json.dumps({"id": "target", "product": {"product_id": "target", "title": "duplicate"}})
            + "\n"
        )
    with pytest.raises(ValueError, match="Duplicate product"):
        list(ShoppingBenchAdapter(documents, queries).products())


def test_pilot_does_not_accept_ignored_settings(tmp_path):
    config = yaml.safe_load(DEFAULT_CONFIG.read_text())
    config["experiment"]["random_order_seeds"] = [42]
    path = tmp_path / "bad.yml"
    path.write_text(yaml.safe_dump(config))
    with pytest.raises(ValueError, match="does not implement"):
        load_config(path)
    with pytest.raises(ValueError, match="at least 10"):
        ShoppingBenchAdapter(Path("unused"), Path("unused"), top_k=5)


@pytest.mark.skipif(
    os.environ.get("RUN_BM25_INTEGRATION") != "1",
    reason="requires the experiment extra and Java 21; separate CI job",
)
def test_real_lucene_pilot_is_reproducible_and_ablates_indexed_fields(tmp_path):
    documents, queries = _inputs(tmp_path)
    config = yaml.safe_load(DEFAULT_CONFIG.read_text())
    config["experiment"]["bootstrap_samples"] = 100
    config_path = tmp_path / "config.yml"
    config_path.write_text(yaml.safe_dump(config))
    first, second = tmp_path / "first", tmp_path / "second"
    for output in (first, second):
        run_pilot(documents, queries, output, config_path=config_path)
    for name in ["summary.json", "analysis.json", "manifest.json", "representation-stats.json"]:
        assert (first / name).read_bytes() == (second / name).read_bytes()
    summary = json.loads((first / "summary.json").read_text())
    assert summary["minimum"]["recall@1"] == 0.5
    assert summary["core_specs"]["recall@1"] == 1.0
    run = [json.loads(line) for line in (first / "runs/minimum.jsonl").read_text().splitlines()]
    assert run[0]["hits"] == []  # Variant/spec text did not leak into the title-only index.
    manifest = json.loads((first / "manifest.json").read_text())
    assert manifest["config"]["bootstrap_samples"] == 100
    assert manifest["query_count"] == 2
    assert manifest["product_count"] == 14


def test_archived_pilot_matches_runs_and_package_analysis():
    import hashlib

    from product_attribute_saturation.analysis import run_analysis

    from study.adapters.base import RelevanceRecord
    from study.attribute_saturation.evaluation import mean_metrics

    evidence = (
        Path(__file__).parents[1] / "packages/python/src" / "product_attribute_saturation/pilot"
    )
    manifest = json.loads((evidence / "manifest.json").read_text())
    qrels = [RelevanceRecord(**row) for row in json.loads((evidence / "qrels.json").read_text())]
    summary = json.loads((evidence / "summary.json").read_text())
    for relative, digest in manifest["files"].items():
        path = evidence / relative
        if relative.startswith("corpora/"):
            continue  # Large corpora are regenerated from the pinned upstream source.
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
    for level, expected in summary.items():
        rows = [
            json.loads(line)
            for line in (evidence / "runs" / f"{level}.jsonl").read_text().splitlines()
        ]
        assert mean_metrics(evaluate_run(rows, qrels)) == expected
    result = run_analysis(manifest["config"]["seed"])
    assert result["pilot_summary"] == summary
    assert result["pilot_queries"] == len(qrels)
