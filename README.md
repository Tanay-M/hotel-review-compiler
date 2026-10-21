# Team 17 - Hotel Review Compiler

A deterministic, compiler-style aspect-based hotel review analyzer for a Compiler Design course project.

**Research and demo update:** The SentiWordNet compiler and independent TextBlob grammar / VADER–TextBlob hybrid are available in the UI and research runner, with five-band labels, source verification, tables and figures. See [the run guide](docs/research-run-guide.md), [module pseudocode](docs/implemented-modules-and-pseudocode.md), and [Booking vocabulary expansion](docs/hybrid-vocabulary-expansion.md). Whole-text scoring stays separate from aspect sentiment. The hybrid has 671 aspect phrases and 497 reviewed lexical forms; the original baseline remains frozen.

**Paper and datasets (21 October):** [IEEE paper, Word](output/paper/Team_17_IEEE_Conference_Paper.docx), [PDF](output/paper/Team_17_IEEE_Conference_Paper.pdf), [figure/table bundle](output/paper/Team_17_Paper_Figures_and_Tables.zip), and [real CSV datasets](output/datasets/README.md) are included. The expanded hybrid obtains 85/148 correct (57.43%, macro-F1 0.3999) versus baseline 42/148 (28.38%, 0.2260) on the inspected SemEval adaptation. Tuple-F1 falls versus the earlier hybrid; all results are development measurements. The newer Booking Italy cohort was audited for hybrid vocabulary coverage only, not a two-system accuracy comparison. See [dataset provenance and licenses](data/README.md). Non-commercial dataset licenses remain separate from project code.

For the faculty review, open [the complete project reference](docs/complete-project-reference.md): all recognized vocabulary, grammar and phase rules, original SentiWordNet scores and domain adjustments, status labels, dashboard mean calculations, diagnostics, examples, and code locations in one file.

**The compiler core, CSV upload/dashboard, and independent hybrid are implemented.** The browser now offers the original SentiWordNet compiler and the independent TextBlob grammar / VADER–TextBlob hybrid. Both support single reviews, per-row CSV results, dashboard summaries, traces and downloads. A single-review comparison runs both methods on the same original text. SQL, LLM calls and new trained-model development remain deferred.

## Browser demo

Start the local server from a terminal in the project directory:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\serve.ps1
```

Then open **http://127.0.0.1:8000** in your browser. Keep the terminal open while using the demo; press **Ctrl+C** there to stop it. With an installed Python 3.10+ runtime, `python -m hotel_compiler.web` is equivalent. Use `--port 8001` if port 8000 is occupied.

Choose **VADER + TextBlob hybrid** (default) or **SentiWordNet compiler baseline** before analyzing text or uploading a CSV. **Compare both methods** shows a same-review comparison with separate result/trace buttons. The five trace tabs are **Tokens, Syntax, Semantics, Scoring, IR**. Hybrid traces show POS/phrase chunks, independent attachment, original component scores, evidence-normalized fusion, domain rules, subjectivity and five strength bands. Its whole-text lexical result stays separate from the recognized-aspect mean. Baseline traces retain original SentiWordNet P/N and its predictive parser. See [hybrid demo instructions](docs/web-hybrid-demo.md).

Each review also has a **Review score**: the mean of its final opinion scores, rounded to six decimals in [-1,+1] and displayed to four decimals. The Mixed label is preserved even when opposite scores cancel. Partial scores are marked **recognized opinions only**; reviews without opinion results show an unavailable score, with an empty numeric CSV cell. This field appears in single/batch results and CSV/report downloads. The dashboard category Mean index still averages category-specific review means across eligible reviews.

Select **CSV & dashboard** to upload a UTF-8 CSV or try 12/100/500-row synthetic demos. Use `examples/hotel_reviews_100.csv` for a simple input: exactly `sr.no` and `review`, with 100 distinct review rows. The form defaults to these header names; no results or annotations are required in the input. Every submitted row has its own table result, filters, pagination/all-row display, and stored result/trace drill-down. The dashboard visualizes coverage, overall sentiment, category distributions, and complaint frequency, with evidence-backed findings and category tables. Clicking a chart filters the supporting reviews. Download the whole review table as CSV or report tables as a CSV/text ZIP for your later IEEE-format report. No raw JSON is displayed or downloaded by the UI. See `docs/web-dashboard.md` and `docs/paper-results-plan.md`.

The local-only server uses the selected analyzer and retains one batch in memory until clear, replacement, or restart. Refresh clears the displayed view. No database or automatic review files are written. Uploads run synchronously with a busy indicator; concurrent CSV uploads receive a readable busy response while other requests remain available. There is no job queue. This is a course demonstration server.

## Run it

Python 3.10 or newer is required. The baseline has no third-party runtime dependencies. The hybrid needs the research extras (already installed in this computer's `.venv`): `python -m pip install -e ".[research]"`. Neither analyzer requires API keys or network calls during analysis. The required genuine SentiWordNet data is packaged with the project.

From the project directory:

```powershell
python -m hotel_compiler "The room was not clean, but the staff were very helpful."
```

On this Windows computer, the launcher can also locate Codex's bundled Python if no normal Python installation is available:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run.ps1 "The room was not clean, but the staff were very helpful."
```

