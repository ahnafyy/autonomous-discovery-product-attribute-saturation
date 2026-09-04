from __future__ import annotations

from collections.abc import Mapping, Sequence


def marginal_attribute_value(scores: Sequence[float]) -> list[float]:
    """Return adjacent marginal gains for an ordered score sequence."""
    if len(scores) < 2:
        return []
    return [current - previous for previous, current in zip(scores, scores[1:])]


def saturation_point(
    scores_by_level: Mapping[str, float],
    ordered_levels: Sequence[str],
    target_fraction: float = 0.95,
) -> str | None:
    """Return the earliest level reaching ``target_fraction`` of the best score."""
    if not 0 < target_fraction <= 1:
        raise ValueError("target_fraction must be in (0, 1]")
    if not scores_by_level:
        return None

    best = max(scores_by_level.values())
    threshold = best * target_fraction
    for level in ordered_levels:
        score = scores_by_level.get(level)
        if score is not None and score >= threshold:
            return level
    return None
