"""Optional target-conditioned neural recovery. Lexical outputs are immutable.

This first stage recovers only explicit, unambiguous, unscored aspect contexts
in Partial hybrid outputs. It does not extract implicit categories or turn
source OBJECTIVE predictions into neutral opinions or five strength labels.
Heavy dependencies are loaded only when a local trained model is requested.
"""
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path

from .neural_data import LABELS, model_input
from .sentiment_policy import overall_polarity

CATEGORIES = frozenset(('Room', 'Staff', 'Service', 'Food', 'Cleanliness', 'Facilities'))


class NeuralAbstention(ValueError):
    """Input lies outside the trained contract; preserve it for inspection."""


@dataclass(frozen=True)
class RecoveryPolicy:
    min_probability: float = .9
    min_margin: float = .2
    enabled: bool = True

    def __post_init__(self):
        for value in (self.min_probability, self.min_margin):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or not 0 <= value <= 1:
                raise ValueError('Recovery thresholds must be finite numbers in [0, 1].')
        if not isinstance(self.enabled, bool):
            raise TypeError('enabled must be bool.')


@dataclass(frozen=True)
class NeuralAttempt:
    record_index: int
    category: str
    aspect: str
    context: str
    start: int
    end: int
    decision: str
    reason: str
    model_label: str | None = None
    probabilities: dict | None = None
    polarity_index: float | None = None


@dataclass(frozen=True)
class NeuralRecovery:
    review_id: str
    original_status: str
    recovery_status: str
    original_scored: int
    recovered: tuple[NeuralAttempt, ...]
    attempts: tuple[NeuralAttempt, ...]
    combined_overall: str
    original_diagnostics: tuple
    model_id: str
    policy: RecoveryPolicy

    def to_dict(self):
        return asdict(self)


def decide(probabilities, policy):
    if set(probabilities) != set(LABELS):
        raise ValueError('Expected Negative, Objective and Positive probabilities.')
    if any(isinstance(v, bool) or not isinstance(v, (float, int)) or not isfinite(v) or not 0 <= v <= 1
           for v in probabilities.values()) or abs(sum(probabilities.values()) - 1) > 1e-4:
        raise ValueError('Invalid probability distribution.')
    ranked = sorted(probabilities, key=probabilities.get, reverse=True)
    label = ranked[0]
    if not policy.enabled:
        return label, False, 'validation_gate_disabled'
    if label == 'Objective':
        return label, False, 'objective_is_not_a_neutral_opinion'
    if probabilities[label] < policy.min_probability:
        return label, False, 'below_probability_threshold'
    if probabilities[label] - probabilities[ranked[1]] < policy.min_margin:
        return label, False, 'ambiguous_probability_margin'
    return label, True, 'accepted_by_validation_gate'


def eligibility(analysis, index):
    record = analysis.records[index]
    if analysis.aspect_analysis_status != 'partial':
        return 'only_partial_reviews_are_routed'
    if record.score is not None or record.evidence.status != 'no_lexical_evidence':
        return 'existing_score_or_component_error'
    if record.category not in CATEGORIES:
        return 'out_of_scope_category'
    if record.inherited:
        return 'inherited_target_requires_inspection'
    text = analysis.review_text
    if not (0 <= record.start < record.end <= len(text) and
            record.start <= record.aspect_start < record.aspect_end <= record.end and
            text[record.start:record.end] == record.opinion_expression and
            text[record.aspect_start:record.aspect_end] == record.aspect_term):
        return 'invalid_or_nonlocal_source_span'
    if any(d.code in {'OUT_OF_SCOPE', 'OUT_OF_SCOPE_PRICE_OPINION', 'COMPLEX_NEGATION', 'UNRESOLVED_CLAUSE'}
           and d.start < record.end and d.end > record.start for d in analysis.diagnostics):
        return 'unresolved_or_excluded_context'
    if any(j != index and r.aspect_start != record.aspect_start
           and record.start <= r.aspect_start < record.end for j, r in enumerate(analysis.records)):
        return 'multiple_targets_in_context'
    return None


def recover_partial(analysis, predictor, policy=None):
    """predictor must supply predict(aspect, context) and model_id; no mutation."""
    policy = policy or predictor.policy
    attempts = []
    for index, record in enumerate(analysis.records):
        if record.score is not None:
            continue
        reason = eligibility(analysis, index)
        probabilities = None
        label = None
        polarity_index = None
        if reason:
            decision = 'not_eligible'
        else:
            try:
                probabilities = predictor.predict(record.aspect_term, record.opinion_expression)
                label, accepted, reason = decide(probabilities, policy)
                decision = 'accepted' if accepted else 'abstained'
                polarity_index = probabilities['Positive'] - probabilities['Negative']
            except NeuralAbstention as error:
                decision = 'abstained'
                reason = str(error)
            except Exception as error:
                decision = 'model_error'
                reason = f'{type(error).__name__}: {error}'
        attempts.append(NeuralAttempt(index, record.category, record.aspect_term,
                                     record.opinion_expression, record.start, record.end,
                                     decision, reason, label, probabilities, polarity_index))
    recovered = tuple(a for a in attempts if a.decision == 'accepted')
    original = tuple(r for r in analysis.records if r.score is not None)
    labels = [r.polarity for r in original] + [a.model_label for a in recovered]
    status = ('neural_assisted' if recovered else 'model_error' if any(a.decision == 'model_error' for a in attempts)
              else 'abstained' if any(a.decision == 'abstained' for a in attempts) else 'not_routed')
    return NeuralRecovery(analysis.review_id, analysis.aspect_analysis_status, status, len(original),
                          recovered, tuple(attempts), overall_polarity(labels), analysis.diagnostics,
                          predictor.model_id, policy)


class LocalNeuralPredictor:
    """Load only a locally trained, manifested SetFit model; no Hub fallback."""
    def __init__(self, model_dir, *, device='cpu'):
        self.path = Path(model_dir).resolve()
        manifest = json.loads((self.path/'recovery_manifest.json').read_text(encoding='utf-8'))
        if tuple(manifest['labels']) != LABELS or manifest['input_template'] != 'aspect: original context':
            raise ValueError('Unsupported neural model contract.')
        for filename, digest in manifest['model_files'].items():
            target = (self.path/filename).resolve()
            if not target.is_relative_to(self.path) or sha256(target.read_bytes()).hexdigest() != digest:
                raise ValueError('Local neural model file integrity check failed.')
        from setfit import SetFitModel
        self.model = SetFitModel.from_pretrained(str(self.path), device=device, local_files_only=True)
        self.model_id = manifest['model_id']
        self.policy = RecoveryPolicy(**manifest['acceptance_policy'])
        self.max_length = manifest['max_length']

    def predict(self, aspect, context):
        value = model_input(aspect, context)
        length = len(self.model.model_body.tokenizer(value, truncation=False)['input_ids'])
        if length > self.max_length:
            raise NeuralAbstention(f'Context exceeds the validated {self.max_length}-token limit; not silently truncated.')
        probabilities = self.model.predict_proba([value], as_numpy=True)[0]
        classes = self.model.model_head.classes_
        return {LABELS[int(label)]: float(p) for label, p in zip(classes, probabilities)}
