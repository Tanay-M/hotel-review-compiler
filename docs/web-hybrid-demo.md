# Independent hybrid in the demo UI

Implemented 18 October 2026. This exposes the existing research hybrid; it does
not change either sentiment algorithm or regenerate the saved paper results.

## Start

From the project folder:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\serve.ps1
```

Open http://127.0.0.1:8000/. Restart an older server and refresh the page to load
the new code. The launcher prefers `.venv`, which already has the hybrid tools.
On another computer, first install `python -m pip install -e ".[research]"`.
No API key, hosted LLM, database or external analysis service is used.

## Single review and comparison

1. Select **VADER + TextBlob hybrid** or **SentiWordNet compiler baseline**.
2. Enter text and select **Analyze review**.
3. **Compare both methods** runs the two independent paths on the same text.
   Use either **Show results & trace** button to inspect that method.
4. See per-context polarity, five-band strength, score, status and diagnostics.
5. The hybrid separately displays its whole-review lexical score and aspect mean.

Example: `The air conditioning wasn't working, but the staff were helpful.`
The hybrid records Facilities failure and positive Staff sentiment separately.
The review remains Mixed even if its arithmetic mean is close to zero.

Hybrid trace tabs:

- **Tokens:** Pattern POS tags, phrase chunks and original source spans.
- **Syntax:** noun phrases and clause segments; no baseline AST is claimed.
- **Semantics:** attached aspect, category, grammar rule and inherited targets.
- **Scoring:** VADER scores, TextBlob polarity/subjectivity/assessments, lexical
  evidence, fusion before domain rules, matched rule, final result and errors.
- **IR:** final context records, including unavailable scores.

The [vocabulary expansion](hybrid-vocabulary-expansion.md) adds a Scoring-tab
panel showing original scores, canonical scoring text and alias matches. Input
wording and grammar spans remain unchanged. Its Booking input is split into five
files under `output/experiments/2026-10-18/booking-vocabulary/inputs/`, retaining
the existing 1,000-row limit. Upload `booking_italy_part_01.csv` through
`booking_italy_part_05.csv` using columns `sr.no` and `review`.

## CSV and dashboard

Select the method, then **CSV & dashboard**. Upload a UTF-8 file with `sr.no` and
`review`; edit column names if the file uses other headers. Every submitted row
has a table entry, including invalid, unsupported and failed rows. **View result
& trace** opens the stored evidence for that row without rerunning the model.

Real input files already available locally:

- `output/datasets/real_hotel_demo_100.csv` — selected demonstration sample.
- `output/datasets/real_hotel_random_200.csv` — broader eligible random sample.
- `output/datasets/semeval_hotels_266_sentences.csv` — original benchmark text;
  its human annotations are kept separately and are not submitted to the models.

Built-in demo buttons are explicitly synthetic. Do not label them real data.

The retained dashboard is labeled with its actual analysis method. Changing the
selector affects the next run; it does not reinterpret an existing batch.
Charts offer complete-only and complete-plus-partial scopes. Unscored contexts
remain in individual results but do not enter category sentiment means/counts.
The hybrid review aspect mean stays unavailable if any extracted context lacks
a score. Completeness and coverage are heuristic processing measures, not accuracy.

## Downloads and implementation

Single-review CSV records method, score scope, net strength and whole-text score.
Batch review CSV has one row per input; aspect CSV retains all contexts.
**Report tables ZIP** contains scoped summaries and method metadata. Hybrid runs
add `hybrid_evidence.csv` with component scores, original spans, attachment pattern,
fusion and contextual rules. No accuracy/F1 is invented for unannotated uploads.
Use the offline research runner for annotated evaluation and paper experiments.

`hotel_compiler/web_analysis.py` adapts the existing `hybrid.py` result contract.
`web.py` routes the selected method; `web_batch.py` retains its batch in memory.
`web_assets/hybrid.js` renders hybrid traces and the live comparison. Neither the
baseline lexer/parser nor its opinion list is used to produce hybrid predictions.
