# Experiment Plan

## Objective

Measure the marginal discovery value of progressively richer, truthful product representations and determine whether product discovery exhibits saturation or degradation before every available attribute is exposed.

## Stage 0 — Deterministic pilot

Use ShoppingBench only. Render five representation levels from the same product records, rebuild one BM25/Pyserini index per level, and run the same query set against every index.

Required outputs:

- paired query-level results for every representation;
- Recall@K, MRR, and nDCG@K;
- marginal attribute value between adjacent levels;
- `k*_90`, `k*_95`, and `k*_99`;
- bootstrap confidence intervals;
- per-category summaries;
- explicit-attribute-query versus broader-query summaries.

Exit criterion: a reproducible signal or a well-explained null result. Do not add LLM calls before this stage is understood.

## Stage 1 — Ordering controls

For products with enough available attributes, compare:

- schema-ordered enrichment;
- repeated random attribute permutations;
- category-priority ordering.

The purpose is to determine whether saturation is an information-volume effect or merely the result of adding one high-value field early.

## Stage 2 — Dense retrieval

Hold the corpus, queries, and representation levels constant and replace lexical retrieval with one fixed embedding model. Recompute the same metrics and saturation statistics.

Exit criterion: determine whether saturation behavior is architecture-specific.

## Stage 3 — LLM reranking / selection

Freeze a candidate set from a retrieval stage and expose representation variants only to the LLM ranking or selection step. This isolates model-use saturation from retrieval saturation.

Start with one model. Add additional model classes only after the experiment is stable.

Track:

- ranking quality;
- correct-product selection rate;
- prompt/input tokens;
- latency and inference cost where available;
- truncation events.

Any degradation result must be rerun without truncation before it can be interpreted as overload.

## Stage 4 — WebShop replication

Reimplement only the benchmark adapter and representation mapping. Preserve the same metric definitions and saturation analysis.

The replication target is the qualitative finding, not identical numerical thresholds. If ShoppingBench and WebShop disagree, category mix, task construction, and available attribute distributions become first-class analysis rather than reasons to hide the discrepancy.

## Stage 5 — Minimum sufficient representation

Only after saturation is established, compare subset policies:

- all applicable attributes;
- random subsets;
- globally common attributes;
- category-priority subsets;
- query-aware subsets.

For product or category context `x`, define the minimum sufficient representation as the smallest subset whose expected discovery score reaches a chosen fraction of the complete-representation score.

## Representation contract

Every benchmark adapter must emit a canonical product record with source provenance for each field. A representation treatment may hide fields, but it may not change the underlying product facts.

Initial semantic groups:

- `minimum`: required/basic discovery fields available in the benchmark;
- `identity`: category and stable identifiers;
- `variants`: color, size, material, style, and analogous variant dimensions;
- `core_specs`: category-specific specifications relevant to comparison;
- `all_applicable`: all truthful fields available for the product and permitted by the mapping.

The exact schema mapping must be versioned. Protocol names are implementation references, not treatment labels in the scientific result.

## Evaluation contract

Given a query set `Q`, a representation level `k`, and retrieval architecture `a`, produce query-level scores `r(q, k, a)` before aggregation.

Primary aggregates:

- Recall@1/5/10;
- MRR;
- nDCG@5/10;
- benchmark-native success metric where appropriate.

Derived measures:

- `MAV(k) = R(k) - R(k-1)`;
- `k*_p = min k : R(k) >= p * max_j R(j)` for p in {0.90, 0.95, 0.99};
- negative marginal value rate;
- representation efficiency per field and per token.

Use paired bootstrap intervals over queries. Random-order experiments require repeated seeds and uncertainty across both queries and permutations.

## Threats to validity to control explicitly

### Query leakage

If a benchmark query is constructed directly from an attribute, removing that field creates an expected penalty. Analyze those queries separately.

### Hidden fields

Ablated information must not remain visible through title rewriting, metadata, retrieval payloads, model tools, or cached candidate text.

### Token truncation

LLM degradation under larger representations is uninterpretable if the relevant information was simply truncated.

### Unequal candidate sets

When testing LLM ranking, keep candidate sets fixed across representation treatments unless retrieval itself is the variable under test.

### Attribute availability bias

Products with many attributes may differ systematically from sparse products. Report attribute-count distributions and stratify when necessary.

### Benchmark dependence

ShoppingBench is the development benchmark; WebShop is the replication benchmark.

## Compute discipline

The experiment escalates only after each cheaper layer provides evidence worth testing at the next layer:

```text
BM25 -> ordering controls -> dense retrieval -> one LLM -> model sweep -> replication
```

This is intentional. The paper should spend model inference only on hypotheses that survived deterministic retrieval experiments.

## Publication decision tree

If performance saturates early, characterize the saturation boundary and minimum sufficient representation.

If performance eventually degrades, distinguish genuine overload from truncation and benchmark artifacts.

If performance remains monotonic, report the continued marginal value of catalog completeness and the conditions under which it persists.

If results differ materially across architectures or benchmarks, make that interaction the main finding rather than averaging it away.
