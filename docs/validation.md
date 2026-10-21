# Part 1 validation - 8 October 2026

## Result

The compiler-core milestone is complete. The architecture-plan example runs through the real lexer, predictive parser, semantic analyzer, SentiWordNet evaluator, and IR generator:

```text
The room was not clean, but the staff were very helpful.

Room  / Cleanliness / not clean    / Negative / -0.1250
Staff / Helpfulness / very helpful / Positive / +0.3125
Overall: Mixed
```

## Checks performed

| Check | Outcome |
|---|---|
| Automated suite | 24 tests passed on Windows / Python 3.12.14 |
| Controlled demonstration corpus | All 24 examples matched the manually specified category, issue, and polarity results |
| Category coverage | Room, Staff, Service, Food, Cleanliness, Facilities |
| Modifier behavior | Negation remains local; intensifiers increase magnitude; scores are clipped |
| Unknown / malformed language | Structured unsupported or partial status; no neutral label fabricated |
| Recovery | Valid neighboring clauses survive; failed clauses clear inherited subject context |
| Source spans | Checked against original Unicode text, including curly contractions and Unicode hyphens |
| CLI | Readable table, JSON, full trace, standard input, exit codes, error messages |
| Windows launcher | Uses the available Python runtime and skips Microsoft Store execution aliases |
| Python compilation | All source modules compile successfully |
| Lexical-resource integrity | 35 subset rows checked against the official source archive; every row is unchanged; checksums match |

Commands:

```powershell
python -m unittest discover -s tests -v
python -m compileall -q hotel_compiler scripts tests
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run.ps1 "The room was not clean, but the staff were very helpful." --review-id demo-17
```

## Interpretation and outstanding work

These checks validate the controlled language and CLI, not accuracy on arbitrary real hotel reviews. The vocabulary is intentionally limited. SentiWordNet senses are selected explicitly. Its zero score for physical `slow` is handled by one visible Service/Facilities rule; lexical-neutral words such as `fast` and `hot` retain their original scores.

At this milestone, database persistence, category aggregation, a web interface, and bulk-file import were not yet implemented. The web interface was subsequently added below. No runtime ML or additional NLP models are included.

## Local web demo validation - 12 October 2026

The basic browser demo now runs the same compiler through a local standard-library HTTP server. It displays aspect results, diagnostics, tokens, syntax, semantics, SentiWordNet scoring evidence, and IR, with optional JSON download. SQL, automatic review storage, stored category aggregation, and bulk import remain deferred.

All 37 automated tests passed on Windows / Python 3.12.14 (24 original compiler/CLI tests and 13 web integration tests). The web tests verify equivalence with the core analyzer, Unicode, partial and unsupported results, input validation, actual vocabulary, static assets, local-only binding, request boundaries, and absence of persistence endpoints. Python compilation and JavaScript syntax checks also passed.

Browser checks confirmed the mixed example, syntax and semantic traces, original P/N scoring evidence, partial and unsupported reviews, shared-aspect handling, Ctrl+Enter analysis, reset, JSON download, and the explicit Service rule for `slow`. A preview is saved in `output/demo/web-demo.jpg`.

Launch from the project folder:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\serve.ps1
```

Open `http://127.0.0.1:8000`, keep the terminal open, and press Ctrl+C there to stop the server.

## CSV bulk milestone validation - 12 October 2026

CSV ingestion and individual exports are implemented without changing the grammar, scoring, or browser UI. The suite has 63 passing tests: 24 original compiler/CLI, 13 web, and 26 CSV/batch/export tests. New checks cover BOM/Unicode, quoted and multiline fields, physical line spans, column mapping, malformed files/limits, per-row invalid inputs, duplicate identities, error isolation, original-pipeline equivalence for every row in 100/500-row fixtures, coverage denominators, JSON traces, CSV joining/formula escaping, export collision/write failure protection, CLI statuses, and the Windows launcher. All Python modules compile.

The 11-row example produced 8 complete, 1 partial, 1 unsupported, and 1 invalid outcome, with both duplicate rows retained. Exit code 1 is intentional: results were successfully exported and some rows need inspection.

Synthetic benchmark files repeat this fixture with unique supplied IDs. Timing includes ingestion, analysis, and all exports with `tracemalloc` enabled; lexical caches were warmed first. Peak values are tracked incremental Python allocations, not process RSS. Results are not real-world accuracy measurements or timing guarantees:

