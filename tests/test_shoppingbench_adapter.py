import gzip
import json
from pathlib import Path
from typing import TextIO

from study.adapters.shoppingbench import ShoppingBenchAdapter, render_document
from study.attribute_saturation.representation import RepresentationLevel


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    def write(stream: TextIO) -> None:
        for row in rows:
            stream.write(json.dumps(row) + "\n")

    if path.suffix == ".gz":
        with gzip.open(path, "wt", encoding="utf-8") as stream:
            write(stream)
        return
    with path.open("w", encoding="utf-8") as stream:
        write(stream)


def test_adapter_loads_published_shapes_and_derives_qrels(tmp_path: Path) -> None:
    documents = tmp_path / "documents.jsonl.gz"
    queries = tmp_path / "queries.jsonl"
    _write_jsonl(
        documents,
        [{"id": "p1", "contents": "ignored", "product": {"product_id": "p1", "title": "TV"}}],
    )
    _write_jsonl(queries, [{"query": "a television", "reward": {"product_id": "p1"}}])

    adapter = ShoppingBenchAdapter(documents, queries)

    assert list(adapter.products())[0].product_id == "p1"
    assert list(adapter.queries())[0].text == "a television"
    assert list(adapter.qrels())[0].product_id == "p1"


def test_render_document_is_cumulative_and_deterministic() -> None:
    product = {
        "product_id": "p1",
        "title": "Trail shoe",
        "brand": "Example",
        "category": "shoes",
        "sku_options": {"2": {"size": "10"}, "1": {"color": "blue"}},
        "attributes": {"waterproof": ["yes"], "material": ["mesh"]},
        "description": "Long description",
    }

    variants = render_document(product, RepresentationLevel.VARIANTS)
    complete = render_document(product, RepresentationLevel.ALL_APPLICABLE)

    assert variants["product"] == {
        "title": "Trail shoe",
        "brand": "Example",
        "category": "shoes",
        "sku_options": {"2": {"size": "10"}, "1": {"color": "blue"}},
    }
    assert variants["contents"].splitlines() == ["Trail shoe", "Example", "shoes", "blue", "10"]
    assert "Long description" not in variants["contents"]
    assert "Long description" in complete["contents"]


def test_render_documents_emits_pyserini_json_collection(tmp_path: Path) -> None:
    source = tmp_path / "source.jsonl"
    queries = tmp_path / "queries.jsonl"
    output = tmp_path / "corpus" / "documents.jsonl"
    _write_jsonl(
        source,
        [{"id": "p1", "product": {"product_id": "p1", "title": "Coffee grinder"}}],
    )
    _write_jsonl(queries, [{"query": "grinder", "reward": {"product_id": "p1"}}])

    ShoppingBenchAdapter(source, queries).render_documents(RepresentationLevel.MINIMUM, output)

    assert json.loads(output.read_text()) == {
        "contents": "Coffee grinder",
        "id": "p1",
        "product": {"title": "Coffee grinder"},
    }
