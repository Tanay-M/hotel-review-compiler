"""Reproducible frozen-versus-fine-tuned MiniLM experiment on human Webis data.

Test predictions are made only after checkpoint selection and acceptance-gate
selection using validation. This is a selected single-target statement task,
not hotel review completeness, intensity accuracy, or official SemEval ABSA.
"""
from collections import Counter
import csv
from datetime import datetime, timezone
from hashlib import sha256
from importlib import metadata
import json
import os
from pathlib import Path
import random
from time import perf_counter

from .neural_data import LABELS, model_input, write_csv
from .neural_fallback import RecoveryPolicy, decide

BASE_MODEL = 'sentence-transformers/all-MiniLM-L6-v2'
BASE_REVISION = '1110a243fdf4706b3f48f1d95db1a4f5529b4d41'


def read_rows(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))


def select_gate(labels, probabilities, *, target_precision=.9, min_accepted=30):
    """Select on validation only; disable if no candidate meets the constraint.

    Precision is empirical on selected validation predictions, not calibrated
    certainty or a guarantee on real-world residuals. Objective is not accepted.
    """
    candidates = []
    for threshold in (.5, .6, .7, .8, .85, .9, .95, .98):
        for margin in (0., .1, .2, .3):
            policy = RecoveryPolicy(threshold, margin)
            accepted = []
            for label, values in zip(labels, probabilities):
                prediction, keep, _ = decide(dict(zip(LABELS, map(float, values))), policy)
                if keep:
                    accepted.append(prediction == LABELS[int(label)])
            precision = sum(accepted)/len(accepted) if accepted else 0.
            if len(accepted) >= min_accepted and precision >= target_precision:
                candidates.append((len(accepted), precision, threshold, margin))
    if not candidates:
        return RecoveryPolicy(1., 1., False), {'accepted': 0, 'precision': None,
                'reason': 'No validation gate met the predeclared precision/support target.'}
    count, precision, threshold, margin = max(candidates, key=lambda r: (r[0], r[1], r[2], r[3]))
    return RecoveryPolicy(threshold, margin), {'accepted': count, 'precision': precision,
            'reason': 'Maximum validation acceptance subject to empirical precision and support constraints.'}


