"""Lazy local neural inference and a presentation-only hybrid supplement."""
from dataclasses import dataclass
from importlib.util import find_spec
import json
import os
from pathlib import Path
from threading import Lock

from .neural_fallback import LocalNeuralPredictor, NeuralRecovery, recover_partial
from .web_analysis import HybridDemoResult, METHODS


class NeuralDependencyError(RuntimeError):
    pass


def model_path():
    default = Path(__file__).resolve().parents[1]/'output/neural/2026-10-23-webis-v1/models/finetuned'
    return Path(os.environ.get('HOTEL_COMPILER_NEURAL_MODEL', str(default))).resolve()


def neural_availability():
    """Lightweight capability check; no torch import or model download."""
    ready = find_spec('torch') is not None and find_spec('setfit') is not None
    try:
        manifest = json.loads((model_path()/'recovery_manifest.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {'available': False, 'message': 'The locally trained neural checkpoint is not installed.'}
    return {'available': ready, 'model_id': manifest['model_id'],
            'policy': manifest['acceptance_policy'],
            'message': 'Local model ready; first use loads its weights.' if ready else
                       'Start_Demo.bat needs the installed .venv-neural environment for neural recovery.'}


_load_lock = Lock()
_inference_lock = Lock()
_predictor = None


class _SerializedPredictor:
    def __init__(self, predictor):
        self.predictor = predictor
        self.model_id = predictor.model_id
        self.policy = predictor.policy

    def predict(self, aspect, context):
        with _inference_lock:
            return self.predictor.predict(aspect, context)


def get_neural_predictor():
    global _predictor
    with _load_lock:
        if _predictor is None:
            info = neural_availability()
            if not info['available']:
                raise NeuralDependencyError(info['message'])
            try:
                import torch
                torch.set_num_threads(4)
                loaded = LocalNeuralPredictor(model_path(), device='cpu')
                _predictor = _SerializedPredictor(loaded)
            except Exception as error:
                raise NeuralDependencyError(f'Could not load the local neural model: {error}') from error
        return _predictor


@dataclass(frozen=True)
class NeuralHybridDemoResult(HybridDemoResult):
    recovery: NeuralRecovery

    def to_dict(self, include_trace=False):
        result = super().to_dict(include_trace)
        result.update(method='hybrid_neural', method_label=METHODS['hybrid_neural'],
                      neural_recovery=self.recovery.to_dict())
        return result


def augment_demo(result, predictor=None):
    predictor = predictor or get_neural_predictor()
    return NeuralHybridDemoResult(result.source, recover_partial(result.source, predictor))


def analyze_neural_demo(text, review_id=None):
    from .web_analysis import analyze_hybrid_demo
    predictor = get_neural_predictor()
    return augment_demo(analyze_hybrid_demo(text, review_id), predictor)


def recovery_summary(batch):
    """Additional opinion counts; never a replacement for lexical aggregation."""
    from collections import Counter
    from .neural_fallback import CATEGORIES
    outcomes = Counter()
    decisions = Counter()
    categories = []
    recoveries = [(row, row.analysis.recovery) for row in batch.rows if row.analysis]
    for row, recovery in recoveries:
        outcomes[recovery.recovery_status] += 1
        decisions.update(a.decision for a in recovery.attempts)
    for category in sorted(CATEGORIES):
        accepted = [(row.row_id, a) for row, recovery in recoveries for a in recovery.recovered
                    if a.category == category]
        categories.append({'category': category, 'opinions': len(accepted),
                           'positive': sum(a.model_label == 'Positive' for _, a in accepted),
                           'negative': sum(a.model_label == 'Negative' for _, a in accepted),
                           'row_ids': list(dict.fromkeys(rid for rid, _ in accepted))})
    return {'assisted_reviews': outcomes['neural_assisted'],
            'added_opinions': decisions['accepted'],
            'eligible_contexts': decisions['accepted'] + decisions['abstained'] + decisions['model_error'],
            'abstained_contexts': decisions['abstained'], 'model_errors': decisions['model_error'],
            'not_eligible_contexts': decisions['not_eligible'],
            'outcomes': dict(outcomes), 'categories': categories,
            'model_id': recoveries[0][1].model_id if recoveries else None,
            'policy': recoveries[0][1].to_dict()['policy'] if recoveries else None}