The execution policy option applies to that invocation only. It does not change the machine's settings. Alternatively, use `py -3` in place of `python` if the standard Windows Python launcher is installed.

Expected result:

```text
Category | Issue       | Opinion      | Polarity | Score
Room     | Cleanliness | not clean    | Negative | -0.1250
Staff    | Helpfulness | very helpful | Positive | +0.3125

Overall: Mixed
```

### Compiler demonstration and JSON

```powershell
python -m hotel_compiler "Room service was slow." --trace
python -m hotel_compiler "The room was not clean, but the staff were very helpful." --json --trace --review-id demo-17
```

`--trace` exposes tokens and positions, the clause AST, semantic attributes, actual SentiWordNet scores and selected senses, modifier adjustments, and final IR records. It is useful for the course demonstration.

Omitting review text prompts for one review in an interactive terminal, or reads one review from standard input. Multiple sentences may be included in that review. Use the separate CSV entry point below for batches.

Exit codes: **0** = complete analysis, **1** = partial or unsupported review (with structured diagnostics), **2** = invalid arguments or a resource error.

## CSV bulk analysis

From the project directory, analyze the included mixed-outcome sample:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\batch.ps1 .\examples\bulk_demo.csv --output-dir .\output\batches\sample-run --progress
```

With a normal Python runtime, the equivalent command is:

```powershell
python -m hotel_compiler.batch_cli examples/bulk_demo.csv --output-dir output/batches/sample-run --progress
```

The CSV needs a `review_text` header; `review_id` is optional. UTF-8/BOM, quoted commas, quotes, and multiline text are supported. Select alternate headers using `--text-column comment --id-column id`. Defaults allow 1,000 data rows, 10 MiB per file, and 10,000 characters per review. `--max-rows` changes the row limit explicitly.

Every CSV record gets a unique internal row ID. Duplicate reviews/external IDs remain separate and are flagged. Readable but empty, oversized, or wrong-width rows receive validation results while other rows continue. Unsupported language retains the original compiler's diagnostics. Malformed CSV, unreadable encoding, missing required headers, and file/row limit violations reject the file before analysis.

The chosen output directory receives:

- **reviews.csv:** one row per input review, original text, status, overall sentiment, joined aspect results, diagnostics, and identity.
- **aspects.csv:** one row per extracted opinion, linked through `row_id`; partial-result scope stays visible.
- **batch.json:** every individual result, its full compiler trace, input/rules fingerprints, and coverage counts.
- **summary.json:** complete-review and separate complete-plus-partial metrics, conclusions, denominators, and supporting row/record identities.
- **report.txt:** readable primary conclusions, coverage/support notes, and category/issue complaints.

CSV text/ID cells that could be interpreted as spreadsheet formulas receive a leading apostrophe. CLI JSON preserves original text and IDs exactly. Existing export files are protected: choose a new output directory for another run. There is no database or automatic export from the Python analyzer. Browser CSV/table downloads are explicit and generated in memory.

Batch exit codes: **0** all reviews complete; **1** results exported but at least one row is partial, unsupported, invalid, or failed; **2** file/argument/resource/export error. The current 12-row sample intentionally produces exit 1 (9 complete, 1 partial, 1 unsupported, 1 invalid). Its `not working` row is now supported; `glorp` is the unknown-word example.

Primary conclusions use complete reviews only. Category/issue counts use distinct internal review IDs; Mixed is retained. Average indices first average within each review, then across reviews. Unsupported/invalid inputs never become Neutral. Add `--include-partial` for a separately labeled secondary terminal/text view; JSON always includes both scopes. See `docs/aggregation.md` for rules and evidence inspection, and `docs/bulk-usage.md` for individual outputs and 100/500-row generation. Coverage percentages measure supported language, not prediction accuracy.

## Supported input

- Six categories: Room, Staff, Service, Food, Cleanliness, Facilities.
- Controlled aspect/opinion vocabulary in `hotel_compiler/resources/domain.json`.
- Optional article and linking verb: `Room clean` and `The room was clean` both work.
- Negation: `not`, `never`, and copula contractions such as `wasn't` / `wasn’t`.
- Intensifiers: `very`, `extremely`, `highly`, `really`, `slightly`, `quite`, `a bit`, and other explicit degree phrases.
- Multiple clauses: `but`, `and`, `however`, commas, and sentence punctuation.
- Repeated opinions for one explicit aspect: `The room was clean and quiet.`
- Longest-match phrases: `room service`, `air conditioning`, and `wi fi`.
- Independent sentences: `The room was dirty. The staff were helpful.`
- Equipment states/verbs: `The AC was not working.`, `The WiFi does not work.`, `The heater didn't function.`
- Configured phrases/aliases: `out of order`, `comfy`, `busted`, `work`/`works`, `function`/`functions`.
- Opinions before aspects: `Very rude staff.`, `A comfortable bed.`
- Selected functional adverbs: `working properly`, `functions well`; negative emphasis: `did not work at all`.
- Inherited copula/auxiliary predicates: `The WiFi works but doesn't work well.`
- Coordinated subjects/adjectives: `The room and bathroom were clean and spacious.`; `Clean and quiet room.`
- Introductions, retained context, and possession: `I found the room clean when we arrived.`; `The room had a comfortable bed.`
- Explicit experiential targets: `I was pleased with the service.`

