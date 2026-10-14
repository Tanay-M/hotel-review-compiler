"""Associate parsed opinion expressions with explicit hotel aspects."""

from .models import Diagnostic, ReviewAST, SemanticRecord, Token
from .vocabulary import load_vocabulary


def analyze_semantics(
    ast: ReviewAST, source: str
) -> tuple[tuple[SemanticRecord, ...], tuple[Diagnostic, ...]]:
    vocabulary = load_vocabulary()
    records: list[SemanticRecord] = []
    diagnostics: list[Diagnostic] = []
    previous_subject: Token | None = None
    for index, clause in enumerate(ast.clauses):
        if clause.connector not in {"and", "but", "however"}:
            previous_subject = None
        inherited = clause.subject is None
        subject = clause.subject or previous_subject
        if subject is None:
            diagnostics.append(Diagnostic(
                "MISSING_ASPECT",
                "This opinion has no explicit hotel aspect in the same sentence. "
                "Pronoun and implicit-aspect inference are outside the current grammar.",
                clause.start, clause.end, "semantic",
            ))
            previous_subject = None
            continue
        aspect = vocabulary["aspects"][subject.value]
        opinion = vocabulary["opinions"][clause.opinion.value]
        alias = " ".join(clause.opinion.text.lower().split())
        alias_spec = vocabulary.get("opinion_aliases", {}).get(alias, {}) if clause.opinion.normalization_rule else {}
        # New equipment/state and domain-specific opinions have explicit
        # compatibility contracts; proximity alone never chooses a sense.
        problem = None
        if ("allowed_aspects" in opinion and subject.value not in opinion["allowed_aspects"] or
                "allowed_categories" in opinion and aspect["category"] not in opinion["allowed_categories"] or
                "allowed_categories" in alias_spec and aspect["category"] not in alias_spec["allowed_categories"] or
                "allowed_aspects" in alias_spec and subject.value not in alias_spec["allowed_aspects"]):
            problem = ("INCOMPATIBLE_OPINION", f"{clause.opinion.text!r} is not configured for aspect {subject.text!r}.")
        elif clause.adverb and clause.adverb.value not in opinion.get("allowed_adverbs", []):
            problem = ("UNSUPPORTED_ADVERB", f"{clause.adverb.text!r} is not configured for opinion {clause.opinion.text!r}.")
        elif clause.emphasis and clause.negation is None:
            problem = ("INVALID_EMPHASIS", "'at all' requires an explicit negation in this grammar.")
        if problem:
            diagnostics.append(Diagnostic(problem[0], problem[1], clause.start, clause.end, "semantic"))
            previous_subject = None
            continue
        # Explicit targets such as WiFi have a specific issue; otherwise use
        # the opinion label (e.g. Room -> Cleanliness) without a duplicate aspect.
        issue = aspect.get("issue", opinion.get("category_senses", {}).get(aspect["category"], {}).get("issue", opinion["issue"]))
        if aspect["category"] == "Room" and aspect.get("issue") != "View":
            # Bedding can be dirty, furniture can be damaged: a broad Room
            # sub-aspect must not hide the opinion's actual issue.
            issue = opinion.get("category_senses", {}).get("Room", {}).get("issue", opinion["issue"])
        modifier = clause.intensifier.value if clause.intensifier else None
        expression_start = clause.opinion_start if clause.opinion_start is not None else (clause.negation or clause.intensifier or clause.opinion).start
        expression_end = clause.opinion_end if clause.opinion_end is not None else clause.opinion.end
        expression = source[expression_start : expression_end]
        if clause.negation and clause.negation.text.lower().replace("\u2019", "'") == "n't":
            # The lexer preserves the contraction's source span, while the
            # semantic expression uses a readable expanded negation.
            tail_start = (clause.intensifier or clause.opinion).start
            expression = "not " + source[tail_start : expression_end]
        records.append(SemanticRecord(
            category=aspect["category"],
            issue=issue,
            aspect_term=subject.value,
            opinion_term=clause.opinion.value,
            opinion_expression=expression,
            negated=clause.negation is not None,
            intensifier=modifier,
            intensity_multiplier=vocabulary["intensifiers"].get(modifier, 1.0),
            aspect_inherited=inherited,
            clause_index=index,
            start=clause.start,
            end=clause.end,
            normalization_rule=clause.opinion.normalization_rule,
            adverb=clause.adverb.value if clause.adverb else None,
            emphasis=clause.emphasis.value if clause.emphasis else None,
            opinion_start=expression_start,
            opinion_end=expression_end,
            syntax_form=clause.form,
        ))
        previous_subject = subject
    return tuple(records), tuple(diagnostics)

