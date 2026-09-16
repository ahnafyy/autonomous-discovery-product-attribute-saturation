# Research Question

## Phenomenon

External product-discovery systems increasingly consume merchant-provided product representations rather than querying an authoritative catalog for every discovery decision. Product schemas permit progressively richer representations: identity, category, variants, specifications, identifiers, media, and other structured attributes. Existing work shows that richer attributes can improve product retrieval, but it is not clear whether discovery quality improves monotonically as every legitimate product attribute is added, whether performance saturates, or whether excessive-but-truthful product information can sometimes reduce retrieval or model selection quality.

## Research Question

For a fixed product corpus and fixed shopping queries, how does external product-discovery performance change as each product is represented with progressively richer sets of truthful, schema-valid attributes, and what is the minimum sufficient representation that preserves nearly all of the performance of the complete representation?

## Minimal Benchmark

The cheapest decisive benchmark is ShoppingBench with its existing BM25/Pyserini retrieval path. For the same products and queries, construct several product-document variants from attributes already present in the source data, rebuild one search index per representation level, and compare paired retrieval metrics.

The initial representation levels are `minimum`, `identity`, `variants`, `core_specs`, and `all_applicable`. Exact fields are determined by benchmark availability and a versioned commerce-schema mapping rather than by fabricated attribute counts.

The first pilot does not require an LLM. A measurable saturation or degradation effect in lexical retrieval is enough to justify expanding to dense retrieval and LLM reranking. If no effect exists there, the representation generator and benchmark controls can be checked before paying for model inference.

## Comparisons And Controls

- Complete available representation: empirical upper-completeness baseline.
- Minimum valid representation: lower-information baseline.
- Schema-ordered enrichment: operationally realistic treatment.
- Randomized attribute-order enrichment: distinguishes quantity effects from one unusually valuable field.
- Query/category-aware subset: later method for testing minimum sufficient representations.
- Fixed query set, product universe, qrels, retrieval settings, and random seeds across treatments.
- Separate analysis of queries that explicitly mention an ablated attribute from broader semantic queries.

## Contribution Hypothesis

The intended contribution is an empirical characterization, not a presupposed algorithmic win. We hypothesize that legitimate product enrichment exhibits diminishing marginal discovery value and that the minimum sufficient representation varies by category, query complexity, retrieval architecture, and model. If supported, a secondary contribution is a benchmark-independent representation-ablation harness and a method for selecting compact product representations that retain a target fraction of full-representation performance.

The reusable artifacts should include benchmark adapters for ShoppingBench and WebShop, versioned product-schema mappings, deterministic representation generation, paired evaluation code, and saturation metrics such as `k*_90`, `k*_95`, and `k*_99`.

## Falsifiers

- Discovery quality improves materially and monotonically through `all_applicable` across both benchmarks and retrieval architectures; there is no practically useful saturation point.
- Apparent saturation disappears when attribute order is randomized, showing that the original effect was caused by a particular field ordering rather than representation richness.
- Apparent degradation disappears after controlling for truncation or token limits, showing that the result was a harness artifact rather than an information-overload effect.
- Results replicate only on ShoppingBench but not WebShop, indicating benchmark/task-construction dependence.
- A compact representation performs well only because the benchmark queries were generated from the same attributes used to select the subset.

## Non-Goals

- Claiming a universal optimal number of product attributes.
- Fabricating attributes that are not present in the underlying benchmark product data.
- Comparing proprietary commerce protocols as the primary research question.
- Measuring transaction-time price or inventory correctness.
- Personalization or collaborative recommendation in the first paper.
- Optimizing product copy or adversarially rewriting descriptions to manipulate rankings.
- Building a production merchant feed service before the empirical phenomenon is established.
