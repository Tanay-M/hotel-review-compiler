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
        ["batch_id", batch.batch_id], ["created_at_utc", batch.created_at], ["source_name", batch.source.source_name],
        ["source_sha256", batch.source.source_sha256], ["analysis_fingerprint", batch.analysis_fingerprint],
        ["reporting_fingerprint", report["reporting_fingerprint"]], ["python_version", platform.python_version()],
        ["platform", platform.platform()], ["analysis_seconds", batch.elapsed_seconds],
        ["timing_scope", "Single observed core batch run, including resource preflight; excludes CSV decoding, reporting, HTTP transfer and browser rendering. Not a repeated performance benchmark."],
        ["primary_scope", "complete_reviews"], ["secondary_scope", "complete_and_partial: recognized opinions only"],
        ["minimum_support_reviews", aggregation["policy"]["minimum_support_reviews"]],
        ["dataset_type", "User-supplied CSV; sampling and real/synthetic provenance must be documented by the author."],
        ["accuracy_precision_recall_f1", "Not measured for this upload: no independent gold labels were provided."],
        ["null_values", "Empty numeric cells mean unavailable, not zero."],
    ])
    tables["conclusions.txt"] = render_report(report, include_partial=True).encode("utf-8")
    tables["README.txt"] = (
        "Results tables for an IEEE-format course report\n\n"
        "reviews.csv has exactly one row per submitted CSV record, including invalid and unsupported inputs.\n"
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
    return tables


def paper_archive(batch: BatchResult, report: dict) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        for name, payload in paper_tables(batch, report).items():
            archive.writestr(name, payload)
    return buffer.getvalue()
