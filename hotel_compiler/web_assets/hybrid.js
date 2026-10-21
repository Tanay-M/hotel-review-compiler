"use strict";

const methodNames = {hybrid: "VADER + TextBlob hybrid", sentiwordnet: "SentiWordNet compiler"};
function renderWholeText() {
  const container = $("whole-text-summary");
  container.replaceChildren();
  container.hidden = analysis?.method !== "hybrid";
  if (container.hidden) return;
  const whole = analysis.whole_text;
  container.append(node("h3", "", "Whole-review lexical sentiment"), fields([
    ["Fused whole-text score", number(whole.score, true)], ["Polarity / strength", `${whole.polarity} / ${whole.strength}`],
    ["VADER compound", number(whole.vader_compound, true)], ["TextBlob polarity", number(whole.textblob_polarity, true)],
  ]), node("p", "score-note", "This scores the complete text separately. The review score above averages extracted aspect contexts. Neither score is confidence or measured accuracy; Mixed aspect opinions remain Mixed."));
  if (whole.errors.length) container.append(node("p", "diagnostic-item", whole.errors.join("; ")));
}

function evidenceCard(evidence, title) {
  const card = node("article", "trace-record score-card");
  card.append(node("h3", "", title), node("blockquote", "", evidence.text), fields([
    ["VADER compound", number(evidence.vader_compound, true)],
    ["VADER positive / neutral / negative", [evidence.vader_positive, evidence.vader_neutral, evidence.vader_negative].map(v => number(v)).join(" / ")],
    ["TextBlob polarity", number(evidence.textblob_polarity, true)],
    ["TextBlob subjectivity", number(evidence.textblob_subjectivity)],
    ["Lexical evidence (VADER / TextBlob)", `${evidence.vader_has_evidence ? "Yes" : "No"} / ${evidence.textblob_has_evidence ? "Yes" : "No"}`],
    ["Fusion policy", evidence.fusion_rule], ["Fusion before domain rule", number(evidence.lexical_fusion_score, true)],
    ["Domain rule", evidence.domain_rule_id || "None"], ["Rule matched text", evidence.domain_matched_text || "None"],
    ["Component disagreement", evidence.component_disagreement ? "Yes" : "No"],
    ["Final score", number(evidence.score, true)], ["Polarity / strength", `${evidence.polarity} / ${evidence.strength}`],
    ["Scoring status", evidence.status],
  ]));
  if (evidence.vocabulary_normalization) {
    const normal = evidence.vocabulary_normalization;
    const original = normal.original_evidence;
    card.append(node("h4", "", "Vocabulary normalization"), fields([
      ["Reviewed replacements", normal.matches.map(m => `${m.original} → ${m.canonical}`).join("; ")],
      ["Scoring copy", normal.scoring_text],
      ["Original VADER compound", number(original.vader_compound, true)],
      ["Original TextBlob polarity", number(original.textblob_polarity, true)],
      ["Original lexical fusion", number(original.lexical_fusion_score, true)],
      ["Vocabulary version", normal.version],
    ]), node("p", "score-note", "Component scores above use the reviewed scoring copy. Original scores are retained here. Review wording and source spans are unchanged; fusion weights and existing domain-rule values are unchanged."));
  }
  if (evidence.textblob_assessments.length) card.append(table(["Assessed words", "Polarity", "Subjectivity", "Label"],
    evidence.textblob_assessments.map(a => [a[0].join(" "), number(a[1], true), number(a[2]), a[3] ?? "—"])));
  if (evidence.errors.length) card.append(node("p", "diagnostic-item", evidence.errors.join("; ")));
  return card;
}

