"""Evidence-backed, deterministic sentences for the aggregated batch result."""

from hashlib import sha256
from importlib.resources import files

from .aggregation import MIN_SUPPORT_REVIEWS, aggregate_batch
from .batch_models import BatchResult


def reporting_fingerprint() -> str:
    digest = sha256()
    for name in ("aggregation.py", "reporting.py"):
        digest.update(name.encode("utf-8") + b"\0")
        digest.update(files("hotel_compiler").joinpath(name).read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _conclusions(view: dict) -> list[dict]:
    scope = view["scope"]
    description = "completely analyzed reviews" if scope == "complete_reviews" else "complete/partial reviews using recognized opinions only"
    total = view["eligible_reviews"]
    conclusions = []

    def add(code, text, row_ids, **metadata):
        conclusions.append({"code": code, "scope": scope, "text": text, "row_ids": row_ids, **metadata})

    if not total:
        add("NO_ELIGIBLE_REVIEWS", f"No {description} are available; sentiment conclusions and averages are unavailable.", [])
    else:
        counts = view["overall_counts"]
        add("OVERALL", f"Among {total} {description}, overall labels are {counts['Positive']} Positive, {counts['Negative']} Negative, {counts['Mixed']} Mixed, and {counts['Neutral']} Neutral.",
            view["eligible_row_ids"], counts=counts, denominator=total)
    for group in view["categories"]:
        category, mentioned = group["category"], group["mentioned_reviews"]
        if not mentioned:
            add("NOT_MENTIONED", f"{category} has no recognized mentions in this scope; no sentiment conclusion is available.", [], category=category, denominator=0)
            continue
        counts = group["polarity_counts"]
        suffix = f" Support is low (fewer than {MIN_SUPPORT_REVIEWS} reviews); avoid generalizing." if group["evidence_status"] == "low_support" else ""
        add("CATEGORY", f"Among {total} {description}, {mentioned} mention {category}: {counts['Positive']} Positive, {counts['Negative']} Negative, {counts['Mixed']} Mixed, and {counts['Neutral']} Neutral.{suffix}",
            [item["row_id"] for item in group["evidence"]], category=category, denominator=mentioned,
            counts=counts, evidence=group["evidence"], evidence_status=group["evidence_status"])
    for group in view["issues"]:
        negative = group["negative_mention_reviews"]
        if not negative:
            continue
        suffix = " Support is low; avoid generalizing." if group["evidence_status"] == "low_support" else ""
        add("ISSUE_COMPLAINT", f"Among {total} {description}, {group['category']} / {group['issue']} has negative mentions in {negative} of {group['mentioned_reviews']} reviews mentioning that issue ({group['negative_mention_percent']:.2f}%). Mixed reviews count once as having a negative mention.{suffix}",
            group["negative_mention_row_ids"], category=group["category"], issue=group["issue"], count=negative,
            denominator=group["mentioned_reviews"], evidence_status=group["evidence_status"],
            evidence=[item for item in group["evidence"] if item["row_id"] in set(group["negative_mention_row_ids"])])
    leaders = [group for group in view["complaint_ranking"] if group["rank"] == 1]
    if leaders:
        names = ", ".join(f"{group['category']} / {group['issue']}" for group in leaders)
        qualification = "tie for the highest" if len(leaders) > 1 else "has the highest"
        add("COMPLAINT_FREQUENCY", f"Among {total} {description}, {names} {qualification} complaint count ({leaders[0]['negative_mention_reviews']} distinct reviews each). This ranks frequency, not severity; inspect support and denominators before interpreting it.",
            list(dict.fromkeys(row_id for group in leaders for row_id in group["row_ids"])), leaders=leaders)
    elif total:
        add("NO_RECOGNIZED_COMPLAINTS", f"No negative opinions were recognized among {total} {description}; this does not establish that the full submitted dataset has no complaints.", view["eligible_row_ids"])
    return conclusions


def build_report(batch: BatchResult) -> dict:
    aggregation = aggregate_batch(batch)
    counts = aggregation["coverage"]["counts"]
    notes = [f"Primary conclusions use {counts['complete']} completely analyzed reviews out of {counts['submitted']} submitted rows. Partial ({counts['partial']}), unsupported ({counts['unsupported']}), invalid ({counts['invalid_input']}), and processing-error ({counts['processing_error']}) rows are excluded from primary sentiment summaries."]
    if aggregation["limited_primary_coverage"]:
        notes.append(f"Limited primary coverage: only {aggregation['primary_complete_share_submitted_percent']:.2f}% of submitted rows are completely analyzed; conclusions provide limited evidence about the full dataset.")
    if counts["duplicate_text_rows"] or counts["duplicate_id_rows"]:
        notes.append(f"Duplicates retained: {counts['duplicate_text_rows']} rows have repeated text and {counts['duplicate_id_rows']} have repeated supplied IDs. These rows count separately and can influence observed frequencies.")
    notes.append("Sentiment indices and coverage are not hotel ratings, confidence, or measured real-world accuracy. Conclusions are generated from counts, without an LLM.")
    return {
        "schema_version": 1, "batch_id": batch.batch_id,
        "analysis_fingerprint": batch.analysis_fingerprint, "reporting_fingerprint": reporting_fingerprint(),
        "source_sha256": batch.source.source_sha256, "aggregation": aggregation, "notes": notes,
        "conclusions": {scope: _conclusions(view) for scope, view in aggregation["views"].items()},
        "evidence_contract": "row_ids resolve through BatchResult.get_row or batch.json rows; record_indices are zero-based positions in the retained analysis.records and scoring trace.",
    }


def render_report(report: dict, *, include_partial: bool = False) -> str:
    lines = [f"TEAM 17 | BATCH REPORT {report['batch_id']}", *report["notes"], "", "Primary: complete reviews"]
    scopes = ["complete_reviews"]
    if include_partial:
        scopes.append("complete_and_partial")
    for scope in scopes:
        if scope == "complete_and_partial":
            lines.extend(["", "Secondary: complete and partial reviews; recognized opinions only"])
        lines.extend(item["text"] for item in report["conclusions"][scope])
        lines.append("Evidence: see summary.json conclusion row_ids and category/issue record_indices; use batch.json for original text and full compiler traces.")
    return "\n".join(lines) + "\n"
