"""Presentation adapter for the independent research hybrid, without rescoring.

The core hybrid and its research exports remain unchanged. This adapter exposes
the existing dashboard record contract and retains every unscored candidate.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
from importlib.resources import files
import json
from time import perf_counter
from uuid import uuid4

from .batch_models import BatchResult, RowOutcome
from .hybrid import HybridAnalysis, HybridAspect, analyze_hybrid_review, default_engine
from .sentiment_policy import DEFAULT_POLICY


METHODS = {"sentiwordnet": "SentiWordNet compiler", "hybrid": "VADER + TextBlob hybrid"}


def validate_method(method):
    if not isinstance(method, str) or method not in METHODS:
        raise ValueError("Choose hybrid or sentiwordnet as the analysis method.")
    return method


@dataclass(frozen=True)
class DemoAspect:
    review_id: str
    source: HybridAspect

    def __getattr__(self, name):
        return getattr(self.source, name)

    @property
    def strength(self):
        return self.source.evidence.strength

    def to_ir(self):
        return {
            "review_id": self.review_id, "category": self.category, "issue": self.issue,
            "aspect_term": self.aspect_term, "opinion_term": self.opinion_expression,
            "opinion_expression": self.opinion_expression, "polarity": self.polarity,
            "score": self.score, "strength": self.strength, "start": self.start, "end": self.end,
        }


@dataclass(frozen=True)
class HybridDemoResult:
    source: HybridAnalysis

    @property
    def review_id(self): return self.source.review_id

    @property
    def review_text(self): return self.source.review_text

    @property
    def status(self): return self.source.aspect_analysis_status

    @property
    def overall(self): return self.source.overall

    @property
    def records(self): return tuple(DemoAspect(self.review_id, r) for r in self.source.records)

    @property
    def diagnostics(self): return self.source.diagnostics

    @property
    def review_score(self): return self.source.aspect_mean_score

    @property
    def review_score_scope(self):
        return "recognized aspect contexts only" if self.review_score is not None else "unavailable"

    @property
    def net_score_band(self): return DEFAULT_POLICY.strength(self.review_score)

    def to_dict(self, include_trace=False):
        result = {
            "method": "hybrid", "method_label": METHODS["hybrid"],
            "review_id": self.review_id, "review_text": self.review_text,
            "status": self.status, "overall": self.overall,
            "review_score": self.review_score, "review_score_scope": self.review_score_scope,
            "net_score_band": self.net_score_band,
            "records": [r.to_ir() for r in self.records],
            "diagnostics": [asdict(d) for d in self.diagnostics],
            "whole_text": asdict(self.source.whole_text),
            "unscored_contexts": sum(r.score is None for r in self.records),
        }
        if include_trace:
            result["trace"] = {
                "language": asdict(self.source.language) if self.source.language else {},
                "sentiment_evaluation": [asdict(r.evidence) for r in self.source.records],
                "intermediate_representation": result["records"],
                "attachments": [asdict(r) for r in self.source.records],
            }
        return result


def analyze_hybrid_demo(text, review_id=None, *, engine=None):
    return HybridDemoResult(analyze_hybrid_review(text, review_id, engine=engine))


def analyze_hybrid_batch(source):
    engine = default_engine()  # Missing shared dependencies fail the upload once.
    digest = sha256()
    for name in ("hybrid.py", "hybrid_nlp.py", "hybrid_vocabulary.py", "sentiment_policy.py", "web_analysis.py", "resources/hybrid_domain.json", "resources/hybrid_vocabulary.json"):
        digest.update(name.encode() + b"\0" + files("hotel_compiler").joinpath(name).read_bytes())
    digest.update(json.dumps({"versions": engine.versions, "resources": engine.lexicon_hashes,
                              "policy": asdict(engine.policy)}, sort_keys=True).encode())
    identifier = str(uuid4())
    created = datetime.now(timezone.utc).isoformat()
    started = perf_counter()
    rows = []
    for row in source.rows:
        row_id = f"{identifier}:{row.ordinal:06d}"
        if row.issues:
            outcome = RowOutcome(row_id, row, "invalid_input")
        else:
            try:
                result = analyze_hybrid_demo(row.review_text, row.supplied_review_id or row_id, engine=engine)
                outcome = RowOutcome(row_id, row, "analyzed", analysis=result)
            except Exception as error:
                outcome = RowOutcome(row_id, row, "processing_error", processing_error=f"{type(error).__name__}: {error}")
        rows.append(outcome)
    return BatchResult(identifier, created, digest.hexdigest(), source, tuple(rows),
                       round(perf_counter() - started, 6), method="hybrid")