New opinion families have compatibility guards: `staff were working` is outside equipment scoring. There are 345 aspect phrases, 356 canonical opinion terms, 32 explicit aliases, and 315 genuine source synsets. Location and Value/Price remain outside the six categories. See [the expansion guide](docs/vocabulary-expansion.md) for grammar, evidence, scoring rules, limitations, and code locations. Restart the browser server after code/resource changes.

Unknown words are retained in the token stream. Unsupported clauses produce diagnostics; subsequent supported clauses can still produce results. An unanalyzed opinion is never silently converted into neutral sentiment.

## Python API

The independent VADER–TextBlob research system now has its own TextBlob grammatical extraction and evidence-aware sentiment fusion. It does not use this compiler's vocabulary/parser. See [the hybrid implementation and pseudocode](docs/independent-hybrid.md) and [research commands](docs/research-run-guide.md). The WebUI below still uses SentiWordNet. New comparison evidence is under `output/experiments/2026-10-15/independent-hybrid-v2/`.

```python
from hotel_compiler import analyze_review

result = analyze_review("The room was dirty but the staff were helpful.", "r-17")
print(result.status)                  # complete
print(result.overall)                 # Mixed
print(result.to_dict())               # JSON-compatible IR/report
print(result.to_dict(include_trace=True))
```

