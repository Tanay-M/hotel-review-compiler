# CSV bulk milestone: usage and code map

CSV ingestion, individual outputs, explicit exports, and coverage reporting were implemented on 12 October 2026. Batches use the same expanded compiler as single reviews; see `robustness.md`. Reporting, browser upload/dashboard, and CSV/text paper-table downloads were added on 13 October; see `aggregation.md` and `web-dashboard.md`. Background job infrastructure remains deferred under the user's minimal-API preference.

## Run a batch

```powershell
Set-Location 'C:\Users\asus\Documents\ChatGPT\CD_Project'
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\batch.ps1 .\examples\bulk_demo.csv --output-dir .\output\batches\my-first-batch --batch-id demo --progress
```

The PowerShell launcher finds an installed Python or the available bundled runtime. Python 3.10+ is sufficient; no dependency installation, API key, network, or database is needed. Portable equivalent:

```powershell
python -m hotel_compiler.batch_cli examples/bulk_demo.csv --output-dir output/batches/my-first-batch --batch-id demo --progress
```

Each invocation performs the entire CSV validation before running the compiler. Existing output files are never overwritten; use a new directory for a new export.

## CSV contract

```csv
review_id,review_text
R001,"The staff were extremely helpful."
R002,"The food was bland; the staff were courteous."
R003,"The air conditioning was not working."
```

- Header names are case-sensitive after trimming surrounding whitespace. Text defaults to `review_text`; missing default `review_id` is allowed.
- For another schema, select `--text-column comment --id-column id`. Explicit non-default ID columns must exist.
- Required encoding is UTF-8 or UTF-8 with BOM. In Excel, choose CSV UTF-8. Other encodings are rejected rather than guessed.
- Quoted commas, escaped quotes, multiline reviews, and CRLF are parsed by Python's CSV reader. Original review text is retained, including Unicode and newlines.
- Extra columns are recorded as ignored metadata; ratings never influence sentiment.
- Limits: 1,000 data records by default, 10 MiB per file, 10,000 characters per review. `--max-rows` changes the row cap; API `CSVLimits` can configure row/file caps. File/row cap violations reject the entire file before sentiment analysis.
- Readable rows with a cell-count mismatch, missing/blank review, or oversized text become `invalid_input`. Other rows continue. Empty CSV records are retained as invalid records.
- Missing/duplicate/blank headers, no data, undecodable bytes, and malformed quoting reject the file. Recovering arbitrary broken quoting would risk assigning the wrong review to an ID.
- Blank external IDs are treated as absent. Nonblank IDs are preserved without trimming. Duplicate IDs/text are flagged on all matching rows, not merged; whitespace/case differences in text are not silently normalized for deduplication.
- Row number means CSV record ordinal, not physical line. Source line start/end are reported separately for multiline fields. A repeated caller ID cannot collide with the internal `batch_id:000001` row identity.

## Read individual outputs

Open `reviews.csv` for one record per input row and `aspects.csv` for opinion-level rows. Join on `row_id`, not the caller's potentially duplicated `review_id`.

The comprehensive `batch.json` contains a `rows` array. Each item holds original text, validation/execution status, an optional `analysis` object, and its five-stage trace. `summary.json` adds category/issue metrics, scoped conclusions, and supporting row/record identities; `report.txt` provides readable primary conclusions. Add `--include-partial` to also display a separately labeled partial-inclusive text view. CSV formula-leading strings are prefixed with an apostrophe for spreadsheet safety; JSON holds the unmodified source.

Inspect the third review and its trace in PowerShell:

```powershell
$taskBatchResults = Get-Content .\output\batches\my-first-batch\batch.json -Raw -Encoding UTF8 | ConvertFrom-Json
$taskBatchResults.rows[2] | ConvertTo-Json -Depth 100
```

Array indices start at zero. The sample's third review is now complete: Facilities / Air Conditioning / Negative, score -0.25. The 12-row fixture also includes a deliberate unknown word (`glorp`), a partial review, and an invalid input to demonstrate inspection of failures.

