"""Batch records retain individual compiler results without changing the core."""

from dataclasses import asdict, dataclass
from typing import Any

from .csv_input import CSVInput, CSVReviewRow
from .models import AnalysisResult


@dataclass(frozen=True)
class RowOutcome:
    row_id: str
    source: CSVReviewRow
    execution_status: str
    analysis: AnalysisResult | None = None
    processing_error: str | None = None

    def to_dict(self, include_trace: bool = False) -> dict[str, Any]:
        return {
            "row_id": self.row_id,
            "row_number": self.source.ordinal,
            "source_lines": {"start": self.source.line_start, "end": self.source.line_end},
            "review_text": self.source.review_text,
            "supplied_review_id": self.source.supplied_review_id,
            "duplicate_text": self.source.duplicate_text,
            "duplicate_id": self.source.duplicate_id,
            "execution_status": self.execution_status,
            "validation_errors": [asdict(issue) for issue in self.source.issues],
            "processing_error": self.processing_error,
            "analysis": self.analysis.to_dict(include_trace=include_trace) if self.analysis else None,
        }


@dataclass(frozen=True)
class BatchResult:
    batch_id: str
    created_at: str
    analysis_fingerprint: str
    source: CSVInput
    rows: tuple[RowOutcome, ...]
    elapsed_seconds: float

    def get_row(self, row_id: str) -> RowOutcome:
        for row in self.rows:
            if row.row_id == row_id:
                return row
        raise KeyError(f"Unknown batch row: {row_id}")

    def summary(self) -> dict[str, Any]:
        counts = {key: 0 for key in (
            "submitted", "analyzed", "invalid_input", "processing_error",
            "complete", "partial", "unsupported", "duplicate_text_rows",
            "duplicate_id_rows", "extracted_opinions",
        )}
        counts["submitted"] = len(self.rows)
        for row in self.rows:
            counts[row.execution_status] += 1
            counts["duplicate_text_rows"] += int(row.source.duplicate_text)
            counts["duplicate_id_rows"] += int(row.source.duplicate_id)
            if row.analysis:
                counts[row.analysis.status] += 1
                counts["extracted_opinions"] += len(row.analysis.records)
        denominator = counts["analyzed"]
        return {
            "counts": counts,
            "coverage": {
                "denominator": "analyzed_rows",
                "denominator_count": denominator,
                "complete_percent": round(100 * counts["complete"] / denominator, 2) if denominator else None,
                "with_opinions_percent": round(100 * (counts["complete"] + counts["partial"]) / denominator, 2) if denominator else None,
                "scope": "Coverage of the controlled grammar, not measured sentiment accuracy.",
            },
        }

    def to_dict(self, include_trace: bool = False) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "batch_id": self.batch_id,
            "status": "completed",
            "created_at": self.created_at,
            "analysis_fingerprint": self.analysis_fingerprint,
            "elapsed_seconds": self.elapsed_seconds,
            "input": {
                "source_name": self.source.source_name,
                "sha256": self.source.source_sha256,
                "text_column": self.source.text_column,
                "id_column": self.source.id_column,
                "ignored_columns": list(self.source.ignored_columns),
            },
            "summary": self.summary(),
            "rows": [row.to_dict(include_trace) for row in self.rows],
        }
