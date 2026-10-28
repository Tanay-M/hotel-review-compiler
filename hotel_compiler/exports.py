"""Explicit batch exports. Existing output files are never overwritten."""

from contextlib import ExitStack
import csv
import json
from io import StringIO
from pathlib import Path
from typing import Any, TextIO

from .batch_models import BatchResult
from .reporting import build_report, render_report


def _spreadsheet_cell(value: Any) -> Any:
    # Guard formula-leading strings, including whitespace-prefixed formulas.
    # Numeric score cells remain numbers; JSON preserves all original strings.
    if isinstance(value, str) and (
        value.startswith(("\t", "\r", "\n")) or value.lstrip().startswith(("=", "+", "-", "@"))
    ):
        return "'" + value
    return value


def _writer(handle: TextIO, fields: list[str]) -> csv.DictWriter:
    writer = csv.DictWriter(handle, fieldnames=fields)
    writer.writeheader()
    return writer


def _write_reviews(handle: TextIO, batch: BatchResult) -> None:
    fields = [
        "method", "batch_id", "row_id", "row_number", "line_start", "line_end", "supplied_review_id",
        "review_text", "duplicate_text", "duplicate_id", "execution_status", "analysis_status",
        "overall", "overall_scope", "review_score", "review_score_scope", "net_score_band", "opinion_count", "categories", "issues", "opinion_expressions", "aspect_results",
        "diagnostics", "validation_errors", "processing_error", "whole_text_score", "whole_text_polarity", "whole_text_strength",
    ]
    if batch.method == 'hybrid_neural':
        fields += ['neural_recovery_status', 'neural_added_opinions', 'augmented_overall',
                   'neural_results', 'neural_model_id']
    if batch.method == 'hybrid_routed':
        fields += ['selected_method', 'routed_status', 'neural_overall', 'model_direction_index',
                   'independent_category_results', 'routed_model_id', 'selected_overall', 'selected_index', 'selected_index_type']
    writer = _writer(handle, fields)
    for row in batch.rows:
        result = row.analysis
        data = {
            "method": batch.method, "batch_id": batch.batch_id, "row_id": row.row_id, "row_number": row.source.ordinal,
            "line_start": row.source.line_start, "line_end": row.source.line_end,
            "supplied_review_id": row.source.supplied_review_id, "review_text": row.source.review_text,
            "duplicate_text": row.source.duplicate_text, "duplicate_id": row.source.duplicate_id,
            "execution_status": row.execution_status, "analysis_status": result.status if result else "",
            "overall": result.overall if result else "",
            "review_score": result.review_score if result else None,
            "review_score_scope": result.review_score_scope if result else "unavailable",
            "net_score_band": result.net_score_band if result else "Unavailable",
            "overall_scope": "recognized clauses only" if result and result.status == "partial" else
                             "no supported opinions" if result and result.status == "unsupported" else
                             "complete review" if result else "not analyzed",
            "opinion_count": len(result.records) if result else 0,
            "categories": "; ".join(dict.fromkeys(r.category for r in result.records)) if result else "",
            "issues": "; ".join(dict.fromkeys(f"{r.category} / {r.issue}" for r in result.records)) if result else "",
            "opinion_expressions": "; ".join(r.opinion_expression for r in result.records) if result else "",
            "aspect_results": "; ".join(f"{r.category} / {r.issue}: {r.opinion_expression} -> {r.polarity} ({format(r.score, '+.6f') if r.score is not None else 'Unavailable'})" for r in result.records) if result else "",
            "diagnostics": " | ".join(f"{d.stage}/{d.code} [{d.start}:{d.end}]: {d.message}" for d in result.diagnostics) if result else "",
            "validation_errors": " | ".join(f"{issue.code}: {issue.message}" for issue in row.source.issues),
            "processing_error": row.processing_error,
            "whole_text_score": result.source.whole_text.score if batch.method in {"hybrid", "hybrid_neural", "hybrid_routed"} and result else None,
            "whole_text_polarity": result.source.whole_text.polarity if batch.method in {"hybrid", "hybrid_neural", "hybrid_routed"} and result else "",
            "whole_text_strength": result.source.whole_text.strength if batch.method in {"hybrid", "hybrid_neural", "hybrid_routed"} and result else "",
        }
        if batch.method == 'hybrid_neural':
            recovery = result.recovery if result else None
            data.update(neural_recovery_status=recovery.recovery_status if recovery else 'not_analyzed',
                        neural_added_opinions=len(recovery.recovered) if recovery else 0,
                        augmented_overall=recovery.combined_overall if recovery else '',
                        neural_results='; '.join(f'{a.category} / {a.aspect}: {a.context} -> {a.model_label}'
                                                 for a in recovery.recovered) if recovery else '',
                        neural_model_id=recovery.model_id if recovery else '')
        if batch.method == 'hybrid_routed':
            r = result.routed if result else None
            data.update(selected_method=r.selected_method if r else 'invalid_input',
                routed_status=r.route_status if r else 'not_analyzed', neural_overall=r.overall if r else '',
                model_direction_index=r.review_index if r else None,
                independent_category_results='; '.join(f"{c['category']}: {c['label']} ({c['model_direction_index']})"
                    for c in r.categories) if r else '', routed_model_id=r.model_id if r else '',
                selected_overall=(r.overall if r.selected_method == 'independent_neural' else result.overall) if r else '',
                selected_index=(r.review_index if r.selected_method == 'independent_neural' else result.review_score) if r else None,
                selected_index_type=('model_direction_index' if r.selected_method == 'independent_neural' else 'lexical_mean') if r else 'unavailable')
        writer.writerow({key: _spreadsheet_cell(value) for key, value in data.items()})


