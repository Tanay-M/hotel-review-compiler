"use strict";

let batch = null;
let csvFile = null;
let batchBusy = false;
let page = 1;
let evidenceIds = null;
let detailRequest = 0;
const polarities = ["Positive", "Negative", "Mixed", "Neutral"];
const colors = {Positive: "#427b60", Negative: "#bd5b47", Mixed: "#b98b32", Neutral: "#81959b",
  complete: "#427b60", partial: "#b98b32", unsupported: "#81959b", invalid_input: "#bd5b47", processing_error: "#8c597e"};

function setMode(mode) {
  if (busy || batchBusy) return;
  $("single-workspace").hidden = mode !== "single";
  $("bulk-workspace").hidden = mode !== "batch";
  $("single-mode").setAttribute("aria-pressed", String(mode === "single"));
  $("batch-mode").setAttribute("aria-pressed", String(mode === "batch"));
  resetResults();
  $("results-section").hidden = mode !== "single";
  $("results-title").textContent = "Aspect-level results";
  detailRequest++;
}
$("single-mode").addEventListener("click", () => setMode("single"));
$("batch-mode").addEventListener("click", () => setMode("batch"));

function uploadError(message) {
  $("upload-error").textContent = message;
  $("upload-error").hidden = !message;
}
function selectFile(file) {
  if (!file) return;
  if (file.size > 10 * 1024 * 1024) { csvFile = null; $("csv-file").value = ""; $("file-label").textContent = "Choose a CSV or drop it here"; uploadError("Choose a CSV no larger than 10 MiB."); return; }
  csvFile = file;
  $("file-label").textContent = `${file.name} · ${(file.size / 1024).toFixed(1)} KiB`;
  uploadError("");
}
$("csv-file").addEventListener("change", (event) => selectFile(event.target.files[0]));
$("drop-zone").addEventListener("dragover", (event) => { event.preventDefault(); $("drop-zone").classList.add("dragging"); });
$("drop-zone").addEventListener("dragleave", () => $("drop-zone").classList.remove("dragging"));
$("drop-zone").addEventListener("drop", (event) => { event.preventDefault(); $("drop-zone").classList.remove("dragging"); if (!batchBusy) selectFile(event.dataTransfer.files[0]); });

function setBatchBusy(value) {
  batchBusy = value;
  document.querySelectorAll("#csv-form input, #csv-form button, [data-demo], #real-booking-demo, .mode-tabs button, #clear-batch, #analysis-method").forEach((control) => { control.disabled = value; });
  $("csv-form").setAttribute("aria-busy", String(value));
  $("upload-button").textContent = value ? "Analyzing CSV…" : "Analyze CSV →";
  $("upload-status").textContent = value ? "Uploading and analyzing every row. Results will appear when complete." : "One batch retained in memory. New successful uploads replace it; restarting the server clears it.";
}

async function uploadCSV(columns = null) {
  if (batchBusy) return;
  if (!csvFile) { uploadError("Choose a CSV or use the real Booking demo."); return; }
  uploadError("");
  setBatchBusy(true);
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 120000);
  try {
    if (!columns) {
      const header = (await csvFile.text()).replace(/^\uFEFF/, "").split(/\r\n|\n|\r/, 1)[0];
      const names = header.split(",").map((name) => name.trim().replace(/^"|"$/g, ""));
      columns = {textColumn: names.includes("review") ? "review" : "review_text",
        idColumn: names.includes("sr.no") ? "sr.no" : "review_id"};
    }
    const query = new URLSearchParams({text_column: columns.textColumn, id_column: columns.idColumn, method: $("analysis-method").value});
    const response = await fetch(`/api/batches?${query}`, {method: "POST", body: csvFile,
      headers: {"Content-Type": "text/csv", "X-File-Name": encodeURIComponent(csvFile.name)}, signal: controller.signal});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "The CSV could not be analyzed.");
    batch = data;
    detailRequest++;
    resetResults();
    $("results-section").hidden = true;
    $("dashboard-scope").value = "complete_reviews";
    clearFilters();
    renderDashboard();
    $("batch-output").hidden = false;
    $("dashboard-title").scrollIntoView({behavior: "smooth", block: "start"});
  } catch (failure) {
    uploadError(failure.name === "AbortError" ? "The upload request timed out. Check the local server before retrying." : failure.message);
  } finally { clearTimeout(timeout); setBatchBusy(false); }
}
$("csv-form").addEventListener("submit", (event) => { event.preventDefault(); uploadCSV(); });
document.querySelectorAll("[data-demo]").forEach((button) => button.addEventListener("click", async () => {
  if (batchBusy) return;
  setBatchBusy(true);
  try {
    const isReviewSample = button.dataset.demo === "100";
    const response = await fetch(isReviewSample ? "/reviews_100.csv" : `/api/demo.csv?rows=${button.dataset.demo}`);
    if (!response.ok) throw new Error("Could not load the demo CSV.");
    selectFile(new File([await response.blob()], isReviewSample ? "hotel_reviews_100.csv" : `synthetic-${button.dataset.demo}.csv`, {type: "text/csv"}));
    setBatchBusy(false);
    await uploadCSV();
  } catch (failure) { setBatchBusy(false); uploadError(failure.message); }
}));