| Reviews | Complete | Partial | Unsupported | Invalid | Ingestion + analysis | Export | Total | Peak tracked allocations |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 100 | 73 | 9 | 9 | 9 | 0.0341 s | 0.0863 s | 0.1203 s | 1.174 MiB |
| 500 | 364 | 45 | 46 | 45 | 0.1566 s | 0.4409 s | 0.5975 s | 4.959 MiB |

The saved 500-row JSON is approximately 2.46 MB and includes every available trace. Export row counts, unique internal IDs, and trace presence were checked after reading the files back. Full benchmark metadata is in `output/batches/validated-benchmark-results.json`; example outputs are under `output/batches/first-milestone`, `validated-100`, and `validated-500`. Generated files are ignored by Git. An initial benchmark exposed unnecessary allocation of the full 10 MiB read limit for small inputs; ingestion now reads bounded 64 KiB chunks.

Limits are 1,000 rows / 10 MiB per file / 10,000 characters per review by default. At this historical milestone, `not working` remained unsupported; the subsequent language expansion below supports it. Category aggregation/conclusions, batch API/dashboard, and SQL remain subsequent work. See `bulk-usage.md` for launch and individual inspection commands.

## Deterministic robustness milestone - 12 October 2026

All 85 tests pass: 24 original compiler/CLI, 14 web, 27 CSV/batch/export, and 20 robustness/evaluation tests. Python compilation also passes. The original 24 demonstration cases retain their expected outcomes. New integration checks compare every result and full trace in 100/500-row expanded-pattern batches with standalone analysis and JSON exports.

The shared compiler now supports equipment state/verb predicates, auxiliary contractions, seven explicit aliases, opinion-before-aspect forms, selected adverbs, and negative emphasis. Guards reject invalid base/finite forms, incompatible equipment targets, unsupported modifiers, and positive `at all`; failures clear inherited context. Tests verify exact source spans, normalized evidence, one-time negation, and resource preflight. Compact aspect IR fields remain unchanged; trace fields are additive.

The 42 packaged SentiWordNet rows match the original rows in the SHA-256-pinned official archive. There are 44 canonical opinions and 53 aspect phrases. P/N are unchanged; five explicit domain calibrations and aliases are separately disclosed in traces. `robustness.md` records every new sense and rule, including the anomalous negative physical-comfort source row.

`examples/robustness_cases.json` contains 100 authored contracts recorded before changes: 70 development and 30 reserved recombinations. Evaluation counts repeated opinion tuples as multisets and reports split/family metrics, mismatches, diagnostics, corpus hash, and analysis fingerprint. Before/after snapshots are in `output/batches/robustness-baseline.json` and `robustness-current.json`.

| Measure on the same 100 authored contracts | Before | Current |
|---|---:|---:|
| Exact status + opinion-tuple outcomes | 29/100 | 100/100 |
| Opinion tuple precision | 100% | 100% |
| Opinion tuple recall | 13.48% | 100% |
| Complete analysis | 5% | 69% |

The remaining 31 cases deliberately require partial/unsupported outcomes. These results establish authored contract behavior, not 100% real-world accuracy; the reserved split is not an independent blind real-review dataset. Independently annotated target reviews remain necessary.

The updated 12-row sample batch produces 9 complete, 1 partial, 1 unsupported, and 1 invalid input, with 13 extracted opinions and no processing errors. Its third review (`The air conditioning was not working.`) is now Negative, -0.25. Trace-preserving exports are saved in `output/batches/robustness-demo/`. CLI and browser API use the same expanded core; restart an existing web server to load changes. No UI redesign, SQL, model, or network dependency was added. Aggregation/reporting is the next milestone.

## Aggregation/reporting milestone - 13 October 2026

All 103 tests pass: 24 original compiler/CLI, 14 web, 27 CSV/batch/export, 20 robustness/evaluation, and 18 aggregation/reporting tests. Python compilation passes. New checks validate hand-computed distinct-review counts, Mixed preservation even at zero average, equal-review weighting despite unequal opinion counts, primary/secondary scope separation, exclusions, duplicates, null no-data values, low-support and coverage thresholds, ties, and complaint frequency rather than severity.

Every conclusion-supporting row ID resolves to retained results. Category/issue record indices resolve to the correct group, and complaint IDs have an actual negative opinion for that group. Reports invoke no second compiler analysis and leave the batch unchanged. Integration checks verify aggregate counts/evidence and JSON report equality for 100/500-row fixtures, five export files, protected report collisions, cleanup after reporting failure, and CLI partial-view selection with unchanged exit codes.

