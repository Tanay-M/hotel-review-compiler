# Functionality-first plan: bulk hotel reviews and aggregate reporting

Status: CSV/bulk processing, initial language expansion, aggregation/reporting, CSV web upload, dashboard, individual review tables/traces, and report-table downloads are implemented. The user's latest instruction reduced Part E to necessary local endpoints with synchronous bounded uploads and one retained batch; worker/queue infrastructure is not implemented or required for this demo. Independently annotated real-review evaluation and repeated performance measurements remain future evidence work. See `web-dashboard.md`, `paper-results-plan.md`, and supporting functionality docs. The original roadmap below records earlier proposals; Parts E/F notes identify the adopted scope.

## Objective and scope

Accept a CSV with 100 or 500 hotel reviews, preserve an individual analysis and trace for every submitted row, and produce transparent batch/category/issue summaries. Improve deterministic language coverage before building the dashboard UI.

The latest faculty request makes bulk analysis and reporting required features. Earlier handoff suggestions remain advisory. The user's earlier no-SQL instruction and deferral of ML/additional NLP models remain the defaults. This plan introduces neither a database nor an LLM. It does not promise unrestricted English understanding.

## Existing foundation

- `hotel_compiler/pipeline.py::analyze_review` is the shared single-review compiler boundary.
- `models.py::AnalysisResult` already contains final records, diagnostics, original text, and all five traces.
- `lexer.py`, `parser.py`, `semantics.py`, `sentiwordnet.py`, and `resources/domain.json` implement the controlled language.
- The local web adapter handles one review. It has no bulk processing, history, or aggregation.
- The planning baseline had 37 tests; the current suite has 115. Neither authored regression tests nor synthetic batches establish accuracy on real reviews.

The bulk layer will call the same compiler. It must not duplicate sentiment logic in CSV handling, aggregation, or the UI.

## Recommended build order

1. Define the CSV/result contracts and an evaluation corpus.
2. Implement and test bulk processing using the current compiler.
3. Expand the compiler in measured, deterministic increments.
4. Implement and test aggregation and evidence-backed conclusions.
5. Add a local batch API and job lifecycle.
6. Build upload, review-detail, and dashboard screens.

Steps 1–5 are functionality work. Step 6 starts only after their outputs are validated. The old persistence-first sequence in `BUILD_PLAN.md` is superseded for this scope; persistence remains optional future work.

## Part A: contracts and examples

Default input is UTF-8 CSV (including UTF-8 BOM), with a header, a required `review_text` column and an optional `review_id` column:

```csv
review_id,review_text
R001,"The staff were extremely helpful."
R002,"The food was bland; the staff were courteous."
R003,"The air conditioning was not working."
```

All three rows are now supported. The third produces Facilities / Air Conditioning / Negative using working's source P=0.25, N=0 and one negation. It was a coverage-gap example before the first Part C expansion.

Requirements:

- Correctly parse quoted commas, quotes, multiline reviews, and Windows line endings using the standard CSV parser.
- Use a selected/explicit column mapping for alternative headers; reject ambiguous column choices.
- Ignore extra columns for analysis and report which text column was used. Ratings do not supply sentiment labels.
- Proposed demo defaults: at most 1,000 data rows, 10 MiB per file, and the existing 10,000-character limit per review. These are configurable limits to validate in benchmarks, not current capabilities.
- Reject unreadable encodings, missing headers/text columns, and structurally malformed files with useful messages. Do not silently replace undecodable text or guess row boundaries after malformed quoting.
- A readable row with an empty or oversized review gets a row validation result; other readable rows continue.
- Preserve original review text and caller IDs. Assign a batch ID and row ordinal as the unique internal identity; duplicate text/IDs remain separate rows and can be flagged. Never silently merge or drop them.
- Use CSV record ordinals for identity and physical source line spans for diagnostics, since multiline fields occupy multiple lines.

