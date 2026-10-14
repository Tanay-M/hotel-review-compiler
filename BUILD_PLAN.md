# Team 17 build plan

The implementation architecture PDF supplies the project requirements. The handoff supplies suggestions, not additional mandatory requirements. The user's current instruction is to build in parts and defer ML and additional NLP enhancements.

## Proposed reprioritization after faculty feedback

The user authorized CSV batches, individual outputs, aggregate conclusions, and broader language coverage, then requested the web UI and a minimal API only where necessary. CSV/batch/export, language expansion, reporting, CSV upload, dashboard, individual review tables/traces, and report-table downloads are implemented. The API uses the existing server with one retained in-memory batch and synchronous bounded uploads; job queues/background lifecycle infrastructure were omitted under the user's latest preference. See `docs/web-dashboard.md` and the supporting functionality docs. The current suite has 115 passing tests.

For this scope, the proposed sequence is contracts/evaluation corpus -> batch engine -> measured compiler expansion -> aggregation/reporting -> local batch API -> dashboard UI. SQL/persistence and ML/LLMs remain deferred. The older parts below record the original sequence; persistence is no longer proposed as a prerequisite to bulk reporting.

## Part 1: compiler core and command-line demonstration

Status: implemented and validated on 8 October 2026. See `docs/validation.md`.

- Document a controlled review grammar and the six-category taxonomy.
- Implement source-preserving lexical analysis, predictive parsing, semantic analysis, SentiWordNet evaluation, and aspect-level IR.
- Support explicit hotel aspects, negation, intensifiers, contrast, and multiple opinions.
- Produce a readable report and a JSON trace of every compiler stage.
- Package the actual lexical data needed by the controlled vocabulary so analysis works offline.
- Verify representative positive, negative, neutral, mixed, partial, and unsupported reviews.

Exit criterion: `The room was not clean, but the staff were very helpful.` produces two records through the real pipeline, and automated regression checks pass.

## Part 2: persistence

Status: pending. The user requested a basic web demo ahead of this part, with no SQL or persistence.

Store reviews and aspect-level results in SQLite. Provide retrieval, category summaries, and tests for persistence and aggregation. Preserve the Part 1 entry point.

## Part 3: user interface and reporting

A basic local interface is implemented as of 12 October 2026: input, results, diagnostics, examples, vocabulary, five compiler traces, and manual JSON download. It uses the existing analysis function and stores nothing automatically. Start it with `scripts/serve.ps1`.

Persistent history remains future work. Category reporting is planned on in-memory batch results and does not require database integration.

Add single-review input, aspect results, expandable compiler traces, stored review history, and category-wise summaries. The interface calls the same compiler used by the CLI.

## Part 4: bulk input and final demonstration

CSV ingestion, per-row outcomes, coverage counts, complete traces, review/aspect exports, and 100/500-row validation are implemented. Category/issue reporting, local CSV upload, dashboard, 500 individual result rows, trace drill-down, and CSV/text report-table downloads were added on 13 October. Parsing is bounded by file/row limits; input is validated before analysis. TXT input is still outside the current CSV-focused implementation. Independently annotated real-review evaluation and repeated performance measurements are the remaining evidence work for the final report.

## IEEE-format course report preparation

The user needs an IEEE conference-template presentation after the project is complete, with no submission. Current paper-table exports preserve descriptive results, scopes/denominators, input/rule hashes, run environment, timing boundaries, and limitations. They contain no JSON. Do not treat authored contract success or synthetic 500-row throughput as real-world accuracy. Follow `docs/paper-results-plan.md` for independent annotation, held-out evaluation, repeated timing, and the final manuscript's results tables.

## Deferred

No embeddings, classifiers, LLM calls, trained POS tagging, dependency parsing, model training, implicit-aspect inference, or automatic taxonomy discovery. Revisit future scope after the planned deterministic system is complete.


## Completed: broad deterministic expansion — 14 October 2026

Expanded to 345 aspect phrases, 356 sourced opinion terms, 32 aliases and 315 genuine SentiWordNet rows. Added coordinated subjects/adjectives, possession, constrained experiential frames and retained context. Six categories remain; no ML/LLM/SQL. Original P/N remain visible with separate documented category preferences. Removed Demo Notes and expanded the single input to full width. All 136 tests pass. The unchanged 100-review development sample improves from 54% to 88% complete coverage; independent real-review accuracy remains future evidence work. See `docs/vocabulary-expansion.md`.