Input validation is separate from compiler status:

| Execution status | Analysis status | Meaning |
|---|---|---|
| analyzed | complete | All recognized clauses succeeded |
| analyzed | partial | Supported results plus diagnostics; overall covers recognized clauses only |
| analyzed | unsupported | No supported opinion records; overall is Unanalyzed, not Neutral |
| invalid_input | absent | Row failed CSV/review validation; compiler was not called |
| processing_error | absent | Unexpected per-review exception; later reviews still attempted |

A corrupt shared lexical resource aborts the job instead of creating one failure per review. Interruptions propagate. Exit 0 means every row complete; exit 1 means usable exports with rows needing inspection; exit 2 means invalid file/arguments/resources or incomplete export.

## Coverage summary

The terminal and JSON report submitted/analyzed/invalid/error counts, complete/partial/unsupported counts, extracted opinion count, and flagged duplicate-row counts. Coverage denominators exclude invalid/processing-error rows and are named explicitly:

```text
complete coverage = complete / analyzed rows
extraction coverage = (complete + partial) / analyzed rows
```

When no row is analyzed, the percentages are null/unavailable. Neither measure is real-world accuracy. Sentiment summaries now use complete reviews as their primary scope and expose recognized opinions from partial reviews separately. See `aggregation.md` for distinct-review counting, Mixed handling, equal-review averages, denominator definitions, and evidence references.

## Generate 100/500-row demonstration files

The generator repeats the mixed-outcome fixture with unique caller IDs. Its output is synthetic, includes repeated text and deliberate unsupported/invalid inputs, and cannot establish language accuracy.

```powershell
python scripts/generate_bulk_demo.py --rows 100 --output output/batches/new-100.csv
python scripts/generate_bulk_demo.py --rows 500 --output output/batches/new-500.csv
python -m hotel_compiler.batch_cli output/batches/new-500.csv --output-dir output/batches/new-500-results --progress
```

On this computer, if `python` is unavailable, replace it with:

```powershell
& "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -X utf8
```

Append the script/module arguments on the same line. Generated files and exports are ignored by Git under `output/batches/`.

## Python API

```python
from hotel_compiler.batch import analyze_csv
from hotel_compiler.exports import export_batch

batch = analyze_csv("examples/bulk_demo.csv", batch_id="demo")
print(batch.summary())
row = batch.get_row("demo:000002")
print(row.to_dict(include_trace=True))
paths = export_batch(batch, "output/batches/api-example")
```

Analysis alone writes nothing. `export_batch` is explicit. Batch metadata includes a source-file SHA-256, analysis code/rules/resource fingerprint, creation time, and analysis duration. Creation times/durations vary; row identities and analysis are reproducible with an explicit batch ID. Each individual trace describes the retained result, not a recomputed interpretation.

## Code map

| File | Responsibility |
|---|---|
| `hotel_compiler/csv_input.py` | UTF-8 decoding, CSV structure, limits, source lines, row issues, duplicate flags |
| `hotel_compiler/batch.py` | Resource preflight/fingerprint, per-row compiler calls, progress, exception isolation |
| `hotel_compiler/batch_models.py` | Unique row identity, stored outcomes/traces, coverage counts, serialization/detail lookup |
| `hotel_compiler/exports.py` | Review/aspect CSV, full JSON, summary JSON/text; formula safeguards; protected file creation |
| `hotel_compiler/aggregation.py` / `reporting.py` | Distinct-review metrics, separate scopes, and evidence-backed conclusions |
| `hotel_compiler/batch_cli.py` | Terminal arguments, status output, explicit export, exit codes |
| `scripts/batch.ps1` / `scripts/run.ps1` | Windows runtime discovery and argument forwarding |
| `scripts/generate_bulk_demo.py` | Synthetic input generation only |
| `tests/test_batch.py` | Ingestion, status/equivalence, exports, failure isolation, 100/500 rows, CLI |

The existing `pipeline.py::analyze_review` remains the only core analyzer. No category or opinion logic is copied into the bulk layer.
