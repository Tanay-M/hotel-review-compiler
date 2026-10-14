# Compiler architecture and language contract

The original Part 1 grammar is preserved below as a historical subset. The current expanded grammar, compatibility guards, vocabulary counts, and additional scoring rules are documented in [vocabulary-expansion.md](vocabulary-expansion.md) (14 October, current) and `robustness.md` (12 October, earlier milestone).

## Purpose and pipeline

The source input is a hotel review in a deliberately restricted English-like language. Its output is aspect-level sentiment IR rather than machine code. The implementation demonstrates explicit lexical, syntactic, and semantic phases; it is a compiler-inspired analyzer, not a full natural-language compiler.

```text
Original review text
  -> lexer.tokenize          -> source-spanned token stream
  -> parser.parse            -> ReviewAST + syntax diagnostics
  -> analyze_semantics       -> aspect/opinion records + semantic diagnostics
  -> sentiwordnet.evaluate   -> polarity/score + lookup and scoring evidence
  -> AnalysisResult          -> aspect-level IR, report, and optional trace
```

`pipeline.analyze_review` is the public integration boundary. It is deterministic apart from generating a review ID when the caller omits one; supply an ID for reproducible serialized output. It does not write to disk or perform network requests. Each result retains the original source text.

The parser constructs one AST. Semantic analysis then annotates the parsed information into separate semantic records. A second parse tree after semantic analysis is unnecessary.

## Lexical contract

Token types: ASPECT, OPINION, FUNCTION_VERB, DETERMINER, COPULA, AUXILIARY, NEGATION, INTENSIFIER, ADVERB, EMPHASIS, CONNECTOR, INTRODUCTION, CONTEXT, POSSESSION, POST_MODIFIER, RELATION, RELATION_TARGET, COMMA, END, WORD, NUMBER, PUNCTUATION.

The lexer uses a regular-expression scanner and longest-match recognition of known aspect phrases. It retains unknown words and punctuation instead of dropping them. It normalizes case and common Unicode apostrophes/hyphens in token values while keeping token text and offsets in the original review. There is no stopword-removal stage: dropping `not` would change the meaning, and ignoring arbitrary words would allow false parses.

Known copula contractions are split into COPULA and NEGATION tokens. For example, `wasn’t` becomes `was` and normalized `not`, with original substrings `was` and `n’t`. Semantic output expands the opinion expression to `not clean` for readability while the trace retains the original contraction spans.

## Original Part 1 grammar

The following factored grammar describes the supported clauses and boundaries. Terminals are the token classes above. EOF is the logical end of the token stream. END covers `.`, `!`, `?`, and `;`. Epsilon is written as `epsilon`.

```text
Review            -> Clause Tail EOF
Tail              -> ConnectorBoundary Clause Tail
                   | Terminator EndTail
                   | epsilon
EndTail           -> Clause Tail | epsilon
ConnectorBoundary -> CONNECTOR CommaOpt | COMMA ConnectorOpt
ConnectorOpt      -> CONNECTOR CommaOpt | epsilon
CommaOpt          -> COMMA | epsilon
Terminator        -> END TerminatorTail
TerminatorTail    -> END TerminatorTail | epsilon

Clause            -> Subject Predicate | Predicate
Subject           -> DeterminerOpt ASPECT CopulaOpt
DeterminerOpt     -> DETERMINER | epsilon
CopulaOpt         -> COPULA | epsilon
Predicate         -> NegationOpt IntensifierOpt OPINION
NegationOpt       -> NEGATION | epsilon
IntensifierOpt    -> INTENSIFIER | epsilon
```

Predicate-only clauses let `The room was clean and quiet` parse as two opinion clauses. Whether the second clause has a valid subject is a semantic question: an earlier explicit subject can be inherited across a connector in the same sentence. `Helpful.` by itself parses as an opinion expression but receives a MISSING_ASPECT diagnostic.

The parser makes predictive decisions from the next token's class. Selected FIRST/FOLLOW sets illustrate why the clause/modifier productions are unambiguous:

| Nonterminal | FIRST (excluding epsilon) | FOLLOW relevant to optional production |
|---|---|---|
| Subject | DETERMINER, ASPECT | NEGATION, INTENSIFIER, OPINION |
| Predicate | NEGATION, INTENSIFIER, OPINION | CONNECTOR, COMMA, END, EOF |
| DeterminerOpt | DETERMINER | ASPECT |
| CopulaOpt | COPULA | NEGATION, INTENSIFIER, OPINION |
| NegationOpt | NEGATION | INTENSIFIER, OPINION |
| IntensifierOpt | INTENSIFIER | OPINION |
| Tail | CONNECTOR, COMMA, END | EOF |
| EndTail | DETERMINER, ASPECT, NEGATION, INTENSIFIER, OPINION | EOF |

Negation precedes intensity: `not very clean` is supported. Multiple negations or repeated intensifiers are rejected rather than guessed. The current parser additionally supports copulas and auxiliaries at the start of inherited predicates; see the expanded productions in `robustness.md`.

