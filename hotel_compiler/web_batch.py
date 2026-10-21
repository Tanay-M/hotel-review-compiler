"""One retained local batch; synchronous bounded upload, no job infrastructure."""

from dataclasses import dataclass
from threading import Lock

from .batch import analyze_batch
from .batch_models import BatchResult
from .csv_input import CSVLimits, parse_review_csv
from .reporting import build_report
from .web_analysis import analyze_hybrid_batch, validate_method, METHODS


class BatchBusyError(RuntimeError):
    pass


@dataclass(frozen=True)
class BatchSession:
    batch: BatchResult
    report: dict

    def overview(self) -> dict:
        data = self.batch.to_dict(include_trace=False)
        data["report"] = self.report
        data["method_label"] = METHODS[self.batch.method]
        return data


class BatchStore:
    """Retain one successful run until replacement, explicit clear, or restart."""
    def __init__(self):
        self._upload_lock = Lock()
        self._state_lock = Lock()
        self._session = None

    def submit(self, payload: bytes, *, method="sentiwordnet", **options) -> BatchSession:
        validate_method(method)
        if not self._upload_lock.acquire(blocking=False):
            raise BatchBusyError("Another CSV is being analyzed. Wait for it to finish.")
        try:
            source = parse_review_csv(payload, limits=CSVLimits(), **options)
            batch = analyze_hybrid_batch(source) if method == "hybrid" else analyze_batch(source)
            session = BatchSession(batch, build_report(batch))
            with self._state_lock:
                self._session = session
            return session
        finally:
            self._upload_lock.release()

    def get(self, batch_id: str) -> BatchSession:
        with self._state_lock:
            if self._session is None or self._session.batch.batch_id != batch_id:
                raise KeyError("This batch is no longer available. Upload it again; the server retains one batch in memory.")
            return self._session

    def clear(self, batch_id: str) -> None:
        with self._state_lock:
            if self._session is None or self._session.batch.batch_id != batch_id:
                raise KeyError("This batch is no longer available.")
            self._session = None
