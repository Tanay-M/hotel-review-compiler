"""Prepare human Webis annotations without model-generated training labels.

The source's OBJECTIVE label remains Objective, not an invented neutral opinion.
Only statements containing exactly one expert aspect are admitted. Splits are
hotel-disjoint, and normalized duplicate target/context inputs are removed.
"""
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
from urllib.request import Request, urlopen
from zipfile import ZipFile

SOURCE_URL = 'https://zenodo.org/records/3266053/files/corpus-webis-tripad-13-sentiment.zip?download=1'
SOURCE_SHA256 = 'd5e7696fceccede81b4300509450fc349a97e881947b22faa0432f26d51a6573'
LABELS = ('Negative', 'Objective', 'Positive')
FIELDS = ['example_id', 'review_id', 'hotel_id', 'source_file', 'start', 'end',
          'aspect_start', 'aspect_end', 'aspect', 'text', 'label', 'input_sha256', 'split']


def write_csv(path, rows, fields):
    with Path(path).open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def model_input(aspect, text):
    return f'{aspect}: {text}'


def duplicate_key(aspect, text):
    return ' '.join(re.findall(r'\w+', model_input(aspect, text).casefold()))


def hotel_split(hotel_id, seed=172026):
    bucket = int(sha256(f'{seed}:{hotel_id}'.encode()).hexdigest()[:8], 16) % 100
    return 'train' if bucket < 70 else 'validation' if bucket < 85 else 'test'


def extract_statements(record, source_file, *, max_chars=600):
    """Return original source substrings and an exclusion ledger, not predictions."""
    text = record['text']
    annotations = record['annotations']
    aspects = annotations.get('de.webis.annotation.Aspect', [])
    hotel = str(record.get('attributes', {}).get('de.webis.attribute.Hotel', {}).get('id', ''))
    review_id = sha256(text.encode()).hexdigest()
    rows, excluded = [], []
    for index, statement in enumerate(annotations.get('de.webis.annotation.Statement', [])):
        start, end = statement['begin'], statement['end']
        reason = None
        if not hotel:
            reason = 'missing_hotel_group'
        elif not 0 <= start < end <= len(text):
            reason = 'invalid_statement_offsets'
        elif len(text[start:end]) > max_chars:
            reason = 'long_statement'
        elif statement.get('polarity', '').capitalize() not in LABELS:
            reason = 'unknown_source_label'
        contained = [a for a in aspects if start <= a['begin'] < a['end'] <= end]
        crossing = [a for a in aspects if a['begin'] < end and a['end'] > start and a not in contained]
        if not reason and crossing:
            reason = 'crossing_aspect_span'
        if not reason and len(contained) != 1:
            reason = 'no_aspect' if not contained else 'multiple_aspects'
        if reason:
            excluded.append({'source_file': source_file, 'statement': index, 'reason': reason})
            continue
        aspect = contained[0]
        target = text[aspect['begin']:aspect['end']]
        context = text[start:end]
        if not target.strip() or not re.search(r'\w', target) or not context.strip():
            excluded.append({'source_file': source_file, 'statement': index, 'reason': 'empty_text'})
            continue
        key = duplicate_key(target, context)
        rows.append(dict(example_id=f'{Path(source_file).stem}:{index}', review_id=review_id,
                         hotel_id=hotel, source_file=source_file, start=start, end=end,
                         aspect_start=aspect['begin'], aspect_end=aspect['end'],
                         aspect=target, text=context, label=statement['polarity'].capitalize(),
                         input_sha256=sha256(key.encode()).hexdigest()))
    return rows, excluded


