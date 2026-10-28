"""A regex lexical analyzer with longest-match hotel aspect recognition."""

import re
from functools import lru_cache

from .models import Token
from .vocabulary import load_vocabulary
from .compiler_profiles import current_profile, compiler_profile


_LEXEME = re.compile(r"[aA]/[cC]\b|\d+(?:\.\d+)?|\w+(?:['\u2019]\w+)*(?:-\w+)*|[^\w\s]", re.UNICODE)
_EXPANDED_LEXEME = re.compile(r"\r\n|\r|\n|[aA]/[cC]\b|\d+(?:\.\d+)?|\w+(?:['\u2019]\w+)*(?:-\w+)*|[^\w\s]", re.UNICODE)
_NORMALIZE = str.maketrans({"\u2019": "'", "\u2010": "-", "\u2011": "-", "\u2013": "-"})
_CONTRACTIONS = {
    "isn't": ("COPULA", "is"), "aren't": ("COPULA", "are"),
    "wasn't": ("COPULA", "was"), "weren't": ("COPULA", "were"),
    "don't": ("AUXILIARY", "do"), "doesn't": ("AUXILIARY", "does"), "didn't": ("AUXILIARY", "did"),
}


@lru_cache(maxsize=2)
def _phrase_table(profile):
    with compiler_profile(profile): vocabulary = load_vocabulary()
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
    return phrases, longest_phrase, frozenset(vocabulary.get('morphology_exclusions', []))


def tokenize(text: str) -> tuple[Token, ...]:
    """Return source-spanned tokens. Unknown words remain visible."""
    vocabulary = load_vocabulary()
    expanded = current_profile() == 'expanded'
    normalized = text.translate(_NORMALIZE)
    lexemes = list((_EXPANDED_LEXEME if expanded else _LEXEME).finditer(normalized))
    phrases, longest_phrase, morphology_exclusions = _phrase_table(current_profile())
    output: list[Token] = []
    i = 0
    while i < len(lexemes):
        current = lexemes[i]
        value, start, end = current.group().lower(), current.start(), current.end()
        if expanded and value in {"it's","they're"}:
            subject, copula = ('it','is') if value=="it's" else ('they','are')
            split = start + len(subject)
            output.extend([Token('PRONOUN',subject,text[start:split],start,split),
                           Token('COPULA',copula,text[split:end],split,end)])
            i += 1
            continue
        if expanded and value == '&':
            output.append(Token('CONNECTOR','and',text[start:end],start,end,'conjunction:&->and'))
            i += 1
            continue
        if expanded and value == 'like' and output and output[-1].value in {'feel','feels','felt','feeling','look','looks','looked','seem','seems','seemed','sound','sounds','smell','smells','taste','tastes'}:
            output.append(Token('RELATION','like',text[start:end],start,end,'grammatical_like:simile'))
            i += 1
            continue
        if expanded and value in {'made','found','kept','included','provided','served','offered','given','taken','put','standing','facing','walking','running','going','getting','allowed'}:
            output.append(Token('COPULA',value,text[start:end],start,end,f'factual_link:{value}'))
            i += 1
            continue
        if expanded and value in vocabulary.get('opinion_verbs', {}):
            previous = output[-1].kind if output else None
            if previous != 'COPULA' or value not in vocabulary['opinions']:
                canonical = vocabulary['opinion_verbs'][value]
                output.append(Token('LEXICAL_VERB', canonical, text[start:end], start, end,
                                    f'native_verb:{value}->{canonical}'))
                i += 1
                continue
        if expanded and value in {'it','they','which','that','who'}:
            output.append(Token('PRONOUN', value, text[start:end], start, end))
            i += 1
            continue
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
                    elif expanded and (after_kind in {'OPINION','INTENSIFIER'} or before in {'DETERMINER','INTRODUCTION'}):
                        kind = 'ASPECT'
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
            elif value in {".", "!", "?", ";"} or expanded and value in {'\r','\n','\r\n'}:
                kind = "END"
            elif value[0].isdigit() and re.fullmatch(r"\d+(?:\.\d+)?", value):
                kind = "NUMBER"
            elif re.fullmatch(r"\w+(?:['-]\w+)*", value):
                kind = "WORD"
            else:
                kind = "PUNCTUATION"
            if expanded and kind == 'WORD' and value not in morphology_exclusions:
                candidates = []
                if value.endswith('iest'): candidates.append(value[:-4] + 'y')
                if value.endswith('ier'): candidates.append(value[:-3] + 'y')
                if value.endswith('est'): candidates.extend([value[:-3], value[:-2], value[:-4]])
                if value.endswith('er'): candidates.extend([value[:-2], value[:-1], value[:-3]])
                stem = next((c for c in candidates if c in vocabulary['opinions'] and len(c) >= 3), None)
                if stem:
                    output.append(Token('OPINION', stem, text[start:end], start, end, f'comparative_lemma:{value}->{stem}'))
                    i += 1
                    continue
            output.append(Token(kind, value, text[start:end], start, end))
            i += 1
    return tuple(output)

