# Team 17 project review guide

**14 October update:** See [the current vocabulary and scoring expansion](vocabulary-expansion.md): 345 aspect phrases, 356 opinion terms, 32 aliases, 315 source synsets, and 136 passing tests. Complete coverage on the unchanged authored 100-review development sample improved from 54% to 88%; this is not sentiment accuracy. The six categories remain unchanged. Older dated measurements below describe their original milestones.

Checked against the actual implementation on 13 October 2026. This guide describes the compiler core, CSV bulk processing, language expansion, aggregate conclusions, CSV upload/dashboard, and per-review table/trace views. Database history remains future scope. See `web-dashboard.md` and `paper-results-plan.md` for the latest UI and IEEE-format report evidence, alongside the functionality docs.

## 1. Your opening explanation

> Our project is an aspect-based hotel review analyzer built with a compiler-style architecture. A single hotel review can contain opposite opinions about different hotel aspects. We tokenize the review, parse a restricted grammar, associate opinions with aspects, apply modifiers, and use SentiWordNet for aspect-level sentiment. Its structured IR preserves opinions separately. The local web UI accepts single reviews or CSVs, shows one result row per uploaded review, and explains all five compiler stages. The dashboard summarizes category/issue feedback and links findings to supporting reviews. CSV report tables preserve scope, denominators, and provenance for our later IEEE-format presentation.

Example:

```text
The room was not clean, but the staff were very helpful.

Room  -> Cleanliness -> not clean    -> Negative -> -0.1250
Staff -> Helpfulness -> very helpful -> Positive -> +0.3125
Overall: Mixed
```

The contribution is the explicit aspect/opinion association and transparent staged processing. SentiWordNet is an existing lexical resource; we do not claim to have created it.

## 2. Problem, category, issue, and opinion

A whole-review label loses useful information: a positive staff experience can conceal a room complaint. The system retains these as separate records.

- **Aspect term:** the phrase occurring in the source, such as `room service` or `receptionist`.
- **Category:** the fixed group it maps to: Room, Staff, Service, Food, Cleanliness, Facilities.
- **Issue:** the specific topic, such as Cleanliness, Helpfulness, Taste, or WiFi.
- **Opinion term:** the lexical head, such as `clean` or `helpful`.
- **Opinion expression:** the head with modifiers, such as `not clean` or `very helpful`.
- **Polarity:** Positive, Negative, or Neutral for that record.
- **Score:** the project's numeric lexical sentiment measure after modifiers.

`The room was dirty` produces Room / Cleanliness. Cleanliness is an issue here, so we do not also invent a second Cleanliness category record. `Cleanliness was poor` has an explicit cleanliness subject and produces Cleanliness / Hygiene. This distinction is a taxonomy convention in the current implementation.

## 3. How execution reaches the logic

```text
python -m hotel_compiler
  -> hotel_compiler/__main__.py
  -> cli.py: main()
  -> pipeline.py: analyze_review()
     -> lexer.py: tokenize()
     -> parser.py: parse()
     -> semantics.py: analyze_semantics()
     -> sentiwordnet.py: evaluate(), once per semantic record
     -> models.py: AnalysisResult / AspectResult
  -> cli.py: table or JSON output
```

The Windows PowerShell launcher only finds Python and forwards arguments. It does not analyze text. The CLI is an input/output adapter. The public `analyze_review()` function contains the orchestration and is reused by the browser and CSV batch engine.

## 4. Walk through the example, stage by stage

### A. Input validation

`pipeline.py:15`, `analyze_review()` validates text type, the optional supplied review ID, and a 10,000-character limit. Empty text returns a diagnostic. It retains the original source text. If no review ID is supplied, it generates a UUID.

### B. Lexical analysis

`lexer.py:18`, `tokenize()` scans the review using a regular expression defined at line 9. It identifies candidate words, numbers, and punctuation, and uses the controlled vocabulary to assign token classes. Explicit aliases retain their original text and record a normalization rule.