Recovery is deliberately outside the success grammar. On a failed clause, the parser skips to a boundary and attempts the next clause. It reports the unsupported source span. It does not extract an opinion from an otherwise failed clause or quietly delete unrecognized words. Recovery also clears inherited subject context, preventing a later word from being attached to a stale aspect.

## Semantic rules

1. An explicit aspect term selects one of the six fixed categories.
2. Longest-match `room service` selects Service, not Room.
3. A specific target such as WiFi selects its issue label. Otherwise the opinion selects the issue: `room was dirty` is Room / Cleanliness, not two category records.
4. Negation and intensifier attributes attach only to the opinion expression in their clause.
5. A predicate-only clause may inherit the immediately available explicit subject across `and`, `but`, or `however`.
6. Sentence ends, standalone commas, and syntax recovery reset inheritance. No pronoun or implicit-aspect inference is performed.
7. Each recognized opinion produces one record. Several records may share a category. The engine does not claim one record equals one review.

The lexicon defines a controlled language. New equipment and domain-specific predicates enforce explicit aspect/category compatibility; `staff were working` is rejected rather than scored as equipment. Older entries do not form a complete semantic type system: `food was slow` retains its lexically neutral result. Adverb applicability and negated `at all` are also checked before scoring.

## SentiWordNet and scoring

SentiWordNet is a lexical resource, not the aspect extractor. The compiler supplies the aspect/opinion association. Each controlled opinion points to a configured SentiWordNet 3.0 POS/offset ID; the current builder uses the first adjective sense unless an explicit domain override applies. The selected source row contains positivity, negativity, terms with sense numbers, and a gloss. The data preparation script checks the original archive hash, selects these exact rows, and preserves their scores.

Let P and N be the source positive and negative scores:

```text
lexical_score = P - N
domain_score  = lexical_score, unless an explicit category-specific rule applies
negation      = -1 if negated, otherwise +1
raw_score     = domain_score * intensity_multiplier * negation
score         = clip(raw_score, -1, +1)
```

Intensity multipliers: very/really/highly = 1.25; extremely = 1.5; no intensifier = 1.0. Scores are rounded to six decimal places. Scores above 0.05 are Positive, below -0.05 are Negative, otherwise Neutral. These are project conventions, not calibrated probabilities or psychological measurements.

The original Part 1 domain calibration is `slow` in Service or Facilities -> -0.5. Its appropriate physical-speed sense (`a:00980527`) has source P=N=0. This rule makes the required `Room service was slow` and `WiFi was slow` examples useful without misrepresenting the source resource. The expanded vocabulary adds four documented rules for functioning, comfortable, noisy, and spacious. Rule IDs/reasons, original P/N, and adjusted scores appear separately in the sentiment trace; see `vocabulary-expansion.md` and the `resources/opinion_senses.csv` audit for current senses and rules. The five-rule description here records the earlier milestone; the current expansion adds explicit category preferences and contextual senses. No statistical or learned model is used.

Example source data and resulting scores:

| Expression | Synset | P | N | Modifier | Final score |
|---|---|---:|---:|---|---:|
| clean | a:00417413 | 0.5 | 0.375 | none | +0.125 |
| not clean | a:00417413 | 0.5 | 0.375 | negation | -0.125 |
| very helpful | a:01195536 | 0.25 | 0 | x1.25 | +0.3125 |
| dirty | a:00419289 | 0 | 0.75 | none | -0.75 |
| average | a:01594146 | 0 | 0 | none | 0 |
| slow (Service) | a:00980527 | 0 | 0 | explicit domain rule | -0.5 |

The overall result is a label over recognized opinions: Positive + Negative -> Mixed; positive with optional neutral -> Positive; negative with optional neutral -> Negative; only neutral -> Neutral; no records -> Unanalyzed. No signed-score normalization is used. For partial analysis, the overall label applies only to the supported clauses.

## IR and failure contract

Each result record contains:

```text
review_id, category, issue, aspect_term, opinion_term,
opinion_expression, polarity, score, start, end
```

`opinion_term` is the lexical head (`clean`); `opinion_expression` retains its modifiers (`not clean`). Span start/end delimit the source clause, including the aspect when it is explicit. In inherited clauses the span delimits the opinion clause, and semantic trace records `aspect_inherited=true` and the inherited aspect term.

Analysis statuses:

- **complete:** at least one record, no unsupported clauses or semantic diagnostics.
- **partial:** some records, plus diagnostics. Consumers must show the incomplete status.
- **unsupported:** no aspect-level records. This is different from Neutral.

Empty reviews return EMPTY_INPUT diagnostics. Invalid argument types, empty supplied IDs, or inputs above 10,000 characters raise an API error. Missing or inconsistent lexical resources raise ResourceError; the CLI converts it to a readable error and exit code 2. The trace is optional in serialized output, so future UI consumers can show final results independently of compiler internals.

## Modules

