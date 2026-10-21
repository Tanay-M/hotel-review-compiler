# Independent hybrid v2: measured development results

Run date: 15 October 2026. Full evidence: `output/experiments/2026-10-15/independent-hybrid-v2/`. These are separate pipelines, not just alternative scorers on the old extraction. See [implementation and module pseudocode](independent-hybrid.md).

## Annotated benchmark

Same declared SemEval-2015 hotel crosswalk as the earlier comparison: 30 original reviews, 266 source sentences, 137 eligible sentences, 148 unambiguous sentence/category classification cases, and 162 coarse category/polarity pairs. Out-of-scope annotations and ambiguous coarse-label cases follow the existing declared protocol, unchanged for both systems. Staff predictions collapse to benchmark Service. This is not the official SemEval task/ranking.

| Metric | SentiWordNet compiler | Independent hybrid v2 |
|---|---:|---:|
| Correct / all eligible classification cases | 42 / 148 | 83 / 148 |
| All-case accuracy | 28.38% | 56.08% |
| Cases with a three-class prediction | 44 / 148 | 92 / 148 |
| Classification coverage | 29.73% | 62.16% |
| Conditional accuracy on each method's scored subset | 95.45% | 90.22% |
| Fixed three-class macro-F1 | 0.2260 | 0.3956 |
| Category/polarity tuple precision | 0.9200 | 0.7194 |
| Category/polarity tuple recall | 0.2840 | 0.6173 |
| Category/polarity tuple F1 | 0.4340 | 0.6645 |

Inference: the independent hybrid recovers many more valid category sentiments, improving recall and end-to-end F1, while producing additional false positives and lowering tuple precision. Conditional accuracies use different selected subsets and cannot replace all-case accuracy. These results compare complete pipelines; they do not prove that score averaging alone improves sentiment quality.

The benchmark has 41 negative, 4 neutral and 103 positive eligible classification cases. Neither method correctly predicts the neutral class here. Hybrid negative recall is 0.2439 and positive recall is 0.7087. Remaining extraction misses, ambiguous attachment and neutral evidence limit performance. Do not hide these limitations behind the larger positive-class support.

**This is development/exploratory evidence.** SemEval errors were examined before v2 was built. Do not describe these results as an unseen held-out test or claim statistically established superiority from these point estimates. Freeze configuration before a fresh evaluation, with splits grouped by parent review. No five-class human intensity annotations are available, so five-band distributions are descriptive.

## Real review coverage (not accuracy)

| Input / outcome | SentiWordNet compiler | Independent hybrid v2 |
|---|---:|---:|
| Curated 100: complete | 97 | 100 |
| Curated 100: unsupported | 3 | 0 |
| Random 200: complete | 1 | 66 |
| Random 200: partial | 11 | 101 |
| Random 200: unsupported | 188 | 33 |
| Random 200: processing errors | 0 | 0 |

The hybrid returns at least some scored aspect output for 167/200 (83.5%) random reviews; only 66/200 (33%) satisfy its heuristic completeness checks. This is **not 83.5% complete analysis or 83.5% accuracy**. Completeness definitions differ between the controlled parser and the open grammatical extractor and remain processing heuristics. The curated 100 were intentionally selected using baseline vocabulary/grammar; 100 complete outputs do not prove 100% correctness.

All 300 sample inputs were checked against the original downloaded Booking archive again; source maps reproduce their documented preparation and the two sample sets do not share parent rows. Review wording was not generated. Preparation trims outer whitespace, removes exact missing-field placeholders and joins original feedback fields when applicable.

## What to open

- `semeval-development/metrics.csv`, `per_class_metrics.csv`, `predictions.csv`: exact counts, reference labels and predictions.
- `semeval-development/annotation_scope.csv`, `excluded_annotations.csv`: complete benchmark scope/exclusions.
- `semeval-development/fig_metrics.pdf`, `fig_confusion.pdf`: vector paper figures; SVG and 300-dpi PNG also available.
- `random200/review_results.csv`: one output row per real review, with independent statuses, means and whole-text scores.
- `random200/opinion_results.csv`: separate method rows with contexts, components, grammar patterns and contextual rule evidence.
- `random200/hybrid_tokens.csv`, `hybrid_noun_phrases.csv`, `hybrid_segments.csv`, `diagnostics.csv`: inspectable grammatical processing.
- Each run includes repeated timing tables, figure alternatives, LaTeX table snippets, inference notes, code snapshot, environment lock and metadata. The SemEval run has benchmark metrics rather than runtime repetitions.
- `source-verification/source_verification.csv`: original-source checks for all 300 samples.

Earlier v1 outputs under `output/experiments/2026-10-15/paper/` are preserved. An earlier untimed intermediate random run under `hybrid-v2/` is not the final v2 evidence above.

## Validation

183 tests passed, including 21 new authored contracts and the existing compiler/CSV/WebUI tests. Python compile checks passed. Baseline lexer/parser/semantics/scoring files and original domain resource hashes match the pre-change snapshot. All 300 saved baseline review scores, statuses and extracted counts match the earlier experiment exactly. Tests establish implementation behavior, not independent sentiment accuracy.
