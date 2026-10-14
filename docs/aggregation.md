# Batch aggregation and conclusions - 13 October 2026

This functionality milestone summarizes retained compiler results. It does not parse review text again, call an LLM, or store a database. CLI batch exports contain five files: `reviews.csv`, `aspects.csv`, `batch.json`, `summary.json`, and `report.txt`. The subsequent UI milestone adds CSV upload/dashboard and CSV/text paper-table downloads; see `web-dashboard.md`. Review CSV columns now additionally contain readable joined aspect results while preserving one row per input.

## Run and inspect

From the project directory:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\batch.ps1 .\examples\bulk_demo.csv --output-dir .\output\batches\my-report --batch-id demo --progress
```

Open `report.txt` for readable conclusions and `summary.json` for metrics, both scopes, row identities, and evidence references. Add `--include-partial` to also display the secondary view in the terminal/text report. JSON always retains both views; this flag never changes primary results. Existing files remain protected, so choose another directory when repeating a run. Exit 1 is expected for the sample's incomplete/invalid inputs; exports remain usable.

The verified sample report is in `output/batches/aggregate-demo/`. Its primary results are 9 complete reviews of 12 submitted rows: 3 Positive, 2 Negative, 3 Mixed, 1 Neutral. Staff is mentioned in 5 complete reviews, all Positive. Complete-plus-partial evidence adds one positive Staff review, with the restricted scope clearly stated. These are synthetic demonstration counts, not hotel-quality conclusions about a real population.

## Counting and scoring rules

| Metric | Rule and denominator |
|---|---|
| Primary scope | Complete reviews only; excludes partial, unsupported, invalid, and failed rows |
| Secondary scope | Complete plus partial reviews; recognized opinions only |
| Overall polarity | One existing overall label per eligible review; percentages divide by eligible reviews |
| Category/issue review count | Distinct internal row IDs mentioning that group; repeated opinions count once |
| Category/issue polarity | Positive and Negative together produce Mixed; a Neutral opinion does not override Positive/Negative |
| Complaint prevalence | Distinct reviews with any negative opinion, including Mixed once, divided by reviews mentioning the group |
| Opinion count | Number of extracted records, separately from review count |
| Average sentiment index | Average scores within each review/group, then average across those distinct reviews |
| Complaint ranking | Descending distinct-review negative-mention count; equal counts share rank |
| Missing evidence | No mentions means `not_mentioned`, zero counts, null percentages/average; never Neutral |

For example, one review with three +0.25 Staff opinions and another with one -0.625 opinion have a Staff mean of `(0.25 - 0.625) / 2 = -0.1875`, rather than weighting the longer review three times. Their review labels remain one Positive and one Negative. A review with +0.125 and -0.125 remains Mixed even though its numeric average is zero.

Internal CSV row IDs define an observation. Duplicate text and caller IDs remain separate, with counts/flags and a report note. This preserves the uploaded rows; frequent duplicated text can influence the apparent complaint frequency. Ranking indicates frequency, not severity, and reports ties explicitly.

## Scope and support

Coverage still reports complete/analyzed and extraction/analyzed percentages. The report separately identifies complete/submitted percentage, so excluded invalid rows cannot hide behind 100% coverage of the analyzed subset. Primary complete/submitted coverage below 80% produces a limited-evidence note. Groups with fewer than five eligible mentions are marked `low_support`. These thresholds are explicit demo conventions, not statistical significance or accuracy estimates.

No eligible complete reviews means no primary sentiment conclusion or average. The system never silently substitutes partial results. Unsupported reviews remain Unanalyzed. Scores are lexicon/rule sentiment indices, not star ratings, calibrated confidence, or prediction accuracy. Even a fully covered batch remains subject to the controlled language and manually selected senses.

## Evidence and API

Every conclusion has a scope and supporting `row_ids`. Category/issue groups include `evidence` entries with zero-based `record_indices` in that row's retained `analysis.records` and scoring trace. Overall conclusions refer to the retained overall labels. Ranking leaders include their complaint-supporting IDs. Original text, diagnostics, and all traces live in the matching `batch.json` row. Caller IDs are not a safe join key because duplicates are allowed.

```python
from hotel_compiler.batch import analyze_csv
from hotel_compiler.reporting import build_report, render_report

batch = analyze_csv("examples/bulk_demo.csv", batch_id="demo")
report = build_report(batch)  # No output files or second analysis
primary = report["aggregation"]["views"]["complete_reviews"]
print(primary["overall_counts"])
print(render_report(report))
complaint = next(c for c in report["conclusions"]["complete_reviews"]
                 if c["code"] == "ISSUE_COMPLAINT")
print(batch.get_row(complaint["row_ids"][0]).to_dict(include_trace=True))
```

`summary.json` identifies source SHA-256, the original compiler fingerprint, and a separate aggregation/reporting code fingerprint. Changing report logic does not claim the compiler used different language rules. Explicit exports protect existing files and remove only newly created outputs when any of the five writes fails.

## Code map and validation

| File / function | Logic |
|---|---|
| `aggregation.py::aggregate_batch` | Scope selection, coverage, policy, both views |
| `aggregation.py::_view` | Grouping by internal row ID, overall counts, complaint ranking |
| `aggregation.py::_group` | Counts, presence polarity, equal-review averages, supporting record indices |
| `reporting.py::_conclusions` | Deterministic sentences, no-data wording, low support, ties |
| `reporting.py::build_report` | Metadata, coverage/duplicate notes, evidence contract |
| `reporting.py::render_report` | Primary text output and optional secondary section |
| `exports.py::export_batch` | Five explicit protected exports |
| `batch_cli.py::main` | Existing batch command, reporting, `--include-partial` |
| `tests/test_aggregation.py` | Hand-computed counts, averaging, scopes, duplicates, ties, evidence, exports, CLI, 100/500 rows |

All 103 tests pass: 24 original compiler/CLI, 14 web, 27 batch/export, 20 robustness/evaluation, and 18 aggregation/reporting tests. Python compilation passes. Tests verify no reanalysis or mutation, retained individual-output equality, report collisions and cleanup, and every supporting ID/record position. The next milestone is a bounded local batch API, then the upload/dashboard UI. SQL and learned NLP/LLM enhancements remain deferred.