| Module | Responsibility |
|---|---|
| models.py | Stage records, final IR, serialization |
| vocabulary.py | Cached controlled vocabulary loading |
| lexer.py | Tokenization and source spans |
| parser.py | Grammar recognition, AST, recovery |
| semantics.py | Aspect association, issue labels, modifiers |
| sentiwordnet.py | Validated lexical resource and score evidence |
| pipeline.py | Public analysis function and overall status |
| cli.py | Report and JSON adapter |

The browser dashboard and CSV bulk engine use this pipeline. There is no SQL database or runtime ML. Explicit exports are file outputs rather than database persistence; the web server holds only one batch in memory.

## Local browser demo (12 October 2026)

`web.py` adds a standard-library HTTP adapter to the existing public pipeline. `POST /api/analyze` accepts a JSON review and returns the same result/trace serialization as the CLI. Complete, partial, and unsupported reviews all receive HTTP 200 because they are valid analysis outcomes; malformed requests receive a readable HTTP error. `GET /api/config` exposes the actual controlled vocabulary and example inputs.

Static assets in `web_assets/` implement review input, result tables, diagnostics, and five stage tabs. The syntax tab renders AST clause cards; the scoring tab separates original P/N values from domain rules, negation, intensity, and clipping. The IR tab shows the actual final records. All review/API strings are rendered as DOM text, not HTML. Source-span rendering accounts for Python's Unicode character indices.

The server binds only to loopback and serves a fixed asset whitelist. It limits request bodies, validates input, and rejects foreign host/origin requests. No SQL, automatic filesystem persistence, or browser local storage is added. The UI now uses CSV downloads and tabular IR rather than raw JSON. One batch is retained in server memory for detail/download requests, as described below. There are no new runtime dependencies. Start with `python -m hotel_compiler.web` or `scripts/serve.ps1`.

## CSV bulk boundary (12 October 2026)

`csv_input.read_review_csv` performs bounded UTF-8 ingestion and whole-file structural validation before analysis. CSV record identity is separate from physical source lines and potentially duplicated caller IDs. Readable invalid rows retain their position and receive input issues.

`batch.analyze_csv` delegates each valid row to the shared `analyze_review`; `BatchResult` retains each outcome and full trace. Resource errors abort the job; other per-review exceptions become processing-error rows. Invalid, partial, and unsupported rows never become neutral through the bulk adapter. Metadata identifies input bytes and analysis code/resources; explicit row IDs make duplicate records safe to join.

`exports.export_batch` writes review-level CSV, aspect-level CSV, JSON with full traces, summary JSON, and a readable report on explicit request. Files use exclusive creation, protect existing results, and clean only newly created outputs on failure. Spreadsheet-leading formula strings are escaped in CSV; JSON preserves source strings. See `bulk-usage.md` for contracts and code map. Execution remains sequential, with measured 100/500-row tests; no new runtime dependencies or UI routes are added.

## Aggregation and reporting boundary (13 October 2026)

`aggregation.aggregate_batch` consumes retained results rather than source text. Primary metrics use complete reviews; a separate view includes recognized opinions from partial reviews. It groups by internal row identity and category/issue, preserves Mixed using the core presence convention, counts any-negative complaints once per review/group, and computes averages within reviews before averaging across reviews. Unsupported/invalid/failed rows never enter sentiment denominators. No mentions produce null averages/percentages, not Neutral.

`reporting.build_report` generates deterministic sentences with explicit scopes, counts, denominators, supporting row IDs, and record indices. It adds limited coverage, duplicate, low support, no-data, and tie wording. Compiler and reporting code have separate fingerprints. `summary.json` retains both scopes; `report.txt` and CLI show primary conclusions by default, with `--include-partial` enabling the separate secondary section. See `aggregation.md` for formulas, thresholds, API, and evidence inspection. The subsequent web boundary is described below.

## CSV dashboard and paper-table boundary (13 October 2026)

The adopted web API is minimal: synchronous CSV submission, retained overview, ordinal-based row detail, CSV/ZIP downloads, and clear. `csv_input.parse_review_csv` is the shared in-memory parsing contract behind file and browser input. `web_batch.BatchStore` rejects simultaneous CSV analysis, atomically replaces one successful in-memory run, preserves an older run on failed upload, and holds full traces without recomputation. Other HTTP requests remain available in the existing threaded server. No job queue, polling lifecycle, or automatic result files are added.

`dashboard.js` displays every submitted row with pagination/all-row selection, search and filters, then uses exact evidence row IDs for chart-to-table drill-down. Only one selected row's full trace is fetched. Charts and tables use the same reporting metrics and explicitly selected scope. All values enter the DOM as text; SVG attributes render chart geometry. The existing single-review input and trace renderer remain available.

`paper_tables.py` builds CSV/text evidence and a ZIP in memory. Review CSVs now include readable joined aspect/opinion outcomes while retaining exactly one row per input. Category/issue/coverage tables carry scopes and denominators; metadata carries rule/input hashes, environment, and observed timing boundaries. No uploaded-data accuracy is fabricated from unlabeled reviews. See `web-dashboard.md` and `paper-results-plan.md`.
