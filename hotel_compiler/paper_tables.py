"""Tabular, reproducible descriptive evidence for a later conference report."""

import csv
from io import BytesIO, StringIO
import platform
from zipfile import ZIP_DEFLATED, ZipFile

from .batch_models import BatchResult
from .exports import _spreadsheet_cell, batch_csv_bytes
from .reporting import render_report


def _csv(headers: list[str], rows: list[list]) -> bytes:
    handle = StringIO(newline="")
    writer = csv.writer(handle)
    writer.writerow(headers)
    writer.writerows([[_spreadsheet_cell(value) for value in row] for row in rows])
    return handle.getvalue().encode("utf-8-sig")


def paper_tables(batch: BatchResult, report: dict) -> dict[str, bytes]:
    """No accuracy is inferred from unlabeled uploads; both scopes are named."""
    aggregation = report["aggregation"]
    counts = aggregation["coverage"]["counts"]
    tables = {"reviews.csv": batch_csv_bytes(batch), "aspects.csv": batch_csv_bytes(batch, "aspects")}
    if batch.method in {"hybrid", "hybrid_neural", "hybrid_routed"}:
        evidence_rows = []
        for row in batch.rows:
            if not row.analysis:
                continue
            for record in row.analysis.records:
                e = record.evidence
                evidence_rows.append([row.row_id, row.source.ordinal, record.category, record.aspect_term,
                    record.opinion_expression, record.grammar_pattern, record.start, record.end,
                    e.vader_compound, e.vader_positive, e.vader_neutral, e.vader_negative,
                    e.textblob_polarity, e.textblob_subjectivity, e.vader_has_evidence,
                    e.textblob_has_evidence, e.lexical_fusion_score, e.fusion_rule,
                    e.domain_rule_id, e.domain_matched_text, e.score, e.polarity, e.strength,
                    e.status, e.component_disagreement, " | ".join(e.errors),
                    (e.vocabulary_normalization or {}).get('scoring_text', ''),
                    '; '.join(f"{m['original']} -> {m['canonical']}" for m in (e.vocabulary_normalization or {}).get('matches', [])),
                    (e.vocabulary_normalization or {}).get('original_evidence', {}).get('vader_compound', e.vader_compound),
                    (e.vocabulary_normalization or {}).get('original_evidence', {}).get('textblob_polarity', e.textblob_polarity)])
        tables["hybrid_evidence.csv"] = _csv([
            "row_id", "row_number", "category", "aspect", "context", "grammar_pattern", "start", "end",
            "vader_compound", "vader_positive", "vader_neutral", "vader_negative",
            "textblob_polarity", "textblob_subjectivity", "vader_has_evidence", "textblob_has_evidence",
            "lexical_fusion_score", "fusion_rule", "domain_rule_id", "domain_matched_text",
            "final_score", "polarity", "strength", "status", "component_disagreement", "errors",
            "vocabulary_scoring_text", "vocabulary_aliases", "original_vader_compound", "original_textblob_polarity"], evidence_rows)
    category_rows, issue_rows, polarity_rows = [], [], []
    for scope, view in aggregation["views"].items():
        for polarity, count in view["overall_counts"].items():
            polarity_rows.append([scope, polarity, count, view["eligible_reviews"], view["overall_percent"][polarity]])
        for group in view["categories"]:
            category_rows.append([scope, group["category"], group["mentioned_reviews"], group["extracted_opinions"],
                                  *group["polarity_counts"].values(), group["negative_mention_reviews"],
                                  group["negative_mention_percent"], group["average_score"], group["evidence_status"]])
        for group in view["issues"]:
            issue_rows.append([scope, group["category"], group["issue"], group["mentioned_reviews"], group["extracted_opinions"],
                               *group["polarity_counts"].values(), group["negative_mention_reviews"],
                               group["negative_mention_percent"], group["average_score"], group["evidence_status"]])
    metric_headers = ["mentioned_reviews", "opinion_count", "positive_reviews", "negative_reviews", "mixed_reviews", "neutral_reviews",
                      "any_negative_reviews", "any_negative_percent_of_mentions", "equal_review_mean_score", "evidence_status"]
    tables["category_summary.csv"] = _csv(["scope", "category", *metric_headers], category_rows)
    tables["issue_summary.csv"] = _csv(["scope", "category", "issue", *metric_headers], issue_rows)
    tables["overall_summary.csv"] = _csv(["scope", "polarity", "reviews", "eligible_reviews_denominator", "percent"], polarity_rows)
    tables["coverage.csv"] = _csv(["metric", "count", "denominator", "percent"],
        [[key, value, "", ""] for key, value in counts.items()] +
        [["complete_of_analyzed", counts["complete"], counts["analyzed"], aggregation["coverage"]["coverage"]["complete_percent"]],
         ["with_opinions_of_analyzed", counts["complete"] + counts["partial"], counts["analyzed"], aggregation["coverage"]["coverage"]["with_opinions_percent"]],
         ["complete_of_submitted", counts["complete"], counts["submitted"], aggregation["primary_complete_share_submitted_percent"]]])
    tables["run_metadata.csv"] = _csv(["field", "value"], [
        ["analysis_method", batch.method], ["batch_id", batch.batch_id], ["created_at_utc", batch.created_at], ["source_name", batch.source.source_name],
        ["source_sha256", batch.source.source_sha256], ["analysis_fingerprint", batch.analysis_fingerprint],
        ["reporting_fingerprint", report["reporting_fingerprint"]], ["python_version", platform.python_version()],
        ["platform", platform.platform()], ["analysis_seconds", batch.elapsed_seconds],
        ["timing_scope", "Single observed core batch run, including resource preflight; excludes CSV decoding, reporting, HTTP transfer and browser rendering. Not a repeated performance benchmark."],
        ["primary_scope", "complete_reviews"], ["secondary_scope", "complete_and_partial: recognized opinions only"],
        ["minimum_support_reviews", aggregation["policy"]["minimum_support_reviews"]],
        ["dataset_type", "User-supplied CSV; sampling and real/synthetic provenance must be documented by the author."],
        ["accuracy_precision_recall_f1", "Not measured for this upload: no independent gold labels were provided."],
        ["null_values", "Empty numeric cells mean unavailable, not zero."],
        ["review_score_method", "Arithmetic mean of final opinion scores within one review, rounded to six decimals in [-1,+1]; opposite opinions still retain the Mixed label."],
        ["review_score_scope", "Hybrid: recognized aspect contexts only; mean unavailable if any context is unscored. Baseline: recognized opinions with its existing scope policy. Blank score means unavailable."],
        ["strength_policy", "Final score <= -0.5 Strong Negative; (-0.5,-0.05) Weak Negative; [-0.05,+0.05] Neutral; (+0.05,+0.5) Weak Positive; >= +0.5 Strong Positive. Descriptive thresholds, not confidence."],
    ])
    tables["conclusions.txt"] = render_report(report, include_partial=True).encode("utf-8")
    tables["README.txt"] = (
        "Results tables for an IEEE-format course report\n\n"
        "reviews.csv has exactly one row per submitted CSV record, including invalid and unsupported inputs.\n"
        "review_score is the mean of that review's final opinion scores, not a confidence or rating.\n"
        "review_score_scope distinguishes complete review, recognized opinions only, and unavailable.\n"
        "No opinion evidence produces a blank score; a numeric zero can be Neutral or cancelling Mixed opinions.\n"
        "strength describes each final opinion score; net_score_band describes the review mean and does not replace Mixed.\n"
        "aspects.csv holds separate extracted opinions; join on row_id, never a duplicated supplied ID.\n"
        "Category/issue polarity counts are distinct reviews, not opinions; Mixed is preserved.\n"
        "Any-negative counts include Mixed once. Scores average within each review before averaging reviews.\n"
        "Both aggregate scopes are explicit. Complete-only is primary; partial-inclusive means recognized opinions only.\n"
        "Blank averages/percentages mean no evidence. Low support, duplicates, and coverage must accompany interpretations.\n"
        "CSV formula-leading strings are apostrophe-escaped for spreadsheet safety. Unicode/BOM are supported.\n"
        "These are descriptive results, not measured prediction accuracy or a star rating.\n"
        "For empirical accuracy, independently annotate representative reviews and evaluate held-out labels.\n"
        "The authored 100-case regression corpus is a separate contract evaluation, not a blind real-world dataset.\n"
        "Record dataset provenance, annotation protocol, model/rule version, limits, hardware, repeated timing methods, and limitations.\n"
        "The ZIP contains no JSON and does not draft or submit a paper.\n"
    ).encode("utf-8")
    if batch.method == 'hybrid_neural':
        from .web_neural import recovery_summary
        summary = recovery_summary(batch)
        rows = []
        for row in batch.rows:
            if not row.analysis: continue
            for a in row.analysis.recovery.attempts:
                p = a.probabilities or {}
                rows.append([row.row_id, row.source.ordinal, a.record_index, a.category, a.aspect,
                             a.context, a.start, a.end, a.decision, a.reason, a.model_label,
                             p.get('Negative'), p.get('Objective'), p.get('Positive'), a.polarity_index,
                             row.analysis.recovery.model_id])
        tables['neural_decisions.csv'] = _csv(['row_id', 'row_number', 'record_index', 'category',
            'aspect', 'context', 'start', 'end', 'decision', 'reason', 'model_label',
            'negative_probability', 'objective_probability', 'positive_probability',
            'model_polarity_index', 'model_id'], rows)
        tables['neural_summary.csv'] = _csv(['field', 'value'],
            [[key, summary[key]] for key in ('model_id', 'assisted_reviews', 'added_opinions',
                'eligible_contexts', 'abstained_contexts', 'model_errors', 'not_eligible_contexts')] +
            [['acceptance_policy', str(summary['policy'])],
             ['scope', 'Original lexical aggregates retained. Neural additions are separate predictions, not measured accuracy.']])
        tables['README.txt'] += (
            '\nNEURAL RECOVERY: original hybrid statuses, scores and aggregate tables are unchanged.\n'
            'Additional accepted opinions and the combined label are separate columns in reviews.csv.\n'
            'neural_decisions.csv records every unscored candidate, probability and abstention.\n'
            'Model probabilities/indices are not lexical sentiment scores or strong/weak labels.\n'
            'neural_assisted is not complete, and recovery counts are not accuracy.\n'
        ).encode('utf-8')
    if batch.method == 'hybrid_routed':
        rows = []
        for row in batch.rows:
            if not row.analysis: continue
            for d in row.analysis.routed.decisions:
                p = d['probabilities']
                rows.append([row.row_id, row.source.ordinal, d['sentence'], d['category'], d['context'],
                    d['start'], d['end'], d['label'], d['accepted'], d['in_scope'], d['reason'],
                    *[p[s] for s in ('Absent', 'Negative', 'Neutral/Mixed', 'Positive')], d['model_direction_index']])
        tables['independent_neural_decisions.csv'] = _csv(['row_id', 'row_number', 'sentence', 'category', 'context',
            'start', 'end', 'predicted_label', 'accepted', 'in_scope', 'reason', 'p_absent', 'p_negative',
            'p_neutral_mixed', 'p_positive', 'model_direction_index'], rows)
        tables['README.txt'] += (
            '\nINDEPENDENT ROUTING: Partial/Unsupported reviews are reanalyzed from ALL original sentences.\n'
            'Neural predictions replace the selected review analysis, not append to hybrid opinions.\n'
            'Legacy aggregate tables remain original hybrid comparison evidence. See reviews.csv neural columns.\n'
            'The learned category-polarity model pools Staff under Service; Facilities maps Building/Business.\n'
            'Neutral/Mixed is the source merged label. No five-strength or neutral-intensity ground truth is claimed.\n'
            'model_direction_index=(Ppos-Pneg)/(Ppos+Pneg); it is not a calibrated sentiment rating.\n'
            'Review index averages available sentence indices by category, then categories equally; any accepted ambiguous category makes it unavailable.\n'
            'Reanalyzed does not mean completely understood or verified correct.\n'
        ).encode('utf-8')
    return tables


def paper_archive(batch: BatchResult, report: dict) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        for name, payload in paper_tables(batch, report).items():
            archive.writestr(name, payload)
    return buffer.getvalue()
