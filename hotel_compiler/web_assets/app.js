"use strict";

const $ = (id) => document.getElementById(id);
const review = $("review-text");
let analysis = null;
let selectedStage = "tokens";
let config = null;
let busy = false;

// All review text and API fields enter the DOM as text, never as HTML.
function node(tag, className = "", text = null) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== null) element.textContent = String(text);
  return element;
}
function badge(value) {
  const known = new Set(["Positive", "Negative", "Neutral", "Mixed", "Unanalyzed", "complete", "partial", "unsupported", "invalid_input", "processing_error"]);
  return node("span", "pill " + (known.has(value) ? value.toLowerCase() : "neutral"), value);
}
function number(value, signed = false) {
  if (value == null || !Number.isFinite(Number(value))) return "Unavailable";
  return (signed && value > 0 ? "+" : "") + Number(value).toFixed(4);
}
function reviewScoreDisplay(result) {
  const display = node("div", "review-score-display");
  const score = result?.review_score;
  display.append(node("span", "score-number review-score-value", score == null ? "—" : number(score, true)));
  display.append(node("small", "review-score-scope", score == null ? "Unavailable" : result.review_score_scope));
  if (score != null && result.net_score_band) display.append(node("small", "review-score-scope", result.net_score_band));
  return display;
}
function sourceSpan(start, end) {
  // Python offsets count Unicode code points, while JS slice counts UTF-16 units.
  return Array.from(analysis.review_text).slice(start, end).join("");
}
function table(headers, rows) {
  const wrap = node("div", "table-wrap");
  const result = node("table");
  const head = node("thead");
  const headRow = node("tr");
  for (const label of headers) {
    const cell = node("th", "", label);
    cell.scope = "col";
    headRow.append(cell);
  }
  head.append(headRow);
  const body = node("tbody");
  for (const values of rows) {
    const row = node("tr");
    for (const value of values) {
      const cell = node("td");
      cell.append(value instanceof Node ? value : document.createTextNode(String(value)));
      row.append(cell);
    }
    body.append(row);
  }
  result.append(head, body);
  wrap.append(result);
  return wrap;
}
function fields(pairs) {
  const list = node("dl", "field-list");
  for (const [name, value] of pairs) {
    const field = node("div");
    field.append(node("dt", "", name), node("dd", "", value));
    list.append(field);
  }
  return list;
}
function error(message) {
  $("request-error").textContent = message;
  $("request-error").hidden = !message;
}
function resetResults() {
  analysis = null;
  $("empty-state").hidden = false;
  $("results-content").hidden = true;
  $("trace-section").hidden = true;
  $("result-summary").replaceChildren();
  $("trace-panel").replaceChildren();
  $("results-body").replaceChildren();
  $("diagnostics").replaceChildren();
  $("analysis-scope").textContent = "";
  $("whole-text-summary").hidden = true;
  $("method-comparison").hidden = true;
  $("method-comparison").replaceChildren();
}
function updateInput() {
  $("char-count").textContent = `${Array.from(review.value).length.toLocaleString()} / 10,000`;
}
function loading(value) {
  busy = value;
  $("analyze-button").disabled = value;
  $("clear-button").disabled = value;
  $("single-mode").disabled = value;
  $("batch-mode").disabled = value;
  $("analysis-method").disabled = value;
  $("compare-button").disabled = value;
  review.disabled = value;
  document.querySelectorAll("#example-buttons button").forEach((button) => { button.disabled = value; });
  $("results-section").setAttribute("aria-busy", String(value));
  $("analyze-button").replaceChildren(document.createTextNode(value ? "Analyzing…" : "Analyze review"));
  if (!value) $("analyze-button").append(node("span", "", "→"));
}

