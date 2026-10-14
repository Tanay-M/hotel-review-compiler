"""Predictive recursive-descent parsing with clause-boundary recovery."""

from .models import Clause, Diagnostic, ReviewAST, Token
from .vocabulary import load_vocabulary


_BOUNDARIES = {"CONNECTOR", "COMMA", "END"}
_PREDICATE_START = {"NEGATION", "INTENSIFIER", "OPINION", "FUNCTION_VERB", "COPULA", "AUXILIARY"}


class _ParseError(Exception):
    pass


class ReviewParser:
    def __init__(self, tokens: tuple[Token, ...]):
        self.tokens = tokens
        self.position = 0
        self.vocabulary = load_vocabulary()

    def _peek(self) -> Token | None:
        return self.tokens[self.position] if self.position < len(self.tokens) else None

    def _take(self, kind: str) -> Token:
        token = self._peek()
        if token is None:
            raise _ParseError(f"Expected {kind}, reached the end of the review.")
        if token.kind != kind:
            raise _ParseError(f"Expected {kind}, found {token.kind} ({token.text!r}).")
        self.position += 1
        return token

    def _optional(self, kind: str) -> Token | None:
        token = self._peek()
        return self._take(kind) if token and token.kind == kind else None

    def _predicate(self, copula=None, auxiliary=None):
        negation = self._optional("NEGATION")
        intensifier = self._optional("INTENSIFIER")
        following = self._peek()
        if auxiliary:
            opinion = self._take("FUNCTION_VERB")
            if opinion.verb_form != "base":
                raise _ParseError("An auxiliary requires a base verb such as 'work' or 'function'.")
        elif copula:
            opinion = self._take("OPINION")
        elif following and following.kind == "FUNCTION_VERB":
            opinion = self._take("FUNCTION_VERB")
        else:
            opinion = self._take("OPINION")
        if opinion.kind == "FUNCTION_VERB" and intensifier and intensifier.value != "really":
            raise _ParseError("Only 'really' may modify a functional verb in this grammar; degree adjectives require a state opinion.")
        adverb = self._optional("ADVERB")
        emphasis = self._optional("EMPHASIS")
        post = self._optional("POST_MODIFIER")
        return negation, intensifier, opinion, adverb, emphasis, post, copula, auxiliary

    def _contexts(self):
        """Only explicitly whitelisted adjuncts are consumed; nothing is ignored."""
        context = []
        while self._peek() and self._peek().kind == "CONTEXT":
            context.append(self._take("CONTEXT"))
        if self._peek() and self._peek().kind == "RELATION":
            context.append(self._take("RELATION"))
            if self._peek() and self._peek().kind == "DETERMINER":
                context.append(self._take("DETERMINER"))
            context.append(self._take("RELATION_TARGET"))
        return tuple(context)

    def _clause(self, connector: str | None) -> tuple[Clause, ...]:
        first = self._peek()
        assert first is not None
        context = []
        introduction = self._optional("INTRODUCTION")
        if introduction:
            context.append(introduction)
            self._optional("COMMA")
        subject = None
        determiner = self._optional("DETERMINER")
        following = self._peek()
        if following and following.kind == "ASPECT":
            subject = self._take("ASPECT")
        elif following is None or following.kind not in _PREDICATE_START:
            raise _ParseError("Expected a hotel aspect or an opinion expression.")
        subjects = [subject] if subject else []
        # Coordinated noun subjects share the predicate, rather than inheriting
        # only its last noun. Look ahead before consuming a clause connector.
        while subject and self._peek() and self._peek().kind in {"CONNECTOR", "COMMA"}:
            saved = self.position
            separator = self._peek()
            if separator.kind == "CONNECTOR" and separator.value != "and":
                break
            self.position += 1
            if separator.kind == "COMMA" and self._peek() and self._peek().kind == "CONNECTOR":
                if self._peek().value != "and":
                    self.position = saved
                    break
                self.position += 1
            self._optional("DETERMINER")
            if self._peek() and self._peek().kind == "ASPECT":
                subjects.append(self._take("ASPECT"))
            else:
                self.position = saved
                break
        copula = self._optional("COPULA")
        auxiliary = self._optional("AUXILIARY") if copula is None else None
        possession = self._optional("POSSESSION") if copula is None and auxiliary is None and subject else None
        if (possession is None and copula is None and auxiliary is None and subject
            and self._peek() and self._peek().kind == "RELATION" and self._peek().value == "with"):
            possession = self._take("RELATION")
        if possession:
            context.append(possession)
            self._optional("DETERMINER")
        if determiner and subject is None and (copula or auxiliary):
            raise _ParseError("An article before a linking verb requires an explicit aspect.")
        predicates = [self._predicate(copula, auxiliary)]
        # A coordinated subject group shares every coordinated predicate.
        if len(subjects) > 1:
            while self._peek() and self._peek().kind == "CONNECTOR" and self._peek().value in {"and", "but"}:
                saved = self.position
                self.position += 1
                if not self._peek() or self._peek().kind not in _PREDICATE_START:
                    self.position = saved
                    break
                next_copula = self._optional("COPULA")
                next_auxiliary = self._optional("AUXILIARY") if next_copula is None else None
                predicates.append(self._predicate(next_copula, next_auxiliary))
        negation, intensifier, opinion, adverb, emphasis, post, _, _ = predicates[0]
        expression_start = (negation or intensifier or opinion).start
        expression_end = (post or emphasis or adverb or opinion).end
        form = "subject_predicate" if subject else "inherited_predicate"
        if (subject is None and introduction and introduction.value in {"i was", "we were", "i am", "we are"}
            and opinion.value in self.vocabulary.get("experience_opinions", [])
            and self._peek() and self._peek().kind == "RELATION" and self._peek().value in {"with", "by"}):
            context.append(self._take("RELATION"))
            self._optional("DETERMINER")
            subject = self._take("ASPECT")
            subjects = [subject]
            form = "experiencer_opinion_target"
        # Multiple prenominal adjectives must finish in an explicit aspect.
        # If no noun follows, roll back and let normal clause recovery handle it.
        if subject is None or possession:
            saved = self.position
            try:
                while self._peek() and (self._peek().kind in {"OPINION", "COMMA"} or
                      self._peek().kind == "CONNECTOR" and self._peek().value == "and"):
                    self._optional("COMMA")
                    self._optional("CONNECTOR")
                    predicates.append(self._predicate())
                if not self._peek() or self._peek().kind != "ASPECT":
                    self.position = saved
                    predicates = predicates[:1]
            except _ParseError:
                self.position = saved
                predicates = predicates[:1]
        if (subject is None or possession) and self._peek() and self._peek().kind == "ASPECT":
            if copula or auxiliary or opinion.kind == "FUNCTION_VERB":
                raise _ParseError("Only an adjective/state opinion may precede an aspect.")
            subject = self._take("ASPECT")
            subjects = [subject]
            form = "possessive_opinion_before_aspect" if possession else "opinion_before_aspect"
        elif possession:
            raise _ParseError("Possession requires an explicit aspect after its opinion.")
        elif determiner and subject is None:
            raise _ParseError("An article/opinion phrase must end with an explicit aspect.")
        context.extend(self._contexts())
        following = self._peek()
        if following and following.kind not in _BOUNDARIES:
            raise _ParseError(
                f"Unexpected {following.text!r} after the opinion; expected a clause boundary."
            )
        clause_end = subject.end if form in {"opinion_before_aspect", "possessive_opinion_before_aspect", "experiencer_opinion_target"} else max((p[5] or p[4] or p[3] or p[2]).end for p in predicates)
        clause_end = max(clause_end, context[-1].end if context else clause_end)
        if len(subjects) > 1:
            form = "coordinated_subjects"
        clauses = []
        for target in subjects or [None]:
            for predicate in predicates:
                negation, intensifier, opinion, adverb, emphasis, post, predicate_copula, predicate_auxiliary = predicate
                clauses.append(Clause(target, opinion, negation, intensifier, connector, first.start, clause_end,
                    copula=predicate_copula, auxiliary=predicate_auxiliary, adverb=adverb, emphasis=emphasis,
                    opinion_start=(negation or intensifier or opinion).start,
                    opinion_end=(post or emphasis or adverb or opinion).end, form=form, context=tuple(context)))
        return tuple(clauses)

    def _boundary(self) -> str | None:
        """Consume punctuation with an optional connector; sentence ends reset context."""
        connector = None
        token = self._peek()
        assert token is not None and token.kind in _BOUNDARIES
        if token.kind == "END":
            while self._peek() and self._peek().kind == "END":
                self.position += 1
            return "sentence_end"
        self._optional("COMMA")
        token = self._optional("CONNECTOR")
        if token:
            connector = token.value
            self._optional("COMMA")
        return connector or "comma"

    def parse(self) -> tuple[ReviewAST, tuple[Diagnostic, ...]]:
        clauses: list[Clause] = []
        diagnostics: list[Diagnostic] = []
        connector = None
        while self._peek():
            first = self._peek()
            if first.kind in _BOUNDARIES:
                # A boundary is legal only after a clause (valid or recovered).
                diagnostics.append(Diagnostic(
                    "EMPTY_CLAUSE", "Expected a clause before this separator.",
                    first.start, first.end, "syntax",
                ))
                self._boundary()
                connector = "recovery"
                continue
            recovered = False
            clause_start_position = self.position
            try:
                clauses.extend(self._clause(connector))
            except _ParseError as error:
                start = first.start
                end = first.end
                while self._peek() and self._peek().kind not in _BOUNDARIES:
                    end = self._peek().end
                    self.position += 1
                if self.position > clause_start_position:
                    end = self.tokens[self.position - 1].end
                diagnostics.append(Diagnostic("UNSUPPORTED_CLAUSE", str(error), start, end, "syntax"))
                recovered = True
            if self._peek():
                boundary_start = self._peek().start
                connector = self._boundary()
                if recovered:
                    connector = "recovery"
                if self._peek() is None and connector not in {"sentence_end", "recovery"}:
                    diagnostics.append(Diagnostic(
                        "MISSING_CLAUSE", "Expected another clause after this separator.",
                        boundary_start, self.tokens[-1].end, "syntax",
                    ))
        return ReviewAST(tuple(clauses)), tuple(diagnostics)


def parse(tokens: tuple[Token, ...]) -> tuple[ReviewAST, tuple[Diagnostic, ...]]:
    return ReviewParser(tokens).parse()

