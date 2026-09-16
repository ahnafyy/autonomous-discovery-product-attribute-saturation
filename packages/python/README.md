# Product attribute saturation

This package ships the archived, reproducible ShoppingBench reduced-corpus BM25 pilot.
`product_attribute_saturation.analysis.run_analysis(seed=20260903)` loads its verified
summaries for the paper/site pipeline. Raw rankings, per-query metrics, bootstrap outputs,
and provenance live in `product_attribute_saturation/pilot/`.

These are reduced-corpus lexical-retrieval observations, not full-benchmark or LLM results.
See the repository's `docs/pilot-evidence.md` for reproduction and limitations.

`expected_distinct_choices` remains only as the inherited cross-language infrastructure
conformance fixture. It is not a result of this study. Registry release remains disabled.