function renderResults() {
  $("results-section").hidden = false;
  $("empty-state").hidden = true;
  $("results-content").hidden = false;
  $("trace-section").hidden = false;
  const summary = $("result-summary");
  const reviewScore = node("div", "review-score-summary");
  reviewScore.append(node("span", "", "Review score"), reviewScoreDisplay(analysis));
  summary.replaceChildren(node("span", "method-label", analysis.method_label || "SentiWordNet compiler"), badge(analysis.status), badge(analysis.overall), reviewScore);
  renderWholeText();
  $("analysis-scope").textContent = `“${analysis.review_text}”` +
    (analysis.status === "partial" ? "\nPartial analysis: sentiment and review score use recognized opinions only." :
      analysis.status === "unsupported" ? "\nNo supported aspect-opinion records were found. Inspect the diagnostics and tokens below." :
        `\n${analysis.records.length} aspect-opinion record${analysis.records.length === 1 ? "" : "s"} · scores range from −1 to +1.`);
  const body = $("results-body");
  body.replaceChildren();
  for (const record of analysis.records) {
    const row = node("tr");
    for (const value of [record.category, record.issue, record.opinion_expression, badge(record.polarity), record.strength || "Unavailable", node("span", "score-number", number(record.score, true))]) {
      const cell = node("td");
      cell.append(value instanceof Node ? value : document.createTextNode(value));
      row.append(cell);
    }
    body.append(row);
  }
  if (!analysis.records.length) {
    const row = node("tr");
    const cell = node("td", "", "No aspect-level results for this review.");
    cell.colSpan = 6;
    row.append(cell);
    body.append(row);
  }
  const diagnostics = $("diagnostics");
  diagnostics.replaceChildren();
  diagnostics.hidden = !analysis.diagnostics.length;
  if (analysis.diagnostics.length) {
    const box = node("div", "diagnostic-box");
    box.append(node("h3", "", `${analysis.diagnostics.length} diagnostic${analysis.diagnostics.length === 1 ? "" : "s"}`));
    for (const item of analysis.diagnostics) {
      const detail = node("div", "diagnostic-item");
      detail.append(node("span", "code", `${item.stage.toUpperCase()} / ${item.code}`), node("p", "", item.message),
        node("span", "code", `Source ${item.start}:${item.end} · ${sourceSpan(item.start, item.end)}`));
      box.append(detail);
    }
    diagnostics.append(box);
  }
  renderTrace();
}