def deduplicate(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[row['input_sha256']].append(row)
    result, excluded = [], []
    for group in groups.values():
        if len({r['label'] for r in group}) > 1:
            discarded = group
            reason = 'conflicting_duplicate_labels'
        else:
            result.append(group[0])
            discarded = group[1:]
            reason = 'duplicate_input'
        excluded.extend({'source_file': r['source_file'], 'statement': r['example_id'],
                         'reason': reason} for r in discarded)
    return result, excluded


def acquire_webis(path):
    path = Path(path)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with urlopen(Request(SOURCE_URL, headers={'User-Agent': 'Team17Research/1.0'}), timeout=90) as response:
            payload = response.read(10_000_001)
        if len(payload) > 10_000_000:
            raise ValueError('Unexpectedly large Webis archive.')
        if sha256(payload).hexdigest() != SOURCE_SHA256:
            raise ValueError('Source archive checksum differs from the reviewed release.')
        path.write_bytes(payload)
    if sha256(path.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError('Webis checksum mismatch; refusing an unidentified source.')
    return path


def prepare_webis(archive_path, output_dir, *, seed=172026, max_chars=600):
    out = Path(output_dir)
    if out.exists():
        raise ValueError('Prepared-data directory already exists; choose a new name.')
    archive_path = acquire_webis(archive_path)
    rows, excluded, review_hashes = [], [], set()
    with ZipFile(archive_path) as archive:
        members = sorted(n for n in archive.namelist() if n.endswith('.json'))
        if len(members) != 2100:
            raise ValueError('Unexpected Webis review count.')
        for member in members:
            record = json.loads(archive.read(member))
            digest = sha256(record['text'].encode()).hexdigest()
            if digest in review_hashes:
                excluded.append({'source_file': member, 'statement': '', 'reason': 'duplicate_review'})
                continue
            review_hashes.add(digest)
            selected, rejected = extract_statements(record, member, max_chars=max_chars)
            rows.extend(selected)
            excluded.extend(rejected)
    rows, rejected = deduplicate(rows)
    excluded.extend(rejected)
    for row in rows:
        row['split'] = hotel_split(row['hotel_id'], seed)
    for key in ('hotel_id', 'review_id', 'input_sha256'):
        groups = [{r[key] for r in rows if r['split'] == s} for s in ('train', 'validation', 'test')]
        if any(groups[i] & groups[j] for i in range(3) for j in range(i)):
            raise ValueError(f'Leakage across data splits: {key}')
    out.mkdir(parents=True)
    counts = {}
    for split in ('train', 'validation', 'test'):
        selected = [r for r in rows if r['split'] == split]
        if set(r['label'] for r in selected) != set(LABELS):
            raise ValueError(f'Class absent from {split}.')
        write_csv(out/f'{split}.csv', selected, FIELDS)
        counts[split] = dict(examples=len(selected), reviews=len({r['review_id'] for r in selected}),
                             hotels=len({r['hotel_id'] for r in selected}),
                             labels=dict(Counter(r['label'] for r in selected)))
    write_csv(out/'exclusions.csv', excluded, ['source_file', 'statement', 'reason'])
    manifest = dict(source='Webis-Tripad-13-Sentiment', source_url=SOURCE_URL,
                    source_sha256=SOURCE_SHA256, source_reviews=2100, license='CC BY 4.0',
                    citation='Wachsmuth et al., Webis Tripad Sentiment Corpus 2013, doi:10.5281/zenodo.3266053',
                    prepared_utc=datetime.now(timezone.utc).isoformat(), seed=seed,
                    max_context_characters=max_chars, counts=counts,
                    label_policy='Human statement Positive/Negative/Objective; Objective is retained, not equated to a neutral opinion.',
                    scope='Exactly one expert-marked aspect wholly inside a short statement; target-conditioned polarity, not six-category extraction.',
                    source_text_policy='Exact original statement and target substrings; no generated or paraphrased reviews.',
                    split_policy='Hash by hotel, 70/15/15 buckets; exact review and normalized target/context duplicates removed before splitting.',
                    exclusions=dict(Counter(r['reason'] for r in excluded)),
                    files={p.name: sha256(p.read_bytes()).hexdigest() for p in out.glob('*.csv')})
    (out/'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return manifest
