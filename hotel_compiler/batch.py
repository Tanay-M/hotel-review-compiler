"""Stateless CSV batching around the existing public compiler pipeline."""

from collections.abc import Callable
from datetime import datetime, timezone
from hashlib import sha256
from importlib.resources import files
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from .batch_models import BatchResult, RowOutcome
from .csv_input import CSVInput, CSVLimits, read_review_csv
from .pipeline import analyze_review
from .sentiwordnet import ResourceError, load_synsets
from .compiler_profiles import current_profile


def analysis_fingerprint() -> str:
    """Identify the analysis code and packaged rules used for a saved run."""
    digest = sha256()
    root = files("hotel_compiler")
    for name in (
        "pipeline.py", "front_end.py", "models.py", "lexer.py", "parser.py", "semantics.py",
        "sentiwordnet.py", "sentiment_policy.py", "vocabulary.py", "resources/domain.json",
        "resources/sentiwordnet.tsv", "resources/provenance.json",
    ):
        digest.update(name.encode("utf-8") + b"\0")
        digest.update(root.joinpath(name).read_bytes())
        digest.update(b"\0")
    if current_profile() == 'expanded':
        for name in ('compiler_profiles.py','expanded_parser.py','resources/domain_expanded.json',
                     'resources/sentiwordnet_expanded.tsv','resources/provenance_expanded.json'):
            digest.update(name.encode()+b'\0'+root.joinpath(name).read_bytes()+b'\0')
    return digest.hexdigest()


def analyze_batch(
    source: CSVInput,
    *,
    batch_id: str | None = None,
    progress: Callable[[int, int], None] | None = None,
) -> BatchResult:
    if batch_id is not None and (not isinstance(batch_id, str) or not batch_id.strip()):
        raise ValueError("Batch ID must be a nonempty string.")
    identifier = batch_id if batch_id is not None else str(uuid4())
    started = perf_counter()
    created_at = datetime.now(timezone.utc).isoformat()
    # A broken shared resource is a job failure, not hundreds of row failures.
    load_synsets()
    fingerprint = analysis_fingerprint()
    rows = []
    for row in source.rows:
        row_id = f"{identifier}:{row.ordinal:06d}"
        if row.issues:
            outcome = RowOutcome(row_id, row, "invalid_input")
        else:
            try:
                result = analyze_review(row.review_text, row.supplied_review_id or row_id)
            except ResourceError:
                raise
            except Exception as error:
                # Report unexpected per-review failures without abandoning valid
                # neighbors. Interrupts and process-exit exceptions propagate.
                outcome = RowOutcome(row_id, row, "processing_error", processing_error=f"{type(error).__name__}: {error}")
            else:
                outcome = RowOutcome(row_id, row, "analyzed", analysis=result)
        rows.append(outcome)
        if progress:
            progress(len(rows), len(source.rows))
    return BatchResult(identifier, created_at, fingerprint, source, tuple(rows), round(perf_counter() - started, 6),
                       method='sentiwordnet' if current_profile()=='expanded' else 'sentiwordnet_original')


def analyze_csv(
    path: str | Path,
    *,
    text_column: str = "review_text",
    id_column: str = "review_id",
    limits: CSVLimits | None = None,
    batch_id: str | None = None,
    progress: Callable[[int, int], None] | None = None,
) -> BatchResult:
    source = read_review_csv(path, text_column=text_column, id_column=id_column, limits=limits)
    return analyze_batch(source, batch_id=batch_id, progress=progress)