function renderTrace() {
  if (!analysis) return;
  const panel = $("trace-panel");
  panel.replaceChildren();
  panel.setAttribute("aria-labelledby", "tab-" + selectedStage);
  document.querySelectorAll("[data-stage]").forEach((button) => {
    const selected = button.dataset.stage === selectedStage;
    button.setAttribute("aria-selected", String(selected));
    button.tabIndex = selected ? 0 : -1;
  });
  const trace = analysis.trace;
  if (analysis.method === "hybrid") { renderHybridTrace(panel, trace); return; }
  if (selectedStage === "tokens") {
    panel.append(node("p", "trace-intro", `${trace.lexical_analysis.length} tokens. Each token retains its original text and zero-based source positions.`));
    panel.append(table(["#", "Source text", "Normalized value", "Token class", "Normalization / verb form", "Span"], trace.lexical_analysis.map((token, index) => [
      index + 1, node("span", "code", token.text), node("span", "code", token.value),
      node("span", "token-kind kind-" + token.kind.toLowerCase(), token.kind), token.normalization_rule ? `${token.normalization_rule}${token.verb_form ? " / " + token.verb_form : ""}` : "None", node("span", "code", `${token.start}:${token.end}`),
    ])));
  } else if (selectedStage === "syntax") {
    panel.append(node("p", "trace-intro", "The predictive parser groups supported expressions into clause nodes in the review AST."));
    const grid = node("div", "record-grid");
    trace.syntax_analysis.clauses.forEach((clause, index) => {
      const card = node("article", "trace-record");
      card.append(node("h3", "", `Clause ${index + 1}`), node("blockquote", "", sourceSpan(clause.start, clause.end)), fields([
        ["Subject", clause.subject?.value || "Omitted; resolved in semantics"],
        ["Opinion", clause.opinion.value], ["Negation token", clause.negation?.value || "None"],
        ["Intensifier token", clause.intensifier?.value || "None"], ["Connector", clause.connector || "Review start"],
        ["Source span", `${clause.start}:${clause.end}`],
        ["Retained context", (clause.context || []).map((token) => token.text).join(" · ") || "None"],
      ]));
      grid.append(card);
    });
    panel.append(grid);
    if (!grid.childElementCount) panel.append(node("p", "no-records", "No supported clauses were parsed. The token trace and diagnostics show where parsing stopped."));
    panel.append(table(["Clause", "Form", "Copula / auxiliary", "Adverb", "Emphasis", "Opinion span"], trace.syntax_analysis.clauses.map((clause, index) => [
      index + 1, clause.form, clause.copula?.text || clause.auxiliary?.text || "None", clause.adverb?.text || "None", clause.emphasis?.text || "None", `${clause.opinion_start}:${clause.opinion_end}`,
    ])));
  } else if (selectedStage === "semantics") {
    panel.append(node("p", "trace-intro", "Explicit vocabulary mappings supply the category and issue. The parsed structure supplies the aspect-opinion relationship and modifier scope."));
    const grid = node("div", "record-grid");
    trace.semantic_analysis.forEach((record) => {
      const card = node("article", "trace-record");
      card.append(node("h3", "", `${record.category} / ${record.issue}`), node("blockquote", "", record.opinion_expression), fields([
        ["Aspect term", record.aspect_term], ["Opinion head", record.opinion_term],
        ["Negated", record.negated ? "Yes" : "No"], ["Intensity", `${record.intensifier || "None"} · × ${record.intensity_multiplier}`],
        ["Inherited aspect", record.aspect_inherited ? "Yes, from the previous clause" : "No, explicit subject"],
        ["AST clause", record.clause_index + 1],
        ["Normalization rule", record.normalization_rule || "None"], ["Adverb / emphasis", [record.adverb, record.emphasis].filter(Boolean).join(" / ") || "None"],
        ["Syntax form", record.syntax_form],
      ]));
      grid.append(card);
    });
    panel.append(grid);
    if (!grid.childElementCount) panel.append(node("p", "no-records", "No aspect-opinion pairs reached semantic evaluation."));
  } else if (selectedStage === "scoring") {
    panel.append(node("p", "trace-intro", "P and N are original SentiWordNet values for the selected sense. Domain rules and modifier adjustments are shown separately. Scores are not confidence percentages."));
    panel.append(node("p", "trace-intro", analysis.review_score == null ? "Review score is unavailable because no opinion scores were produced." :
      `Review score = sum of ${analysis.records.length} final opinion scores ÷ ${analysis.records.length} = ${number(analysis.review_score, true)} (${analysis.review_score_scope}). Mixed labels are preserved even when scores cancel.`));
    trace.sentiment_evaluation.forEach((score, index) => {
      const record = analysis.records[index];
      const card = node("article", "trace-record score-card");
      const heading = node("div", "record-head");
      heading.append(node("h3", "", `${record.category} / ${record.issue} · ${record.opinion_expression}`), badge(record.polarity));
      card.append(heading, node("p", "sense-label", `Selected sense: ${score.synset}`), node("p", "gloss", score.gloss));
      if (score.sense_selection) card.append(node("p", "score-note", score.sense_selection));
      const scores = node("div", "score-grid");
      for (const [label, value] of [["P · source", score.positive_score], ["N · source", score.negative_score], ["P − N · lexical", score.lexical_score], ["Final score", score.final_score]]) {
        const item = node("div");
        item.append(node("span", "", label), node("strong", "", number(value, label === "Final score")));
        scores.append(item);
      }
      card.append(scores);
      if (score.normalization_rule) card.append(node("p", "sense-label", `Normalization: ${score.normalization_rule}`));
      if (score.calibration_reason) card.append(node("p", "calibration", `Explicit domain rule (${score.domain_rule_id}): ${number(score.lexical_score)} → ${number(score.domain_score, true)}. ${score.calibration_reason}`));
      card.append(node("p", "formula", `${number(score.domain_score, true)} × ${score.intensity_multiplier} (intensity) × ${score.negation_multiplier} (negation) = ${number(score.unclipped_score, true)}`),
        node("p", "score-note", `Objective source score: ${number(score.objective_score)}. Final score is clipped to [−1, +1]. Neutral interval: −0.05 to +0.05.`));
      panel.append(card);
    });
    if (!trace.sentiment_evaluation.length) panel.append(node("p", "no-records", "No supported opinion pairs were available for sentiment scoring."));
  } else {
    panel.append(node("p", "trace-intro", "The final aspect-level IR preserves each extracted opinion. Multiple records can belong to the same review."), table(
      ["Category", "Issue", "Aspect", "Opinion", "Polarity", "Score", "Source span"], trace.intermediate_representation.map((record) => [record.category, record.issue, record.aspect_term, record.opinion_expression, badge(record.polarity), number(record.score, true), `${record.start}:${record.end}`])));
  }
}

