"""Core primitives for product-attribute saturation experiments."""

from .metrics import marginal_attribute_value, saturation_point
from .representation import RepresentationLevel, render_product

__all__ = [
    "RepresentationLevel",
    "marginal_attribute_value",
    "render_product",
    "saturation_point",
]