For the example:

```text
The      DETERMINER
room     ASPECT
was      COPULA
not      NEGATION
clean    OPINION
,        COMMA
but      CONNECTOR
the      DETERMINER
staff    ASPECT
were     COPULA
very     INTENSIFIER
helpful  OPINION
.        END
```

A copula is a linking verb such as `is`, `was`, or `were`. An intensifier modifies strength, as `very` does.

Each token stores `kind`, normalized `value`, original `text`, and `start`/`end` positions. Positions are zero-based Python character indices, with an exclusive end: `source[start:end]` returns the original substring. They allow traceability and precise error messages.

Longest-match phrase recognition ensures `room service` becomes one ASPECT token, rather than identifying `room` separately. Case and common Unicode apostrophe/hyphen variants are normalized in values while original spans are preserved. Unknown words become WORD tokens; they are not deleted. `not` is never removed as a stopword.

`wasn't` / `wasn’t` becomes COPULA `was` plus NEGATION `not`, while retaining the original substrings. Supported copula contractions are `isn't`, `aren't`, `wasn't`, and `weren't`.

### C. Syntax analysis

`parser.py:35`, `_clause()` checks the order and structure of tokens. A simplified description of the main clause is:

```text
Clause    -> Subject Predicate | Predicate
Subject   -> [DETERMINER] ASPECT [COPULA]
Predicate -> [NEGATION] [INTENSIFIER] OPINION
```

Square brackets mean optional in this simplified presentation. The full factored grammar and selected FIRST/FOLLOW sets are in `docs/architecture.md`.

This is the original clause subset. Current additions include `ASPECT AUXILIARY NEGATION FUNCTION_VERB` (`AC does not work`) and opinion-before-aspect (`Very rude staff`). Auxiliaries require base verb forms; compatibility and selected adverbs are checked semantically. See `robustness.md` for the complete expanded shapes.

The parser is handwritten and predictive, using the next token class to choose its action. It uses recursive-descent-style methods and an iterative loop for review clauses; it does not use PLY, Yacc, or a generated parsing table.

`_peek()` inspects the next token, `_take()` requires and consumes a token class, and `_optional()` consumes an optional token. `_boundary()` at line 86 handles punctuation and connectors. The main `parse()` method at line 102 builds the AST and handles recovery.

The example produces two `Clause` nodes in a `ReviewAST`:

```text
ReviewAST
  Clause 1:
    subject = room
    opinion = clean
    negation = not
    intensifier = absent
  Clause 2:
    connector = but
    subject = staff
    opinion = helpful
    negation = absent
    intensifier = very
```

An AST preserves the structure relevant to later interpretation. We do not separately emit a complete concrete parse tree containing every grammar expansion and punctuation node.

### D. Semantic analysis

`semantics.py:7`, `analyze_semantics()` interprets the AST. It maps aspect terms to categories, determines issue labels, links each opinion to its subject, and attaches modifier attributes.

```text
Record 1: category=Room, issue=Cleanliness,
          opinion=clean, negated=True, intensity_multiplier=1.0

Record 2: category=Staff, issue=Helpfulness,
          opinion=helpful, negated=False, intensity_multiplier=1.25
```

Category and issue selection occurs at lines 28-32. Negation/intensity attributes are recorded at lines 47-49. The numeric score change happens later in `sentiwordnet.evaluate()`.

An aspect-specific issue takes precedence: `WiFi was slow` produces Facilities / WiFi. Otherwise the opinion label supplies the issue: `room was dirty` produces Room / Cleanliness.

Subject inheritance at lines 15-18 supports `The room was clean and quiet`: the second predicate has no repeated subject, but the previous explicit room subject can be inherited across the connector. Sentence ends, standalone commas, and parser recovery clear this context. Pronoun inference is not implemented.

The semantic distinction matters for `Helpful.`: its opinion expression can be parsed, but there is no explicit aspect. The result receives MISSING_ASPECT rather than an invented category.

