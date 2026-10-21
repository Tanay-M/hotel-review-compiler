"""Tabular and scientific-figure summary of the inspected vocabulary corpus."""
import argparse
import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from audit_booking_vocabulary import write_csv


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as f: return list(csv.DictReader(f))


def build(root):
    from hotel_compiler.hybrid import HybridEngine
    from hotel_compiler.hybrid_vocabulary import vocabulary
    from hotel_compiler.hybrid_nlp import domain
    before = json.loads((root / 'before/summary.json').read_text())
    after = json.loads((root / 'after/summary.json').read_text())
    manifest = json.loads((root / 'inputs/source_manifest.json').read_text())
    assert before['source_rows'] == after['source_rows'] == manifest['source_rows']
    assert before['policy'] == after['policy']
    assert before['baseline_fingerprint'] == after['baseline_fingerprint']
    assert before['resource_hashes']['hybrid_domain'] == after['resource_hashes']['hybrid_domain']
    for key in ('vader_lexicon', 'textblob_lexicon'):
        assert before['resource_hashes'][key] == after['resource_hashes'][key]
    old_rows = read_csv(root / 'before/reviews.csv'); new_rows = read_csv(root / 'after/reviews.csv')
    assert [(r['sr.no'], r['review']) for r in old_rows] == [(r['sr.no'], r['review']) for r in new_rows]
    report = root / 'report'; report.mkdir(exist_ok=False)
    body_count = manifest['nonblank_body_rows']
    def with_score(rows): return sum(int(r['scored_contexts']) > 0 for r in rows)
    comparisons = [
        ('Source rows retained', before['source_rows'], after['source_rows']),
        ('Nonblank review bodies', body_count, body_count),
        ('Missing review bodies', manifest['empty_body_rows_retained'], manifest['empty_body_rows_retained']),
        ('Aspect phrases', before['aspect_phrases'], after['aspect_phrases']),
        ('Reviewed lexical forms', 0, len(vocabulary()['lexical_aliases'])),
        ('Reviews with at least one scored aspect', with_score(old_rows), with_score(new_rows)),
        ('Complete processing', before['statuses'].get('complete', 0), after['statuses'].get('complete', 0)),
        ('Partial processing', before['statuses'].get('partial', 0), after['statuses'].get('partial', 0)),
        ('Unsupported processing', before['statuses'].get('unsupported', 0), after['statuses'].get('unsupported', 0)),
        ('Extracted contexts', before['extracted_contexts'], after['extracted_contexts']),
        ('Scored contexts', before['scored_contexts'], after['scored_contexts']),
        ('Unscored contexts', before['unscored_contexts'], after['unscored_contexts']),
        ('Adjective occurrences without lexical lookup support', before['unsupported_adjective_occurrences'], after['unsupported_adjective_occurrences']),
        ('Adjective types without lexical lookup support', before['unsupported_adjective_types'], after['unsupported_adjective_types']),
    ]
    write_csv(report / 'coverage_comparison.csv', ['measure', 'before', 'after', 'change'],
        ({'measure': label, 'before': a, 'after': b, 'change': b-a} for label, a, b in comparisons))
    changes = []
    for a, b in zip(old_rows, new_rows):
        changes.append({'sr.no': a['sr.no'], 'before_status': a['status'], 'after_status': b['status'],
            'before_contexts': a['contexts'], 'after_contexts': b['contexts'],
            'before_scored_contexts': a['scored_contexts'], 'after_scored_contexts': b['scored_contexts'],
            'before_aspect_mean': a['aspect_mean'], 'after_aspect_mean': b['aspect_mean'],
            'before_diagnostics': a['diagnostics'], 'after_diagnostics': b['diagnostics']})
    write_csv(report / 'review_changes.csv', list(changes[0]), changes)
    engine = HybridEngine(); alias_rows = []
    for word, spec in vocabulary()['lexical_aliases'].items():
        alias_rows.append({'form': word, 'canonical': spec['canonical'], 'categories': '; '.join(spec['categories']),
            'reason': spec['reason'], 'native_lookup_exists': engine.has_native_lexical(word),
            'corpus_adjective_occurrences': spec['observed_adjective_occurrences'],
            'example_source_row': spec['example_source_row']})
    write_csv(report / 'lexical_catalog.csv', list(alias_rows[0]), alias_rows)
    original_domain = json.loads((ROOT / 'hotel_compiler/resources/hybrid_domain.json').read_text(encoding='utf-8'))
    added = [{'category': category, 'phrase': word} for category, words in domain()['aspects'].items()
             for word in words if word not in original_domain['aspects'][category]]
    write_csv(report / 'added_aspect_phrases.csv', ['category', 'phrase'], added)
    additions = after['scored_contexts'] - before['scored_contexts']
    gap_reduction = 100 * (before['unsupported_adjective_occurrences'] - after['unsupported_adjective_occurrences']) / before['unsupported_adjective_occurrences']
    rows = '\n'.join(f'| {label} | {a:,} | {b:,} |' for label, a, b in comparisons)
    (report / 'README.md').write_text(f'''# Booking vocabulary development results

The supplied Crawlfeeds Booking Italy file contains {manifest['source_rows']:,} source rows.
{body_count:,} contain review-body text; {manifest['empty_body_rows_retained']:,} have no body after removing literal \\N missing markers.
Titles, field headings, ratings, hotel/reviewer identity and other metadata are excluded from model input.
Original positive and negative body fields are joined verbatim with a newline. No spelling or wording is rewritten in the input.
Duplicates and missing-body rows remain in the source row sequence. Source SHA-256: `{manifest['source_sha256']}`.

## What changed

Independent hybrid aspect vocabulary increased from {before['aspect_phrases']} to {after['aspect_phrases']} phrases.
The project-curated catalog contains {len(alias_rows)} lexical forms, including explicit inflections and spelling variants.
Known native entries take precedence; category guards prevent unrestricted substitution.
For matched native-unknown terms, the tools score a canonical working copy and retain the original component evidence.
Typography normalization in that scoring copy preserves contraction negation and original character spans.
The original review, sentiment lexicons, six categories, fusion weights and existing contextual-rule values are preserved.
These are vocabulary-development changes; fusion/override ablations remain deferred.

| Measure | Before | After |
|---|---:|---:|
{rows}

Additional scored contexts: **{additions:,}**. Adjective instances without lexical lookup support decrease by **{gap_reduction:.1f}%**.
Some unsupported adjective tokens are factual descriptors, names or tagging errors, not missing sentiment words.
The larger extraction set means scored-context counts cannot be interpreted as an identical-case accuracy comparison.

At least one scored aspect is available for {with_score(old_rows):,}/{body_count:,} ({100*with_score(old_rows)/body_count:.2f}%)
nonblank bodies before expansion and {with_score(new_rows):,}/{body_count:,} ({100*with_score(new_rows)/body_count:.2f}%) afterwards.
Complete processing applies to only {after['statuses'].get('complete',0):,}/{body_count:,} ({100*after['statuses'].get('complete',0)/body_count:.2f}%) afterwards.
Many long reviews contain Location/Price topics or unresolved narrative clauses; useful scored aspects coexist with Partial status.
No unsupported or partial review is relabeled Complete to improve the reported percentages.

## Research interpretation

This corpus was inspected to develop the vocabulary. These are descriptive development measurements, not unseen-test accuracy.
There are no independent aspect-polarity annotations, so accuracy, precision, recall and F1 are not reported.
Canonical substitutions are project interpretations; numerical strengths are not independently calibrated human intensity labels.
The SentiWordNet baseline fingerprint and existing hybrid domain-rule hash match the before snapshot.
The earlier paper experiments and manuscript have not been regenerated or replaced.

## Files to inspect

- `coverage_comparison.csv`: numerical table suitable for reporting coverage with the stated denominators.
- `review_changes.csv`: all {manifest['source_rows']:,} row-level before/after outcomes.
- `lexical_catalog.csv`: every lexical form, canonical expression, category guard and observed adjective frequency.
- `added_aspect_phrases.csv`: the {len(added)} newly recognized aspect phrases.
- `../after/reviews.csv`: one result per original row.
- `../after/contexts.csv`: original contexts, scores, alias matches and scoring copies.
- `../after/unscored_contexts.csv`: remaining scoring gaps.
- `../before/source_snapshot.zip` and `../after/source_snapshot.zip`: reproducible analysis snapshots.
- `../inputs/booking_italy_part_01.csv` through `booking_italy_part_05.csv`: UI-ready parts of at most 1000 rows.
- `../inputs/booking_italy_all.csv`: all original row IDs and prepared review text; use the audit runner for all rows.
- `../inputs/original_crawlfeeds.csv`: byte-identical original CSV, with its original metadata.

In the UI select Hybrid, then CSV & dashboard. Upload a part with columns `sr.no` and `review`.
Missing-body rows appear as invalid input in the UI and are named `empty_body` in this audit.

## Reproduce

Run `scripts/audit_booking_vocabulary.py SOURCE --output-dir NEW_FOLDER --stage before` with the original snapshot,
then the `after` stage with the expanded snapshot. Both must use the exact same source bytes.
Run `scripts/report_booking_vocabulary.py NEW_FOLDER` after both stages.
The builder `scripts/build_hybrid_vocabulary.py` regenerates the explicit reviewed catalog; it does not learn from ratings.
''', encoding='utf-8')
    plot(report, before, after, body_count)
    print(f'Report: {report.resolve()}')
    print(f'Additional scored contexts: {additions}; lexical gap instances reduced {gap_reduction:.1f}%')