The Windows launcher was run with `--include-partial` against the 12-row sample, saving all five files under `output/batches/aggregate-demo/`. Primary results are 9 complete reviews: 3 Positive, 2 Negative, 3 Mixed, and 1 Neutral; Staff is mentioned in 5 complete reviews, all Positive. Secondary results are 10 complete/partial reviews: 4 Positive, 2 Negative, 3 Mixed, and 1 Neutral. The report states 75% primary coverage of submitted rows and retains duplicate/low-support notes. Exit 1 is expected because incomplete/invalid inputs were exported successfully. These are synthetic demonstration results, not real-world accuracy or population estimates.

Individual CSVs and `batch.json` retain their contracts. New `summary.json` stores metrics/conclusions for both scopes and a separate reporting fingerprint; `report.txt` is readable primary text with an optional secondary section. No SQL, learned model, new dependency, or UI route was introduced. Next: local batch API/lifecycle, followed by upload/dashboard UI. See `aggregation.md`.

## CSV web dashboard and paper-table milestone - 13 October 2026

All 115 tests pass (the prior 103 plus 12 bulk web tests), and all Python modules compile. Both JavaScript files pass syntax checks. The adopted API is synchronous and minimal under the user's preference: one retained in-memory batch, bounded upload, overview/detail/download/clear, and a busy response for simultaneous CSV analysis. No worker queue, SQL, external service, or automatic review files are added.

HTTP tests validate shared file/byte CSV contracts, all 500 individually fetched results/traces against standalone analysis, and a 100-row review CSV with exactly 100 result rows. ZIP checks cover all seven CSV tables and two text files, explicit scopes, null no-data values, input/rule hashes, and absence of fabricated accuracy. Other checks include BOM/Unicode/multiline/custom columns/formula escaping, malformed-file preservation of the previous run, successful replacement, clear, limits, routes, origin restrictions, and health/detail availability during analysis.

Browser checks used the real file chooser for `examples/bulk_demo.csv`, deliberately selected an absent text column and verified the old successful dashboard remained intact, then uploaded the correct file. Synthetic 500-row checks verified pagination (51-100), all 500 rendered rows, review 500's partial result/trace, search, negative-chart evidence filtering, complete/partial scope selection, invalid row 10 with validation and no fabricated trace, and an actual successful CSV/text ZIP download. The single-review Mixed example still works. Narrow and 1280-pixel desktop layouts were inspected; browser error/warning logs are empty. Saved UI previews are under `output/ui/`.

The synthetic 500-row demo produces 500 table rows: 376 complete, 42 partial, 41 unsupported, 41 invalid, zero processing errors, and 543 opinions. Primary overall counts are 125 Positive, 84 Negative, 125 Mixed, and 42 Neutral. Coverage is 376/500 = 75.2% of submitted and 376/459 = 81.92% of analyzed rows. Repeated text remains visible and counted separately. A ready-to-inspect 500-row CSV/text evidence bundle is saved under `output/paper-demo-500/`, including `reviews.csv` and `report-tables.zip`.

The visible UI output is tabular/cards/charts with CSV downloads; raw AST/IR JSON panels and JSON downloads were removed. Internal transport and existing CLI JSON contracts remain implementation details. CSV review exports add categories, issues, opinion expressions, and readable joined aspect results while preserving one row per input. A report readiness panel and `paper-results-plan.md` distinguish descriptive results, authored contract evaluation, independently labeled accuracy, and repeated performance evidence. No manuscript or submission was created. See `web-dashboard.md` for launch and usage.

## Vocabulary expansion validation — 14 October 2026

The full suite passes 136 tests (21 new expansion tests); Python compilation and both JavaScript syntax checks pass. Tests cover all 356 canonical opinions and their negated forms with unchanged SentiWordNet P/N, source-row integrity, coordinated subjects/opinions, retained context, possession, category senses, compatibility/recovery, and existing 500-row HTTP equivalence. The existing 100-review input retains its SHA-256 and exactly one output per row: complete/partial/unsupported changed from 54/28/18 to 88/6/6, with 167 opinions and no processing errors. This is development-sample coverage, not independent accuracy. See [the detailed guide](vocabulary-expansion.md) and `output/evaluation/vocabulary-expansion-2026-10-14/`.

## Individual review score validation 14 October 2026

All 145 tests pass, including nine review-score tests. Review score is the six-decimal mean of final opinion scores, with complete or recognized-only scope. Tests cover unequal category/opinion counts, Mixed cancellation versus Neutral zero versus unavailable, source-score preservation, clipped extremes, partial/empty results, runtime-error and invalid rows, CSV/report consistency, HTTP upload/detail/download results and unchanged category-specific dashboard means. Both JavaScript syntax checks and Python compilation pass. Single-review summary, batch table, trace, CLI and CSV/report outputs expose the field.
