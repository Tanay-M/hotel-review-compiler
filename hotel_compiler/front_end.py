"""Shared validation, lexer, parser and aspect semantics for both scorers."""
from dataclasses import dataclass
from uuid import uuid4

from .lexer import tokenize
from .parser import parse
from .semantics import analyze_semantics
from .models import Diagnostic, ReviewAST, SemanticRecord, Token

MAX_REVIEW_LENGTH = 10_000


@dataclass(frozen=True)
class CompiledReview:
    review_id: str
    review_text: str
    tokens: tuple[Token, ...]
    ast: ReviewAST
    semantics: tuple[SemanticRecord, ...]
    diagnostics: tuple[Diagnostic, ...]

    @property
    def status(self):
        return 'complete' if self.semantics and not self.diagnostics else 'partial' if self.semantics else 'unsupported'


def compile_frontend(text: str, review_id: str | None = None) -> CompiledReview:
    if not isinstance(text, str):
        raise TypeError('Review text must be a string.')
    if review_id is not None and (not isinstance(review_id, str) or not review_id.strip()):
        raise ValueError('Review ID must be a nonempty string.')
    if len(text) > MAX_REVIEW_LENGTH:
        raise ValueError(f'A review must contain at most {MAX_REVIEW_LENGTH:,} characters.')
    identifier = review_id if review_id is not None else str(uuid4())
    if not text.strip():
        return CompiledReview(identifier, text, (), ReviewAST(()), (),
                              (Diagnostic('EMPTY_INPUT', 'Enter a hotel review to analyze.', 0, len(text), 'input'),))
    tokens = tokenize(text)
    ast, syntax_diagnostics = parse(tokens)
    semantics, semantic_diagnostics = analyze_semantics(ast, text)
    return CompiledReview(identifier, text, tokens, ast, semantics, syntax_diagnostics + semantic_diagnostics)
