"""Train, evaluate and run independent neural rerouting with tabular evidence."""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from .neural_data import write_csv
from .neural_training import read_rows
from .routed_data import CATEGORIES
from .routed_model import load_routed_predictor, reanalyze_review
from .routed_training import metrics, pairs


def hybrid_pairs(analysis):
    grouped = {}
    for r in analysis.records:
        if r.score is None: continue
        category = 'Service' if r.category == 'Staff' else r.category
        if category in CATEGORIES: grouped.setdefault(category, set()).add(r.polarity)
    result = set()
    for c, labels in grouped.items():
        label = 'Neutral/Mixed' if 'Neutral' in labels or {'Positive', 'Negative'} <= labels else next(iter(labels))
        result.add((c, label))
    return result


def routed_pairs(result): return {(c['category'], 'Neutral/Mixed' if c['label'] in {'Mixed', 'Mixed/uncertain'} else c['label']) for c in result.categories}


def comparison_details(output_dir):
    """Derive error analysis from frozen predictions; never fit new thresholds."""
    out = Path(output_dir); records = read_rows(out/'predictions.csv')
    grouped = {}
    for r in records: grouped.setdefault(r['id'], {})[r['system']] = r
    per_category, changes = [], []
    for c in CATEGORIES:
        for system in ('Hybrid', 'Routed pipeline'):
            gold, predicted = [], []
            for methods in grouped.values():
                r = methods[system]
                gold.append({tuple(p) for p in json.loads(r['gold']) if p[0] == c})
                predicted.append({tuple(p) for p in json.loads(r['prediction']) if p[0] == c})
            per_category.append({'category': c, 'system': system, **metrics(gold, predicted)})
    for sid, methods in grouped.items():
        original, routed = methods['Hybrid'], methods['Routed pipeline']
        g = {tuple(p) for p in json.loads(original['gold'])}
        a = {tuple(p) for p in json.loads(original['prediction'])}
        b = {tuple(p) for p in json.loads(routed['prediction'])}
        changes.append({'id': sid, 'review_id': original['review_id'], 'text': original['text'],
            'hybrid_status': original['hybrid_status'],
            'new_correct_pairs': len((g & b)-a), 'lost_correct_pairs': len((g & a)-b),
            'new_false_pairs': len((b-g)-a), 'removed_false_pairs': len((a-g)-b)})
    write_csv(out/'per_category_comparison.csv', per_category, list(per_category[0]))
    write_csv(out/'case_changes.csv', changes, list(changes[0]))
    totals = {k: sum(r[k] for r in changes) for k in ('new_correct_pairs', 'lost_correct_pairs', 'new_false_pairs', 'removed_false_pairs')}
    (out/'change_summary.json').write_text(json.dumps(totals, indent=2), encoding='utf-8')
    # Additional taxonomy sensitivity: the legacy model often assigns room
    # hygiene to Room, while Trip-MA labels Cleanliness. No fitting is performed.
    def merged(value):
        groups = {}
        for c, label in json.loads(value):
            groups.setdefault('Room/Cleanliness' if c in {'Room', 'Cleanliness'} else c, set()).add(label)
        return {(c, next(iter(labels)) if len(labels) == 1 else 'Neutral/Mixed') for c, labels in groups.items()}
    sensitivity = []
    for scope in ('all_test', 'hybrid_partial_or_unsupported'):
        for system in ('Hybrid', 'Routed pipeline'):
            chosen = [r for r in records if r['system'] == system and (scope == 'all_test' or r['routed'] == 'True')]
            sensitivity.append({'scope': scope, 'system': system, 'segments': len(chosen),
                **metrics([merged(r['gold']) for r in chosen], [merged(r['prediction']) for r in chosen])})
    write_csv(out/'taxonomy_sensitivity.csv', sensitivity, list(sensitivity[0]))
    return totals