def train_neural(data_dir, output_dir, *, steps=256, batch_size=4, max_length=128,
                 per_class=256, seed=172026, device='cuda'):
    os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')
    os.environ.setdefault('HF_HUB_DISABLE_TELEMETRY', '1')
    os.environ.setdefault('HF_HUB_DISABLE_XET', '1')
    import numpy as np
    import torch
    from datasets import Dataset
    from setfit import SetFitModel, Trainer, TrainingArguments
    from huggingface_hub import snapshot_download
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score

    if steps < 1 or batch_size < 1 or max_length < 16 or per_class < 2:
        raise ValueError('Positive training budget and at least two examples per class required.')
    out = Path(output_dir)
    if out.exists():
        raise ValueError('Training output directory exists; prior evidence is protected.')
    data = Path(data_dir)
    source_manifest = json.loads((data/'manifest.json').read_text(encoding='utf-8'))
    for name, digest in source_manifest['files'].items():
        if sha256((data/name).read_bytes()).hexdigest() != digest:
            raise ValueError(f'Prepared data changed after manifest creation: {name}')
    if device == 'cuda' and not torch.cuda.is_available():
        raise RuntimeError('CUDA is unavailable. Install a CUDA PyTorch wheel or explicitly choose --device cpu.')
    torch.set_num_threads(4)
    torch.manual_seed(seed)
    np.random.seed(seed)
    random.seed(seed)
    if device == 'cuda':
        torch.cuda.manual_seed_all(seed)
        torch.cuda.reset_peak_memory_stats()
    out.mkdir(parents=True)
    (out/'data_manifest.json').write_text(json.dumps(source_manifest, indent=2), encoding='utf-8')
    versions = {n: metadata.version(n) for n in ['torch', 'setfit', 'sentence-transformers', 'transformers',
                                                'datasets', 'scikit-learn', 'accelerate']}
    start = perf_counter()
    # SetFit 1.1.3 does not forward its revision argument to SentenceTransformer;
    # resolve the immutable snapshot first so the encoder is actually pinned.
    snapshot = snapshot_download(BASE_MODEL, revision=BASE_REVISION,
                                 allow_patterns=['*.json', '*.txt', '*.safetensors', 'README.md'])
    frozen = SetFitModel.from_pretrained(snapshot, device=device,
                                        head_params={'class_weight': 'balanced', 'max_iter': 1000})
    frozen.model_body.max_seq_length = max_length
    tokenizer = frozen.model_body.tokenizer
    excluded = []

    def load(split):
        all_rows = read_rows(data/f'{split}.csv')
        valid = []
        for row in all_rows:
            row['input'] = model_input(row['aspect'], row['text'])
            if len(tokenizer(row['input'], truncation=False)['input_ids']) > max_length:
                excluded.append({'split': split, 'example_id': row['example_id'], 'reason': 'token_length_limit'})
            else:
                valid.append(row)
        return valid, all_rows

    train, _ = load('train')
    validation, validation_all = load('validation')
    # No test examples/predictions are used for fitting, checkpoint or gate choice.
    label = lambda rows: np.array([LABELS.index(r['label']) for r in rows])
    labels_train = label(train)
    labels_validation = label(validation)
    train_inputs = [r['input'] for r in train]
    validation_inputs = [r['input'] for r in validation]
    def validation_f1(probabilities):
        predictions = dict(zip([r['example_id'] for r in validation], probabilities.argmax(axis=1)))
        return f1_score(label(validation_all), [predictions.get(r['example_id'], -1) for r in validation_all],
                        labels=range(3), average='macro', zero_division=0)
    timings = []
    before_hash = None
    parameter_name = None

    def encoder_fingerprint(model):
        name, weight = next(iter(model.model_body.named_parameters()))
        return name, sha256(weight.detach().cpu().numpy().tobytes()).hexdigest()

    def fit_head(model):
        t = perf_counter()
        features = model.model_body.encode(train_inputs, batch_size=16, show_progress_bar=False)
        model.model_head.fit(features, labels_train)
        return perf_counter()-t

    print(f'CUDA={torch.cuda.is_available()}, device={device}; head training examples={len(train)}', flush=True)
    timings.append({'stage': 'frozen_head_training', 'seconds': fit_head(frozen)})
    frozen_prob = frozen.predict_proba(validation_inputs, batch_size=16, as_numpy=True)
    frozen_validation_f1 = validation_f1(frozen_prob)
    frozen.save_pretrained(str(out/'models/frozen'))
    print(f'Frozen MiniLM validation macro-F1={frozen_validation_f1:.4f}', flush=True)

    # A classical ML comparator uses exactly the same admitted training inputs.
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=20000)
    tfidf = LogisticRegression(class_weight='balanced', max_iter=1000, random_state=seed)
    tfidf.fit(vectorizer.fit_transform(train_inputs), labels_train)
    tfidf_prob = tfidf.predict_proba(vectorizer.transform(validation_inputs))
    import joblib
    joblib.dump({'vectorizer': vectorizer, 'classifier': tfidf, 'labels': LABELS}, out/'tfidf_model.joblib')

    fine = SetFitModel.from_pretrained(str(out/'models/frozen'), device=device, local_files_only=True)
    fine.model_body.max_seq_length = max_length
    parameter_name, before_hash = encoder_fingerprint(fine)
    chosen = []
    for cls in range(3):
        pool = [r for r in train if LABELS.index(r['label']) == cls]
        random.Random(seed+cls).shuffle(pool)
        chosen.extend(pool[:per_class])
    random.Random(seed).shuffle(chosen)
    write_csv(out/'contrastive_training_examples.csv', chosen, list(chosen[0]))
    args = TrainingArguments(output_dir=str(out/'training-checkpoints'), batch_size=batch_size,
                             num_epochs=1, max_steps=steps, num_iterations=4, max_length=max_length,
                             body_learning_rate=2e-5, use_amp=device == 'cuda', seed=seed,
                             logging_steps=25, report_to='none', save_strategy='no', eval_strategy='no')
    trainer = Trainer(model=fine, args=args, train_dataset=Dataset.from_dict({
        'text': [r['input'] for r in chosen], 'label': [LABELS.index(r['label']) for r in chosen]}))
    t = perf_counter()
    print(f'Fine-tuning encoder on {len(chosen)} balanced human examples for up to {steps} steps.', flush=True)
    trainer.train_embeddings([r['input'] for r in chosen], [LABELS.index(r['label']) for r in chosen])
    timings.append({'stage': 'encoder_fine_tuning', 'seconds': perf_counter()-t})
    training_steps_completed = trainer.st_trainer.state.global_step
    loss_rows = [dict(step=entry.get('step'), epoch=entry.get('epoch'),
                      loss=entry.get('embedding_loss', entry.get('loss')),
                      grad_norm=entry.get('grad_norm'), learning_rate=entry.get('learning_rate'))
                 for entry in trainer.st_trainer.state.log_history
                 if 'embedding_loss' in entry or 'loss' in entry]
    write_csv(out/'training_loss.csv', loss_rows, ['step', 'epoch', 'loss', 'grad_norm', 'learning_rate'])
    # Train the same LR head on all admitted training rows, isolating encoder adaptation.
    fine.model_head = LogisticRegression(class_weight='balanced', max_iter=1000, random_state=seed)
    timings.append({'stage': 'fine_tuned_head_training', 'seconds': fit_head(fine)})
    _, after_hash = encoder_fingerprint(fine)
    if before_hash == after_hash:
        raise RuntimeError('Encoder fingerprint did not change; do not claim neural fine-tuning.')
    fine_prob = fine.predict_proba(validation_inputs, batch_size=16, as_numpy=True)
    fine_validation_f1 = validation_f1(fine_prob)
    fine.save_pretrained(str(out/'models/finetuned'))
    print(f'Fine-tuned MiniLM validation macro-F1={fine_validation_f1:.4f}', flush=True)

    model_values = {'frozen': (frozen, frozen_prob), 'finetuned': (fine, fine_prob)}
    selected = 'finetuned' if fine_validation_f1 > frozen_validation_f1 else 'frozen'
    gates = {}
    for name, (model, probabilities) in model_values.items():
        policy, evidence = select_gate(labels_validation, probabilities)
        gates[name] = {'policy': as_policy(policy), 'validation': evidence}
        folder = out/'models'/name
        files = {str(p.relative_to(folder)).replace('\\', '/'): sha256(p.read_bytes()).hexdigest()
                 for p in folder.rglob('*') if p.is_file()}
        manifest = dict(model_id=f'webis-{name}-{sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()[:12]}',
                        base_model=BASE_MODEL, base_revision=BASE_REVISION, labels=LABELS,
                        input_template='aspect: original context', max_length=max_length,
                        acceptance_policy=as_policy(policy), model_files=files,
                        training_source_sha256=source_manifest['source_sha256'],
                        source_label_policy=source_manifest['label_policy'],
                        scope='Known explicit aspect polarity only; Objective abstains; no five-strength training labels.')
        (folder/'recovery_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')

    # Freeze choice before the held-out test labels/predictions are evaluated.
    settings = dict(selected_model=selected, gates=gates, selection='validation macro-F1; ties prefer frozen',
                    gate_target_precision=.9, gate_minimum_validation_accepted=30,
                    seed=seed, max_steps=steps, batch_size=batch_size, max_length=max_length,
                    encoder_training_examples=len(chosen), head_training_examples=len(train),
                    training_steps_completed=training_steps_completed,
                    validation_macro_f1={'frozen': float(frozen_validation_f1), 'finetuned': float(fine_validation_f1)},
                    encoder_parameter=parameter_name, encoder_hash_before=before_hash, encoder_hash_after=after_hash,
                    trained_utc=datetime.now(timezone.utc).isoformat(), versions=versions)
    (out/'frozen_settings.json').write_text(json.dumps(settings, indent=2), encoding='utf-8')
    test, test_all = load('test')
    probabilities_test = {
        'frozen': frozen.predict_proba([r['input'] for r in test], batch_size=16, as_numpy=True),
        'finetuned': fine.predict_proba([r['input'] for r in test], batch_size=16, as_numpy=True),
        'tfidf': tfidf.predict_proba(vectorizer.transform([r['input'] for r in test]))}
    metric_rows, predictions, per_class, confusions = [], [], [], []
    for split, valid, all_rows, values in [
        ('validation', validation, validation_all, {'frozen': frozen_prob, 'finetuned': fine_prob, 'tfidf': tfidf_prob}),
        ('test', test, test_all, probabilities_test)]:
        for name, probabilities in values.items():
            actual = label(all_rows)
            by_id = dict(zip([r['example_id'] for r in valid], probabilities))
            predicted = []
            accepted = []
            for row in all_rows:
                p = by_id.get(row['example_id'])
                pred = int(p.argmax()) if p is not None else -1
                predicted.append(pred)
                decision = None
                if name in gates and p is not None:
                    decision = decide(dict(zip(LABELS, map(float, p))), RecoveryPolicy(**gates[name]['policy']))
                    if decision[1]: accepted.append(pred == LABELS.index(row['label']))
                predictions.append(dict(system=name, split=split, example_id=row['example_id'],
                    review_id=row['review_id'], hotel_id=row['hotel_id'], aspect=row['aspect'], text=row['text'],
                    gold=row['label'], prediction=LABELS[pred] if pred >= 0 else 'Unavailable',
                    negative_probability=float(p[0]) if p is not None else None,
                    objective_probability=float(p[1]) if p is not None else None,
                    positive_probability=float(p[2]) if p is not None else None,
                    accepted=decision[1] if decision else False, reason=decision[2] if decision else 'not_gated_or_long_input'))
            report = classification_report(actual, predicted, labels=range(3), target_names=LABELS, output_dict=True, zero_division=0)
            metric_rows.append(dict(system=name, split=split, cases=len(all_rows), scored=len(by_id),
                correct=int(sum(a == b for a, b in zip(actual, predicted))), accuracy=float(accuracy_score(actual, predicted)),
                macro_f1=float(f1_score(actual, predicted, labels=range(3), average='macro', zero_division=0)),
                accepted=len(accepted), accepted_correct=sum(accepted),
                acceptance_precision=sum(accepted)/len(accepted) if accepted else None,
                scope='Selected single-aspect Webis statement polarity; Objective is not Neutral opinion.'))
            per_class.extend(dict(system=name, split=split, label=cls, **report[cls]) for cls in LABELS)
            cm = confusion_matrix(actual, predicted, labels=[0, 1, 2, -1])
            confusions.extend(dict(system=name, split=split, gold=LABELS[i], prediction=(LABELS[j] if j < 3 else 'Unavailable'), count=int(cm[i,j]))
                              for i in range(3) for j in range(4))
    write_csv(out/'metrics.csv', metric_rows, list(metric_rows[0]))
    write_csv(out/'predictions.csv', predictions, list(predictions[0]))
    write_csv(out/'per_class_metrics.csv', per_class, list(per_class[0]))
    write_csv(out/'confusion_counts.csv', confusions, list(confusions[0]))
    write_csv(out/'length_exclusions.csv', excluded, ['split', 'example_id', 'reason'])
    write_csv(out/'timings.csv', timings, ['stage', 'seconds'])
    settings.update(total_seconds=perf_counter()-start,
                    peak_gpu_allocated_bytes=torch.cuda.max_memory_allocated() if device == 'cuda' else 0,
                    gpu=torch.cuda.get_device_name(0) if device == 'cuda' else None,
                    measured_task='Human-labelled single-expert-aspect statement polarity, not end-to-end review ABSA.',
                    code_hashes={p.name: sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('neural*.py')})
    (out/'run_manifest.json').write_text(json.dumps(settings, indent=2), encoding='utf-8')
    plot_results(out, metric_rows, confusions)
    print(json.dumps({'selected': selected, 'metrics': metric_rows, 'output': str(out)}, indent=2), flush=True)
    return settings


