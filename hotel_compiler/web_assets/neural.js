"use strict";

const neuralReasons = {
  accepted_by_validation_gate: "Accepted by the validation-selected gate",
  objective_is_not_a_neutral_opinion: "Objective statement: no opinion added",
  below_probability_threshold: "Below the probability threshold",
  ambiguous_probability_margin: "Top two predictions are too close",
  inherited_target_requires_inspection: "Inherited target needs inspection",
  only_partial_reviews_are_routed: "Only Partial reviews are routed",
  unresolved_or_excluded_context: "Unresolved or excluded context",
  multiple_targets_in_context: "Multiple targets in the context",
  validation_gate_disabled: "Validation gate is disabled",
};
function neuralReason(reason) { return neuralReasons[reason] || reason.replaceAll("_", " "); }
function modelProbability(value) { return value == null ? "—" : `${(100 * value).toFixed(1)}%`; }
function neuralOpinions(recovery) {
  const box = node("div", "neural-opinions");
  for (const a of recovery?.recovered || []) {
    const line = node("p");
    line.append(node("strong", "", `${a.category} / ${a.aspect}`), node("span", "", ` “${a.context}” `), badge(a.model_label));
    box.append(line);
  }
  if (!box.childElementCount) box.append(node("span", "muted", "No additional predictions"));
  return box;
}

function renderNeuralResults() {
  const panel = $("neural-result");
  panel.replaceChildren();
  const recovery = analysis?.neural_recovery;
  panel.hidden = !recovery;
  if (!recovery) return;
  panel.append(node("p", "eyebrow", "ADDITIONAL NEURAL STAGE · MINILM"), node("h3", "", "Neural recovery"), fields([
    ["Original hybrid status", analysis.status], ["Recovery outcome", recovery.recovery_status.replaceAll("_", " ")],
    ["Original hybrid overall", analysis.overall], ["Overall with accepted additions", recovery.combined_overall],
    ["Additional opinion predictions", recovery.recovered.length], ["Local model", recovery.model_id],
  ]), node("p", "score-note", "Original scores and diagnostics are retained below. Neural-assisted does not mean Complete or verified correct. Model probabilities are not sentiment intensity, and are not included in the lexical review mean."));
  if (recovery.recovered.length) panel.append(table(["Category", "Aspect", "Original context", "Added prediction", "Model probability"],
    recovery.recovered.map(a => [a.category, a.aspect, a.context, badge(a.model_label), modelProbability(a.probabilities[a.model_label])])));
  else panel.append(node("p", "no-records", "No additional sentiment passed the routing and acceptance rules."));
  const detail = node("details", "neural-decisions");
  detail.append(node("summary", "", `Routing and prediction evidence · ${recovery.attempts.length} unscored contexts`),
    node("p", "score-note", `Accept Positive/Negative only: probability ≥ ${modelProbability(recovery.policy.min_probability)}, top-two margin ≥ ${modelProbability(recovery.policy.min_margin)}. Objective and uncertain predictions abstain. The model only handles eligible explicit aspects in Partial reviews.`));
  if (recovery.attempts.length) detail.append(table(["Category / aspect", "Original context", "Model label", "P(Negative)", "P(Objective)", "P(Positive)", "Decision", "Reason", "Source span"],
    recovery.attempts.map(a => [`${a.category} / ${a.aspect}`, a.context, a.model_label || "Not run",
      modelProbability(a.probabilities?.Negative), modelProbability(a.probabilities?.Objective), modelProbability(a.probabilities?.Positive),
      a.decision.replaceAll("_", " "), neuralReason(a.reason), `${a.start}:${a.end}`])));
  panel.append(detail);
}

function renderNeuralDashboard() {
  const panel = $("neural-dashboard");
  panel.replaceChildren();
  const summary = batch?.neural_summary;
  panel.hidden = !summary;
  $("neural-filter-label").hidden = !summary;
  if (!summary) return;
  panel.append(node("p", "eyebrow", "PARTIAL REVIEW RECOVERY · LOCAL NEURAL MODEL"), node("h3", "", "What the neural stage added"));
  const cards = node("div", "neural-metrics");
  for (const [title, count] of [["Reviews with additions", summary.assisted_reviews], ["Additional predictions", summary.added_opinions],
    ["Eligible contexts", summary.eligible_contexts], ["Abstained contexts", summary.abstained_contexts]]) {
    const card = node("div", "metric-card");
    card.append(node("span", "small-label", title), node("strong", "", count.toLocaleString()));
    cards.append(card);
  }
  panel.append(cards, node("p", "score-note", "These counts cover all submitted rows and do not change with the lexical dashboard scope. The charts and Mean index below retain the original hybrid results. Neural additions are shown separately; they do not establish accuracy or make a Partial review Complete."));
  const actions = node("div", "form-actions");
  for (const [label, status] of [["Show reviews with additions", "neural_assisted"], ["Show abstained reviews", "abstained"]]) {
    const button = node("button", "secondary small", label); button.type = "button";
    button.addEventListener("click", () => {
      applyEvidence(batch.rows.filter(r => r.analysis?.neural_recovery?.recovery_status === status).map(r => r.row_id), label);
    });
    actions.append(button);
  }
  panel.append(actions, table(["Category", "Additional Positive", "Additional Negative", "Additional opinions", "Reviews"],
    summary.categories.map(group => {
      const button = node("button", "text-button", group.category); button.type = "button"; button.disabled = !group.opinions;
      button.addEventListener("click", () => applyEvidence(group.row_ids, `Neural additions / ${group.category}`));
      return [button, group.positive, group.negative, group.opinions, group.row_ids.length];
    })), node("p", "score-note", `Model: ${summary.model_id || "No analyzed rows"}. ${summary.not_eligible_contexts} ineligible contexts; ${summary.model_errors} model errors. Report tables include the full neural decision ledger.`));
}
