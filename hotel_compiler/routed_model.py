"""Independent multi-category neural reanalysis, not hybrid opinion completion."""
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
import re

from .routed_data import CATEGORIES, HEADS, STATES


def load_routed_predictor(folder, *, device='cpu'):
    """Load a versioned ML or fine-tuned DL checkpoint without changing routing."""
    manifest = json.loads((Path(folder)/'routed_manifest.json').read_text(encoding='utf-8'))
    if manifest.get('model_type') == 'dl_category_pair':
        from .dl_pair import LocalDLModel
        return LocalDLModel(folder, device=device)
    return LocalRoutedModel(folder, device=device)


def decode_heads(probabilities, thresholds):
    """Each head predicts Absent/Negative/Neutral-Mixed/Positive independently."""
    decisions = []
    for category in HEADS:
        p = probabilities[category]
        if set(p) != set(STATES): raise ValueError('Wrong category head labels.')
        from math import isfinite
        if any(isinstance(v, bool) or not isinstance(v, (float, int)) or not isfinite(v) or not 0 <= v <= 1
               for v in p.values()) or abs(sum(p.values())-1) > 1e-4:
            raise ValueError('Invalid category head probabilities.')
        state = max(STATES, key=p.get)
        accepted = state != 'Absent' and p[state] >= thresholds[category]
        # Conditional direction index; not a calibrated rating or intensity label.
        denominator = p['Positive'] + p['Negative']
        score = ((p['Positive']-p['Negative'])/denominator
                 if accepted and state in {'Positive', 'Negative'} and denominator else None)
        decisions.append({'category': category, 'label': state, 'accepted': accepted,
            'in_scope': category in CATEGORIES, 'probabilities': p,
            'model_direction_index': score,
            'reason': 'absent' if state == 'Absent' else 'below_validation_threshold' if not accepted else
                      'excluded_or_background' if category not in CATEGORIES else 'accepted'})
    return decisions


def sentence_spans(text):
    """Conservative original-text boundaries; no hybrid segmentation or vocabulary."""
    previous = 0
    for match in re.finditer(r'(?<=[.!?])\s+|[\r\n]+', text):
        start, end = previous, match.start()
        while start < end and text[start].isspace(): start += 1
        while end > start and text[end-1].isspace(): end -= 1
        if start < end: yield start, end
        previous = match.end()
    start, end = previous, len(text)
    while start < end and text[start].isspace(): start += 1
    while end > start and text[end-1].isspace(): end -= 1
    if start < end: yield start, end


def overall(labels):
    labels = set(labels)
    if {'Positive', 'Negative'} <= labels or 'Neutral/Mixed' in labels: return 'Mixed/uncertain' if not {'Positive', 'Negative'} <= labels else 'Mixed'
    if 'Positive' in labels: return 'Positive'
    if 'Negative' in labels: return 'Negative'
    return 'Unanalyzed'


@dataclass(frozen=True)
class RoutedReview:
    original_status: str
    route_status: str
    selected_method: str
    overall: str
    review_index: float | None
    categories: tuple
    records: tuple
    decisions: tuple
    warnings: tuple
    model_id: str

    def to_dict(self): return asdict(self)


def reanalyze_review(text, hybrid_status, predictor):
    """Partial/Unsupported: process ALL original sentences as a separate method.

    No access to hybrid records, aspect matches, scores or diagnostics is needed.
    Complete reviews and processing failures are never routed.
    """
    if hybrid_status not in {'partial', 'unsupported'}:
        return RoutedReview(hybrid_status, 'not_routed', 'hybrid', 'Unanalyzed', None,
                            (), (), (), (), predictor.model_id)
    spans = list(sentence_spans(text))
    try:
        values = predictor.predict_many([text[s:e] for s, e in spans])
    except Exception as error:
        return RoutedReview(hybrid_status, 'model_error', 'independent_neural', 'Unanalyzed', None,
            (), (), (), ({'code': 'NEURAL_MODEL_ERROR', 'start': 0, 'end': len(text),
                'message': f'{type(error).__name__}: {error}'},), predictor.model_id)
    if len(values) != len(spans): raise ValueError('Model output count mismatch.')
    records, decisions, warnings = [], [], []
    for index, ((start, end), value) in enumerate(zip(spans, values)):
        if value is None:
            warnings.append({'code': 'NEURAL_LENGTH_LIMIT', 'start': start, 'end': end,
                             'message': 'Sentence exceeds the validated token length; retained for inspection.'})
            continue
        for d in decode_heads(value, predictor.thresholds):
            entry = dict(d, sentence=index, context=text[start:end], start=start, end=end)
            decisions.append(entry)
            if d['accepted'] and d['in_scope']: records.append(entry)
    categories = []
    for category in CATEGORIES:
        group = [r for r in records if r['category'] == category]
        if not group: continue
        scores = [r['model_direction_index'] for r in group]
        mean = sum(scores)/len(scores) if all(s is not None for s in scores) else None
        categories.append({'category': category, 'label': overall(r['label'] for r in group),
                           'model_direction_index': mean, 'sentences': len(group)})
    indices = [r['model_direction_index'] for r in categories]
    mean = sum(indices)/len(indices) if indices and all(v is not None for v in indices) else None
    warnings.append({'code': 'SOURCE_TAXONOMY', 'start': 0, 'end': len(text),
        'message': 'Staff is pooled under Service in training. Neutral/Mixed is a merged source label. Facilities maps Building/Business.'})
    return RoutedReview(hybrid_status, 'reanalyzed' if records else 'abstained', 'independent_neural',
        overall(r['label'] for r in records), mean, tuple(categories), tuple(records),
        tuple(decisions), tuple(warnings), predictor.model_id)


class LocalRoutedModel:
    def __init__(self, folder, *, device='cpu'):
        path = Path(folder).resolve()
        manifest = json.loads((path/'routed_manifest.json').read_text(encoding='utf-8'))
        if tuple(manifest['heads']) != HEADS or tuple(manifest['states']) != STATES:
            raise ValueError('Unsupported routed model schema.')
        for name, digest in manifest['files'].items():
            target = (path/name).resolve()
            if not target.is_relative_to(path) or sha256(target.read_bytes()).hexdigest() != digest:
                raise ValueError('Routed checkpoint integrity mismatch.')
        from sentence_transformers import SentenceTransformer
        import joblib
        self.encoder = SentenceTransformer(str(path/'encoder'), device=device, local_files_only=True)
        self.encoder.max_seq_length = manifest['max_length']
        self.heads = joblib.load(path/'heads.joblib')
        self.thresholds = manifest['thresholds']
        self.max_length = manifest['max_length']
        self.model_id = manifest['model_id']

    def predict_many(self, texts):
        admitted = [i for i, text in enumerate(texts)
                    if len(self.encoder.tokenizer(text, truncation=False)['input_ids']) <= self.max_length]
        results = [None]*len(texts)
        if not admitted: return results
        features = self.encoder.encode([texts[i] for i in admitted], batch_size=16, show_progress_bar=False)
        arrays = {c: self.heads[c].predict_proba(features) for c in HEADS}
        for j, i in enumerate(admitted):
            results[i] = {c: {state: 0. for state in STATES} for c in HEADS}
            for category in HEADS:
                for state, p in zip(self.heads[category].classes_, arrays[category][j]):
                    results[i][category][STATES[int(state)]] = float(p)
        return results
