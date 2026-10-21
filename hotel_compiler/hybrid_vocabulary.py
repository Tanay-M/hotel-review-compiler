"""Reviewed lexical coverage, independent of the SentiWordNet baseline.

Original reviews and library resources are never mutated. Alias replacement is
limited to an explicit, category-guarded scoring copy and logged as evidence.
"""
from functools import lru_cache
from importlib.resources import files
import json
import re


@lru_cache(maxsize=1)
def vocabulary():
    data = json.loads(files('hotel_compiler').joinpath('resources/hybrid_vocabulary.json').read_text(encoding='utf-8'))
    categories = {'Room', 'Staff', 'Service', 'Food', 'Cleanliness', 'Facilities'}
    for word, spec in data['lexical_aliases'].items():
        if not word or not spec['canonical'] or word == spec['canonical']:
            raise ValueError('Invalid hybrid vocabulary alias.')
        if not spec['categories'] or not set(spec['categories']) <= categories:
            raise ValueError(f'Invalid alias category: {word}')
    return data


def has_alias(word):
    return word.lower() in vocabulary()['lexical_aliases']


@lru_cache(maxsize=1)
def _alias_pattern():
    aliases = vocabulary()['lexical_aliases']
    return re.compile(r'(?<!\w)(?:' + '|'.join(re.escape(w) for w in sorted(aliases, key=len, reverse=True)) + r')(?!\w)', re.I)


def normalize_opinions(text, category, native_has_lexical):
    matches = []
    aliases = vocabulary()['lexical_aliases']
    def replace(match):
        word = match.group().lower(); spec = aliases[word]
        # A whole-text result has no single category; only universally allowed
        # lexical forms can be normalized there.
        allowed = category in spec['categories'] if category else len(spec['categories']) == 6
        if not allowed or native_has_lexical(word): return match.group()
        canonical = spec['canonical']
        if match.group().isupper(): canonical = canonical.upper()
        elif match.group()[0].isupper(): canonical = canonical[0].upper() + canonical[1:]
        matches.append({'original': match.group(), 'canonical': canonical,
                        'start': match.start(), 'end': match.end(), 'reason': spec['reason']})
        return canonical
    working = _alias_pattern().sub(replace, text)
    if matches:
        # Keep lexical normalization from losing contraction scope: VADER
        # recognizes ASCII n't, whereas typographic apostrophes are not reliably
        # recognized. This scoring-copy change preserves original span lengths.
        working = working.translate(str.maketrans({'’': "'", '‘': "'"}))
    return working, matches
