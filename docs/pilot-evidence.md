# ShoppingBench reduced-corpus pilot

This is an engineering pilot, not full-benchmark performance. Its numerical observations
are registered as `PILOT-BM25-001` and `PILOT-BM25-002`. All query-level runs, metrics,
bootstrap outputs, and provenance are archived in
[`packages/python/src/product_attribute_saturation/pilot`](../packages/python/src/product_attribute_saturation/pilot).
The Python analysis reads this archive; `paperkit build` generates the paper/site values.
Tests recompute metrics from archived rankings and verify archived file hashes.

## Provenance and reproduction

The upstream source is [ShoppingBench commit 2f4d132](https://github.com/yjwjy/ShoppingBench/tree/2f4d132500d4962d7ee3143e103b93499c82aca0).
Its `resources/documents.jsonl.gz` is a Git LFS object with SHA-256
`a0ba9a8618ce72a7b383a6de31acf6e5bf138873da0d13ad8a1a6b0271e8e9d1`.
The query file is `data/synthesize_product_test.jsonl`; its digest is in `selection.json`.
Data and benchmark code originate from the upstream Apache-2.0 project.

Install Git LFS and fetch that pinned checkout, including the document object, then run:

```bash
python -m study.prepare_shoppingbench_subset \
  --documents /path/to/ShoppingBench/resources/documents.jsonl.gz \
  --queries /path/to/ShoppingBench/data/synthesize_product_test.jsonl \
  --output runs/subset-input
python -m study.run_shoppingbench_pilot \
  --documents runs/subset-input/documents.jsonl \
  --queries runs/subset-input/queries.jsonl \
  --output runs/subset-pilot
```

The selection keeps all target products, plus products whose
`SHA256("20260903:" + product_id) mod 256 == 0`. This is deterministic and selects
11,019 products from 2,746,368 source products, including all 250 targets. All 250
single-product queries are retained. Input IDs, titles, target membership, and uniqueness
are checked. Every Lucene index must contain the exact expected number of documents.
Two successful runs had identical rankings, metrics, analysis, and manifests.

For the full experiment, pass the original complete corpus directly to the runner.
The archived manifest records corpora hashes; large corpora and binary indexes are not
bundled, but can be regenerated. All non-corpus files listed in the manifest are bundled.
Lucene index bytes are not a determinism contract; query results and statistical outputs are.

## Interpretation

The final enrichment step adds short descriptions, descriptions, price, sold count, and
service. The group-order pilot is conditional on that exact treatment, not an isolated
attribute-count effect. `all_applicable` means all mapped textual fields, excluding IDs,
shop IDs, URLs, and images. This is not a schema-conformance certification.

Rendering preserves existing values in deterministic order and excludes upstream
`contents` so ablated facts cannot leak through that pre-rendered field. Nested keys are
not added to the indexed text, matching the initial value-only pilot convention. Nested
SKU delivery fields can remain within the variant group. Titles, specifications, and
descriptions can repeat facts; enrichment does not guarantee independent new information.
The treatment map and renderer version are recorded in the manifest.

MRR is truncated at the retrieved depth (`top_k`, default 10), not unbounded reciprocal
rank. Qrels identify the benchmark target, not every acceptable alternative. Thus these
are target-product retrieval scores. The 2,000 percentile bootstrap resamples use the
same query indices for every treatment. Intervals are pointwise and conditional on the
fixed reduced corpus; they do not capture corpus-sampling or ordering uncertainty.
Saturation is measured against the best observed level, which need not be the richest.
All-zero curves are undefined. Discrete saturation intervals include bootstrap level
counts and must not be interpreted as an equivalence or generalization guarantee.

## Next experiment

Run the same config against the full corpus before extrapolating these observations.
Then add seeded random field-order and length controls, retaining identical queries and
candidates. Stratify using the benchmark's requested-field annotations without exposing
those annotations to the retriever. Dense retrieval and LLM selection remain later stages;
no paid APIs were called for this pilot.
