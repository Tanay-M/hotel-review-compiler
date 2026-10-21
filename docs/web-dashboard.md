# CSV dashboard and review table - 13 October 2026

**18 October update:** The [hybrid demo](web-hybrid-demo.md) adds the independent VADER–TextBlob method to single reviews and CSV uploads, component/grammar traces, five strength bands, same-review comparison and method-labeled downloads. The existing baseline remains selectable. Hybrid dependencies use the research extras; the older baseline milestone below remains recorded as originally implemented.

**14 October update:** See [the current vocabulary and scoring expansion](vocabulary-expansion.md): 345 aspect phrases, 356 opinion terms, 32 aliases, 315 source synsets, and 136 passing tests. Complete coverage on the unchanged authored 100-review development sample improved from 54% to 88%; this is not sentiment accuracy. The six categories remain unchanged. Older dated measurements below describe their original milestones.

The existing local Python server now provides single-review analysis, CSV upload, a consolidated dashboard, and a tabular result for every submitted row. There are no new runtime dependencies, SQL tables, external model calls, or hosted services. The API is the small connection required between browser controls and the Python compiler, with no background job queue.

## Open it

```powershell
Set-Location 'C:\Users\asus\Documents\ChatGPT\CD_Project'
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\serve.ps1
```

Open `http://127.0.0.1:8000`. If an older server is still running, stop it with Ctrl+C first and start this command again. `--port 8001` selects another local port. Keep the terminal open while using the UI.

Select **CSV & dashboard**. Choose/drop a UTF-8 CSV, adjust the review-text/ID header names if needed, and click **Analyze CSV**. The form defaults are `review` and `sr.no`. The downloadable `examples/hotel_reviews_100.csv` contains exactly those two columns and 100 distinct synthetic hotel reviews; the **100 reviews** button uses this same input. No categories, sentiment labels, scores, or expected results belong in this input file: the application computes them. For existing `review_text` / `review_id` files, set those header names in the form; a missing `review_id` column is allowed. The shared reader supports Unicode/BOM, quoted commas, multiline text, and original source preservation. Limits remain 1,000 data records, 10 MiB, and 10,000 characters per review. A structurally invalid file produces an error without replacing the previous successful batch. Readable invalid rows retain their own table output.

The 100-review sample contains distinct, nonblank review texts, including language outside the current grammar. The 12/500-review stress demos also include repeated text and deliberately invalid rows. These synthetic examples demonstrate operation; they are not independent evidence of natural-language accuracy.

## Individual outputs

The table has one row per submitted review: ordinal, caller ID, original text, all recognized aspect/opinion results, overall label, analysis/execution status, and a **View result & trace** button. Repeated caller IDs remain separate and flagged. Multiple extracted opinions appear together in their original review's result cell.

Search text, IDs, categories, issues, or opinion expressions. Filter status, overall polarity, and category. Use pagination or **All rows**; a 500-row upload has 500 accessible result rows. Unsupported/invalid rows remain present rather than being dropped or labeled Neutral. An invalid input shows validation errors and no fabricated compiler trace.

Opening a row retrieves its retained result, including all five stages, without reanalysis. Tokens, clause fields, semantics, scoring evidence, and final IR have human-readable tables/cards. P/N, aliases, domain rule IDs/reasons, modifiers, and source spans remain visible. There is no raw JSON panel or JSON download in the UI. Single-review downloads also use a one-row CSV.

## Dashboard

- Summary cards show all submitted rows, complete rows, rows needing inspection, and extracted opinion count.
- Overall sentiment counts preserve Mixed. The coverage chart includes every submitted row, including invalid/failed inputs.
- Category bars show review-level distributions among mentions, not counts of opinions.
- Complaint bars rank distinct-review negative mentions by frequency, retaining ties; Mixed counts once as a complaint.
- Category tables show denominators, positive/negative/mixed/neutral counts, complaint prevalence, equal-review average indices, and evidence support.
- Deterministic findings have buttons for their supporting reviews. Clicking a chart or finding filters the individual table to the relevant row IDs. **Reset filters** returns to the whole dataset.

The primary scope is complete reviews. A separately labeled selector includes complete and partial reviews using recognized opinions only. Table filters never silently change dashboard totals. Low coverage, duplicate rows, low support, and absent categories remain visible. See `aggregation.md` for formulas and thresholds.