def _write_aspects(handle: TextIO, batch: BatchResult) -> None:
    writer = _writer(handle, [
        "method", "batch_id", "row_id", "row_number", "review_id", "analysis_status", "category", "issue",
        "aspect_term", "opinion_term", "opinion_expression", "polarity", "score", "strength", "start", "end",
    ])
    for row in batch.rows:
        if row.analysis is None:
            continue
        for record in row.analysis.records:
            data = {
                "method": batch.method, "batch_id": batch.batch_id, "row_id": row.row_id, "row_number": row.source.ordinal,
                "analysis_status": row.analysis.status, **record.to_ir(),
            }
            writer.writerow({key: _spreadsheet_cell(value) for key, value in data.items()})


def batch_csv_bytes(batch: BatchResult, kind: str = "reviews") -> bytes:
    """Generate a complete downloadable table without filesystem writes."""
    if kind not in {"reviews", "aspects"}:
        raise ValueError("Unknown CSV table.")
    handle = StringIO(newline="")
    (_write_reviews if kind == "reviews" else _write_aspects)(handle, batch)
    return handle.getvalue().encode("utf-8-sig")


def export_batch(batch: BatchResult, directory: str | Path, *, include_partial_report: bool = False) -> dict[str, Path]:
    """Write individual outputs and reports, cleaning our new files on failure.

    Exclusive creation protects existing files, even if another process creates
    an output between directory validation and opening it. No automatic saves
    occur in the analyzer; callers must explicitly choose this destination.
    """
    destination = Path(directory)
    destination.mkdir(parents=True, exist_ok=True)
    paths = {name: destination / name for name in ("reviews.csv", "aspects.csv", "batch.json", "summary.json", "report.txt")}
    created: list[Path] = []
    try:
        with ExitStack() as stack:
            handles = {}
            for name, path in paths.items():
                handles[name] = stack.enter_context(path.open("x", encoding="utf-8-sig" if name.endswith(".csv") else "utf-8", newline=""))
                created.append(path)
            _write_reviews(handles["reviews.csv"], batch)
            _write_aspects(handles["aspects.csv"], batch)
            json.dump(batch.to_dict(include_trace=True), handles["batch.json"], ensure_ascii=False, indent=2)
            handles["batch.json"].write("\n")
            report = build_report(batch)
            json.dump(report, handles["summary.json"], ensure_ascii=False, indent=2)
            handles["summary.json"].write("\n")
            handles["report.txt"].write(render_report(report, include_partial=include_partial_report))
    except BaseException:
        for path in created:
            path.unlink(missing_ok=True)
        raise
    return paths
