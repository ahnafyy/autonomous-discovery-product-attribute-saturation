import pytest

from study.attribute_saturation.metrics import marginal_attribute_value, saturation_point
from study.attribute_saturation.representation import RepresentationLevel, render_product


def test_render_product_is_monotonic_by_declared_groups() -> None:
    product = {
        "title": "Example TV",
        "brand": "Example",
        "category": "television",
        "color": "black",
        "refresh_rate_hz": 120,
        "weight_lb": 42,
    }
    groups = {
        "minimum": ("title", "brand"),
        "identity": ("category",),
        "variants": ("color",),
        "core_specs": ("refresh_rate_hz",),
        "all_applicable": ("weight_lb",),
    }

    minimum = render_product(product, groups, RepresentationLevel.MINIMUM)
    core_specs = render_product(product, groups, RepresentationLevel.CORE_SPECS)

    assert minimum == {"title": "Example TV", "brand": "Example"}
    assert set(minimum).issubset(core_specs)
    assert "weight_lb" not in core_specs


def test_marginal_attribute_value() -> None:
    assert marginal_attribute_value([0.5, 0.7, 0.72]) == pytest.approx([0.2, 0.02])


def test_saturation_point_uses_best_observed_score() -> None:
    scores = {
        "minimum": 0.60,
        "identity": 0.80,
        "variants": 0.94,
        "core_specs": 0.99,
        "all_applicable": 1.00,
    }
    levels = ["minimum", "identity", "variants", "core_specs", "all_applicable"]

    assert saturation_point(scores, levels, 0.95) == "core_specs"
