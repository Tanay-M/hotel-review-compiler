"""The public orchestration boundary shared by future input/output adapters."""

from uuid import uuid4

from .lexer import tokenize
from .models import AnalysisResult, Diagnostic, ReviewAST
from .parser import parse
from .semantics import analyze_semantics
from .sentiwordnet import evaluate


MAX_REVIEW_LENGTH = 10_000


def analyze_review(text: str, review_id: str | None = None) -> AnalysisResult:
    """Compile a review into aspect-level records and an inspectable stage trace.

    Unsupported language is returned as diagnostics. Bad API argument types,
    oversized inputs, and broken lexical resources are explicit exceptions.
    """
    if not isinstance(text, str):
        raise TypeError("Review text must be a string.")
    if review_id is not None and (not isinstance(review_id, str) or not review_id.strip()):
        raise ValueError("Review ID must be a nonempty string.")
    if len(text) > MAX_REVIEW_LENGTH:
        raise ValueError(f"A review must contain at most {MAX_REVIEW_LENGTH:,} characters.")
    identifier = review_id if review_id is not None else str(uuid4())
    if not text.strip():
        return AnalysisResult(
            identifier, text, "unsupported", "Unanalyzed", (),
            (Diagnostic("EMPTY_INPUT", "Enter a hotel review to analyze.", 0, len(text), "input"),),
            (), ReviewAST(()), (),
        )
    tokens = tokenize(text)
    ast, syntax_diagnostics = parse(tokens)
    semantics, semantic_diagnostics = analyze_semantics(ast, text)
    records = tuple(evaluate(record, identifier) for record in semantics)
    diagnostics = syntax_diagnostics + semantic_diagnostics
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
    return AnalysisResult(identifier, text, status, overall, records, diagnostics, tokens, ast, semantics)