function renderHybridTrace(panel, trace) {
  const language = trace.language;
  if (selectedStage === "tokens") {
    panel.append(node("p", "trace-intro", "Independent TextBlob Pattern tokens and grammatical tags. Character spans refer to the original review, including contractions."),
      table(["#", "Text", "POS", "Phrase chunk", "Preposition chunk", "Sentence", "Source span"], (language.tokens || []).map((t, i) =>
        [i + 1, t.text, t.pos, t.chunk, t.preposition, t.sentence + 1, `${t.start}:${t.end}`])));
  } else if (selectedStage === "syntax") {
    panel.append(node("p", "trace-intro", "Shallow phrase chunks and our clause segmentation. This path does not call the baseline predictive parser or build its AST."));
    for (const [label, items] of [["Noun phrases", language.noun_phrases || []], ["Clause segments", language.segments || []]]) {
      panel.append(node("h3", "", label));
      if (!items.length) { panel.append(node("p", "no-records", "None recognized.")); continue; }
      const keys = Object.keys(items[0]);
      panel.append(table(keys.map(k => k.replaceAll("_", " ")), items.map(item => keys.map(k => Array.isArray(item[k]) ? item[k].join(" · ") : item[k] ?? "—"))));
    }
  } else if (selectedStage === "semantics") {
    panel.append(node("p", "trace-intro", "Independent rules attach grammatical opinion contexts to six hotel categories. Unknown or unscored contexts remain visible."));
    panel.append(table(["Category", "Aspect", "Original context", "Attachment pattern", "Inherited target", "Aspect span", "Context span", "Score status"], trace.attachments.map(r =>
      [r.category, r.aspect_term, r.opinion_expression, r.grammar_pattern, r.inherited ? "Yes" : "No", `${r.aspect_start}:${r.aspect_end}`, `${r.start}:${r.end}`, r.evidence.status])));
  } else if (selectedStage === "scoring") {
    panel.append(node("p", "trace-intro", "Both tools run on each context. With evidence from both, lexical fusion = 0.5 × VADER + 0.5 × TextBlob. With evidence from one, retain that score. A component error remains an error. Hotel rules retain the original scores; subjectivity is not confidence."));
    trace.sentiment_evaluation.forEach((e, i) => panel.append(evidenceCard(e, `${analysis.records[i].category} / ${analysis.records[i].aspect_term}`)));
    panel.append(evidenceCard(analysis.whole_text, "Separate whole-review lexical evidence"));
  } else {
    panel.append(node("p", "trace-intro", "Hybrid intermediate records retain every extracted context, including unavailable scores. Opposing opinions retain Mixed even when their mean cancels."),
      table(["Category", "Rule / issue", "Aspect", "Context", "Polarity", "Strength", "Score", "Span"], analysis.records.map(r =>
        [r.category, r.issue, r.aspect_term, r.opinion_expression, r.polarity, r.strength, number(r.score, true), `${r.start}:${r.end}`])));
  }
}

$("analysis-method").addEventListener("change", () => {
  resetResults();
  $("method-description").textContent = $("analysis-method").value === "hybrid"
    ? "Independent grammatical extraction with VADER and TextBlob sentiment evidence."
    : "Original controlled lexer, predictive grammar and SentiWordNet sense scoring.";
});

$("compare-button").addEventListener("click", async () => {
  if (busy) return;
  resetResults(); error(""); loading(true);
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 30000);
  try {
    const results = await Promise.all(["sentiwordnet", "hybrid"].map(async method => {
      const response = await fetch("/api/analyze", {method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({text: review.value, method}), signal: controller.signal});
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "Comparison failed.");
      return {...result, method, method_label: methodNames[method]};
    }));
    const display = result => { analysis = result; selectedStage = "tokens"; renderResults(); };
    display(results.find(r => r.method === $("analysis-method").value));
    const comparison = $("method-comparison");
    comparison.hidden = false;
    comparison.append(node("h3", "", "Same review · two independent methods"),
      table(["Method", "Status", "Overall", "Aspect contexts", "Aspect mean", "Net strength", "Evidence"], results.map(result => {
        const button = node("button", "secondary small", "Show results & trace"); button.type = "button";
        button.addEventListener("click", () => display(result));
        return [result.method_label, result.status, result.overall, result.records.length, number(result.review_score, true), result.net_score_band, button];
      })), node("p", "score-note", "This is a live comparison, not an accuracy test. The methods can extract different contexts; opinions are not paired by position."));
  } catch (failure) { error(failure.name === "AbortError" ? "Comparison timed out. Check the local server." : failure.message); }
  finally { clearTimeout(timeout); loading(false); }
});
