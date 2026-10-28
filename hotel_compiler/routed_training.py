"""Hotel-disjoint category/polarity training; freeze choices before test scoring."""
from collections import Counter, defaultdict
from hashlib import sha256
import json
import os
from pathlib import Path
import random
from time import perf_counter

from .neural_data import write_csv
from .neural_training import BASE_MODEL, BASE_REVISION, read_rows
from .routed_data import CATEGORIES, HEADS, STATES
from .routed_model import decode_heads


def pairs(labels): return {(c, p) for c, p in labels.items() if c in CATEGORIES}


def metrics(gold, predictions):
    true = sum(len(g & p) for g, p in zip(gold, predictions))
    ng, np = sum(map(len, gold)), sum(map(len, predictions))
    return {'gold_pairs': ng, 'predicted_pairs': np, 'matched_pairs': true,
            'precision': true/np if np else 0., 'recall': true/ng if ng else 0.,
            'pair_micro_f1': 2*true/(ng+np) if ng+np else 0.,
            'exact_segment_match': sum(g == p for g, p in zip(gold, predictions))/len(gold) if gold else 0.}


def decoded(values, thresholds):
    return [{(d['category'], d['label']) for d in decode_heads(p, thresholds) if d['accepted'] and d['in_scope']}
            if p is not None else set() for p in values]


def choose_thresholds(gold_labels, values):
    thresholds = {}
    for category in HEADS:
        best = None
        for threshold in (.25, .35, .45, .5, .55, .6, .65, .7, .75, .8, .85, .9):
            tp = ng = npred = 0
            for labels, prob in zip(gold_labels, values):
                actual = labels.get(category)
                p = prob[category] if prob else None
                state = max(p, key=p.get) if p else 'Absent'
                pred = state if state != 'Absent' and p[state] >= threshold else None
                ng += actual is not None; npred += pred is not None
                tp += actual == pred and actual is not None
            score = 2*tp/(ng+npred) if ng+npred else 0.
            candidate = (score, threshold)
            if best is None or candidate > best: best = candidate
        thresholds[category] = best[1]
    return thresholds


