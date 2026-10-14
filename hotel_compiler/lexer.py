"""A regex lexical analyzer with longest-match hotel aspect recognition."""

import re

from .models import Token
from .vocabulary import load_vocabulary


_LEXEME = re.compile(r"[aA]/[cC]\b|\d+(?:\.\d+)?|\w+(?:['\u2019]\w+)*(?:-\w+)*|[^\w\s]", re.UNICODE)
_NORMALIZE = str.maketrans({"\u2019": "'", "\u2010": "-", "\u2011": "-", "\u2013": "-"})
_CONTRACTIONS = {
    "isn't": ("COPULA", "is"), "aren't": ("COPULA", "are"),
    "wasn't": ("COPULA", "was"), "weren't": ("COPULA", "were"),
    "don't": ("AUXILIARY", "do"), "doesn't": ("AUXILIARY", "does"), "didn't": ("AUXILIARY", "did"),
}


def tokenize(text: str) -> tuple[Token, ...]:
    """Return source-spanned tokens. Unknown words are retained as WORD tokens."""
    vocabulary = load_vocabulary()
    # Lowercase individual values, not the whole source: Unicode lowercasing
    # can change a string's length and would invalidate source positions.
    normalized = text.translate(_NORMALIZE)
    lexemes = list(_LEXEME.finditer(normalized))
    phrases = {term: ("ASPECT", term, None, None) for term in vocabulary["aspects"]}
    phrases.update({term: ("OPINION", term, None, None) for term in vocabulary["opinions"]})
    phrases.update({term: (spec["kind"], spec["canonical"], f"opinion_alias:{term}->{spec['canonical']}", spec.get("verb_form"))
                    for term, spec in vocabulary.get("opinion_aliases", {}).items()})
    phrases.update({term: ("ADVERB", term, None, None) for term in vocabulary.get("predicate_adverbs", [])})
    phrases.update({term: ("EMPHASIS", term, None, None) for term in vocabulary.get("emphasis_phrases", [])})
    for field, kind in (("introductions", "INTRODUCTION"), ("context_phrases", "CONTEXT"),
                        ("possessives", "POSSESSION"), ("post_modifiers", "POST_MODIFIER"),
                        ("context_relations", "RELATION"), ("relation_targets", "RELATION_TARGET")):
        phrases.update({term: (kind, term, None, None) for term in vocabulary.get(field, [])})
    phrases.update({term: ("INTENSIFIER", term, None, None) for term in vocabulary["intensifiers"]})
    longest_phrase = max(len(term.split()) for term in phrases)
    output: list[Token] = []
    i = 0
    while i < len(lexemes):
        current = lexemes[i]
        value, start, end = current.group().lower(), current.start(), current.end()
        if value in _CONTRACTIONS:
            kind, root = _CONTRACTIONS[value]
            split = start + len(root)
            output.extend([
                Token(kind, root, text[start:split], start, split),
                Token("NEGATION", "not", text[split:end], split, end),
            ])
            i += 1
            continue
        for width in range(min(longest_phrase, len(lexemes) - i), 0, -1):
            matches = lexemes[i : i + width]
            # Known phrases may span whitespace, never punctuation.
            gaps = [normalized[a.end() : b.start()] for a, b in zip(matches, matches[1:])]
            phrase = " ".join(m.group().lower() for m in matches)
            if phrase in phrases and all(gap.isspace() for gap in gaps):
                start, end = matches[0].start(), matches[-1].end()
                kind, canonical, rule, form = phrases[phrase]
                if phrase in vocabulary["aspects"] and phrase in vocabulary["opinions"]:
                    # Explicit positional disambiguation for polysemous words
                    # such as the noun "safe" versus the adjective "safe".
                    after = lexemes[i + width].group().lower() if i + width < len(lexemes) else None
                    after_kind = phrases.get(after, (None,))[0]
                    before = output[-1].kind if output else None
                    if after in vocabulary["copulas"] or after in vocabulary.get("auxiliaries", []) or (
                        before == "OPINION" and after_kind != "ASPECT"
                    ):
                        kind = "ASPECT"
                output.append(Token(kind, canonical, text[start:end], start, end, rule, form))
                i += width
                break
        else:
            value, start, end = current.group().lower(), current.start(), current.end()
            if value in vocabulary["negations"]:
                kind = "NEGATION"
            elif value in vocabulary["intensifiers"]:
                kind = "INTENSIFIER"
            elif value in vocabulary["connectors"]:
                kind = "CONNECTOR"
            elif value in vocabulary["determiners"]:
                kind = "DETERMINER"
            elif value in vocabulary["copulas"]:
                kind = "COPULA"
            elif value in vocabulary.get("auxiliaries", []):
                kind = "AUXILIARY"
            elif value == ",":
                kind = "COMMA"
            elif value in {".", "!", "?", ";"}:
                kind = "END"
            elif value[0].isdigit() and re.fullmatch(r"\d+(?:\.\d+)?", value):
                kind = "NUMBER"
            elif re.fullmatch(r"\w+(?:['-]\w+)*", value):
                kind = "WORD"
            else:
                kind = "PUNCTUATION"
            output.append(Token(kind, value, text[start:end], start, end))
            i += 1
    return tuple(output)