$("real-booking-demo").addEventListener("click", async () => {
  if (batchBusy) return;
  setBatchBusy(true);
  try {
    const response = await fetch("/api/real-demo.csv");
    if (!response.ok) throw new Error("The cleaned Booking dataset is unavailable. Upload its local CSV instead.");
    selectFile(new File([await response.blob()], "booking_italy_cleaned_demo_500.csv", {type:"text/csv"}));
    setBatchBusy(false);
    await uploadCSV();
  } catch (failure) { setBatchBusy(false); uploadError(failure.message); }
});

function svgNode(tag, attributes) {
  const element = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [key, value] of Object.entries(attributes)) element.setAttribute(key, String(value));
  return element;
}
function bar(label, count, denominator, color, action, detail = "") {
  const button = node("button", "bar-item");
  button.type = "button";
  const heading = node("span", "bar-heading");
  heading.append(node("span", "", label), node("strong", "", detail || `${count} / ${denominator}`));
  const svg = svgNode("svg", {viewBox: "0 0 300 9", preserveAspectRatio: "none", "aria-hidden": "true"});
  svg.append(svgNode("rect", {width: 300, height: 9, rx: 4, fill: "#edf0e8"}), svgNode("rect", {width: denominator ? 300 * count / denominator : 0, height: 9, rx: 4, fill: color}));
  button.append(heading, svg);
  button.setAttribute("aria-label", `${label}: ${count} of ${denominator}. View supporting reviews.`);
  button.disabled = !count;
  button.addEventListener("click", action);
  return button;
}
function applyEvidence(ids, label) {
  clearFilters(false);
  evidenceIds = new Set(ids);
  $("evidence-filter").hidden = false;
  $("evidence-filter").textContent = `Supporting reviews: ${label}. Reset filters to return to all submitted rows.`;
  page = 1;
  renderReviewTable();
  $("review-table-section").scrollIntoView({behavior: "smooth", block: "start"});
}
function currentView() { return batch.report.aggregation.views[$("dashboard-scope").value]; }
function renderDashboard() {
  if (!batch) return;
  const report = batch.report;
  const aggregation = report.aggregation;
  const counts = aggregation.coverage.counts;
  const view = currentView();
  const scopeLabel = view.scope === "complete_reviews" ? "Complete reviews" : "Complete + partial; recognized opinions only";
  $("dataset-label").textContent = `${batch.method_label} · ${batch.input.source_name} · ${counts.submitted.toLocaleString()} submitted rows · analyzed in ${batch.elapsed_seconds.toFixed(3)} s`;
  renderNeuralDashboard();
  renderRoutedDashboard();
  $("scope-description").textContent = `${view.eligible_reviews} eligible reviews. ${scopeLabel}. Unsupported, invalid, and failed rows stay outside sentiment counts.`;
  const cards = $("metric-cards");
  cards.replaceChildren();
  for (const [label, value, note] of [["Submitted reviews", counts.submitted, "Every CSV record has its own table row"],
    [batch.routed_summary ? "Original hybrid Complete" : "Completely analyzed", counts.complete, `${aggregation.primary_complete_share_submitted_percent ?? "—"}% of submitted · ${aggregation.coverage.coverage.complete_percent ?? "—"}% of analyzed`],
    [batch.routed_summary ? "Original hybrid needs inspection" : "Need inspection", counts.submitted - counts.complete, "Partial, unsupported, invalid or failed"],
    ["Extracted opinions", counts.extracted_opinions, "Complete and partial reviews combined"]]) {
    const card = node("article", "metric-card");
    card.append(node("span", "small-label", label), node("strong", "", value.toLocaleString()), node("span", "", note));
    cards.append(card);
  }
  $("coverage-notes").replaceChildren(...report.notes.map((note) => node("p", "", note)));
  $("overall-caption").textContent = `${batch.neural_summary ? "Original hybrid: " : ""}${view.eligible_reviews} eligible reviews in the selected scope. Mixed is preserved.`;
  $("overall-chart").replaceChildren(...polarities.map((polarity) => bar(polarity, view.overall_counts[polarity], view.eligible_reviews, colors[polarity],
    () => applyEvidence(view.overall_row_ids[polarity], `${scopeLabel} / overall ${polarity}`))));
  const coverage = $("coverage-chart");
  coverage.replaceChildren(...["complete", "partial", "unsupported", "invalid_input", "processing_error"].map((status) => bar(status.replaceAll("_", " "), counts[status], counts.submitted, colors[status], () => {
    applyEvidence(batch.rows.filter((row) => (row.analysis?.status || row.execution_status) === status).map((row) => row.row_id), `All submitted / ${status}`);
  })));
  const categoryChart = $("category-chart");
  categoryChart.replaceChildren();
  for (const group of view.categories) {
    const button = node("button", "category-bar");
    button.type = "button";
    const caption = node("span", "bar-heading");
    caption.append(node("strong", "", group.category), node("span", "", group.mentioned_reviews ? `${group.mentioned_reviews} reviews${group.evidence_status === "low_support" ? " · low support" : ""}` : "Not mentioned"));
    const svg = svgNode("svg", {viewBox: "0 0 300 14", preserveAspectRatio: "none", "aria-hidden": "true"});
    svg.append(svgNode("rect", {width: 300, height: 14, rx: 4, fill: "#edf0e8"}));
    let x = 0;
    for (const polarity of polarities) {
      const width = group.mentioned_reviews ? 300 * group.polarity_counts[polarity] / group.mentioned_reviews : 0;
      svg.append(svgNode("rect", {x, width, height: 14, fill: colors[polarity]}));
      x += width;
    }
    button.append(caption, svg);
    button.setAttribute("aria-label", `${group.category}, ${group.mentioned_reviews} reviews: ${polarities.map((p) => `${group.polarity_counts[p]} ${p}`).join(", ")}. View supporting reviews.`);
    button.disabled = !group.mentioned_reviews;
    button.addEventListener("click", () => applyEvidence(group.evidence.map((item) => item.row_id), `${scopeLabel} / ${group.category}`));
    categoryChart.append(button);
  }
  const complaints = view.complaint_ranking.slice(0, 8);
  $("complaint-chart").replaceChildren(...complaints.map((group) => bar(`${group.category} / ${group.issue}`, group.negative_mention_reviews,
    complaints[0].negative_mention_reviews, colors.Negative, () => applyEvidence(group.row_ids, `${scopeLabel} / negative mention: ${group.category} / ${group.issue}`),
    `${group.negative_mention_reviews} of ${group.mentioned_reviews} mentions · rank ${group.rank}`)));
  if (!complaints.length) $("complaint-chart").append(node("p", "no-records", view.eligible_reviews ? "No negative opinions recognized in this scope." : "No eligible reviews in this scope."));
  const categoryRows = view.categories.map((group) => {
    const name = node("button", "text-button", group.category);
    name.type = "button";
    name.disabled = !group.mentioned_reviews;
    name.addEventListener("click", () => applyEvidence(group.evidence.map((item) => item.row_id), `${scopeLabel} / ${group.category}`));
    return [name, group.mentioned_reviews, ...polarities.map((p) => group.polarity_counts[p]),
      group.negative_mention_percent === null ? "—" : `${group.negative_mention_reviews} / ${group.mentioned_reviews} (${group.negative_mention_percent}%)`,
      group.average_score === null ? "—" : number(group.average_score, true), group.evidence_status.replaceAll("_", " ")];
  });
  $("category-table").replaceChildren(table(["Category", "Mentioning reviews", "Positive", "Negative", "Mixed", "Neutral", "Any negative", "Mean index", "Evidence"], categoryRows));
  const findings = $("batch-conclusions");
  findings.replaceChildren();
  for (const conclusion of report.conclusions[view.scope]) {
    if (conclusion.code === "NOT_MENTIONED") continue;
    const line = node("article", "finding");
    line.append(node("p", "", conclusion.text));
    if (conclusion.row_ids.length) {
      const button = node("button", "text-button", `View ${conclusion.row_ids.length} supporting reviews →`);
      button.type = "button";
      button.addEventListener("click", () => applyEvidence(conclusion.row_ids, `${scopeLabel} / ${conclusion.category || "overall"}${conclusion.issue ? " / " + conclusion.issue : ""}`));
      line.append(button);
    }
    findings.append(line);
  }
  $("run-metadata").replaceChildren(table(["Run evidence", "Value"], [
    ["Analysis method", batch.method_label], ["Source file", batch.input.source_name], ["Source SHA-256", report.source_sha256], ["Analysis rules fingerprint", report.analysis_fingerprint],
    ["Reporting fingerprint", report.reporting_fingerprint], ["Created (UTC)", batch.created_at], ["Observed core analysis time", `${batch.elapsed_seconds.toFixed(6)} s`],
    ["Uploaded-data accuracy / precision / recall / F1", "Not measured: independent gold labels not supplied"],
  ]));
  const select = $("category-filter");
  if (select.options.length === 1) for (const group of view.categories) { const option = node("option", "", group.category); select.append(option); }
}
$("dashboard-scope").addEventListener("change", () => { clearFilters(); renderDashboard(); });

