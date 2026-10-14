"""Records exchanged between the compiler's stages."""

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Token:
    kind: str
    value: str
    text: str
    start: int
    end: int
    normalization_rule: str | None = None
    verb_form: str | None = None


@dataclass(frozen=True)
class Diagnostic:
    code: str
    message: str
    start: int
    end: int
    stage: str


@dataclass(frozen=True)
class Clause:
    subject: Token | None
    opinion: Token
    negation: Token | None
    intensifier: Token | None
    connector: str | None
    start: int
    end: int
    copula: Token | None = None
    auxiliary: Token | None = None
    adverb: Token | None = None
    emphasis: Token | None = None
    opinion_start: int | None = None
    opinion_end: int | None = None
    form: str = "subject_predicate"
    context: tuple[Token, ...] = ()


@dataclass(frozen=True)
class ReviewAST:
    clauses: tuple[Clause, ...]


@dataclass(frozen=True)
class SemanticRecord:
    category: str
    issue: str
    aspect_term: str
    opinion_term: str
    opinion_expression: str
    negated: bool
    intensifier: str | None
    intensity_multiplier: float
    aspect_inherited: bool
    clause_index: int
    start: int
    end: int
    normalization_rule: str | None = None
    adverb: str | None = None
    emphasis: str | None = None
    opinion_start: int | None = None
    opinion_end: int | None = None
    syntax_form: str = "subject_predicate"


@dataclass(frozen=True)
class ScoreEvidence:
    synset: str
    gloss: str
    positive_score: float
    negative_score: float
    objective_score: float
    lexical_score: float
    domain_score: float
    calibration_reason: str | None
    intensity_multiplier: float
    negation_multiplier: int
    unclipped_score: float
    final_score: float
    normalization_rule: str | None = None
    domain_rule_id: str | None = None
    sense_selection: str | None = None


@dataclass(frozen=True)
class AspectResult:
    review_id: str
    category: str
    issue: str
    aspect_term: str
    opinion_term: str
    opinion_expression: str
    polarity: str
    score: float
    start: int
    end: int
    evidence: ScoreEvidence

    def to_ir(self) -> dict[str, Any]:
        record = asdict(self)
        record.pop("evidence")
        return record


@dataclass(frozen=True)
class AnalysisResult:
    review_id: str
    review_text: str
    status: str
    overall: str
    records: tuple[AspectResult, ...]
    diagnostics: tuple[Diagnostic, ...]
    tokens: tuple[Token, ...] = field(repr=False)
    ast: ReviewAST = field(repr=False)
    semantics: tuple[SemanticRecord, ...] = field(repr=False)

    def to_dict(self, include_trace: bool = False) -> dict[str, Any]:
        output = {
            "review_id": self.review_id,
            "review_text": self.review_text,
            "status": self.status,
            "overall": self.overall,
            "records": [r.to_ir() for r in self.records],
            "diagnostics": [asdict(d) for d in self.diagnostics],
        }
        if include_trace:
            output["trace"] = {
                "lexical_analysis": [asdict(t) for t in self.tokens],
                "syntax_analysis": asdict(self.ast),
                "semantic_analysis": [asdict(s) for s in self.semantics],
                "sentiment_evaluation": [asdict(r.evidence) for r in self.records],
                "intermediate_representation": [r.to_ir() for r in self.records],
            }
        return output

