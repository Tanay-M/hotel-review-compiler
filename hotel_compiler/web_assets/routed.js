"use strict";

function renderRoutedResult() {
  const panel = $("routed-result"); panel.replaceChildren();
  const result = analysis?.routed_analysis; panel.hidden = !result;
  if (!result) return;
  const routed = result.selected_method === "independent_neural";
  panel.append(node("p", "eyebrow", "FINE-TUNED DEEP LEARNING"),
    node("h3", "", routed ? "Selected result: neural category & sentiment analysis" : "Selected result: original hybrid"),
    fields([["Routing", result.route_status.replaceAll("_", " ")], ["Original hybrid status", analysis.status],
      ["Selected overall", routed ? result.overall : analysis.overall],
      [routed ? "Neural direction index" : "Hybrid lexical mean", number(routed ? result.review_index : analysis.review_score, true)],
      ["Trained model", result.model_id]]));
  if (!routed) {
    panel.append(node("p", "score-note", "Complete reviews retain the hybrid result. Processing errors are not routed as if they were language failures."));
    return;
  }
  panel.append(node("p", "score-note", "This is a fresh analysis of every original sentence in this review. It does not append hybrid opinions or require a matched aspect word. Results below are the selected neural output; the original hybrid remains available for comparison."));
  if (result.categories.length) panel.append(table(["Predicted category", "Sentiment", "Model direction index", "Evidence sentences"],
    result.categories.map(c => [c.category, c.label, number(c.model_direction_index, true), c.sentences])));
  else panel.append(node("p", "no-records", "No in-scope category passed its validation-selected threshold. The review remains for inspection."));
  panel.append(node("p", "score-note", "Index = (P(Positive) − P(Negative)) / (P(Positive) + P(Negative)); category indices average sentence indices, then the review averages categories equally. It is not a calibrated sentiment rating, lexical mean, or strong/weak intensity score. Accepted Neutral/Mixed evidence makes that category/review index unavailable."));
  panel.append(node("p", "score-note", "Training taxonomy: Staff feedback is pooled under Service; Facilities maps Building/Business. The source merges Neutral and Mixed. No separate Staff accuracy or five-strength accuracy is claimed. Reanalyzed does not mean verified correct or Complete."));
  const detail = node("details");
  detail.append(node("summary", "", `Independent sentence evidence · ${result.records.length} accepted category predictions`),
    table(["Category", "Original sentence", "Predicted label", "Prediction probability", "Direction index", "Source span"],
      result.records.map(r => [r.category, r.context, r.label, modelProbability(r.probabilities[r.label]),
        number(r.model_direction_index, true), `${r.start}:${r.end}`])));
  panel.append(detail);
  const decisions = node("details");
  decisions.append(node("summary", "", `All category decisions · ${result.decisions.length}`),
    table(["Sentence", "Category", "Model label", "Decision", "Reason", "P(Absent)", "P(Negative)", "P(Neutral/Mixed)", "P(Positive)"],
      result.decisions.map(d => [d.context, d.category, d.label, d.accepted && d.in_scope ? "Selected" : "Not selected",
        d.reason.replaceAll("_", " "), ...["Absent", "Negative", "Neutral/Mixed", "Positive"].map(k => modelProbability(d.probabilities[k]))])));
  panel.append(decisions);
  for (const warning of result.warnings.filter(w => w.code !== "SOURCE_TAXONOMY")) panel.append(node("p", "diagnostic-item", warning.message));
}

function renderRoutedDashboard() {
  const panel = $("routed-dashboard"); panel.replaceChildren();
  const s = batch?.routed_summary; panel.hidden = !s;
  if (!s) return;
  panel.append(node("p", "eyebrow", "SELECTED NEURAL OUTPUT · PARTIAL / UNSUPPORTED REVIEWS"), node("h3", "", "Independent review reanalysis"));
  const cards = node("div", "neural-metrics");
  for (const [label, count] of [["Reviews routed", s.routed_reviews], ["With category results", s.neural_results],
    ["Abstained reviews", s.abstained_reviews], ["Hybrid retained", s.retained_hybrid]]) {
    const card = node("div", "metric-card"); card.append(node("span", "small-label", label), node("strong", "", count.toLocaleString())); cards.append(card);
  }
  panel.append(cards, node("p", "score-note", `Every Partial/Unsupported review is independently processed from its full original text. These are separate selected neural results, not additions to hybrid opinions. Counts cover all submitted rows, independently of the lexical scope selector. Counts are not accuracy. ${s.model_errors} model errors. The original hybrid charts below remain comparison evidence and keep their lexical Mean index.`));
  const actions = node("div", "form-actions");
  for (const [label, outcome] of [["Show reanalyzed reviews", "reanalyzed"], ["Show abstained reviews", "abstained"], ["Show retained hybrid reviews", "not_routed"]]) {
    const b = node("button", "secondary small", label); b.type = "button";
    b.addEventListener("click", () => applyEvidence(batch.rows.filter(r => r.analysis?.routed_analysis?.route_status === outcome).map(r => r.row_id), label));
    actions.append(b);
  }
  panel.append(actions, node("h4", "", "Neural category results · all routed reviews"),
    table(["Category", "Positive reviews", "Negative reviews", "Mixed/uncertain reviews", "Mean model index", "Index denominator"],
      s.categories.map(c => {
        const b = node("button", "text-button", c.category); b.type = "button";
        b.addEventListener("click", () => applyEvidence(c.row_ids, `Independent neural / ${c.category}`));
        return [b, c.positive, c.negative, c.mixed_uncertain, number(c.mean_model_index, true), `${c.index_reviews} reviews`];
      })), node("p", "score-note", "Mean model index averages the available per-review category indices. Ambiguous Neutral/Mixed entries are excluded from that numeric mean and counted separately. Staff is pooled under Service; this does not add a seventh category. Model indices and lexical scores have different meanings."));
}

function routedCategoryLines(result) {
  const box = node("div", "neural-opinions");
  for (const c of result?.categories || []) {
    const line = node("p"); line.append(node("strong", "", c.category), node("span", "", `${c.label} · ${number(c.model_direction_index, true)}`)); box.append(line);
  }
  if (!box.childElementCount) box.append(node("span", "muted", "No selected neural categories"));
  return box;
}