def plot(out, before, after, bodies):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family': 'DejaVu Serif', 'font.size': 8, 'axes.spines.top': False, 'axes.spines.right': False})
    fig, ax = plt.subplots(figsize=(6.6, 2.8), layout='constrained')
    colors = {'complete': '#477966', 'partial': '#b48b4d', 'unsupported': '#8a949e'}
    for x, result in enumerate((before, after)):
        bottom = 0
        for status in ('complete', 'partial', 'unsupported'):
            value = result['statuses'].get(status, 0)
            ax.bar(x, value, bottom=bottom, width=.5, color=colors[status], label=status.title() if x == 0 else None)
            ax.text(x, bottom + value/2, f'{value:,}', ha='center', va='center', fontsize=8)
            bottom += value
    ax.set_xticks([0,1], ['Before vocabulary expansion', 'After vocabulary expansion'])
    ax.set_ylabel('Review bodies'); ax.set_ylim(0, bodies * 1.15)
    ax.set_title(f'Processing coverage on {bodies:,} nonblank review bodies')
    ax.legend(ncols=3, loc='upper center', frameon=False)
    for suffix in ('png', 'pdf', 'svg'): fig.savefig(out / f'fig_processing_coverage.{suffix}', dpi=300)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(6.6, 2.6), layout='constrained')
    metrics = [('Scored contexts', 'scored_contexts'), ('Unscored contexts', 'unscored_contexts')]
    for i, (label, key) in enumerate(metrics):
        for shift, result, color in [(-.18, before, '#8a949e'), (.18, after, '#477966')]:
            v = result[key]; ax.bar(i+shift, v, width=.34, color=color,
                                   label=('Before' if shift < 0 else 'After') if i == 0 else None)
            ax.text(i+shift, v+150, f'{v:,}', ha='center', fontsize=8)
    ax.set_xticks([0,1], [m[0] for m in metrics]); ax.set_ylabel('Extracted aspect contexts')
    ax.set_ylim(0, max(before['scored_contexts'],after['scored_contexts'])*1.15)
    ax.set_title('Vocabulary development coverage; not correctness')
    ax.legend(frameon=False)
    for suffix in ('png', 'pdf', 'svg'): fig.savefig(out / f'fig_context_coverage.{suffix}', dpi=300)
    plt.close(fig)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('directory', type=Path)
    build(p.parse_args().directory)