function clearFilters(render = true) {
  for (const id of ["review-search", "status-filter", "polarity-filter", "category-filter", "neural-filter"]) $(id).value = "";
  evidenceIds = null;
  $("evidence-filter").hidden = true;
  page = 1;
  if (render) renderReviewTable();
}
function filteredRows() {
  const search = $("review-search").value.toLocaleLowerCase().trim();
  return batch.rows.filter((row) => {
    const records = row.analysis?.records || [];
    const routed = row.analysis?.routed_analysis;
    const isNeural = routed?.selected_method === "independent_neural";
    if (evidenceIds && !evidenceIds.has(row.row_id)) return false;
    if ($("status-filter").value && (row.analysis?.status || row.execution_status) !== $("status-filter").value) return false;
    if ($("polarity-filter").value && (isNeural ? routed.overall : row.analysis?.overall || "Unanalyzed") !== $("polarity-filter").value) return false;
    if ($("neural-filter").value && row.analysis?.neural_recovery?.recovery_status !== $("neural-filter").value) return false;
    if ($("category-filter").value && !(isNeural ? routed.categories : records).some((r) => r.category === $("category-filter").value)) return false;
    const text = `${row.review_text || ""} ${row.supplied_review_id || ""} ${records.map((r) => `${r.category} ${r.issue} ${r.opinion_expression}`).join(" ")}`.toLocaleLowerCase();
    return !search || text.includes(search);
  });
}
function renderReviewTable() {
  if (!batch) return;
  const rows = filteredRows();
  const size = Number($("page-size").value);
  const pages = Math.max(1, Math.ceil(rows.length / size));
  page = Math.max(1, Math.min(page, pages));
  const start = (page - 1) * size;
  const display = rows.slice(start, start + size);
  const values = display.map((row) => {
    const id = node("div", "review-id", row.supplied_review_id || "—");
    if (row.duplicate_id || row.duplicate_text) id.append(node("small", "duplicate-label", `Duplicate ${[row.duplicate_id ? "ID" : "", row.duplicate_text ? "text" : ""].filter(Boolean).join(" / ")}`));
    const opinions = node("div", "row-opinions");
    for (const record of row.analysis?.records || []) {
      const line = node("p");
      line.append(node("strong", "", `${record.category} / ${record.issue}`), node("span", "", `“${record.opinion_expression}” `), badge(record.polarity), node("span", "", ` · ${record.strength || "Unavailable"}`), node("span", "score-number", ` ${number(record.score, true)}`));
      opinions.append(line);
    }
    if (!opinions.childElementCount) opinions.append(node("span", "muted", "No extracted opinions"));
    const details = node("button", "secondary small", "View result & trace");
    details.type = "button";
    details.setAttribute("aria-label", `View result and trace for review ${row.row_number}`);
    details.addEventListener("click", () => loadDetail(row));
    let cells = [row.row_number, id, node("span", "review-text-cell", row.review_text || "Blank / missing"), opinions,
      badge(row.analysis?.overall || "Unanalyzed"), reviewScoreDisplay(row.analysis), badge(row.analysis?.status || row.execution_status)];
    if (batch.neural_summary) {
      const n = row.analysis?.neural_recovery;
      const original = node("div", "original-hybrid-cell");
      original.append(badge(row.analysis?.status || row.execution_status), badge(row.analysis?.overall || "Unanalyzed"), reviewScoreDisplay(row.analysis));
      const originalDetails = node("details");
      originalDetails.append(node("summary", "", `Original aspect results (${row.analysis?.records.length || 0})`), opinions);
      original.append(originalDetails);
      cells = [row.row_number, id, node("span", "review-text-cell", row.review_text || "Blank / missing"), original];
      cells.push(node("span", "neural-status", n?.recovery_status.replaceAll("_", " ") || "Not analyzed"),
        neuralOpinions(n), n ? badge(n.combined_overall) : "—");
    }
    if (batch.routed_summary) {
      const r = row.analysis?.routed_analysis;
      const selectedNeural = r?.selected_method === "independent_neural";
      const original = node("details");
      original.append(node("summary", "", `${row.analysis?.status || row.execution_status} / ${row.analysis?.overall || "Unanalyzed"}`),
        reviewScoreDisplay(row.analysis), opinions);
      cells = [row.row_number, id, node("span", "review-text-cell", row.review_text || "Blank / missing"), original,
        node("span", "neural-status", r ? selectedNeural ? `ML/DL · ${r.route_status}` : "Hybrid retained" : "Not analyzed"),
        selectedNeural ? routedCategoryLines(r) : "See retained hybrid result",
        node("span", "pill", selectedNeural ? r.overall : row.analysis?.overall || "Unanalyzed"),
        node("span", "score-number", selectedNeural ? `Model index: ${number(r.review_index, true)}` : `Lexical: ${number(row.analysis?.review_score, true)}`)];
    }
    return [...cells, details];
  });
  const headers = batch.routed_summary
    ? ["Row", "Review ID", "Original review", "Original hybrid (expand)", "Selected method", "Independent categories", "Selected overall", "Selected index"]
    : batch.neural_summary
    ? ["Row", "Review ID", "Original review", "Original hybrid", "Neural recovery", "Additional predictions", "Overall with additions"]
    : ["Row", "Review ID", "Original review", "Aspect-level results", "Overall", "Review score", "Status"];
  $("review-table").replaceChildren(table([...headers, "Details"], values));
  if (!rows.length) $("review-table").append(node("p", "no-records", "No reviews match these filters. Reset filters to show all submitted rows."));
  $("review-table-count").textContent = `${rows.length.toLocaleString()} of ${batch.rows.length.toLocaleString()} rows`;
  $("page-description").textContent = `${rows.length ? start + 1 : 0}–${Math.min(start + size, rows.length)} of ${rows.length.toLocaleString()} · Page ${page} / ${pages}`;
  $("previous-page").disabled = page === 1;
  $("next-page").disabled = page === pages;
}
async function loadDetail(row) {
  const request = ++detailRequest;
  const identifier = batch.batch_id;
  $("detail-status").textContent = `Loading review ${row.row_number} and its stored trace…`;
  try {
    const response = await fetch(`/api/batches/${identifier}/reviews/${row.row_number}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Could not load the review.");
    if (request !== detailRequest || identifier !== batch?.batch_id) return;
    showBatchReview(data);
    $("detail-status").textContent = `Review ${row.row_number} loaded. Scroll below for results and compiler stages.`;
  } catch (failure) { if (request === detailRequest) $("detail-status").textContent = failure.message; }
}
for (const id of ["review-search", "status-filter", "polarity-filter", "category-filter", "neural-filter", "page-size"]) $(id).addEventListener(id === "review-search" ? "input" : "change", () => { page = 1; renderReviewTable(); });
$("reset-filters").addEventListener("click", () => clearFilters());
$("previous-page").addEventListener("click", () => { page--; renderReviewTable(); });
$("next-page").addEventListener("click", () => { page++; renderReviewTable(); });

function downloadBatch(kind) {
  if (!batch) return;
  const link = node("a");
  link.href = `/api/batches/${batch.batch_id}/download/${kind}`;
  link.download = kind === "paper" ? "report-tables.zip" : `${kind}.csv`;
  document.body.append(link);
  link.click();
  link.remove();
}
$("download-reviews").addEventListener("click", () => downloadBatch("reviews"));
$("download-paper").addEventListener("click", () => downloadBatch("paper"));
$("clear-batch").addEventListener("click", async () => {
  if (!batch || batchBusy) return;
  try {
    const response = await fetch(`/api/batches/${batch.batch_id}`, {method: "DELETE"});
    if (!response.ok && response.status !== 404) throw new Error("Could not clear this batch.");
    batch = null;
    detailRequest++;
    resetResults();
    $("results-section").hidden = true;
    $("batch-output").hidden = true;
    $("neural-dashboard").replaceChildren();
    $("neural-dashboard").hidden = true;
    $("routed-dashboard").replaceChildren();
    $("routed-dashboard").hidden = true;
    for (const id of ["review-table", "batch-conclusions", "run-metadata", "category-table", "category-chart", "complaint-chart", "coverage-chart", "overall-chart", "metric-cards", "coverage-notes"]) $(id).replaceChildren();
    csvFile = null;
    $("csv-file").value = "";
    $("file-label").textContent = "Choose a CSV or drop it here";
    $("upload-status").textContent = "Batch cleared from server memory. Choose a CSV to start again.";
  } catch (failure) { uploadError(failure.message); }
});
