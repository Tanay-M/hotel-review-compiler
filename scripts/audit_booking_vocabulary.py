"""Reproducible, unlabeled vocabulary audit of a Crawlfeeds Booking CSV.

Field labels, ratings, titles and reviewer identity never enter analysis. This
is a development coverage audit, not an accuracy evaluation or lexicon learner.
"""
import argparse
from collections import Counter, defaultdict
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
import csv
import json
import re
import sys
from time import perf_counter
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def write_csv(path, fields, rows):
    with path.open('x', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: ("'" + str(value) if isinstance(value, str) and
                (value.startswith(('\t', '\r', '\n')) or value.lstrip().startswith(('=', '+', '-', '@'))) else value)
                for key, value in row.items()})


def read_source(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        required = {'positive_review_text', 'negative_review_text'}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f'Missing expected fields: {sorted(required)}')
        records = []
        for ordinal, row in enumerate(reader, 1):
            # Only literal missing-value markers are removed. Original nonempty
            # fields are joined verbatim, without spelling or sentiment edits.
            parts = [row.get(k) or '' for k in ('positive_review_text', 'negative_review_text')]
            retained = [p for p in parts if p.strip() and p.strip() != r'\N']
            text = '\n'.join(retained)
            records.append({'sr.no': ordinal, 'review': text, 'source_id': row.get('uniq_id', ''),
                'original_parts': parts, 'language': row.get('language', '')})
    return records


