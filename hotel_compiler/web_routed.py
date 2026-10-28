"""Dashboard adapter for whole-review routing to an independent classifier."""
from collections import Counter
from dataclasses import dataclass
from importlib.util import find_spec
import json
import os
from pathlib import Path
from threading import Lock

from .routed_model import load_routed_predictor, RoutedReview, reanalyze_review
from .web_analysis import HybridDemoResult, METHODS
from .web_neural import NeuralDependencyError


def model_path():
    default = Path(__file__).resolve().parents[1]/'output/neural/2026-10-23-dl-pair-human-v1/models/best'
    return Path(os.environ.get('HOTEL_COMPILER_ROUTED_MODEL', str(default))).resolve()


def availability():
    try: manifest = json.loads((model_path()/'routed_manifest.json').read_text(encoding='utf-8'))
    except (OSError, ValueError): return {'available': False, 'message': 'Independent neural checkpoint is not installed.'}
    dependency = 'transformers' if manifest.get('model_type') == 'dl_category_pair' else 'sentence_transformers'
    ready = find_spec('torch') is not None and find_spec(dependency) is not None
    return {'available': ready, 'model_id': manifest['model_id'], 'model_type': manifest.get('model_type'),
            'message': 'Fine-tuned category-conditioned DL transformer ready.' if ready else 'Use the .venv-neural demo runtime.'}


_load_lock = Lock(); _predict_lock = Lock(); _model = None


class _Serialized:
    def __init__(self, model):
        self.model = model; self.model_id = model.model_id; self.thresholds = model.thresholds

    def predict_many(self, texts):
        with _predict_lock: return self.model.predict_many(texts)


def get_model():
    global _model
    with _load_lock:
        if _model is None:
            info = availability()
            if not info['available']: raise NeuralDependencyError(info['message'])
            try:
                import torch
                torch.set_num_threads(4)
                device = os.environ.get('HOTEL_COMPILER_ROUTED_DEVICE') or ('cuda' if torch.cuda.is_available() else 'cpu')
                if device not in {'cpu', 'cuda'}: raise ValueError('Choose cpu or cuda for routed inference.')
                _model = _Serialized(load_routed_predictor(model_path(), device=device))
            except Exception as error:
                raise NeuralDependencyError(f'Could not load independent neural model: {error}') from error
        return _model


@dataclass(frozen=True)
class RoutedDemoResult(HybridDemoResult):
    routed: RoutedReview

    def to_dict(self, include_trace=False):
        value = super().to_dict(include_trace)
        value.update(method='hybrid_routed', method_label=METHODS['hybrid_routed'], routed_analysis=self.routed.to_dict())
        return value


def route_demo(result, predictor=None):
    predictor = predictor or get_model()
    return RoutedDemoResult(result.source, reanalyze_review(result.review_text, result.status, predictor))


def analyze_demo(text, review_id=None):
    from .web_analysis import analyze_hybrid_demo
    predictor = get_model()
    return route_demo(analyze_hybrid_demo(text, review_id), predictor)


def summary(batch):
    outcomes = Counter(); categories = {}; neural_overall = Counter(); method_counts = Counter()
    model_id = None
    for row in batch.rows:
        if not row.analysis: continue
        r = row.analysis.routed; model_id = r.model_id
        outcomes[r.route_status] += 1; method_counts[r.selected_method] += 1
        if r.selected_method != 'independent_neural': continue
        neural_overall[r.overall] += 1
        for c in r.categories:
            group = categories.setdefault(c['category'], {'category': c['category'], 'row_ids': [],
                'positive': 0, 'negative': 0, 'mixed_uncertain': 0, 'indices': []})
            group['row_ids'].append(row.row_id)
            group['positive' if c['label'] == 'Positive' else 'negative' if c['label'] == 'Negative' else 'mixed_uncertain'] += 1
            if c['model_direction_index'] is not None: group['indices'].append(c['model_direction_index'])
    for group in categories.values():
        group['mean_model_index'] = sum(group['indices'])/len(group['indices']) if group['indices'] else None
        group['index_reviews'] = len(group.pop('indices'))
    return {'outcomes': dict(outcomes), 'selected_methods': dict(method_counts), 'model_id': model_id,
        'routed_reviews': method_counts['independent_neural'], 'neural_results': outcomes['reanalyzed'],
        'model_errors': outcomes['model_error'],
        'abstained_reviews': outcomes['abstained'], 'retained_hybrid': method_counts['hybrid'],
        'neural_overall': dict(neural_overall), 'categories': sorted(categories.values(), key=lambda c:c['category'])}
