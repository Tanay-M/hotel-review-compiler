# Evidence for the later IEEE-format course report

**14 October update:** See [the current vocabulary and scoring expansion](vocabulary-expansion.md): 345 aspect phrases, 356 opinion terms, 32 aliases, 315 source synsets, and 136 passing tests. Complete coverage on the unchanged authored 100-review development sample improved from 54% to 88%; this is not sentiment accuracy. The six categories remain unchanged. Older dated measurements below describe their original milestones.

The user requested an IEEE conference-template presentation after completing the project, with no submission. This document prepares results collection, not a manuscript. The UI's report-table ZIP already supplies descriptive results and run provenance. IEEE recommends replicable methods and a results discussion that states limitations without overstating findings: [IEEE conference paper structure](https://conferences.ieeeauthorcenter.ieee.org/write-your-paper/structure-your-paper/). Select the conference template when writing; [IEEE's conference template page](https://www.ieee.org/conferences/publishing/templates) is the template entry point.

## Separate the kinds of evidence

| Evidence | Available now | Claim it supports |
|---|---|---|
| Per-review results | CSV with exactly one row per submitted record, plus opinion-level CSV | What the implemented system extracted and diagnosed |
| Aggregate findings | Category/issue/overall/coverage CSVs with both scopes | Descriptive counts and sentiment indices on that uploaded dataset |
| Rule correctness | 115 automated tests, original 24 examples, 100 authored contracts | Declared contracts, recovery, scoring, batching, and UI/API integration |
| Corpus evaluation | Existing authored development/reserved evaluator | Metrics on those authored cases, not blind real-world accuracy |
| Runtime observation | Duration, Python/platform, source/rules hashes | One observed core run under stated boundaries |
| Real-world extraction/polarity accuracy | Not yet available | Requires independent annotation and held-out evaluation |
| Repeated performance benchmark | Not yet available | Requires controlled repeated runs and documented hardware |

A 500-row synthetic demo repeats the small fixture. Its larger size validates batching and display behavior, not vocabulary breadth. A complete analysis indicates grammar coverage, not correctness against a human interpretation. Results with no supported opinions are Unanalyzed; they must not be counted as Neutral.

## Recommended final experimental setup

1. Freeze/version the compiler and report rules; retain their fingerprints with every run.
2. Obtain a representative English hotel-review dataset with documented source, sampling, duplicates, and permission to use it. Separate synthetic demonstrations from real reviews. Save its raw-input hash.
3. Independently annotate category, issue, opinion polarity, and optionally spans for each review. Document annotators, instructions, taxonomy, ambiguous cases, and disagreement resolution. Keep gold labels separate from model outputs.
4. Split by unique review before tuning; avoid duplicate text in development and test sets. Do not revise held-out labels to match the compiler or add rules based on held-out errors and still call it blind evaluation.
5. Evaluate opinion-tuple precision/recall/F1 using the existing multiset matching convention. Report denominators, micro/macro conventions, polarity agreement on correctly matched category/issue opinions, coverage, and errors. Missing predictions on gold-supported cases affect recall; unsupported reviews must not simply disappear from accuracy evaluation.
6. For timing, specify processor/RAM/OS/Python, input size/review lengths, resource-cache state, measured stages, warm-up, repeat count, and mean/median/spread. Separate CSV parsing, core analysis, aggregation, transfer, and UI rendering. The dashboard's single observed core duration is not an end-to-end benchmark.
7. If comparing the original and expanded rules, hold dataset, labels, splits, and matching protocol constant. State which rules changed. Compare deterministic baselines without introducing deferred ML/LLM components.

## Tables to use in Results and Discussion

- Dataset composition: real versus synthetic, number of rows/unique texts, text lengths, split sizes, category distribution.
- Coverage: complete, partial, unsupported, invalid, failed; complete/analyzed and complete/submitted clearly distinguished.
- Extraction evaluation: precision, recall, F1, gold/predicted/matched opinion counts, status counts, per-category error breakdown. Include independently evaluated metrics only when obtained.
- Category/issue inference: distinct review counts, polarity buckets, any-negative prevalence and denominator, equal-review index, scope and low support.
- Performance: repeated 100/500-review experiments with clearly stated timing boundaries, environment, and uncertainty.
- Representative results: a small selected subset of the one-row-per-review table with diagnosis/scoring explanations. The full 500-row table belongs in supporting material or a separate results file rather than a tiny conference-page table.
- Error analysis/limitations: pronouns, arbitrary grammar, implicit aspects, sarcasm, manually selected senses, domain calibrations, duplicate influence, and complete-only selection bias.

Useful future figures are category sentiment distributions, coverage, complaint counts, an extraction confusion/error summary where labels exist, and runtime versus batch size. Dashboard charts are inspection views; produce properly sized standalone plotting-tool figures for the final document after the experimental data is fixed. No figure or table should describe sentiment scores as confidence percentages or star ratings.

## Export interpretation

`reviews.csv` is the final per-review table. `aspects.csv` preserves repeated opinions and is joined by internal `row_id`. Category/issue tables have `scope` and `mentioned_reviews`; complaint percentage divides by that group's mentions, not all uploaded rows. A zero mean can coexist with Mixed. Blank means/percentages indicate no data. Duplicates count separately in descriptive summaries and are flagged.

`run_metadata.csv` records input hash, analysis/reporting version fingerprints, timestamp, runtime/environment, and timing scope. The CSV/text ZIP includes no JSON. Keep the original input and export together for reproducibility. Exported CSV strings may carry a leading apostrophe for spreadsheet formula protection; this formatting safeguard is not a compiler normalization rule.

The earlier 100 authored contracts matched 100 expected outcomes after expansion. Report this as authored contract validation, including deliberately partial/unsupported cases; it is not 100% natural-language accuracy. The baseline/current snapshots remain historical evidence under their own core fingerprints. Independently annotated real-review results are the remaining prerequisite for empirical accuracy claims in the final course report.