async function analyze() {
  if (busy) return;
  error("");
  const max = config?.max_review_length || 10000;
  if (Array.from(review.value).length > max) {
    error(`A review must contain at most ${max.toLocaleString()} characters.`);
    return;
  }
  loading(true);
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch("/api/analyze", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({text: review.value, method: $("analysis-method").value}), signal: controller.signal,
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "The local analyzer could not complete this request.");
    analysis = data;
    $("method-comparison").hidden = true;
    renderResults();
  } catch (failure) {
    error(failure.name === "AbortError" ? "The request timed out. Check that the local server is still running." :
      failure instanceof TypeError ? "Could not reach the local analyzer. Keep the server terminal open and try again." : failure.message);
  } finally {
    clearTimeout(timeout);
    loading(false);
  }
}

$("review-form").addEventListener("submit", (event) => { event.preventDefault(); analyze(); });
review.addEventListener("input", () => { updateInput(); error(""); resetResults(); });
review.addEventListener("keydown", (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") { event.preventDefault(); $("review-form").requestSubmit(); }
});
$("clear-button").addEventListener("click", () => { review.value = ""; updateInput(); resetResults(); error(""); review.focus(); });
const tabs = [...document.querySelectorAll("[data-stage]")];
tabs.forEach((button, index) => {
  button.addEventListener("click", () => { selectedStage = button.dataset.stage; renderTrace(); });
  button.addEventListener("keydown", (event) => {
    let next;
    if (event.key === "ArrowRight") next = (index + 1) % tabs.length;
    else if (event.key === "ArrowLeft") next = (index + tabs.length - 1) % tabs.length;
    else if (event.key === "Home") next = 0;
    else if (event.key === "End") next = tabs.length - 1;
    else return;
    event.preventDefault(); tabs[next].click(); tabs[next].focus();
  });
});
$("download-button").addEventListener("click", () => {
  if (!analysis) return;
  const values = ["method", "review_id", "review_text", "status", "overall", "review_score", "review_score_scope", "net_score_band", "whole_text_score", "opinion_count", "aspect_results", "diagnostics"];
  const record = [analysis.method || "sentiwordnet", analysis.review_id, analysis.review_text, analysis.status, analysis.overall, analysis.review_score, analysis.review_score_scope, analysis.net_score_band, analysis.whole_text?.score ?? null, analysis.records.length,
    analysis.records.map((r) => `${r.category} / ${r.issue}: ${r.opinion_expression} -> ${r.polarity} (${number(r.score, true)})`).join("; "),
    analysis.diagnostics.map((d) => `${d.code}: ${d.message}`).join("; ")];
  const cell = (value) => {
    if (value == null) return '""';
    if (typeof value === "number") return String(value);
    let text = String(value);
    if (/^[\t\r\n]/.test(text) || /^[=+\-@]/.test(text.trimStart())) text = "'" + text;
    return '"' + text.replaceAll('"', '""') + '"';
  };
  const csv = "\uFEFF" + [values, record].map((row) => row.map(cell).join(",")).join("\r\n") + "\r\n";
  const url = URL.createObjectURL(new Blob([csv], {type: "text/csv;charset=utf-8"}));
  const link = node("a");
  link.href = url;
  link.download = `review-${analysis.review_id.replace(/[^a-zA-Z0-9_-]/g, "")}.csv`;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});

