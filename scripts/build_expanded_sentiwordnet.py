"""Build a separate broad compiler lexicon from checksum-pinned SentiWordNet.

All adjective lemmas use their first WordNet-ranked sense (not highest sentiment).
Existing explicit senses/domain conventions remain. No VADER/TextBlob scores,
ratings, benchmark labels or prediction outcomes select words or senses.
"""
from collections import Counter
from hashlib import sha256
from pathlib import Path
import csv
import json
import re
import zipfile

from prepare_sentiwordnet import SOURCE_SHA256

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / 'hotel_compiler/resources'


def build():
    source = ROOT / 'data/vendor/sentiwordnet.zip'
    assert sha256(source.read_bytes()).hexdigest() == SOURCE_SHA256
    base = json.loads((RES / 'domain.json').read_text(encoding='utf-8'))
    vocab = json.loads(json.dumps(base))
    hybrid = json.loads((RES / 'hybrid_domain.json').read_text(encoding='utf-8'))
    overlay = json.loads((RES / 'hybrid_vocabulary.json').read_text(encoding='utf-8'))
    conflicts = []
    for category, terms in hybrid['aspects'].items():
        for term in terms + overlay['aspect_additions'].get(category, []):
            if term in vocab['aspects'] and vocab['aspects'][term]['category'] != category:
                conflicts.append({'aspect': term, 'original_category': vocab['aspects'][term]['category'], 'hybrid_category': category})
            vocab['aspects'].setdefault(term, {'category': category})
    # Grammar words cannot become adjectives simply because a WordNet sense exists.
    reserved = set('i we you he she it they me us them who which that this these those there here only also still just always never no not nor neither without nothing anything something two three four five six seven eight nine ten a an the my our your his her its their and but or yet although because while if than as of to for with from near by at on in into was were is are be been being am has have had do does did can could will would should must really very quite more most less least much so too then when where how'.split())
    for key in ('copulas','auxiliaries','negations','determiners','connectors','intensifiers','predicate_adverbs','post_modifiers'):
        reserved.update(base.get(key, []))
    reserved.update('one both all some any each every another other many few several enough'.split())
    reserved.update('about after before between among upon through throughout until over under into onto than of as since despite towards along beyond beside within during across around such out up down off back away past right left like'.split())
    lookup = {}; rows = {}; header = []; non_adjectives=set()
    with zipfile.ZipFile(source) as archive:
        corpus = archive.read('sentiwordnet/SentiWordNet_3.0.0.txt').decode('utf-8')
    for line in corpus.splitlines():
        if not line: continue
        if line.startswith('#'): header.append(line); continue
        fields = line.split('\t', 5)
        pos, offset, positive, negative, terms, gloss = fields
        identifier = f'{pos}:{offset}'; rows[identifier] = line
        if pos in {'n','v','r'}:
            non_adjectives.update(entry.rsplit('#',1)[0] for entry in terms.split())
        if pos in {'a', 'v'}:
            for entry in terms.split():
                word, rank = entry.rsplit('#', 1)
                lookup.setdefault((pos, word), []).append((int(rank), identifier))
    added = []
    for (pos, word), senses in sorted(lookup.items()):
        if pos != 'a' or not re.fullmatch(r'[a-z][a-z_-]*', word): continue
        if word in reserved or word in vocab['opinions'] or word in vocab.get('opinion_aliases', {}): continue
        sense = min(senses)[1]
        vocab['opinions'][word] = {'synset': sense, 'issue': 'Quality', 'sense_selection': 'First WordNet-ranked adjective sense; source P/N unchanged; no polarity-based sense selection.'}
        if '_' in word:
            phrase = word.replace('_', ' ')
            if phrase not in vocab['aspects'] and phrase not in vocab['opinions']:
                vocab.setdefault('opinion_aliases', {}).setdefault(phrase, {'canonical': word, 'kind': 'OPINION'})
        added.append(word)
    # Native verb senses support explicit experience predicates, with direction
    # decided by grammar, not by copying a whole-sentence library prediction.
    verbs = {'love': ['love','loved','loves'], 'like': ['like','liked','likes'],
             'enjoy': ['enjoy','enjoyed','enjoys'], 'hate': ['hate','hated','hates'],
             'dislike': ['dislike','disliked','dislikes'], 'recommend': ['recommend','recommended','recommends'],
             'appreciate': ['appreciate','appreciated','appreciates'], 'prefer': ['prefer','preferred','prefers'],
             'disappoint': ['disappoint','disappointed','disappoints'], 'impress': ['impress','impressed','impresses'],
             'help': ['help','helped','helps'], 'assist': ['assist','assisted','assists'],
             'ignore': ['ignore','ignored','ignores']}
    vocab['opinion_verbs'] = {}
    for lemma, forms in verbs.items():
        if ('v', lemma) not in lookup: continue
        key = f'verb_{lemma}'; sense = min(lookup['v', lemma])[1]
        vocab['opinions'][key] = {'synset': sense, 'source_lemma': lemma, 'issue': 'Quality',
                                  'sense_selection': 'First WordNet-ranked verb sense for an explicit grammatical predicate; P/N unchanged.'}
        for form in forms: vocab['opinion_verbs'][form] = key
    for form, spec in overlay['lexical_aliases'].items():
        if form in reserved: continue
        canonical = spec['canonical'].replace(' ', '_')
        stems = ([form[:-4]+'y'] if form.endswith('iest') else [form[:-3]+'y'] if form.endswith('ier') else [])
        if form.endswith('est'): stems += [form[:-3],form[:-2],form[:-4]]
        if form.endswith('er'): stems += [form[:-2],form[:-1],form[:-3]]
        if any(len(s)>=3 and s in vocab['opinions'] for s in stems): continue
        if form not in vocab['opinions'] and form not in vocab['aspects'] and canonical in vocab['opinions']:
            vocab.setdefault('opinion_aliases', {}).setdefault(form, {'canonical': canonical, 'kind': 'OPINION', 'allowed_categories': spec['categories']})
    vocab['intensifiers'].update({'moderately': .9, 'pretty': 1.1, 'truly': 1.25, 'highly': 1.25,
                                  'surprisingly': 1.1, 'terribly': 1.5, 'totally': 1.5, 'super': 1.25})
    vocab['copulas'] = list(dict.fromkeys(vocab['copulas'] + ['looks','looked','feels','felt','tastes','tasted','smelling','seeming','looking','feeling','stayed']))
    vocab['grammar_profile'] = 'expanded'
    vocab['resource_profile'] = 'expanded'
    vocab['morphology_exclusions'] = sorted(word for word in non_adjectives | reserved
                                          if re.search(r'(?:er|est)$',word) and word not in vocab['opinions'])
    vocab['sense_policy'] = 'Keep original configured senses; new native entries use lowest WordNet lemma rank, never sentiment magnitude or benchmark labels.'
    # Widen existing equipment contracts to corresponding named new equipment.
    equipment_words = re.compile(r'\b(?:ac|a/c|air|conditioning|conditioner|fan|heating|heater|radiator|wifi|wi-fi|internet|router|tv|television|fridge|refrigerator|shower|tap|faucet|toilet|flush|plumbing|drain|sink|water|lift|elevator|dryer|microwave|oven|kettle|dishwasher|machine|socket|outlet|light|lamp|lock|keycard)\b')
    equipment = {t for t, spec in vocab['aspects'].items() if spec['category'] == 'Facilities' and equipment_words.search(t)}
    for term in ('working','functioning','operational','functional','broken','malfunctioning','leaky'):
        if term in vocab['opinions'] and 'allowed_aspects' in vocab['opinions'][term]:
            vocab['opinions'][term]['allowed_aspects'] = sorted(set(vocab['opinions'][term]['allowed_aspects']) | equipment)
    # Original aliases for leaking/cooling retain their tighter scope contracts.
    required = {spec['synset'] for spec in vocab['opinions'].values()}
    required.update(s['synset'] for spec in vocab['opinions'].values() for s in spec.get('category_senses', {}).values())
    subset = ('\n'.join(header + ['# Expanded project subset: unchanged source rows.'] + [rows[k] for k in sorted(required)]) + '\n').encode()
    (RES / 'sentiwordnet_expanded.tsv').write_bytes(subset)
    (RES / 'domain_expanded.json').write_text(json.dumps(vocab, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    manifest = {'resource':'SentiWordNet 3.0.0', 'profile':'expanded', 'license':'CC BY-SA 3.0',
                'source_archive_sha256':SOURCE_SHA256, 'subset_sha256':sha256(subset).hexdigest(),
                'opinion_terms':len(vocab['opinions']), 'aspect_phrases':len(vocab['aspects']),
                'opinion_aliases':len(vocab['opinion_aliases']), 'selected_synsets':len(required),
                'new_adjective_lemmas':len(added), 'native_verb_lemmas':len(verbs),
                'aspect_category_conflicts_retaining_original':conflicts, 'sense_selection':vocab['sense_policy'],
                'original_resource_hashes':{n:sha256((RES / n).read_bytes()).hexdigest() for n in ['domain.json','sentiwordnet.tsv','provenance.json']}}
    (RES / 'provenance_expanded.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in manifest.items() if k not in {'aspect_category_conflicts_retaining_original','original_resource_hashes'}}, indent=2))


if __name__ == '__main__': build()