### E. Sentiment evaluation

`sentiwordnet.py:54`, `evaluate()` looks up the configured opinion sense in the packaged lexical resource, computes its net score, applies an optional documented domain rule, then applies negation/intensity and assigns polarity.

The detailed calculation is in section 5 below.

### F. IR and output

`models.py:91`, `AspectResult` defines the aspect-level result. `to_ir()` at line 104 creates its dictionary representation. `AnalysisResult.to_dict()` at line 122 serializes the review, statuses, results, and diagnostics, optionally adding all compiler traces.

An IR record contains:

```text
review_id, category, issue, aspect_term, opinion_term,
opinion_expression, polarity, score, start, end
```

`ScoreEvidence` stores the exact synset, gloss, original scores, any calibration, modifier multipliers, and final score. The compact IR excludes this evidence; the full trace includes it.

`pipeline.py:40` computes the overall label over recognized opinions. Positive plus Negative yields Mixed. A positive result with optional neutral records yields Positive; a negative result with optional neutral records yields Negative; only neutral records yield Neutral; no records yield Unanalyzed. It does not average opposing scores into a neutral label.

`cli.py:12`, `_report()` prints the table. `cli.py:40`, `main()` parses options and chooses table or JSON output.

## 5. SentiWordNet: what it is and what we actually use