def evaluate(data_dir, model_dir, output_dir, *, device='cpu'):
    """No fitting or selection here; evaluate frozen checkpoint on all test rows."""
    from .hybrid import HybridEngine, analyze_hybrid_review
    out = Path(output_dir)
    if out.exists(): raise ValueError('Evaluation evidence already exists.')
    out.mkdir(parents=True)
    predictor = load_routed_predictor(model_dir, device=device)
    engine = HybridEngine(); rows = read_rows(Path(data_dir)/'test.csv')
    records = []
    methods = ('Hybrid', 'Routed pipeline')
    by_method = {m: [] for m in methods}; gold = []; subset = []
    routed_outcomes = Counter()
    for i, r in enumerate(rows):
        base = analyze_hybrid_review(r['text'], r['id'], engine=engine)
        original = hybrid_pairs(base)
        result = reanalyze_review(r['text'], base.aspect_analysis_status, predictor)
        selected = routed_pairs(result) if result.selected_method == 'independent_neural' else original
        g = pairs(json.loads(r['labels'])); gold.append(g)
        subset.append(base.aspect_analysis_status in {'partial', 'unsupported'})
        routed_outcomes[result.route_status] += 1
        for m, predicted in zip(methods, (original, selected)):
            by_method[m].append(predicted)
            records.append({'system': m, 'id': r['id'], 'review_id': r['review_id'], 'text': r['text'],
                'hybrid_status': base.aspect_analysis_status, 'routed': subset[-1], 'route_status': result.route_status,
                'gold': json.dumps(sorted(g)), 'prediction': json.dumps(sorted(predicted))})
        if (i+1) % 200 == 0: print(f'Evaluated {i+1}/{len(rows)} segments.', flush=True)
    values = []
    for scope in ('all_test', 'hybrid_partial_or_unsupported'):
        indices = [i for i in range(len(rows)) if scope == 'all_test' or subset[i]]
        for m in methods:
            values.append({'scope': scope, 'system': m, 'segments': len(indices),
                **metrics([gold[i] for i in indices], [by_method[m][i] for i in indices])})
    write_csv(out/'metrics.csv', values, list(values[0]))
    write_csv(out/'predictions.csv', records, list(records[0]))
    comparison_details(out)
    # Paired descriptive review-cluster bootstrap; no claim of a new universal benchmark.
    import random
    grouped = {}
    for i, r in enumerate(rows): grouped.setdefault(r['review_id'], []).append(i)
    groups = list(grouped.values()); rng = random.Random(172026); differences = []
    for _ in range(1000):
        ids = [i for _ in groups for i in groups[rng.randrange(len(groups))]]
        a = metrics([gold[i] for i in ids], [by_method['Hybrid'][i] for i in ids])['pair_micro_f1']
        b = metrics([gold[i] for i in ids], [by_method['Routed pipeline'][i] for i in ids])['pair_micro_f1']
        differences.append(b-a)
    differences.sort()
    metadata = {'model_id': predictor.model_id, 'test_sha256': sha256((Path(data_dir)/'test.csv').read_bytes()).hexdigest(),
        'route_counts': dict(routed_outcomes), 'paired_cluster_bootstrap_f1_difference_95pct': [differences[24], differences[974]],
        'scope': 'Trip-MA five mapped categories; Staff pooled Service; Neutral and Mixed merged by source. Entire test includes no-in-scope segments.',
        'selection': 'Checkpoint and thresholds frozen using validation before test predictions. No adjustments made in this evaluator.'}
    (out/'evaluation_manifest.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    plot(out, values)
    print(json.dumps(values, indent=2), flush=True)
    return values


def plot(out, values):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family': 'Times New Roman', 'font.size': 9, 'pdf.fonttype': 42, 'svg.fonttype': 'none'})
    fig, ax = plt.subplots(figsize=(6.9, 3), layout='constrained')
    rows = [r for r in values if r['scope'] == 'all_test']
    for offset, key in enumerate(('precision', 'recall', 'pair_micro_f1')):
        ax.bar([i+(offset-1)*.23 for i in range(len(rows))], [r[key] for r in rows], width=.22,
               label=key.replace('_', ' ').title(), color=str(.2+offset*.25), edgecolor='black')
    ax.set_xticks(range(len(rows)), [r['system'] for r in rows]); ax.set_ylim(0,1)
    ax.set_ylabel('Category–polarity pair score'); ax.legend(frameon=False); ax.grid(axis='y', linestyle=':', alpha=.4)
    for ext in ('pdf','svg','png'): fig.savefig(out/f'fig_routed_comparison.{ext}', dpi=300)
    plt.close(fig)


def compare_csv(path, model_dir, output_dir, *, device='cpu'):
    from .csv_input import read_review_csv, CSVLimits
    from .hybrid import HybridEngine, analyze_hybrid_review
    from .exports import _spreadsheet_cell
    out = Path(output_dir)
    if out.exists(): raise ValueError('Output exists; choose a new directory.')
    source = read_review_csv(path, text_column='review', id_column='sr.no', limits=CSVLimits(max_rows=10000))
    predictor = load_routed_predictor(model_dir, device=device); engine = HybridEngine()
    rows, details = [], []
    for i, r in enumerate(source.rows):
        row = {'row': r.ordinal, 'review_id': r.supplied_review_id, 'review': r.review_text,
            'hybrid_status': '', 'hybrid_overall': '', 'hybrid_mean': None, 'selected_method': 'invalid_input',
            'neural_status': '', 'neural_overall': '', 'model_direction_index': None, 'category_results': '',
            'selected_overall': '', 'selected_index': None, 'selected_index_type': 'unavailable',
            'validation_errors': '; '.join(x.message for x in r.issues)}
        if not r.issues:
            base = analyze_hybrid_review(r.review_text, r.supplied_review_id, engine=engine)
            result = reanalyze_review(r.review_text, base.aspect_analysis_status, predictor)
            row.update(hybrid_status=base.aspect_analysis_status, hybrid_overall=base.overall,
                hybrid_mean=base.aspect_mean_score, selected_method=result.selected_method,
                neural_status=result.route_status, neural_overall=result.overall if result.selected_method == 'independent_neural' else '',
                model_direction_index=result.review_index,
                selected_overall=result.overall if result.selected_method == 'independent_neural' else base.overall,
                selected_index=result.review_index if result.selected_method == 'independent_neural' else base.aspect_mean_score,
                selected_index_type='model_direction_index' if result.selected_method == 'independent_neural' else 'lexical_mean',
                category_results='; '.join(f"{c['category']}: {c['label']} ({c['model_direction_index']})" for c in result.categories))
            details.extend(dict(d, row=r.ordinal, probabilities=json.dumps(d['probabilities'])) for d in result.decisions)
        rows.append(row)
        if (i+1) % 100 == 0: print(f'Analyzed {i+1}/{len(source.rows)} reviews.', flush=True)
    out.mkdir(parents=True)
    for name, records in [('review_results.csv', rows), ('neural_decisions.csv', details)]:
        write_csv(out/name, [{k:_spreadsheet_cell(v) for k,v in r.items()} for r in records], list(records[0]) if records else ['row'])
    summary = {'reviews': len(rows), 'selected_methods': dict(Counter(r['selected_method'] for r in rows)),
        'neural_outcomes': dict(Counter(r['neural_status'] for r in rows)), 'model_id': predictor.model_id,
        'source_sha256': source.source_sha256, 'accuracy': 'Not measured; Booking has no human category labels.'}
    (out/'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps(summary, indent=2))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__); sub = p.add_subparsers(dest='command', required=True)
    prepare = sub.add_parser('prepare'); prepare.add_argument('--output-dir', required=True)
    train = sub.add_parser('train'); train.add_argument('--data-dir', required=True); train.add_argument('--output-dir', required=True)
    train.add_argument('--device', default='cuda', choices=['cpu','cuda']); train.add_argument('--steps', type=int, default=384)
    for name, key in [('evaluate', '--data-dir'), ('compare-csv', '--input')]:
        cmd = sub.add_parser(name); cmd.add_argument(key, required=True); cmd.add_argument('--model', required=True)
        cmd.add_argument('--output-dir', required=True); cmd.add_argument('--device', default='cpu', choices=['cpu','cuda'])
    args = p.parse_args(argv)
    if args.command == 'prepare':
        from .routed_data import prepare as run
        print(json.dumps(run(args.output_dir), indent=2))
    elif args.command == 'train':
        from .routed_training import train as run
        run(args.data_dir, args.output_dir, steps=args.steps, device=args.device)
    elif args.command == 'evaluate': evaluate(args.data_dir, args.model, args.output_dir, device=args.device)
    else: compare_csv(args.input, args.model, args.output_dir, device=args.device)
    return 0


if __name__ == '__main__': raise SystemExit(main())
