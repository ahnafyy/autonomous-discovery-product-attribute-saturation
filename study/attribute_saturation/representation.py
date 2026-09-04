from __future__ import annotations

from enum import StrEnum
from typing import Any, Mapping


class RepresentationLevel(StrEnum):
    MINIMUM = "minimum"
    IDENTITY = "identity"
    VARIANTS = "variants"
    CORE_SPECS = "core_specs"
    ALL_APPLICABLE = "all_applicable"


GROUP_ORDER = (
    RepresentationLevel.MINIMUM,
    RepresentationLevel.IDENTITY,
    RepresentationLevel.VARIANTS,
    RepresentationLevel.CORE_SPECS,
    RepresentationLevel.ALL_APPLICABLE,
)


def render_product(
    product: Mapping[str, Any],
    groups: Mapping[str, tuple[str, ...]],
    level: RepresentationLevel,
) -> dict[str, Any]:
    """Return a deterministic ablated product view up to ``level``.

    ``groups`` is benchmark/schema-specific. This function deliberately does not
    infer missing fields or generate product facts; it only selects fields that
    already exist in ``product``.
    """

    selected: dict[str, Any] = {}
    for group in GROUP_ORDER:
        for field in groups.get(group.value, ()):  # preserve declared order
            if field in product and product[field] not in (None, "", [], {}):
                selected[field] = product[field]
        if group == level:
            break
    return selected
