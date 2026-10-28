"""Human category/polarity supervision for independent review reanalysis.

Trip-MA distributes token/POS/lemma serialization, not untouched raw review text.
We recover surface tokens and detokenize; original serialization is retained.
No hybrid predictions or star ratings supply training labels.
"""
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
from urllib.request import urlopen

from .neural_data import write_csv

REVISION = 'a9f47df668d3e2ec37bb13e04d1005fb1623d91d'
SOURCES = {
    'english_training.json': '80c970ddb148dd3eadd504a13838b519b369a8b4239f009fb079327e065fbbd7',
    'english_test.json': '08e1948f6bbfb61a95cca9b84a7f315e12cf068bf39d5b485e28e887768bee72',
    'README.md': '963503a7fca8e43fcf646554440e8240b8c354ff6c29c1e1a0e20bd7c4f6ccad',
}
CROSSWALK = {'ROOMS': 'Room', 'CLEANLINESS': 'Cleanliness', 'SERVICE': 'Service',
             'CHECKIN': 'Service', 'FOOD': 'Food', 'BUILDING': 'Facilities',
             'BUSINESS': 'Facilities', 'LOCATION': 'Excluded', 'VALUE': 'Excluded',
             'OTHER': 'Other', 'NOTRELATED': 'NotRelated'}
CATEGORIES = ('Room', 'Cleanliness', 'Service', 'Food', 'Facilities')
HEADS = (*CATEGORIES, 'Excluded', 'Other', 'NotRelated')
STATES = ('Absent', 'Negative', 'Neutral/Mixed', 'Positive')


def surface_text(serialized):
    from nltk.tokenize.treebank import TreebankWordDetokenizer
    tokens = []
    for unit in serialized.split():
        pieces = unit.rsplit('/', 2)
        if len(pieces) != 3 or not pieces[0]:
            raise ValueError(f'Unexpected source token serialization: {unit!r}')
        tokens.append(pieces[0])
    return TreebankWordDetokenizer().detokenize(tokens)


def normalized(text):
    import re
    return ' '.join(re.findall(r'\w+', text.casefold()))


def mapped_labels(labels):
    groups = defaultdict(set)
    for category, code in labels.items():
        if category not in CROSSWALK or code not in {'p', 'n', 'x', 'ip', 'in', 'ix'}:
            raise ValueError('Unrecognized human annotation; refusing a guessed mapping.')
        groups[CROSSWALK[category]].add({'p': 'Positive', 'n': 'Negative', 'x': 'Neutral/Mixed'}[code[-1]])
    return {category: next(iter(values)) if len(values) == 1 else 'Neutral/Mixed'
            for category, values in groups.items()}


def prepare(output_dir, source_dir='data/vendor/neural-training/trip-ma'):
    out = Path(output_dir)
    if out.exists(): raise ValueError('Prepared output exists; choose a new directory.')
    raw = Path(source_dir); raw.mkdir(parents=True, exist_ok=True)
    for name, expected in SOURCES.items():
        path = raw/name
        if not path.exists():
            payload = urlopen(f'https://raw.githubusercontent.com/diegma/trip-maml/{REVISION}/EN/{name}', timeout=60).read()
            if sha256(payload).hexdigest() != expected: raise ValueError('Source download checksum mismatch.')
            path.write_bytes(payload)
        if sha256(path.read_bytes()).hexdigest() != expected: raise ValueError('Unrecognized source release.')
    records = {name: [json.loads(line) for line in (raw/name).read_text(encoding='utf-8').splitlines() if line.strip()]
               for name in SOURCES if name.endswith('.json')}
    test_hotels = {str(r['hotelId']) for r in records['english_test.json']}
    excluded = []
    rows = []
    # Hotel identities only, not test sentiment labels, define the leakage guard.
    for filename, reviews in records.items():
        for r in reviews:
            hotel = str(r['hotelId']); rid = str(r['reviewId'])
            if filename == 'english_training.json' and hotel in test_hotels:
                excluded.append({'id': rid, 'reason': 'training_hotel_in_official_test'})
                continue
            split = 'test' if filename == 'english_test.json' else (
                'validation' if int(sha256(('172026:'+hotel).encode()).hexdigest()[:8], 16) % 100 < 20 else 'train')
            if len(r['segments']) != len(r['segmentLabels']): raise ValueError('Source annotation alignment error.')
            for index, (segment, labels) in enumerate(zip(r['segments'], r['segmentLabels'])):
                text = surface_text(segment)
                rows.append({'id': f'{rid}:{index}', 'review_id': rid, 'hotel_id': hotel,
                    'source_file': filename, 'split': split, 'text': text,
                    'serialized_source': segment, 'source_labels': json.dumps(labels, sort_keys=True),
                    'labels': json.dumps(mapped_labels(labels), sort_keys=True),
                    'text_hash': sha256(normalized(text).encode()).hexdigest()})
    # All copies of cross-split duplicated text are excluded, never relocated.
    by_text = defaultdict(list)
    for row in rows: by_text[row['text_hash']].append(row)
    retained = []
    for group in by_text.values():
        if len({r['split'] for r in group}) > 1 or len({r['labels'] for r in group}) > 1:
            excluded.extend({'id': r['id'], 'reason': 'cross_split_or_conflicting_text_duplicate'} for r in group)
        else:
            retained.append(group[0])
            excluded.extend({'id': r['id'], 'reason': 'duplicate_text'} for r in group[1:])
    for key in ('hotel_id', 'review_id', 'text_hash'):
        sets = [{r[key] for r in retained if r['split'] == s} for s in ('train', 'validation', 'test')]
        assert all(not sets[i] & sets[j] for i in range(3) for j in range(i)), key
    out.mkdir(parents=True)
    counts = {}
    for split in ('train', 'validation', 'test'):
        chosen = sorted([r for r in retained if r['split'] == split], key=lambda r: r['id'])
        write_csv(out/f'{split}.csv', chosen, list(chosen[0]))
        counts[split] = {'segments': len(chosen), 'reviews': len({r['review_id'] for r in chosen}),
            'hotels': len({r['hotel_id'] for r in chosen}),
            'category_support': dict(Counter(c for r in chosen for c in json.loads(r['labels'])))}
    write_csv(out/'exclusions.csv', excluded, ['id', 'reason'])
    manifest = {'source': 'Trip-MA English / Trip-MAML author release', 'revision': REVISION,
        'sources': SOURCES, 'counts': counts, 'crosswalk': CROSSWALK,
        'label_policy': 'Human labels; p/ip Positive, n/in Negative, x/ix Neutral/Mixed. Absence uses exhaustive source annotations.',
        'staff_policy': 'No separately supervised Staff class. Staff-related feedback remains within source Service.',
        'split_policy': 'Official test retained; remove overlapping training hotels; derive validation by hotel hash; remove cross-split text duplicates.',
        'text_policy': 'Surface tokens recovered from source serialization and detokenized; no generated reviews or inferred human labels.',
        'licence': 'No explicit dataset licence found in author repository; local research use, no public redistribution included.',
        'files': {p.name: sha256(p.read_bytes()).hexdigest() for p in out.glob('*.csv')}}
    (out/'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return manifest
