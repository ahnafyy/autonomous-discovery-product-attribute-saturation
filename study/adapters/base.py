from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Protocol


@dataclass(frozen=True)
class QueryRecord:
    query_id: str
    text: str


@dataclass(frozen=True)
class ProductRecord:
    product_id: str
    fields: Mapping[str, object]


class BenchmarkAdapter(Protocol):
    """Minimal contract required by the saturation experiment."""

    name: str

    def products(self) -> Iterable[ProductRecord]: ...

    def queries(self) -> Iterable[QueryRecord]: ...

    def qrels_path(self) -> Path: ...

    def build_index(self, rendered_documents: Path, output_dir: Path) -> None: ...

    def run_retrieval(self, index_dir: Path, output_path: Path) -> None: ...