The same function is used by the CLI, browser adapter, and bulk engine. It has no storage or UI side effects. Source positions are zero-based Python character offsets; `text[start:end]` extracts the span. These are character positions, not byte offsets.

## Validate it

```powershell
python -m unittest discover -s tests -v
python -m compileall -q hotel_compiler scripts tests
```

`examples/reviews.json` contains 24 original cases. `examples/robustness_cases.json` adds 100 authored language contracts, including rejections and reserved recombinations. The suite has 145 tests: nine review-score tests, 21 expanded-vocabulary/grammar/scoring tests plus 24 original compiler/CLI, 14 single-review web, 27 CSV/batch/export, 20 robustness/evaluation, 18 aggregation/reporting, and 12 bulk web tests. Checks include all 500 individual HTTP results/traces, one-row-per-review CSVs, paper ZIP tables, mappings/Unicode, limits, memory lifecycle, and concurrent requests. These demonstrate contracts, not real-world accuracy. Web tests need localhost permission inside a network-restricted sandbox.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\evaluate.ps1 .\examples\robustness_cases.json
```

## Scoring and limitations

SentiWordNet scores are read directly from the official resource; NLTK is not required at runtime. Opinion senses are statically configured: existing senses are preserved, and new terms use the first ranked adjective sense unless an explicit hotel-context override applies. No NLP model predicts senses.

Base score = positive score - negative score. Negation reverses its sign, intensifiers multiply it, and the final score is clipped to [-1, 1]. A magnitude at most 0.05 is Neutral. Positive and negative results produce an overall Mixed label without cancelling into Neutral.

Explicit category preferences cover 73 terms across 100 adjustments, retaining the five original calibrations. Original SentiWordNet P/N and lexical score remain unchanged and visible beside the separate domain score and rule. `fresh` has category-specific senses. `working` uses its positive equipment sense (P=0.25, N=0); negation gives -0.25. Lexically neutral `fast` has a positive Service/Facilities preference; `hot` has a negative Room-temperature preference and remains lexically neutral. These preferences are project conventions, not SentiWordNet values. See [the scoring explanation and audit manifest](docs/vocabulary-expansion.md).

This version recognizes a **restricted review language**, not general English. It retains selected explicit time/context phrases but does not infer implicit aspects/pronouns, sarcasm, unrestricted temporal relations, arbitrary verbs/modals, or complicated negation. `not bad` and `not very helpful` use deterministic conventions without pragmatic inference. Supported contractions are `isn't`, `aren't`, `wasn't`, `weren't`, and `don't`/`doesn't`/`didn't` with configured functional verbs. `cannot work`, `not only ... but also ...`, and repeated negation remain diagnosed.

See `docs/architecture.md` for the grammar, phase boundaries, and scoring convention. See `BUILD_PLAN.md` for the remaining build parts.

## Resource attribution

The packaged SentiWordNet subset contains 315 original synset rows covering 356 controlled opinion terms and configured contextual senses, with source scores unchanged. It is distributed under **Creative Commons Attribution-ShareAlike 3.0**; attribution/license are in `hotel_compiler/resources/SENTIWORDNET_LICENSE.txt`. Provenance and SHA-256 hashes are in `hotel_compiler/resources/provenance.json`.

Baccianella, S., Esuli, A., and Sebastiani, F. (2010). *SentiWordNet 3.0: An Enhanced Lexical Resource for Sentiment Analysis*. LREC.

The curated vocabulary builder is `python scripts/expand_hotel_vocabulary.py`; it also generates `hotel_compiler/resources/opinion_senses.csv`. To obtain the verified upstream archive or reproduce the currently configured subset:

```powershell
python scripts/prepare_sentiwordnet.py --download
```

This maintenance operation downloads the official NLTK corpus archive and verifies its pinned checksum before selecting rows. Normal analysis is fully offline. The original archive is excluded from Git.

