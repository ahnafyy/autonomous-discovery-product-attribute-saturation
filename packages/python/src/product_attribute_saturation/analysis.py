from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ExpectedDistinct:
    numerator: int
    denominator: int
    value: float

    def as_dict(self) -> dict[str, int | float]:
        return asdict(self)


def expected_distinct_choices(options: int, choices: int) -> ExpectedDistinct:
    """Return the exact expected occupied-option count for uniform independent choices."""
    if options <= 0 or choices < 0:
        raise ValueError("options must be positive and choices must be non-negative")
    exact = options * (1 - Fraction(options - 1, options) ** choices)
    return ExpectedDistinct(
        numerator=exact.numerator,
        denominator=exact.denominator,
        value=float(exact),
    )


def run_analysis(seed: int) -> dict[str, Any]:
    """Load the archived real-data pilot; occupancy is only a conformance fixture."""
    evidence = Path(__file__).parent / "pilot"
    summary = json.loads((evidence / "summary.json").read_text())
    manifest = json.loads((evidence / "manifest.json").read_text())
    analysis = json.loads((evidence / "analysis.json").read_text())
    if seed != manifest["config"]["seed"]:
        raise ValueError("Configured seed differs from archived pilot; regenerate evidence")
    return {
        "status": "Reduced-corpus BM25 pilot; not a full-benchmark or LLM result",
        "representation_levels": len(summary),
        "random_seed": seed,
        "pilot_products": manifest["product_count"],
        "pilot_queries": manifest["query_count"],
        "core_specs_recall": summary["core_specs"]["recall@10"],
        "full_minus_core_recall": (
            summary["all_applicable"]["recall@10"] - summary["core_specs"]["recall@10"]
        ),
        "pilot_summary": summary,
        "pilot_analysis": analysis,
    }