async function initialize() {
  updateInput();
  try {
    const response = await fetch("/api/config");
    if (!response.ok) throw new Error("Could not load the demo vocabulary. Refresh the page after checking the local server.");
    config = await response.json();
    for (const example of config.examples) {
      const button = node("button", "", example.label);
      button.type = "button";
      button.title = example.text;
      button.addEventListener("click", () => { review.value = example.text; updateInput(); resetResults(); error(""); review.focus(); });
      $("example-buttons").append(button);
    }
    const content = $("vocabulary-content");
    content.replaceChildren(node("p", "", "The lists below describe the SentiWordNet baseline. The hybrid uses an independent hotel-aspect dictionary and grammatical opinion discovery; it is not restricted to this opinion list."), node("p", "", `${config.categories.length} categories · ${Object.keys(config.aspects).length} baseline aspect phrases · ${Object.keys(config.opinions).length} baseline opinion terms`));
    if (config.hybrid_vocabulary) content.append(node("p", "", `Hybrid: ${config.hybrid_vocabulary.aspect_phrases} aspect phrases and ${config.hybrid_vocabulary.reviewed_lexical_forms} reviewed opinion forms. Unknown forms are normalized only in a separate, category-guarded scoring copy; original evidence remains in the Scoring trace. Version: ${config.hybrid_vocabulary.version}.`));
    for (const [title, values] of [["Categories", config.categories], ["Aspect phrases", Object.keys(config.aspects)], ["Opinion terms", Object.keys(config.opinions)]]) {
      content.append(node("h3", "", title));
      const words = node("div", "word-list");
      values.forEach((value) => words.append(node("span", "", value)));
      content.append(words);
    }
    content.append(node("p", "", `Negations: ${config.negations.join(", ")}. Intensifiers: ${Object.keys(config.intensifiers).join(", ")}. Connectors: ${config.connectors.join(", ")}.`),
      node("p", "", "Supports a broad curated hotel vocabulary, coordinated subjects/adjectives, introductory phrases, possession forms, selected context phrases, and equipment failures. The six categories remain fixed; location, price/value, unrestricted pronoun inference and sarcasm remain outside scope."));
  } catch (failure) { error(failure.message); }
}
initialize();

function showBatchReview(row) {
  resetResults();
  $("results-section").hidden = false;
  $("results-title").textContent = `Review ${row.row_number} · ${row.supplied_review_id || "No supplied ID"}`;
  selectedStage = "tokens";
  if (row.analysis) {
    analysis = row.analysis;
    renderResults();
  } else {
    $("empty-state").hidden = true;
    $("results-content").hidden = false;
    const reviewScore = node("div", "review-score-summary");
    reviewScore.append(node("span", "", "Review score"), reviewScoreDisplay(null));
    $("result-summary").replaceChildren(badge(row.execution_status), reviewScore);
    $("analysis-scope").textContent = row.review_text || "Blank or missing review text.";
    const tr = node("tr");
    const td = node("td", "", "No compiler result: this row was not analyzed.");
    td.colSpan = 6;
    tr.append(td);
    $("results-body").replaceChildren(tr);
    $("diagnostics").hidden = false;
    $("diagnostics").replaceChildren(...row.validation_errors.map((issue) => node("p", "diagnostic-item", `${issue.code}: ${issue.message}`)));
    if (row.processing_error) $("diagnostics").append(node("p", "diagnostic-item", row.processing_error));
  }
  $("results-title").tabIndex = -1;
  $("results-title").focus({preventScroll: true});
  $("results-section").scrollIntoView({behavior: "smooth", block: "start"});
}
