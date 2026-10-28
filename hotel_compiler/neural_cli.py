"""Offline preparation, GPU training, and tabular neural-recovery experiments."""
import argparse
from collections import Counter
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import sys
from time import perf_counter

from .neural_data import prepare_webis, write_csv
from .neural_fallback import LocalNeuralPredictor, recover_partial


def report_csv(path, rows, fields):
    from .exports import _spreadsheet_cell
    write_csv(path, [{k: _spreadsheet_cell(v) for k, v in r.items()} for r in rows], fields)


def analyze_inputs(inputs, output_dir, predictor, *, source_metadata=None):
    from .hybrid import HybridEngine, analyze_hybrid_review
    from .pipeline import analyze_review
    out = Path(output_dir)
    if out.exists(): raise ValueError('Output directory exists; use a new run name.')
    out.mkdir(parents=True)
    engine = HybridEngine()
    reviews, decisions, opinions = [], [], []
    for index, item in enumerate(inputs, 1):
        identifier, text, errors = item
        row = dict(row_ordinal=index, review_id=identifier, review=text, validation_errors='; '.join(errors),
                   compiler_status='', compiler_overall='', compiler_mean='',
                   hybrid_status='', hybrid_overall='', hybrid_mean='', original_scored='',
                   recovery_status='invalid_input' if errors else '', recovered_opinions=0,
                   augmented_overall='', original_diagnostics='', elapsed_seconds=0.)
        if errors:
            reviews.append(row)
            continue
        start = perf_counter()
        base = analyze_review(text, identifier, profile='expanded')
        hybrid = analyze_hybrid_review(text, identifier, engine=engine)
        augmented = recover_partial(hybrid, predictor)
        row.update(compiler_status=base.status, compiler_overall=base.overall, compiler_mean=base.review_score,
                   hybrid_status=hybrid.aspect_analysis_status, hybrid_overall=hybrid.overall,
                   hybrid_mean=hybrid.aspect_mean_score, original_scored=augmented.original_scored,
                   recovery_status=augmented.recovery_status, recovered_opinions=len(augmented.recovered),
                   augmented_overall=augmented.combined_overall,
                   original_diagnostics='; '.join(d.code for d in hybrid.diagnostics),
                   elapsed_seconds=perf_counter()-start)
        reviews.append(row)
        for attempt in augmented.attempts:
            values = asdict(attempt)
            probabilities = values.pop('probabilities') or {}
            decisions.append(dict(row_ordinal=index, review_id=identifier, **values,
                                   negative_probability=probabilities.get('Negative'),
                                   objective_probability=probabilities.get('Objective'),
                                   positive_probability=probabilities.get('Positive'), model_id=predictor.model_id))
        for record in hybrid.records:
            opinions.append(dict(row_ordinal=index, review_id=identifier, method='Hybrid lexical', category=record.category,
                                 aspect=record.aspect_term, context=record.opinion_expression,
                                 start=record.start, end=record.end, polarity=record.polarity,
                                 lexical_score=record.score, model_polarity_index=None))
        for attempt in augmented.recovered:
            opinions.append(dict(row_ordinal=index, review_id=identifier, method='Neural recovery', category=attempt.category,
                                 aspect=attempt.aspect, context=attempt.context, start=attempt.start, end=attempt.end,
                                 polarity=attempt.model_label, lexical_score=None,
                                 model_polarity_index=attempt.polarity_index))
        if index % 50 == 0: print(f'Analyzed {index}/{len(inputs)} reviews.', flush=True)
    report_csv(out/'review_results.csv', reviews, list(reviews[0]) if reviews else ['review_id'])
    report_csv(out/'neural_decisions.csv', decisions, list(decisions[0]) if decisions else ['review_id', 'decision', 'reason'])
    report_csv(out/'opinion_results.csv', opinions, list(opinions[0]) if opinions else ['review_id', 'method'])
    summary = dict(submitted=len(reviews), recovered_opinions=sum(r['recovered_opinions'] for r in reviews),
                   reviews_with_recovery=sum(r['recovered_opinions'] > 0 for r in reviews),
                   outcomes=dict(Counter(r['recovery_status'] for r in reviews)), model_id=predictor.model_id,
                   acceptance_policy=asdict(predictor.policy),
                   source=source_metadata,
                   interpretation='Unlabelled reviews measure recovery availability, not accuracy; original statuses/diagnostics retained.',
                   model_index='Positive probability minus Negative probability; not a lexical sentiment score or strength label.')
    (out/'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(f"{len(reviews)} reviews; {summary['recovered_opinions']} additional opinions in {summary['reviews_with_recovery']} reviews.")
    print(out.resolve())
    return summary


def evaluate_semeval_neural(path, output_dir, predictor):
    """Same declared legacy adaptation, still development evidence, never training."""
    from .compiler_profiles import compiler_profile
    from .hybrid import HybridEngine, analyze_hybrid_review
    from .pipeline import analyze_review
    from .research_data import load_semeval
    from .research_metrics import classification_metrics, coarse_category, map_semeval_category
    from .sentiment_policy import overall_polarity
    out = Path(output_dir)
    if out.exists(): raise ValueError('Evaluation output exists; use a new name.')
    out.mkdir(parents=True)
    names = ('SentiWordNet', 'Hybrid', 'Hybrid + neural recovery')
    cases = {n: [] for n in names}
    tuples = {n: Counter() for n in names}
    attempts = []
    engine = HybridEngine()
    with compiler_profile('expanded'):
        for sentence in load_semeval(path):
            gold = {(map_semeval_category(o['category']), o['polarity'].capitalize()) for o in sentence['opinions']
                    if map_semeval_category(o['category']) is not None}
            if not gold: continue
            text = sentence['text']; sid = sentence['sentence_id']
            base = analyze_review(text, sid)
            hybrid = analyze_hybrid_review(text, sid, engine=engine)
            augmented = recover_partial(hybrid, predictor)
            baseline_pairs = {(coarse_category(r.category), r.polarity) for r in base.records}
            hybrid_pairs = {(coarse_category(r.category), r.polarity) for r in hybrid.records if r.score is not None}
            augmented_pairs = hybrid_pairs | {(coarse_category(a.category), a.model_label) for a in augmented.recovered}
            attempts.extend(dict(sentence_id=sid, **asdict(a)) for a in augmented.attempts)
            for name, actual in zip(names, (baseline_pairs, hybrid_pairs, augmented_pairs)):
                tuples[name].update(gold=len(gold), predicted=len(actual), matched=len(gold & actual))
                for category in sorted({c for c, _ in gold}):
                    labels = {p for c, p in gold if c == category}
                    if len(labels) != 1: continue
                    cases[name].append(dict(system=name, parent_id=sentence['parent_id'], sentence_id=sid,
                        category=category, gold=next(iter(labels)),
                        prediction=overall_polarity(p for c, p in actual if c == category)))
    metrics = []
    for name in names:
        values = classification_metrics(cases[name]); tc = tuples[name]
        metrics.append(dict(system=name, **{k: v for k, v in values.items() if k != 'classes'},
            tuple_precision=tc['matched']/tc['predicted'] if tc['predicted'] else 0,
            tuple_recall=tc['matched']/tc['gold'] if tc['gold'] else 0,
            tuple_f1=2*tc['matched']/(tc['predicted']+tc['gold']) if tc['predicted']+tc['gold'] else 0))
    write_csv(out/'metrics.csv', metrics, list(metrics[0]))
    flat = [r for group in cases.values() for r in group]
    write_csv(out/'predictions.csv', flat, list(flat[0]))
    # JSON is internal trace evidence; faculty-facing result files remain CSV.
    (out/'recovery_trace.json').write_text(json.dumps(attempts, indent=2), encoding='utf-8')
    (out/'evaluation_scope.json').write_text(json.dumps(dict(
        role='Previously inspected SemEval development adaptation; not an untouched test set.',
        model_id=predictor.model_id, policy=asdict(predictor.policy),
        source_sha256=sha256(Path(path).read_bytes()).hexdigest(),
        training='Webis only; no SemEval labels used for model training, gate or checkpoint selection.'), indent=2), encoding='utf-8')
    for r in metrics: print(f"{r['system']}: {r['correct']}/{r['cases']}, macro-F1={r['macro_f1']:.4f}, tuple-F1={r['tuple_f1']:.4f}")
    return metrics


def main(argv=None):
    if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    prepare = sub.add_parser('prepare-webis')
    prepare.add_argument('--archive', type=Path, default=Path('data/vendor/neural-training/webis-tripad-13-sentiment.zip'))
    prepare.add_argument('--output-dir', type=Path, required=True)
    train = sub.add_parser('train')
    train.add_argument('--data-dir', type=Path, required=True)
    train.add_argument('--output-dir', type=Path, required=True)
    train.add_argument('--steps', type=int, default=256)
    train.add_argument('--batch-size', type=int, default=4)
    train.add_argument('--per-class', type=int, default=256)
    train.add_argument('--max-length', type=int, default=128)
    train.add_argument('--device', choices=['cpu', 'cuda'], default='cuda')
    single = sub.add_parser('analyze')
    single.add_argument('--text', required=True)
    batch = sub.add_parser('compare-csv')
    batch.add_argument('input', type=Path)
    batch.add_argument('--text-column', default='review')
    batch.add_argument('--id-column', default='sr.no')
    evaluate = sub.add_parser('evaluate-semeval')
    evaluate.add_argument('input', type=Path)
    for command in (single, batch, evaluate):
        command.add_argument('--model', type=Path, required=True)
        command.add_argument('--device', choices=['cpu', 'cuda'], default='cpu')
        command.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == 'prepare-webis':
        print(json.dumps(prepare_webis(args.archive, args.output_dir), indent=2))
        return 0
    if args.command == 'train':
        from .neural_training import train_neural
        train_neural(args.data_dir, args.output_dir, steps=args.steps, batch_size=args.batch_size,
                     per_class=args.per_class, max_length=args.max_length, device=args.device)
        return 0
    predictor = LocalNeuralPredictor(args.model, device=args.device)
    if args.command == 'evaluate-semeval':
        evaluate_semeval_neural(args.input, args.output_dir, predictor)
        return 0
    if args.command == 'analyze':
        inputs = [('one', args.text, [])]
        source_metadata = {'type': 'single_text', 'sha256': sha256(args.text.encode()).hexdigest()}
    else:
        from .csv_input import read_review_csv, CSVLimits
        source = read_review_csv(args.input, text_column=args.text_column, id_column=args.id_column,
                                 limits=CSVLimits(max_rows=10000, max_file_bytes=20*1024*1024))
        inputs = [(r.supplied_review_id or str(r.ordinal), r.review_text or '', [i.message for i in r.issues])
                  for r in source.rows]
        source_metadata = {'path': str(args.input.resolve()), 'sha256': source.source_sha256,
                           'text_column': source.text_column, 'id_column': source.id_column}
    analyze_inputs(inputs, args.output_dir, predictor, source_metadata=source_metadata)
    return 0


if __name__ == '__main__': raise SystemExit(main())
