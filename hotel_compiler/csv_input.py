"""Strict UTF-8 CSV ingestion, independent of sentiment analysis."""

from collections import Counter
import csv
from dataclasses import dataclass, replace
from hashlib import sha256
from io import StringIO
from pathlib import Path
from threading import Lock

from .pipeline import MAX_REVIEW_LENGTH


class CSVInputError(ValueError):
    """The file cannot be safely interpreted as a review batch."""


@dataclass(frozen=True)
class CSVLimits:
    max_rows: int = 1_000
    max_file_bytes: int = 10 * 1024 * 1024

    def __post_init__(self) -> None:
        for value in (self.max_rows, self.max_file_bytes):
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                raise ValueError("CSV limits must be positive integers.")


@dataclass(frozen=True)
class InputIssue:
    code: str
    message: str


@dataclass(frozen=True)
class CSVReviewRow:
    ordinal: int
    line_start: int
    line_end: int
    review_text: str | None
    supplied_review_id: str | None
    issues: tuple[InputIssue, ...] = ()
    duplicate_text: bool = False
    duplicate_id: bool = False


@dataclass(frozen=True)
class CSVInput:
    source_name: str
    source_sha256: str
    text_column: str
    id_column: str | None
    ignored_columns: tuple[str, ...]
    rows: tuple[CSVReviewRow, ...]


_CSV_FIELD_LOCK = Lock()


def read_review_csv(
    path: str | Path,
    *,
    text_column: str = "review_text",
    id_column: str = "review_id",
    limits: CSVLimits | None = None,
) -> CSVInput:
    """Validate the entire file before returning any rows.

    Missing default review_id is allowed. Explicit non-default column names
    must exist. Empty CSV records are retained as invalid rows, not skipped.
    Duplicate flags identify all rows sharing nonblank text or an external ID.
    """
    limits = limits or CSVLimits()
    for name in (text_column, id_column):
        if not isinstance(name, str) or not name.strip():
            raise CSVInputError("Column names must be nonempty strings.")
    text_column, id_column = text_column.strip(), id_column.strip()
    if text_column == id_column:
        raise CSVInputError("Review text and ID must use different columns.")
    source = Path(path)
    with source.open("rb") as handle:
        chunks = []
        byte_count = 0
        while byte_count <= limits.max_file_bytes:
            chunk = handle.read(min(65_536, limits.max_file_bytes + 1 - byte_count))
            if not chunk:
                break
            chunks.append(chunk)
            byte_count += len(chunk)
        payload = b"".join(chunks)
    if len(payload) > limits.max_file_bytes:
        raise CSVInputError(f"CSV exceeds the {limits.max_file_bytes:,}-byte file limit.")
    return parse_review_csv(payload, source_name=source.name, text_column=text_column, id_column=id_column, limits=limits)


def parse_review_csv(
    payload: bytes, *, source_name: str = "upload.csv", text_column: str = "review_text",
    id_column: str = "review_id", limits: CSVLimits | None = None,
) -> CSVInput:
    """Use the same CSV contract for an in-memory upload; never save a file."""
    limits = limits or CSVLimits()
    if not isinstance(payload, bytes):
        raise TypeError("CSV input must be bytes.")
    if len(payload) > limits.max_file_bytes:
        raise CSVInputError(f"CSV exceeds the {limits.max_file_bytes:,}-byte file limit.")
    for name in (text_column, id_column):
        if not isinstance(name, str) or not name.strip():
            raise CSVInputError("Column names must be nonempty strings.")
    text_column, id_column = text_column.strip(), id_column.strip()
    if text_column == id_column:
        raise CSVInputError("Review text and ID must use different columns.")
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise CSVInputError("CSV must use UTF-8 encoding; export it as CSV UTF-8.") from error

    # csv.field_size_limit is process-global. Restore it even on failure and
    # serialize our readers, so an oversized field becomes a row error rather
    # than preventing its valid neighbors from being read.
    with _CSV_FIELD_LOCK:
        previous_limit = csv.field_size_limit()
        csv.field_size_limit(max(previous_limit, limits.max_file_bytes))
        try:
            reader = csv.reader(StringIO(text, newline=""), strict=True)
            try:
                header = next(reader)
            except StopIteration as error:
                raise CSVInputError("CSV is empty; a header row is required.") from error
            names = [name.strip() for name in header]
            if not names or any(not name for name in names):
                raise CSVInputError("Every CSV header must have a nonempty column name.")
            if len(set(names)) != len(names):
                raise CSVInputError("CSV contains duplicate column names.")
            if text_column not in names:
                raise CSVInputError(f"Missing review text column {text_column!r}. Available: {', '.join(names)}.")
            if id_column not in names and id_column != "review_id":
                raise CSVInputError(f"Missing selected ID column {id_column!r}.")
            text_index = names.index(text_column)
            id_index = names.index(id_column) if id_column in names else None
            rows: list[CSVReviewRow] = []
            while True:
                line_start = reader.line_num + 1
                try:
                    values = next(reader)
                except StopIteration:
                    break
                ordinal = len(rows) + 1
                if ordinal > limits.max_rows:
                    raise CSVInputError(f"CSV exceeds the {limits.max_rows:,}-review row limit.")
                review = values[text_index] if text_index < len(values) else None
                identifier = values[id_index] if id_index is not None and id_index < len(values) else None
                if identifier is not None and not identifier.strip():
                    identifier = None
                issues = []
                if len(values) != len(names):
                    issues.append(InputIssue("COLUMN_COUNT", f"Expected {len(names)} cells, found {len(values)}."))
                if review is None or not review.strip():
                    issues.append(InputIssue("EMPTY_REVIEW", "Review text is missing or blank."))
                elif len(review) > MAX_REVIEW_LENGTH:
                    issues.append(InputIssue("REVIEW_TOO_LONG", f"Review exceeds {MAX_REVIEW_LENGTH:,} characters."))
                rows.append(CSVReviewRow(ordinal, line_start, reader.line_num, review, identifier, tuple(issues)))
            if not rows:
                raise CSVInputError("CSV contains a header but no review rows.")
        except csv.Error as error:
            raise CSVInputError(f"Malformed CSV near physical line {reader.line_num}: {error}.") from error
        finally:
            csv.field_size_limit(previous_limit)

    text_counts = Counter(row.review_text for row in rows if row.review_text and row.review_text.strip())
    id_counts = Counter(row.supplied_review_id for row in rows if row.supplied_review_id is not None)
    rows = [replace(row,
                    duplicate_text=bool(row.review_text and text_counts[row.review_text] > 1),
                    duplicate_id=bool(row.supplied_review_id is not None and id_counts[row.supplied_review_id] > 1))
            for row in rows]
    return CSVInput(
        source_name, sha256(payload).hexdigest(), text_column,
        id_column if id_index is not None else None,
        tuple(name for name in names if name not in {text_column, id_column}), tuple(rows),
    )