Create a small CSV fixture set for file behavior and a separate manually annotated language corpus. Aim for 100–200 varied hotel reviews initially, including real target-format examples where available. Label expected aspect, issue, polarity, source expression, and unsupported/ambiguous cases. Keep a held-out subset that does not drive vocabulary/rule selection.

Exit condition: accepted CSV shape, failure behavior, row identity, and example expected outputs are documented before bulk code changes.

## Part B: bulk engine and individual outputs

Proposed new boundaries:

| Module | Responsibility |
|---|---|
| `csv_input.py` | Decode and validate CSV; yield identified review rows |
| `batch.py` | Run `analyze_review` per valid row; track status and progress |
| `batch_models.py` | Batch metadata, row outcomes, versioned serialization |
| `exports.py` | Produce review-level and aspect-level CSV plus JSON results |

Each row output must contain its identity, original text, analysis status, overall label, aspect results, diagnostics, and access to the five existing traces. Separate importer/execution status (`analyzed`, `invalid_input`, `processing_error`) from compiler status (`complete`, `partial`, `unsupported`). Do not convert exceptions or unsupported reviews into Neutral.

Process sequentially first: the existing vocabulary and lexical data are cached, and 500 rows do not inherently require concurrency. Measure throughput and memory before adding workers. A failure caused by an individual review must not stop other rows. Missing/corrupt shared lexical resources should fail the job visibly rather than generate hundreds of misleading row failures.

Return summary fields in list output, with full traces accessed for one selected row. Avoid transferring every trace to the browser in the initial listing. Retain the computed result for the batch lifetime so detail, exports, and summary all describe the same run. Record a rules/resource fingerprint with the batch.

First deliverable is a terminal-invoked CSV analysis command and export files; its precise command is to be introduced during implementation. Export:

- `reviews.csv`: one row per submitted review, with status, overall label, diagnostics summary, and IDs.
- `aspects.csv`: one row per extracted opinion, with category, issue, polarity, score, source positions, and review identity.
- `batch.json`: batch metadata, summaries, individual outcomes, and traces.

Use standards-compliant CSV quoting. Make spreadsheet-facing exports safe for formula-leading review text/IDs; preserve unmodified originals in JSON.

Exit condition: 100-row and 500-row fixtures produce the expected number of individual row outputs; mixed valid/invalid rows retain identities; every analyzed row agrees with a standalone call using the same ID; full traces remain accessible; measured time/memory are recorded.

## Part C: compiler robustness

Batch size and language understanding are separate concerns. Adding vocabulary alone will not fix missing grammatical constructions. Add one supported language family at a time, documenting its grammar, semantic interpretation, source spans, and scoring evidence.

Priority order:

1. **Functional-state opinions and common phrases:** `working`, `functioning`, `not working`, `out of order`. Select suitable SentiWordNet senses where available; document category-specific rules when their lexical score is neutral or a phrase has no suitable entry. Consume negation exactly once.
2. **Explicit word-form aliases:** `works`/`working` and selected hotel-domain forms. Use curated aliases, not unrestricted stemming or guessed synonym replacement. Original source text remains intact.
3. **Additional predicate grammar:** `The AC does not work`, `The WiFi did not work`, and contracted auxiliaries. Extend token classes and parser/AST deliberately; adding a verb to the adjective vocabulary is not a general grammar solution.
4. **Adjective-before-aspect forms:** `rude staff`, `delicious food`, `very slow service`, including multiword aspects. Establish attachment rules rather than scanning for any nearby aspect/opinion pair.
5. **More hotel vocabulary and issue definitions:** expand from observed dataset gaps; retain the six categories initially. Track allowed aspect/opinion combinations and avoid misleading assignments such as applying functional-state rules to unrelated targets.
6. **Modifiers and recovery:** support selected adverbs such as `properly`, `well`, and `at all` only with explicit interpretations. Improve boundaries so a supported neighboring clause survives an unsupported clause, while ambiguous material remains diagnosed.
7. **Selected multi-sentence/coordinated forms:** add only after clear attachment/scope rules and regression examples. Pronouns, shared predicates across multiple subjects, nested negation, and ambiguous references need dedicated designs; do not infer them through a broad proximity heuristic.

