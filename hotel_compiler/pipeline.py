"""The public orchestration boundary shared by future input/output adapters."""

from .models import AnalysisResult
from .front_end import compile_frontend, MAX_REVIEW_LENGTH
from .sentiwordnet import evaluate
from .compiler_profiles import compiler_profile, current_profile


def analyze_review(text: str, review_id: str | None = None, *, profile: str | None = None) -> AnalysisResult:
    """Compile a review into aspect-level records and an inspectable stage trace.

    Unsupported language is returned as diagnostics. Bad API argument types,
    oversized inputs, and broken lexical resources are explicit exceptions.
    """
    if profile is not None:
        with compiler_profile(profile):
            return analyze_review(text, review_id)
    front = compile_frontend(text, review_id)
    identifier, tokens, ast, semantics = front.review_id, front.tokens, front.ast, front.semantics
    records = tuple(evaluate(record, identifier) for record in semantics)
    diagnostics = front.diagnostics
    status = "complete" if records and not diagnostics else "partial" if records else "unsupported"
    polarities = {record.polarity for record in records}
    if "Positive" in polarities and "Negative" in polarities:
        overall = "Mixed"
    elif "Positive" in polarities:
        overall = "Positive"
    elif "Negative" in polarities:
        overall = "Negative"
    elif records:
        overall = "Neutral"
    else:
        overall = "Unanalyzed"
    return AnalysisResult(identifier, text, status, overall, records, diagnostics, tokens, ast, semantics,
                          compiler_profile=current_profile())