## Downloads and IEEE report evidence

**Review results CSV** includes exactly one row per submitted review, with original text, status, overall label, categories, issues, opinion expressions, and a readable joined aspect-result field. It exports the entire dataset regardless of table filters/pagination.

**Report tables ZIP** contains seven UTF-8 CSV files: reviews, extracted aspects, category summary, issue summary, overall summary, coverage, and run metadata; plus conclusions and explanatory text. It contains no JSON. Both aggregation scopes and percentage denominators are explicit. Metadata includes source SHA-256, compiler/reporting fingerprints, creation time, Python/platform, observed core duration, timing boundaries, and the absence of gold-label accuracy measurements. Empty numeric cells mean unavailable. Formula-leading strings are escaped for spreadsheet use.

These tables support descriptive results in the later IEEE-format course report. They do not automatically establish accuracy, produce a star rating, draft the paper, or submit it. See `paper-results-plan.md` for the evaluation evidence still required before making empirical claims.

## Minimal local API and memory lifecycle

| Endpoint | Purpose |
|---|---|
| `POST /api/analyze` | Existing single-review result and trace |
| `POST /api/batches?text_column=...&id_column=...` | Raw CSV body, shared validation/analysis, lightweight results and report |
| `GET /api/batches/{id}` | Retained overview; no full trace array |
| `GET /api/batches/{id}/reviews/{ordinal}` | One stored row and full trace |
| `GET /api/batches/{id}/download/reviews` | One-row-per-review CSV |
| `GET /api/batches/{id}/download/aspects` | Opinion-level CSV |
| `GET /api/batches/{id}/download/paper` | CSV/text report ZIP |
| `DELETE /api/batches/{id}` | Explicitly clear the retained batch |

CSV uploads complete synchronously in the existing threaded HTTP server. Only one CSV analysis can run at a time; another receives a readable busy response. Health, existing detail, and single-review requests remain available. No worker/queue, polling states, automatic history, or disk writes are introduced. One successful batch is retained until replacement, clear, or server restart. Page refresh clears the displayed view; there is no saved browser history/local storage. A new successful upload makes old batch IDs unavailable. Download results before replacing/restarting if you need to retain them.

Loopback binding, host/origin checks, fixed static routes, bounded input bodies, and safe text rendering remain. All downloads are built in memory; browser downloads are explicit user actions. For batches that become slow in real use, background processing can be considered separately.

## Code and validation

`csv_input.parse_review_csv` gives file and browser uploads the same contract. `web_batch.BatchStore` retains one immutable result and report. `web.py` supplies upload/detail/download routes. `paper_tables.py` generates CSV/text evidence. `dashboard.js` renders charts, scopes, filters, pagination, and table rows. `app.js` renders individual results and all compiler stages. `exports.py::batch_csv_bytes` shares the table format with CLI exports.

All 115 tests pass, including 12 new bulk HTTP tests. Tests fetch and compare all 500 individual outputs/traces to standalone analysis, verify 100-row CSV and ZIP contents, mapping/Unicode/BOM/multiline handling, exclusions, limits, replacement/clear, busy behavior, and endpoint checks. Browser testing also verified real file selection, a bad-column error preserving the old batch, 500-row pagination/all-row view, review 500, search, negative-chart drill-down, scopes, invalid input detail, and a successful ZIP download. Responsive preview was inspected at narrow and desktop widths, with no browser error/warning logs. Python compilation and both JavaScript syntax checks pass.

Dashboard design draws on the table tasks of finding, comparing, inspecting, and acting on records described in [NN/g's data-table guidance](https://www.nngroup.com/articles/data-tables/). The implementation uses an overview-to-evidence flow, explicit filters, and accessible labeled values rather than relying on color alone.

## Review score

Single-review summaries and the batch table show Review score, the mean of that review's final opinion scores. The scoring trace shows the method and count. Mixed labels remain even when the mean is zero. Partial scores are marked recognized opinions only; unsupported, invalid and failed rows show a dash and a blank numeric CSV cell. Single-review CSV and batch/report reviews.csv include review_score and review_score_scope. Category Mean index continues to average category-specific review means in the selected scope.
