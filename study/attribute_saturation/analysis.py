"""Paired, query-resampled uncertainty for ordered representation treatments."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from study.attribute_saturation.metrics import saturation_point


def paired_analysis(
    rows_by_level: Mapping[str, Sequence[dict]],
    *,
    seed: int,
    samples: int,
    targets: Sequence[float],
) -> dict:
    import numpy as np

    if samples < 1:
        raise ValueError("bootstrap_samples must be positive")
    levels = list(rows_by_level)
    ids = [str(row["query_id"]) for row in rows_by_level[levels[0]]]
    if not ids or len(set(ids)) != len(ids):
        raise ValueError("Expected non-empty unique query ids")
    metrics = sorted(rows_by_level[levels[0]][0]["metrics"])
    matrices = []
    for level in levels:
        rows = rows_by_level[level]
        by_id = {str(row["query_id"]): row["metrics"] for row in rows}
        if len(by_id) != len(rows) or set(by_id) != set(ids):
            raise ValueError("Treatments must contain identical unique query ids")
        if any(set(values) != set(metrics) for values in by_id.values()):
            raise ValueError("Treatments must contain identical metrics")
        matrices.append([[by_id[qid][metric] for metric in metrics] for qid in ids])
    values = np.asarray(matrices, dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("Non-finite query metrics")
    point = values.mean(axis=1)
    boot = np.empty((samples, len(levels), len(metrics)))
    rng = np.random.default_rng(seed)
    for start in range(0, samples, 64):
        stop = min(start + 64, samples)
        indices = rng.integers(0, len(ids), size=(stop - start, len(ids)))
        # Every level and metric receives the same query resample.
        boot[start:stop] = values[:, indices, :].mean(axis=2).transpose(1, 0, 2)

    def interval(array):
        return np.quantile(array, [0.025, 0.975]).tolist()

    result = {
        "query_count": len(ids),
        "bootstrap_samples": samples,
        "seed": seed,
        "interval": "pointwise paired query bootstrap, percentile 95%",
        "metrics": {},
    }
    for m, metric in enumerate(metrics):
        scores = dict(zip(levels, point[:, m].tolist(), strict=True))
        deltas = np.diff(values[:, :, m], axis=0)
        saturation = {}
        for target in targets:
            key = f"k_star_{round(target * 100)}"
            selected = [
                saturation_point(dict(zip(levels, row, strict=True)), levels, target)
                for row in boot[:, :, m]
            ]
            valid = [levels.index(level) for level in selected if level is not None]
            # k* is discrete: report ordered endpoint levels and its full bootstrap mass.
            bounds = (
                np.quantile(valid, [0.025, 0.975], method="nearest").astype(int) if valid else None
            )
            saturation[key] = {
                "level": saturation_point(scores, levels, target),
                "ci95_levels": [levels[i] for i in bounds] if bounds is not None else None,
                "bootstrap_counts": {level: selected.count(level) for level in [*levels, None]},
            }
            saturation[key]["bootstrap_counts"]["undefined"] = saturation[key][
                "bootstrap_counts"
            ].pop(None)
        result["metrics"][metric] = {
            "levels": {
                level: {"mean": scores[level], "ci95": interval(boot[:, i, m])}
                for i, level in enumerate(levels)
            },
            "adjacent_marginal_value": [
                {
                    "from": levels[i],
                    "to": levels[i + 1],
                    "mean": float(point[i + 1, m] - point[i, m]),
                    "ci95": interval(boot[:, i + 1, m] - boot[:, i, m]),
                    "queries_worse": int((deltas[i] < 0).sum()),
                    "queries_better": int((deltas[i] > 0).sum()),
                }
                for i in range(len(levels) - 1)
            ],
            "saturation": saturation,
        }
    return result