def as_policy(policy):
    return {'min_probability': policy.min_probability, 'min_margin': policy.min_margin, 'enabled': policy.enabled}


def plot_results(out, metrics, confusions):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family': 'Times New Roman', 'font.size': 9, 'pdf.fonttype': 42, 'svg.fonttype': 'none'})
    rows = [r for r in metrics if r['split'] == 'test']
    names = {'frozen': 'Frozen MiniLM', 'finetuned': 'Fine-tuned MiniLM', 'tfidf': 'TF-IDF + LR'}
    fig, ax = plt.subplots(figsize=(6.9, 2.8), layout='constrained')
    for offset, (key, title, color) in enumerate([('accuracy', 'Accuracy', '.25'), ('macro_f1', 'Macro-F1', '.7')]):
        xs = [i + (offset-.5)*.32 for i in range(len(rows))]
        ax.bar(xs, [r[key] for r in rows], .3, label=title, color=color, edgecolor='black')
    ax.set_xticks(range(len(rows)), [names[r['system']] for r in rows])
    ax.set_ylim(0, 1); ax.set_ylabel('Score'); ax.legend(frameon=False); ax.grid(axis='y', linestyle=':', alpha=.5)
    for suffix in ('pdf', 'svg', 'png'): fig.savefig(out/f'fig_heldout_statement_metrics.{suffix}', dpi=300)
    plt.close(fig)