Test contrast pairs and scope failures, including `working` versus `not working`, `not very helpful`, `doesn't work`, `not only ... but also ...`, repeated negation, and unsupported material around valid clauses. The latter constructions may initially be rejected with a specific diagnostic; the requirement is to avoid confidently wrong extraction.

Retain original P/N, selected sense/gloss, domain rule identifier/reason, intensity, negation, and final score in evidence. A zero lexical score cannot become negative through multiplication by -1; functional-state rules must address this explicitly. Preserve original positions if aliases or phrase recognition change token values.

After each increment, compare development and held-out results:

- Complete/partial/unsupported review counts and rates.
- Precision/recall of extracted aspect–issue–polarity tuples under a documented matching rule.
- Polarity accuracy on correctly matched opinions, and error breakdowns.
- Unsupported expressions and grammar patterns ranked by frequency.
- Existing regression tests and source-span/negation checks.

Increased extraction coverage is not automatically increased accuracy. Do not set or claim an accuracy percentage before measuring the annotated corpus. Plain-English arbitrary reviews, multilingual reviews, sarcasm, implicit aspects, and unrestricted pronoun resolution remain limitations unless separately designed and validated.

Exit condition: each declared supported language family has positive/negative examples and failure/scope counterexamples; baseline behavior is retained or deliberately documented; benchmark results and residual limitations are published. No runtime trained NLP or LLM is introduced.

## Part D: aggregate inference before dashboard UI

Implemented on 13 October 2026. `aggregation.py` consumes batch results and produces structured metrics. `reporting.py` turns those metrics into deterministic sentences with counts, scope, and evidence IDs. Neither component guesses sentiment from review text again. See `aggregation.md` for API, files, thresholds, and validation.

Two views:

- **Coverage:** submitted rows, invalid/failed rows, complete, partial, unsupported, and rows yielding at least one opinion. Denominators accompany every percentage. Complete rate is complete/valid analyzed rows; extraction coverage is (complete+partial)/valid analyzed rows; invalid/failed row counts remain visible separately.
- **Sentiment:** primary conclusions use complete reviews. An optional separate view includes recognized opinions from partial reviews and explicitly labels that scope. Unsupported/invalid/failed inputs are never neutral and do not enter sentiment averages.

Aggregation rules:

1. Overall Positive/Negative/Mixed/Neutral counts use one existing overall label per eligible review. Preserve Mixed rather than letting positive and negative scores cancel into a supposed neutral review.
2. For each category, group records by internal review identity and category. Count distinct reviews mentioning that category, then derive Positive/Negative/Mixed/Neutral from that review's category polarities using the same label convention as the core. Multiple opinions do not create multiple reviews.
3. Keep extracted opinion counts separate from review counts. Mixed category reviews are their own bucket. If calculating any-negative complaint prevalence, count a mixed review once as having a negative mention and name that metric explicitly.
4. Category average scores first average eligible opinions within each review/category, then average those review/category scores. This gives each review equal weight. Show supporting review count and label the score as a lexicon/rule sentiment index, not a rating or confidence percentage.
5. Issue summaries show distinct-review complaint counts and their denominators, with links/identities for supporting reviews. Do not confuse the frequently discussed issue with the most severe issue.
6. Not-mentioned categories are absent/insufficient evidence, not Neutral. Low-count results, ties, and no-data cases have explicit wording.
7. Primary wording must say, for example, `Among 80 completely analyzed reviews, ...`; it must not imply findings cover all 500 rows. If coverage is low, state that limited coverage weakens the conclusion about the full dataset.

Possible conclusions include `Staff received positive feedback in 30 of 40 complete reviews mentioning Staff` or `WiFi had negative mentions in 12 of 20 complete reviews mentioning WiFi`. These sentences come from actual counts, not an LLM. Do not average SentiWordNet P/N into an overall hotel star rating.

