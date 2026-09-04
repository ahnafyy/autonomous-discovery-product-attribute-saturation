# Autonomous Discovery Product Attribute Saturation

Research repository for **How Much Product Data Is Enough? Measuring Attribute Saturation in LLM-Based Product Discovery**.

The study asks a narrow empirical question: as a merchant exposes progressively richer, truthful product data to an external discovery system, when do additional attributes stop improving retrieval or selection quality? We also test whether additional valid attributes can ever reduce performance.

The goal is not to prove that richer catalogs are good or bad. The goal is to measure the marginal discovery value of product information and identify the minimum sufficient representation under different retrieval architectures, models, query types, and product categories.

## Research questions

**RQ1 — Saturation.** How much valid product information is required before additional attributes provide negligible improvement in discovery quality?

**RQ2 — Overload.** Can adding additional truthful, schema-valid product attributes reduce retrieval or selection quality?

**RQ3 — Heterogeneity.** How does the saturation point vary by product category, query complexity, retrieval architecture, and model?

**RQ4 — Selection.** Can a smaller, intelligently selected subset of attributes preserve nearly all of the discovery value of the complete representation?

## Core measurement

For a product representation level `k`, let `R(k)` be retrieval or selection quality. The marginal value of another enrichment step is

```text
MAV(k) = R(k) - R(k - 1)
```

The primary saturation statistic is the smallest representation that retains a target fraction of the best observed performance:

```text
k*_95 = min k such that R(k) >= 0.95 * R(max)
```

We will also report 90% and 99% thresholds, negative marginal-value events, token/field efficiency, and uncertainty intervals.

## Experimental strategy

ShoppingBench is the primary benchmark because it provides a large real-product corpus, grounded shopping tasks, evaluation tooling, and a rebuildable Pyserini/Lucene search index. WebShop is the independent replication benchmark. The first milestone intentionally uses only ShoppingBench and BM25 so the existence of a saturation signal can be tested before spending money on LLM inference.

Product representations are derived only from attributes that exist in the benchmark and map to a legitimate commerce product schema. We will not invent arbitrary filler attributes or vary the product facts themselves. The initial schema lens is the OpenAI product-feed specification; UCP is a secondary mapping used to test whether conclusions depend on one representation convention.

The experiment separates retrieval from model decision-making. The planned sequence is BM25 lexical retrieval, dense semantic retrieval, then LLM reranking or selection over a fixed candidate set. That separation lets us distinguish retrieval saturation from LLM reasoning saturation.

## Representation treatments

The exact fields depend on what each benchmark product actually contains. The initial treatment family is:

| Level | Representation |
| --- | --- |
| `minimum` | Minimum valid discovery representation available in the benchmark |
| `identity` | Minimum plus category and stable identity fields |
| `variants` | Identity plus variant-defining attributes such as color, size, material, or equivalent category fields |
| `core_specs` | Variants plus category-relevant specifications |
| `all_applicable` | Every truthful, applicable attribute available for that product |

The study will additionally compare schema-order enrichment, randomized attribute orders, and query/category-aware subsets. Randomized orderings are necessary to avoid mistaking one high-value field for an attribute-count effect.

## Evaluation matrix

The full target matrix is two benchmarks × several representation levels × lexical/dense/LLM retrieval stages × multiple models. We will not run the full matrix immediately.

The execution order is:

1. ShoppingBench + BM25 + representation levels.
2. Add randomized attribute-order controls and confidence intervals.
3. Add dense retrieval if the signal survives.
4. Add one LLM reranker/selector over a fixed candidate set.
5. Expand to a small model set only after the phenomenon is established.
6. Replicate the key result on WebShop.
7. Only then implement a minimum-sufficient-representation selector.

A null result is acceptable. If discovery performance continues improving through the complete representation, the paper becomes evidence for the continued marginal value of catalog completeness rather than a saturation paper.

## Repository layout

```text
research/
  question.md              research charter and falsifiers
  claims.yml               executable/public claims only after evidence exists

docs/
  experiment-plan.md       staged experimental protocol

study/
  attribute_saturation/    benchmark-independent representation and metric primitives
  adapters/                ShoppingBench and WebShop adapter interfaces
  configs/                 versioned experiment configurations

packages/                  publication-package template infrastructure
paper/                     manuscript source
artifacts/                 generated evidence only
```

The `study/` scaffold is deliberately thin. Benchmark-specific code should adapt benchmark products, queries, qrels, and index builders into a common experiment contract. It should not reimplement ShoppingBench or WebShop.

## Scientific guardrails

The query set, ground truth, candidate universe, product facts, and model settings must remain fixed when comparing representation treatments. Any field removed for an ablation must be removed consistently from the indexed or model-visible representation rather than silently remaining available through another channel.

ShoppingBench queries that explicitly mention an ablated attribute will be analyzed separately from broader semantic queries. WebShop replication is important because its task construction differs and helps identify benchmark-specific effects.

We will report paired uncertainty estimates across the same queries and use repeated random attribute orderings where ordering is a treatment. We will not claim a universal attribute count; the expected output is a conditional saturation curve by category, query type, architecture, and model.

## Current milestone

**Milestone 0: scaffold and validate the experimental contract.**

The first implementation target is a deterministic pilot that can render several product representations from the same ShoppingBench product record, build separate BM25 indexes, run identical queries against each index, and emit paired retrieval metrics. No LLM calls are required for this milestone.

See [`docs/experiment-plan.md`](docs/experiment-plan.md) and [`research/question.md`](research/question.md) for the complete plan.

## Release framework

This repository was created from a checked research-paper/package template. The existing `paperkit` tooling, claim ledger, reproducibility artifacts, manuscript build, and release validation remain the publication framework. Experimental results should flow into generated artifacts rather than being manually copied into the paper.