def train(data_dir, output_dir, *, steps=384, device='cuda', seed=172026):
    os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')
    os.environ.setdefault('HF_HUB_DISABLE_XET', '1')
    import numpy as np
    import torch
    import joblib
    from datasets import Dataset
    from huggingface_hub import snapshot_download
    from setfit import SetFitModel, Trainer, TrainingArguments
    from sklearn.linear_model import LogisticRegression
    from sklearn.feature_extraction.text import TfidfVectorizer
    from importlib.metadata import version
    out, data = Path(output_dir), Path(data_dir)
    if out.exists(): raise ValueError('Training evidence exists; choose a new output directory.')
    if device == 'cuda' and not torch.cuda.is_available(): raise RuntimeError('CUDA is unavailable.')
    manifest = json.loads((data/'manifest.json').read_text(encoding='utf-8'))
    for name, digest in manifest['files'].items():
        if sha256((data/name).read_bytes()).hexdigest() != digest: raise ValueError('Prepared data changed.')
    out.mkdir(parents=True)
    (out/'data_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    torch.set_num_threads(4); torch.manual_seed(seed); np.random.seed(seed); random.seed(seed)
    if device == 'cuda': torch.cuda.manual_seed_all(seed); torch.cuda.reset_peak_memory_stats()
    started = perf_counter()
    snapshot = snapshot_download(BASE_MODEL, revision=BASE_REVISION,
        allow_patterns=['*.json', '*.txt', '*.safetensors', 'README.md'])
    model = SetFitModel.from_pretrained(snapshot, device=device)
    model.model_body.max_seq_length = 128
    tokenizer = model.model_body.tokenizer
    train_rows, val_rows = read_rows(data/'train.csv'), read_rows(data/'validation.csv')
    exclusions = []
    def valid(rows, split):
        selected = []
        for r in rows:
            if len(tokenizer(r['text'], truncation=False)['input_ids']) > 128:
                exclusions.append({'split': split, 'id': r['id'], 'reason': 'token_length'})
            else: selected.append(r)
        return selected
    admitted = valid(train_rows, 'train')
    val_admitted = valid(val_rows, 'validation')
    texts = [r['text'] for r in admitted]
    gold_train = [json.loads(r['labels']) for r in admitted]
    gold_val = [json.loads(r['labels']) for r in val_rows]
    versions = {n: version(n) for n in ('torch', 'setfit', 'sentence-transformers', 'scikit-learn', 'transformers')}
    def fit_heads(features):
        heads = {}
        for category in HEADS:
            y = [STATES.index(g.get(category, 'Absent')) for g in gold_train]
            heads[category] = LogisticRegression(class_weight='balanced', max_iter=1000, random_state=seed).fit(features, y)
        return heads
    def arrays(heads, features, rows, all_rows):
        result = [None]*len(all_rows)
        index = {r['id']: i for i, r in enumerate(all_rows)}
        probs = {c: heads[c].predict_proba(features) for c in HEADS}
        for j, r in enumerate(rows):
            p = {c: {state: 0. for state in STATES} for c in HEADS}
            for c in HEADS:
                for state, value in zip(heads[c].classes_, probs[c][j]): p[c][STATES[int(state)]] = float(value)
            result[index[r['id']]] = p
        return result
    candidates = {}; history = []
    for name in ('frozen', 'finetuned'):
        if name == 'finetuned':
            groups = defaultdict(list)
            for r in admitted: groups[r['labels']].append(r)
            selected = []
            for key in sorted(groups):
                pool = groups[key][:]; random.Random(seed+len(selected)).shuffle(pool)
                if len(pool) >= 2: selected.extend(pool[:24])
            combinations = sorted({r['labels'] for r in selected})
            labels = [combinations.index(r['labels']) for r in selected]
            write_csv(out/'encoder_training_examples.csv', selected, list(selected[0]))
            name0, weight0 = next(iter(model.model_body.named_parameters()))
            before = sha256(weight0.detach().cpu().numpy().tobytes()).hexdigest()
            args = TrainingArguments(output_dir=str(out/'checkpoints'), batch_size=4, num_epochs=1,
                max_steps=steps, max_length=128, num_iterations=4, body_learning_rate=2e-5,
                use_amp=device == 'cuda', seed=seed, logging_steps=50, report_to='none', save_strategy='no', eval_strategy='no')
            trainer = Trainer(model=model, args=args, train_dataset=Dataset.from_dict({'text': [r['text'] for r in selected], 'label': labels}))
            t = perf_counter()
            trainer.train_embeddings([r['text'] for r in selected], labels)
            _, weight1 = next(iter(model.model_body.named_parameters()))
            after = sha256(weight1.detach().cpu().numpy().tobytes()).hexdigest()
            if before == after: raise RuntimeError('Encoder weights did not change.')
            history = [{'step': r.get('step'), 'loss': r.get('embedding_loss', r.get('loss'))}
                       for r in trainer.st_trainer.state.log_history if 'embedding_loss' in r or 'loss' in r]
            adaptation = {'examples': len(selected), 'steps': trainer.st_trainer.state.global_step,
                'seconds': perf_counter()-t, 'parameter': name0, 'before_hash': before, 'after_hash': after}
        train_features = model.model_body.encode(texts, batch_size=16, show_progress_bar=False)
        heads = fit_heads(train_features)
        val_features = model.model_body.encode([r['text'] for r in val_admitted], batch_size=16, show_progress_bar=False)
        values = arrays(heads, val_features, val_admitted, val_rows)
        thresholds = choose_thresholds(gold_val, values)
        scores = metrics([pairs(g) for g in gold_val], decoded(values, thresholds))
        folder = out/'models'/name; (folder/'encoder').mkdir(parents=True)
        model.model_body.save_pretrained(str(folder/'encoder'))
        joblib.dump(heads, folder/'heads.joblib')
        candidates[name] = {'thresholds': thresholds, 'validation': scores, 'values': values}
        print(f'{name}: validation pair micro-F1={scores["pair_micro_f1"]:.4f}', flush=True)
    # Lightweight classical comparator, same admitted examples and labels.
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=20000)
    classic_heads = fit_heads(vectorizer.fit_transform(texts))
    classic_values = arrays(classic_heads, vectorizer.transform([r['text'] for r in val_admitted]), val_admitted, val_rows)
    classic_thresholds = choose_thresholds(gold_val, classic_values)
    joblib.dump({'vectorizer': vectorizer, 'heads': classic_heads}, out/'tfidf.joblib')
    candidates['tfidf'] = {'thresholds': classic_thresholds,
        'validation': metrics([pairs(g) for g in gold_val], decoded(classic_values, classic_thresholds)), 'values': classic_values}
    chosen = max(('frozen', 'finetuned'), key=lambda n: (candidates[n]['validation']['pair_micro_f1'], n == 'frozen'))
    settings = {'selected': chosen, 'selection': 'validation joint category-polarity micro-F1; frozen wins ties',
        'candidates': {n: {k: v for k, v in c.items() if k != 'values'} for n, c in candidates.items()},
        'seed': seed, 'max_length': 128, 'adaptation': adaptation, 'versions': versions,
        'base_model': BASE_MODEL, 'revision': BASE_REVISION, 'head_training_examples': len(admitted),
        'category_mapping': manifest['crosswalk'], 'staff_policy': manifest['staff_policy']}
    for name in ('frozen', 'finetuned'):
        folder = out/'models'/name
        file_hashes = {str(p.relative_to(folder)).replace('\\', '/'): sha256(p.read_bytes()).hexdigest() for p in folder.rglob('*') if p.is_file()}
        checkpoint = {'heads': HEADS, 'states': STATES, 'max_length': 128, 'thresholds': candidates[name]['thresholds'],
            'files': file_hashes, 'model_id': f'tripma-routed-{name}-'+sha256(json.dumps(file_hashes, sort_keys=True).encode()).hexdigest()[:12],
            'label_policy': manifest['label_policy'], 'crosswalk': manifest['crosswalk']}
        (folder/'routed_manifest.json').write_text(json.dumps(checkpoint, indent=2), encoding='utf-8')
    # Settings and thresholds are saved BEFORE reading/evaluating the held-out test.
    (out/'frozen_settings.json').write_text(json.dumps(settings, indent=2), encoding='utf-8')
    test_rows = read_rows(data/'test.csv'); test_admitted = valid(test_rows, 'test')
    from .routed_model import LocalRoutedModel
    gold_test = [json.loads(r['labels']) for r in test_rows]
    all_metrics, predictions = [], []
    for name in ('frozen', 'finetuned', 'tfidf'):
        if name == 'tfidf':
            test_values = arrays(classic_heads, vectorizer.transform([r['text'] for r in test_admitted]), test_admitted, test_rows)
        else:
            local = LocalRoutedModel(out/'models'/name, device=device)
            test_values = local.predict_many([r['text'] for r in test_rows])
            del local
        for split, rows, gold, values in [('validation', val_rows, gold_val, candidates[name]['values']),
                                          ('test', test_rows, gold_test, test_values)]:
            pred = decoded(values, candidates[name]['thresholds'])
            all_metrics.append({'system': name, 'split': split, 'segments': len(rows), **metrics([pairs(g) for g in gold], pred)})
            for r, g, p in zip(rows, gold, pred):
                predictions.append({'system': name, 'split': split, 'id': r['id'], 'review_id': r['review_id'],
                    'text': r['text'], 'gold': json.dumps(sorted(pairs(g))), 'prediction': json.dumps(sorted(p))})
    write_csv(out/'metrics.csv', all_metrics, list(all_metrics[0]))
    write_csv(out/'predictions.csv', predictions, list(predictions[0]))
    write_csv(out/'length_exclusions.csv', exclusions, ['split', 'id', 'reason'])
    write_csv(out/'training_loss.csv', history, ['step', 'loss'])
    settings.update(total_seconds=perf_counter()-started,
        peak_tensor_bytes=torch.cuda.max_memory_allocated() if device == 'cuda' else 0,
        gpu=torch.cuda.get_device_name(0) if device == 'cuda' else None,
        code_hashes={p.name: sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('routed*.py')})
    (out/'run_manifest.json').write_text(json.dumps(settings, indent=2), encoding='utf-8')
    print(json.dumps({'selected': chosen, 'metrics': all_metrics}, indent=2), flush=True)
    return settings
