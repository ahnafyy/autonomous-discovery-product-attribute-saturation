from __future__ import annotations

import gzip
import json
import shutil
import subprocess
import sys
from collections.abc import Iterable, Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any, TextIO

from study.adapters.base import ProductRecord, QueryRecord, RelevanceRecord
from study.attribute_saturation.representation import RepresentationLevel, render_product

SHOPPINGBENCH_GROUPS: Mapping[str, tuple[str, ...]] = {
    "minimum": ("title",),
    "identity": ("brand", "category"),
    "variants": ("sku_options",),
    "core_specs": ("attributes", "specification"),
    "all_applicable": ("short_description", "description", "price", "sold_count", "service"),
}


@contextmanager
def _open_text(path: Path) -> Iterator[TextIO]:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            yield stream
    else:
        with path.open(encoding="utf-8") as stream:
            yield stream


def _jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with _open_text(path) as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: expected a JSON object")
            yield value


def _text_values(value: object) -> Iterable[str]:
    """Flatten a JSON value in stable order without adding absent product facts."""
    if isinstance(value, Mapping):
        for key in sorted(value, key=str):
            yield from _text_values(value[key])
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _text_values(item)
    elif value is not None and not isinstance(value, bool):
        text = str(value).strip()
        if text:
            yield text


def render_document(product: Mapping[str, Any], level: RepresentationLevel) -> dict[str, Any]:
    rendered = render_product(product, SHOPPINGBENCH_GROUPS, level)
    contents = "\n".join(
        text
        for field in rendered.values()
        for text in _text_values(field)
    )
    return {
        "id": str(product["product_id"]),
        "contents": contents,
        "product": rendered,
    }


class ShoppingBenchAdapter:
    """Adapter for ShoppingBench's published processed corpus and product tasks."""

    name = "shoppingbench"

    def __init__(self, documents_path: Path, queries_path: Path, top_k: int = 10) -> None:
        self.documents_path = documents_path
        self.queries_path = queries_path
        self.top_k = top_k

    def products(self) -> Iterable[ProductRecord]:
        for document in _jsonl(self.documents_path):
            product = document.get("product")
            if not isinstance(product, dict):
                raise ValueError("ShoppingBench document is missing object field 'product'")
            product_id = str(product.get("product_id", document.get("id", "")))
            if not product_id:
                raise ValueError("ShoppingBench document is missing a product id")
            fields = dict(product)
            fields["product_id"] = product_id
            yield ProductRecord(product_id=product_id, fields=fields)

    def queries(self) -> Iterable[QueryRecord]:
        for index, row in enumerate(_jsonl(self.queries_path), start=1):
            query = row.get("query")
            if not isinstance(query, str) or not query.strip():
                raise ValueError(f"ShoppingBench query row {index} has no query text")
            yield QueryRecord(query_id=str(index), text=query.strip())

    def qrels(self) -> Iterable[RelevanceRecord]:
        for index, row in enumerate(_jsonl(self.queries_path), start=1):
            reward = row.get("reward")
            if not isinstance(reward, dict) or "product_id" not in reward:
                raise ValueError(f"ShoppingBench query row {index} has no reward.product_id")
            yield RelevanceRecord(str(index), str(reward["product_id"]))

    def render_documents(self, level: RepresentationLevel, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8", newline="\n") as stream:
            for record in self.products():
                document = render_document(record.fields, level)
                stream.write(json.dumps(document, sort_keys=True, ensure_ascii=False) + "\n")

    def build_index(self, rendered_documents: Path, output_dir: Path) -> None:
        if output_dir.exists():
            shutil.rmtree(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pyserini.index.lucene",
                "--collection",
                "JsonCollection",
                "--input",
                str(rendered_documents.parent),
                "--index",
                str(output_dir),
                "--generator",
                "DefaultLuceneDocumentGenerator",
                "--threads",
                "1",
                "--storeRaw",
            ],
            check=True,
        )

    def run_retrieval(self, index_dir: Path, output_path: Path) -> None:
        try:
            from pyserini.search.lucene import LuceneSearcher
        except ImportError as error:  # pragma: no cover - depends on optional Java stack
            raise RuntimeError("install the 'experiment' extra to run Pyserini") from error

        searcher = LuceneSearcher(str(index_dir))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8", newline="\n") as stream:
            for query in self.queries():
                hits = searcher.search(query.text, k=self.top_k, remove_dups=True)
                row = {
                    "query_id": query.query_id,
                    "query": query.text,
                    "hits": [
                        {"product_id": hit.docid, "rank": rank, "score": hit.score}
                        for rank, hit in enumerate(hits, start=1)
                    ],
                }
                stream.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