def prepare(path, root, records):
    digest = sha256(path.read_bytes()).hexdigest()
    target = root / 'inputs'
    if target.exists():
        manifest = json.loads((target / 'source_manifest.json').read_text(encoding='utf-8'))
        if manifest['source_sha256'] != digest:
            raise ValueError('Output folder belongs to a different input file.')
        archived = target / 'original_crawlfeeds.csv'
        if not archived.exists():
            with archived.open('xb') as f: f.write(path.read_bytes())
        elif sha256(archived.read_bytes()).hexdigest() != digest:
            raise ValueError('Archived source no longer matches the original CSV.')
        with (target / 'booking_italy_all.csv').open(encoding='utf-8-sig', newline='') as f:
            prepared = list(csv.DictReader(f))
        if prepared != [{'sr.no': str(r['sr.no']), 'review': r['review']} for r in records]:
            raise ValueError('Prepared reviews no longer match the original source fields.')
        return
    target.mkdir(parents=True)
    with (target / 'original_crawlfeeds.csv').open('xb') as f: f.write(path.read_bytes())
    fields = ['sr.no', 'review']
    # Input CSV text is exact, not spreadsheet-formula escaped; these files are
    # analysis inputs. Escaping would change the model input and its hash.
    def input_csv(destination, rows):
        with destination.open('x', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows({k: r[k] for k in fields} for r in rows)
    input_csv(target / 'booking_italy_all.csv', records)
    for start in range(0, len(records), 1000):
        input_csv(target / f'booking_italy_part_{start // 1000 + 1:02d}.csv', records[start:start + 1000])
    write_csv(target / 'source_rows.csv', ['sr.no', 'source_id', 'review_sha256', 'positive_field_sha256', 'negative_field_sha256'],
        ({'sr.no': r['sr.no'], 'source_id': r['source_id'],
          'review_sha256': sha256(r['review'].encode()).hexdigest(),
          'positive_field_sha256': sha256(r['original_parts'][0].encode()).hexdigest(),
          'negative_field_sha256': sha256(r['original_parts'][1].encode()).hexdigest()} for r in records))
    manifest = {'source_path': str(path.resolve()), 'source_sha256': digest, 'source_rows': len(records),
        'nonblank_body_rows': sum(bool(r['review'].strip()) for r in records),
        'empty_body_rows_retained': sum(not r['review'].strip() for r in records),
        'language_counts': dict(Counter(r['language'] for r in records)),
        'duplicate_nonblank_text_rows': sum(n - 1 for text, n in Counter(r['review'] for r in records).items() if text),
        'model_input': 'Original positive_review_text then negative_review_text, joined by newline. Only blank fields and literal \\N markers removed.',
        'excluded_from_model_input': 'title, field headings, ratings, reviewer names/countries, hotel names/addresses, URLs and all other metadata',
        'input_text_rewritten': False, 'dataset_role': 'inspected vocabulary development corpus; not unseen test data',
        'ui_parts': 'All source rows retained in ordered parts of at most 1000. IDs match original source ordinals.'}
    (target / 'source_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')


def audit(source, root, stage):
    from hotel_compiler.hybrid import HybridEngine, analyze_hybrid_review
    from hotel_compiler.hybrid_nlp import domain
    from hotel_compiler.batch import analysis_fingerprint
    records = read_source(source)
    root.mkdir(parents=True, exist_ok=True)
    prepare(source, root, records)
    out = root / stage
    out.mkdir(exist_ok=False)
    engine = HybridEngine()
    with ZipFile(out / 'source_snapshot.zip', 'x', compression=ZIP_DEFLATED) as z:
        for p in sorted((ROOT / 'hotel_compiler').glob('*.py')):
            z.write(p, p.relative_to(ROOT))
        for p in sorted((ROOT / 'hotel_compiler/resources').glob('*')):
            if p.is_file(): z.write(p, p.relative_to(ROOT))
        z.write(Path(__file__), 'scripts/audit_booking_vocabulary.py')
    statuses = Counter(); diagnostics = Counter(); adjectives = Counter(); unknown = Counter(); nouns = Counter()
    word_rows = defaultdict(set); examples = {}; review_rows = []; context_rows = []; gaps = []
    phrases = Counter(); n_contexts = n_scored = 0; started = perf_counter()
    for ordinal, row in enumerate(records, 1):
        text = row['review']; result = analyze_hybrid_review(text, f'booking-{ordinal:06d}', engine=engine)
        status = result.aspect_analysis_status if text.strip() else 'empty_body'
        statuses[status] += 1; diagnostics.update(d.code for d in result.diagnostics)
        n_contexts += len(result.records); n_scored += sum(r.score is not None for r in result.records)
        review_rows.append({'sr.no': ordinal, 'review': text, 'status': status, 'overall': result.overall,
            'aspect_mean': result.aspect_mean_score, 'contexts': len(result.records),
            'scored_contexts': sum(r.score is not None for r in result.records),
            'diagnostics': '; '.join(d.code for d in result.diagnostics)})
        if result.language:
            for token in result.language.tokens:
                word = token.text.lower()
                if not re.fullmatch(r"[a-z]+(?:[-'][a-z]+)*", word): continue
                if token.pos.startswith('JJ'):
                    adjectives[word] += 1; word_rows[word].add(ordinal); examples.setdefault(word, ordinal)
                    if not engine.has_lexical(word): unknown[word] += 1
                if token.pos in {'NN', 'NNS'}: nouns[word] += 1
            for phrase in result.language.noun_phrases: phrases[phrase['text'].lower()] += 1
        for index, r in enumerate(result.records):
            context = {'sr.no': ordinal, 'context_index': index, 'category': r.category, 'aspect': r.aspect_term,
                'context': r.opinion_expression, 'score': r.score, 'polarity': r.polarity,
                'grammar_pattern': r.grammar_pattern, 'domain_rule': r.evidence.domain_rule_id,
                'vocabulary_normalized': bool(getattr(r.evidence, 'vocabulary_normalization', None)),
                'scoring_copy': (getattr(r.evidence, 'vocabulary_normalization', None) or {}).get('scoring_text', ''),
                'lexical_aliases': '; '.join(f"{m['original']} -> {m['canonical']}" for m in (getattr(r.evidence, 'vocabulary_normalization', None) or {}).get('matches', [])),
                'vader_compound': r.evidence.vader_compound, 'textblob_polarity': r.evidence.textblob_polarity}
            context_rows.append(context)
            if r.score is None: gaps.append(context)
        if ordinal % 500 == 0:
            print(f'{stage}: {ordinal}/{len(records)} reviews', flush=True)
    write_csv(out / 'reviews.csv', list(review_rows[0]), review_rows)
    context_fields = ['sr.no', 'context_index', 'category', 'aspect', 'context', 'score', 'polarity', 'grammar_pattern', 'domain_rule', 'vocabulary_normalized', 'scoring_copy', 'lexical_aliases', 'vader_compound', 'textblob_polarity']
    write_csv(out / 'contexts.csv', context_fields, context_rows)
    write_csv(out / 'unscored_contexts.csv', context_fields, gaps)
    write_csv(out / 'adjective_inventory.csv', ['term', 'occurrences', 'reviews', 'has_lexical_evidence', 'example_source_row'],
        ({'term': word, 'occurrences': count, 'reviews': len(word_rows[word]),
          'has_lexical_evidence': engine.has_lexical(word), 'example_source_row': examples[word]}
         for word, count in adjectives.most_common()))
    write_csv(out / 'unknown_adjectives.csv', ['term', 'occurrences', 'reviews', 'example_source_row'],
        ({'term': word, 'occurrences': count, 'reviews': len(word_rows[word]), 'example_source_row': examples[word]}
         for word, count in unknown.most_common()))
    write_csv(out / 'noun_inventory.csv', ['term', 'occurrences'], ({'term': w, 'occurrences': n} for w, n in nouns.most_common()))
    write_csv(out / 'noun_phrase_inventory.csv', ['phrase', 'occurrences'], ({'phrase': w, 'occurrences': n} for w, n in phrases.most_common()))
    summary = {'stage': stage, 'source_rows': len(records), 'statuses': dict(statuses),
        'extracted_contexts': n_contexts, 'scored_contexts': n_scored, 'unscored_contexts': n_contexts - n_scored,
        'adjective_types': len(adjectives), 'adjective_occurrences': sum(adjectives.values()),
        'unsupported_adjective_types': len(unknown), 'unsupported_adjective_occurrences': sum(unknown.values()),
        'diagnostics': dict(diagnostics), 'elapsed_seconds': round(perf_counter() - started, 3),
        'aspect_phrases': sum(len(v) for v in domain()['aspects'].values()),
        'policy': asdict(engine.policy), 'baseline_fingerprint': analysis_fingerprint(),
        'resource_hashes': engine.lexicon_hashes, 'library_versions': engine.versions,
        'normalized_contexts': sum(r['vocabulary_normalized'] for r in context_rows),
        'input_sha256': sha256((root / 'inputs/booking_italy_all.csv').read_bytes()).hexdigest(),
        'accuracy': 'Not measured; no independent aspect sentiment gold labels supplied.',
        'coverage_note': 'Counts include all source rows; blank body rows retained. Complete is a heuristic processing status.'}
    (out / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--stage', choices=('before', 'after'), required=True)
    args = parser.parse_args()
    audit(args.source, args.output_dir, args.stage)