Exit condition: hand-computed fixtures agree for repeated opinions, mixed reviews, duplicates, partial/unsupported inputs, absent categories, uneven review lengths, ties, and empty eligible sets. Every conclusion can be traced to the exact individual review results that support it.

## Part E: local API and bounded batch lifecycle

Adopted implementation: minimal synchronous upload/overview/detail/download/clear routes in the existing threaded server, one successful batch in memory, bounded CSV input, and a busy response for concurrent uploads. Other requests remain available. The latest user instruction favors necessary endpoints only; the background job/expiry/cancellation proposal below is deferred. See `web-dashboard.md` for the actual contracts.

Extend `web.py` only after the non-UI functionality passes its checks. Proposed routes are illustrative contracts to finalize in implementation:

- `POST /api/batches`: validate and submit a CSV plus text-column selection; return a batch ID.
- `GET /api/batches/{id}`: job state, progress, counts, and summary when ready.
- `GET /api/batches/{id}/reviews`: paginated lightweight rows with status/category/polarity filters.
- `GET /api/batches/{id}/reviews/{row_id}`: original text, final results, diagnostics, and full trace.
- `GET /api/batches/{id}/exports/{format}`: explicit result download.

Use a bounded in-memory batch store and one background job worker initially, separate from HTTP request handling. Track queued/running/completed/failed/cancelled states, processed/total rows, and cancellation between rows. Define job limits, expiry, maximum retained results, and shutdown behavior; never silently evict a running job. Restart loses in-memory history, and exports allow users to keep results. No automatic review files, SQL, database migration, Redis, or distributed worker service is required.

Keep loopback binding, request limits, local request checks, and safe text rendering. Bulk limits differ from the existing 64 KiB single-review request limit and must be explicit. A result-detail request must read the saved run result, not recompute it under potentially changed rules.

Exit condition: API outputs match the terminal bulk outputs, large uploads do not block status/detail access, bounded resource usage is measured, failed/cancelled jobs and expired IDs receive clear responses, and restart behavior is documented.

## Part F: UI after functionality

Implemented on 13 October: CSV upload/mapping, loading feedback, pagination/all-row table, filters, retained review/trace detail, coverage and category/complaint charts, evidence drill-down, and CSV/text downloads. The presentation uses no raw JSON. Progress is an honest busy indicator for the synchronous operation, not a fabricated percentage. Paper evidence exports accompany the user's new IEEE-format report requirement.

Add a CSV upload/column selection preview, processing progress, a paginated individual-review table, review-detail views reusing the existing five trace tabs, summary cards/category charts, issue rankings, evidence drill-down, and exports. Display coverage beside conclusions and clearly identify the aggregation scope. Reuse the current single-review screen. Do not render 500 full traces at once.

Exit condition: a 500-review demonstration supports upload -> progress -> aggregate conclusion -> supporting review -> its compiler evidence, with readable partial/unsupported/error states.

## Future decisions

- SQLite becomes useful if the faculty needs saved history across restarts, comparisons between batches, or reproducible stored runs; it is not necessary for this first bulk demo.
- A trained NLP or LLM fallback is a separate future-scope decision only if measured rule-based coverage remains inadequate for the required dataset. Its results must have a distinct provenance and must not be presented as compiler extraction or SentiWordNet-generated P/N.
- Default scope is English hotel reviews. A sample of the faculty's intended CSV and confirmation of other required languages would refine the corpus and later milestones; they do not prevent this plan.

## First implementation increment (completed)

Parts A/B implement CSV contracts, batching, individual exports, and coverage. Part C expands the compiler against 100 authored contracts, including deliberate rejections; this is not independent real-world evaluation. Part D adds verified aggregation/conclusions. Adopted Parts E/F provide the minimal local API, CSV dashboard, per-review tables/traces, and CSV/text report downloads. Further evidence and language expansion should use independently annotated target reviews and measured failures. SQL and learned models remain deferred.
