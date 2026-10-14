"""Count retained opinions by distinct batch row, without reinterpreting text."""

from collections import defaultdict
from math import fsum

from .batch_models import BatchResult, RowOutcome
from .vocabulary import load_vocabulary


POLARITIES = ("Positive", "Negative", "Mixed", "Neutral")
MIN_SUPPORT_REVIEWS = 5
LOW_COMPLETE_COVERAGE_PERCENT = 80


def _polarity(records) -> str:
    """Use the core's presence convention; opposite opinions remain Mixed."""
    values = {record.polarity for _, record in records}
    if "Positive" in values and "Negative" in values:
        return "Mixed"
    if "Positive" in values:
        return "Positive"
    if "Negative" in values:
        return "Negative"
    return "Neutral"


def _percent(count: int, denominator: int) -> float | None:
    return round(100 * count / denominator, 2) if denominator else None


def _group(group: dict, scope: str, category: str, issue: str | None = None) -> dict:
    count = len(group)
    buckets = {label: [] for label in POLARITIES}
    positive, negative, evidence, means = [], [], [], []
    for row_id, records in group.items():
        buckets[_polarity(records)].append(row_id)
        if any(record.polarity == "Positive" for _, record in records):
            positive.append(row_id)
        if any(record.polarity == "Negative" for _, record in records):
            negative.append(row_id)
        means.append(fsum(record.score for _, record in records) / len(records))
        evidence.append({"row_id": row_id, "record_indices": [index for index, _ in records]})
    return {
        "scope": scope, "category": category, "issue": issue,
        "evidence_status": "not_mentioned" if not count else "low_support" if count < MIN_SUPPORT_REVIEWS else "supported",
        "mentioned_reviews": count, "extracted_opinions": sum(len(records) for records in group.values()),
        "polarity_counts": {label: len(ids) for label, ids in buckets.items()},
        "polarity_percent": {label: _percent(len(ids), count) for label, ids in buckets.items()},
        "polarity_row_ids": buckets,
        "percentage_denominator": "distinct eligible reviews mentioning this category/issue",
        "positive_mention_reviews": len(positive), "positive_mention_percent": _percent(len(positive), count),
        "positive_mention_row_ids": positive,
        "negative_mention_reviews": len(negative), "negative_mention_percent": _percent(len(negative), count),
        "negative_mention_row_ids": negative,
        "average_score": round(fsum(means) / count, 6) if count else None,
        "score_method": "Mean of opinion scores within each review/group, then mean across distinct reviews; a lexicon/rule sentiment index, not a rating or confidence.",
        "evidence": evidence,
    }


def _view(rows: list[RowOutcome], scope: str) -> dict:
    categories, issues = defaultdict(dict), defaultdict(dict)
    overall = {label: [] for label in POLARITIES}
    for row in rows:
        overall[row.analysis.overall].append(row.row_id)
        for index, record in enumerate(row.analysis.records):
            categories[record.category].setdefault(row.row_id, []).append((index, record))
            issues[record.category, record.issue].setdefault(row.row_id, []).append((index, record))
    category_metrics = [_group(categories[category], scope, category) for category in load_vocabulary()["categories"]]
    issue_metrics = [_group(group, scope, category, issue) for (category, issue), group in sorted(issues.items())]
    complaints = sorted((group for group in issue_metrics if group["negative_mention_reviews"]),
                        key=lambda group: (-group["negative_mention_reviews"], group["category"], group["issue"]))
    ranks, previous, rank = [], None, 0
    for position, group in enumerate(complaints, 1):
        if group["negative_mention_reviews"] != previous:
            rank = position
        previous = group["negative_mention_reviews"]
        ranks.append({"rank": rank, "category": group["category"], "issue": group["issue"],
                      "negative_mention_reviews": previous, "mentioned_reviews": group["mentioned_reviews"],
                      "negative_mention_percent": group["negative_mention_percent"],
                      "row_ids": group["negative_mention_row_ids"], "evidence_status": group["evidence_status"]})
    return {
        "scope": scope, "eligible_reviews": len(rows), "eligible_row_ids": [row.row_id for row in rows],
        "extracted_opinions": sum(len(row.analysis.records) for row in rows),
        "overall_counts": {label: len(ids) for label, ids in overall.items()},
        "overall_percent": {label: _percent(len(ids), len(rows)) for label, ids in overall.items()},
        "overall_row_ids": overall, "overall_percentage_denominator": "eligible reviews in this scope",
        "categories": category_metrics, "issues": issue_metrics,
        "complaint_ranking": ranks,
        "ranking_method": "Distinct reviews with any negative mention, including Mixed once; ties share rank. Frequency is not severity.",
    }


def aggregate_batch(batch: BatchResult) -> dict:
    """Return primary complete-review and separate complete+partial metrics."""
    analyzed = [row for row in batch.rows if row.execution_status == "analyzed" and row.analysis]
    complete = [row for row in analyzed if row.analysis.status == "complete"]
    recognized = [row for row in analyzed if row.analysis.status in {"complete", "partial"}]
    summary = batch.summary()
    share = _percent(len(complete), len(batch.rows))
    return {
        "schema_version": 1, "coverage": summary,
        "primary_complete_share_submitted_percent": share,
        "limited_primary_coverage": share is not None and share < LOW_COMPLETE_COVERAGE_PERCENT,
        "policy": {
            "primary_scope": "complete_reviews", "secondary_scope": "complete_and_partial",
            "minimum_support_reviews": MIN_SUPPORT_REVIEWS,
            "low_complete_coverage_percent_of_submitted": LOW_COMPLETE_COVERAGE_PERCENT,
            "threshold_note": "Demo reporting conventions, not statistical significance or measured accuracy.",
            "duplicates": "Repeated CSV rows remain separate observations; duplicate flags stay visible in coverage and individual outputs.",
            "partial": "Secondary view uses recognized opinions only; it never changes the primary view.",
        },
        "views": {
            "complete_reviews": _view(complete, "complete_reviews"),
            "complete_and_partial": _view(recognized, "complete_and_partial"),
        },
    }