SentiWordNet adds positive, negative, and objective sentiment scores to WordNet senses. A synset represents a particular concept/meaning, so a word can belong to several synsets. A gloss is the short definition of that sense. WordNet's concept of a synset and SentiWordNet's score interface are described by the [Princeton WordNet documentation](https://wordnet.princeton.edu/) and [NLTK SentiWordNet documentation](https://www.nltk.org/howto/sentiwordnet.html).

Our runtime does not import NLTK. It reads genuine SentiWordNet 3.0 data directly from `hotel_compiler/resources/sentiwordnet.tsv`. The data came from the official NLTK corpus distribution. The subset has **42 original synset rows covering 44 canonical opinion terms**. Multiple terms can share a synset; seven explicit aliases normalize to configured opinions.

`domain.json` chooses the sense explicitly. For example:

```json
"clean": {"synset": "a:00417413", "issue": "Cleanliness"}
```

`a` is the adjective POS label. `00417413` is the WordNet 3.0 synset offset used by the resource; it is an identifier, not a score. This is controlled sense selection, not automatic word-sense disambiguation or POS tagging.

`load_synsets()` at `sentiwordnet.py:26` reads the resource, verifies its SHA-256 hash, parses the rows, and checks that configured opinions belong to their selected synsets. `@lru_cache(maxsize=1)` avoids reloading the vocabulary/resource on every review in a process. A hash checks data integrity; it does not prove sentiment accuracy.

### Scoring formula

```text
lexical_score = positive_score - negative_score
domain_score = lexical_score, unless a documented domain rule applies
negation_multiplier = -1 for negation, otherwise +1
raw_score = domain_score * intensity_multiplier * negation_multiplier
final_score = clip(raw_score, -1, +1)
```

The formula is implemented at `sentiwordnet.py:54`. Objective score is `1 - positive_score - negative_score`; it is reported as evidence but is not used as a confidence value or as a multiplier in the formula.

| Expression | Source P | Source N | Calculation | Final |
|---|---:|---:|---|---:|
| clean | 0.5 | 0.375 | 0.5 - 0.375 | +0.125 |
| not clean | 0.5 | 0.375 | (0.5 - 0.375) x -1 | -0.125 |
| helpful | 0.25 | 0 | 0.25 - 0 | +0.25 |
| very helpful | 0.25 | 0 | 0.25 x 1.25 | +0.3125 |
| extremely helpful | 0.25 | 0 | 0.25 x 1.5 | +0.375 |
| average | 0 | 0 | 0 - 0 | 0 |

Intensity factors in `domain.json:91`: very/highly/really = 1.25, extremely = 1.5. Scores above +0.05 are Positive, below -0.05 are Negative, otherwise Neutral. Clipping prevents an intensity factor from pushing the final score outside [-1, 1]. These factors and the threshold are documented project conventions; they have not been tuned on a labeled evaluation dataset. A score is not a probability or a percentage of confidence.

### The explicit slow rule

The correct physical-speed sense of `slow`, `a:00980527`, has P=N=0 in the source. For Service and Facilities, `domain.json:90` defines a hotel-domain complaint score of -0.5. Thus `Room service was slow` and `WiFi was slow` are Negative. `evaluate()` applies the adjustment and discloses it in the trace; original TSV scores remain unchanged. There are now five calibrated opinion entries: slow, functioning, comfortable, noisy, and spacious. Each has an explicit rule ID/reason. See `robustness.md` for source values and the surprising negative physical-comfort source row that requires a separate Room rule.

Be precise: -0.5 is our explicit domain rule, not a value returned by SentiWordNet. Other categories do not receive that adjustment. `fast` and `hot` currently remain Neutral in their selected senses. This is a limitation of lexicon-based sentiment and our initial controlled scoring policy.

### Why a subset and how to extend it

A subset makes the controlled prototype small and offline. It does not claim that the whole SentiWordNet database has only 42 senses or 44 terms.

`scripts/prepare_sentiwordnet.py:20` can fetch the pinned original archive, verify its hash, select exact configured POS/offset rows without changing their scores, and regenerate attribution/provenance. It is a maintenance script, not part of each analysis run. The resource license is CC BY-SA 3.0 and is preserved in `SENTIWORDNET_LICENSE.txt`.

To extend an aspect alias, update the aspect dictionary. To extend an opinion, choose a suitable SentiWordNet sense, add the opinion/issue mapping, regenerate the subset, and add a regression example. New sentence structures require parser/grammar changes, not just extra vocabulary.

## 6. Capabilities and honest limits

### Working now

- Command-line input, a basic local browser demo, and Python API.
- Six fixed categories, 53 aspect phrases, 44 canonical opinion terms, and seven explicit aliases.
- Optional determiner/copula in the supported pattern.
- `not`, `never`, four copula contractions, and `don't`/`doesn't`/`didn't` with supported functional verbs.
- `working`, `functioning`, `operational`, `out of order`, `works`, and `functions` for configured equipment targets.
- Opinion-before-aspect forms such as `Very rude staff`; selected `properly`/`well` and negated `at all`.
- `very`, `extremely`, `highly`, `really`.
- `and`, `but`, `however`, supported comma boundaries, and sentence punctuation.
- Multiple aspects and multiple opinion records for the same aspect.
- Multiple explicit sentences in one review.
- Longest-match phrases and preserved source positions.
- Genuine SentiWordNet scoring with explicit selected senses and transparent evidence.
- Table output, JSON IR, and optional full compiler trace.
- Diagnostics and clause-boundary recovery.
- CSV batches with separate individual results, validation failures, traces, and review/aspect/JSON exports; 100/500-row runs validated.
- Category/issue aggregates, distinct-review complaint counts, equal-review sentiment averages, and conclusions with supporting IDs. Primary scope uses complete reviews; recognized partial opinions have a separate view.
- CSV browser upload, dashboard charts, table filtering/pagination/all-row view, retained individual traces, and CSV/text report-table downloads. The visible output has no raw JSON.
- 115 tests: 24 original compiler/CLI, 14 single-review web, 27 CSV/batch/export, 20 robustness/evaluation, 18 aggregation/reporting, and 12 bulk web tests. All 500 individual HTTP results/traces are compared with standalone analysis.

### Not implemented yet

- SQLite persistence or saved history across server restarts. The server retains one batch in memory and writes no automatic review files.
- TXT batch input and background job queues; CSV upload/dashboard is implemented through a minimal synchronous local API. Single-review stdin still accepts one review.
- Review scraping or fetching.
- Full English grammar, arbitrary verbs, pronoun resolution, implicit-aspect detection, sarcasm, or temporal interpretation.
- Arbitrary verbs/modals such as `cannot work`; contractions only work within the supported equipment grammar.
- Trained models, embeddings, LLM calls, automatic POS tagging, or automatic sense disambiguation.
- Accuracy, precision, recall, or F1 measurements on an independently labeled real-world dataset.

### Status is different from sentiment

| Status | Meaning | Example |
|---|---|---|
| complete | Recognized records, no diagnostics | `The room was clean.` |
| partial | Some supported records and some diagnostics | `The room was odd but the staff were helpful.` |
| unsupported | No aspect-level records | `The room was glorp.` |

`glorp` is outside the opinion vocabulary. Unsupported means outside the implemented language, not that the customer is neutral. `The room was comfortable` now produces Room / Comfort / Positive through a disclosed domain rule. `The service was average` is a supported Neutral result. A partial review's overall label applies only to analyzed clauses.

## 7. Run the project on this Windows computer

### Browser demo

```powershell
Set-Location 'C:\Users\asus\Documents\ChatGPT\CD_Project'
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\serve.ps1
```

Open `http://127.0.0.1:8000` in your browser. Keep the terminal open; stop the server with Ctrl+C. Restart an older running server to load the new routes. **Single review** shows results/diagnostics and five compiler tabs. **CSV & dashboard** uploads data, shows consolidated charts and one result row per review, then retrieves individual traces on demand. Use the synthetic 12/100/500 buttons for a demo. **Review results CSV** exports all rows; **Report tables ZIP** exports scoped CSV/text evidence for the report. No raw JSON is displayed. The UI shares the CLI compiler and adds no database. Use `--port 8001` if needed.

### Command-line demo

Open PowerShell and enter:

```powershell
Set-Location 'C:\Users\asus\Documents\ChatGPT\CD_Project'
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run.ps1 "The room was not clean, but the staff were very helpful."
```

This command was verified on the current machine. The launcher skips Windows Store Python aliases and can use Codex's available bundled runtime. The ExecutionPolicy option is limited to that PowerShell process; no permanent setting change is made.

Show every stage:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run.ps1 "The room was not clean, but the staff were very helpful." --trace
```

Show machine-readable IR and trace:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run.ps1 "The room was not clean, but the staff were very helpful." --json --trace --review-id demo-17
```

With a normal Python 3.10+ installation, the equivalent portable command is:

```powershell
python -m hotel_compiler "The room was not clean, but the staff were very helpful." --trace
python -m unittest discover -s tests -v
```

On this computer, the test command can also use the verified bundled executable:

```powershell
& "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -X utf8 -m unittest discover -s tests -v
```

No dependency installation, API key, or internet connection is required for normal analysis. CLI exit codes: 0 complete, 1 partial/unsupported, 2 invalid arguments/resource error. In the web API, those analysis statuses are included in a normal HTTP 200 response; invalid HTTP/API requests receive appropriate error responses.

### CSV batch demo

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\batch.ps1 .\examples\bulk_demo.csv --output-dir .\output\batches\review-demo --progress
```

Open the exported `reviews.csv` for individual outcomes, `aspects.csv` for extracted opinions, and `batch.json` for all traces. `summary.json` contains aggregate metrics/evidence and `report.txt` contains readable conclusions. Add `--include-partial` for a separate secondary text view. The sample intentionally includes an unknown word, partial review, empty row, duplicate ID, and multiline review. Exit 1 means those issues were reported and results were exported. Re-running requires another output directory to protect existing files. See `bulk-usage.md` and `aggregation.md` for 100/500-row inputs, individual-result inspection, and aggregate rules.

## 8. A five-minute demonstration

Run the launcher with these review strings, in order:

1. `The room was clean.` -> Room / Cleanliness / Positive / +0.125.
2. `The room was not clean.` -> the same lexical head becomes Negative / -0.125.
3. `The staff were extremely helpful.` -> helpful's +0.25 becomes +0.375.
4. `The room was not clean, but the staff were very helpful.` -> two records, opposite polarities, overall Mixed. Add `--trace` to show the phases.
5. `Room service was slow.` -> longest-match Service category and the disclosed domain adjustment.
6. `The service was average.` -> supported Neutral.
7. `The room was odd but the staff were helpful.` -> partial analysis with a diagnostic and a retained positive Staff record.
8. Show the successful test run.

Do not improvise arbitrary English examples without first checking vocabulary and grammar. If a professor supplies unsupported language, show the diagnostic and explain the controlled scope rather than claiming universal language understanding.

## 9. Likely professor questions

**Why does this belong in Compiler Design?**

The implementation has explicit tokens, a grammar-driven parser, an AST, semantic attributes, structured IR, and phase-specific diagnostics. Its source language is restricted review text and its target is structured sentiment data. It demonstrates compiler front-end concepts; it does not generate executable machine code.

**What is the enhancement over a whole-review sentiment system?**

It retains separate aspect/opinion records, so negative room feedback is not hidden by positive staff feedback. The enhancement is a design built around the original SentiWordNet technique; we have not imported or modified a pre-existing legacy application's code.

**Does SentiWordNet find the aspects?**

No. The controlled vocabulary and semantic analyzer identify and associate aspects. SentiWordNet supplies lexical sentiment scores for configured opinion senses.

**Are you using machine learning or NLTK?**

No trained model runs in this project. We read actual SentiWordNet data directly. NLTK supplied the corpus distribution, but its Python library is not a runtime dependency. The compiler logic uses the Python standard library.

**Is there a custom DFA or Lex/Flex lexer?**

There is no handwritten DFA transition table or Lex/Flex executable. The lexer uses Python's regex scanner plus deterministic vocabulary and phrase-recognition rules. It demonstrates lexical-analysis concepts without claiming to implement the regex engine itself.

**What parser algorithm is used?**

A handwritten predictive, recursive-descent-style parser with one-token lookahead. Optional symbols are handled explicitly, and clause repetition uses a loop. It is not a generated LR/LALR parser, and there is no runtime FIRST/FOLLOW table generation.

**Why both a parser and semantic analysis?**

The parser recognizes valid arrangements and constructs clauses. Semantic analysis determines their domain interpretation and whether each opinion has an aspect. `Helpful.` illustrates a syntactically recognizable predicate with a semantic missing-aspect error.

**How do you prevent negation from affecting the next aspect?**

Negation is stored in an individual Clause node and applied only to its semantic record. It is not a global toggle for the review.

**What does but do? Does the second clause receive extra weight?**

It is a boundary/connector that preserves separate clauses. No special extra contrast weight is currently applied. Mixed sentiment is preserved in the overall label.

**How are issue labels selected?**

Through explicit vocabulary rules. A target-specific issue wins, such as Facilities / WiFi; otherwise the opinion's label is used, such as Room / Cleanliness.

**How are word senses selected?**

Each controlled opinion has a configured POS/offset ID. This is explicit domain sense selection, not an automatic context-disambiguation model. The selected gloss is visible in the trace.

**Are the numerical scores invented or hardcoded?**

The bundled P/N scores are actual unchanged SentiWordNet data. Multipliers, clipping, and thresholds are project rules. Five opinion entries have separate documented domain calibrations, including slow and physical room comfort. Aliases are explicit interpretations. The trace distinguishes normalization, original P/N, domain adjustments, and modifiers.

**Why not normalize by the sum of signed sentiment values?**

The current system scores each opinion directly. A denominator containing signed values can cancel or become zero. We avoid that formula and retain opposite aspect results rather than flattening them.

**Is a score of 0.75 a 75% accuracy/confidence estimate?**

No. It is a lexical sentiment measure under our scoring convention. Neither confidence nor accuracy has been calibrated from these values.

**How do you handle unknown words?**

They stay in the token stream. If the clause cannot match the grammar, it produces a syntax diagnostic and recovery continues at the next boundary. We preserve valid neighboring clauses and do not assign unknown language a neutral label.

**What is the IR and why have it?**

The IR is a consistent aspect-level record. It separates core interpretation from output/storage adapters, lets one review produce several records, and will provide a shared contract for persistence and UI work.

**Is there a symbol table or code optimization phase?**

There is no declaration/scoping symbol table or optimizer. The vocabulary is a lexicon, not a conventional programming-language symbol table. Those compiler phases are not required by this analysis task or current architecture.

**How do you know the project works?**

The suite has 115 tests covering the original examples, 100 authored contracts, modifier scope, source positions, compatibility, genuine source scores, batching, aggregate counts/averages, and conclusion evidence. Bulk HTTP checks compare all 500 individual results/traces to standalone analysis and verify paper CSV/ZIP outputs. Browser testing covers file upload, table pagination/filtering, chart drill-down, and detail views. Authored-case success and synthetic batching do not establish real-world ABSA accuracy.

**Can it process thousands of reviews or save results?**

It supports terminal and browser CSV batches, with a default limit of 1,000 rows and tested 100/500-row synthetic runs. Every input row has a table output, including invalid/unsupported inputs. The dashboard aggregates complete reviews, preserves Mixed, and counts internal review IDs; recognized partial opinions have a separate view. Clicking a finding/chart reveals its supporting rows and stored traces. Downloads are explicit CSV/text outputs. The server retains one batch in memory until clear, replacement, or restart; there is no SQL history.

**How is the overall batch conclusion calculated?**

Count one existing overall label per eligible review. For categories/issues, group opinions by internal review ID and retain Mixed when positive and negative opinions coexist. Average scores within each review first, then across reviews, so long reviews do not dominate. Primary results exclude partial/unsupported/invalid/failed rows; a separate recognized-opinion view includes partial rows. Unsupported inputs are never Neutral. Conclusions are fixed sentences built from these counts, with evidence IDs; no LLM is used. Low coverage, small counts, missing evidence, and ties are stated explicitly.

**What is the time complexity?**

For the current fixed vocabulary and maximum phrase length, the design scans tokens and clauses with bounded work per token, so processing grows approximately linearly with review length. Tokens/AST/results require memory proportional to input size. Resource loading is cached. This is an algorithmic explanation, not a benchmark result or a claim about all regex inputs.

**What are the main limitations?**

Restricted vocabulary and grammar, manually configured senses, simplified negation/intensity, and no pragmatic context. For example, `not very helpful` uses deterministic sign reversal/intensity, which does not perfectly reflect conversational nuance. Sarcasm, pronouns, implicit aspects, and context-sensitive preferences are not resolved.

**What comes next?**

Collect independently annotated target reviews for held-out extraction/polarity evaluation and controlled repeated timing, then use those results in the IEEE-format course report. Additional grammar work should follow measured failures. SQL, background job infrastructure, ML, and additional NLP models remain deferred.

## 10. Code map to keep beside you

| Logic | File and starting line | Function / data |
|---|---|---|
| Entry point | `hotel_compiler/__main__.py:1` | Calls CLI main |
| CSV validation | `hotel_compiler/csv_input.py` | `read_review_csv()` |
| Bulk orchestration | `hotel_compiler/batch.py` | `analyze_csv()` / `analyze_batch()` |
| Batch results and coverage | `hotel_compiler/batch_models.py` | `BatchResult` / `RowOutcome` |
| Explicit exports | `hotel_compiler/exports.py` | `export_batch()` |
| Category/issue aggregates | `hotel_compiler/aggregation.py` | `aggregate_batch()` / `_view()` / `_group()` |
| Conclusions and supporting IDs | `hotel_compiler/reporting.py` | `build_report()` / `_conclusions()` / `render_report()` |
| Batch terminal adapter | `hotel_compiler/batch_cli.py` | `main()` |
| Local web server | `hotel_compiler/web.py` | HTTP adapter calling the existing pipeline |
| One retained CSV batch | `hotel_compiler/web_batch.py` | `BatchStore` / `BatchSession` |
| Upload, charts and per-review table | `hotel_compiler/web_assets/dashboard.js` | Upload / `renderDashboard()` / `renderReviewTable()` / `loadDetail()` |
| Report evidence CSV/ZIP | `hotel_compiler/paper_tables.py` | `paper_tables()` / `paper_archive()` |
| Browser rendering and trace tabs | `hotel_compiler/web_assets/app.js` | API submission and DOM presentation |
| Browser layout | `hotel_compiler/web_assets/index.html` and `styles.css` | Input, results, diagnostics, and trace sections |
| Input, options, output | `hotel_compiler/cli.py:40` | `main()` |
| Readable report | `hotel_compiler/cli.py:12` | `_report()` |
| Pipeline and validation | `hotel_compiler/pipeline.py:15` | `analyze_review()` |
| Overall label | `hotel_compiler/pipeline.py:40` | Presence of record polarities |
| Token scanner | `hotel_compiler/lexer.py:9` | `_LEXEME` regex |
| Token classes, normalization, longest match | `hotel_compiler/lexer.py:18` | `tokenize()` |
| Clause grammar | `hotel_compiler/parser.py:35` | `_clause()` |
| Clause boundaries | `hotel_compiler/parser.py:86` | `_boundary()` |
| Review AST and recovery | `hotel_compiler/parser.py:102` | `ReviewParser.parse()` |
| Aspect association and modifiers | `hotel_compiler/semantics.py:7` | `analyze_semantics()` |
| Category/issue choice | `hotel_compiler/semantics.py:28` | Aspect/opinion lookup |
| Resource verification/loading | `hotel_compiler/sentiwordnet.py:26` | `load_synsets()` |
| Sentiment formula | `hotel_compiler/sentiwordnet.py:54` | `evaluate()` |
| Stage structures | `hotel_compiler/models.py:8` | Frozen dataclasses |
| IR record | `hotel_compiler/models.py:91` | `AspectResult` |
| JSON and stage trace | `hotel_compiler/models.py:122` | `AnalysisResult.to_dict()` |
| Vocabulary validation/loading | `hotel_compiler/vocabulary.py:9` | `validate_vocabulary()` / `load_vocabulary()` |
| Categories and aspect dictionary | `hotel_compiler/resources/domain.json:2` | Taxonomy/aliases |
| Opinion senses/issues | `hotel_compiler/resources/domain.json:58` | Opinion dictionary |
| Explicit slow rule | `hotel_compiler/resources/domain.json:90` | Calibration configuration |
| Aliases and functional verb forms | `hotel_compiler/resources/domain.json:139` | Explicit normalization rules |
| Modifier words/factors | `hotel_compiler/resources/domain.json:154` | Negations/intensifiers |
| Evaluation metrics and corpus | `hotel_compiler/evaluation.py` / `examples/robustness_cases.json` | Labeled contract comparison |
| Real lexical scores | `hotel_compiler/resources/sentiwordnet.tsv:27` | Source data columns/rows |
| Resource preparation | `scripts/prepare_sentiwordnet.py:20` | `prepare()` |
| Windows launch | `scripts/run.ps1:1` | Python discovery and forwarding |
| Core regressions | `tests/test_pipeline.py:8` | `CompilerTests` |
| CLI regressions | `tests/test_cli.py:19` | `CommandLineTests` |
| Demonstration cases | `examples/reviews.json:1` | 24 manually specified cases |

For studying, read pipeline.py first, then lexer.py, parser.py, semantics.py, sentiwordnet.py, and models.py. Read the domain vocabulary beside these modules; it contains many of the project's explicit domain decisions.
