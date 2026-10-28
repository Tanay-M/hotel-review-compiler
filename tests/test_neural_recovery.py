"""Authored source-integrity and abstention contracts, not accuracy evidence."""
from dataclasses import replace
import unittest

from hotel_compiler.neural_data import deduplicate, extract_statements, hotel_split
from hotel_compiler.neural_fallback import RecoveryPolicy, decide, recover_partial
from hotel_compiler.hybrid import HybridAnalysis, HybridAspect, HybridEvidence
from hotel_compiler.hybrid_nlp import NLPDiagnostic
from hotel_compiler.neural_training import select_gate


def evidence(score=None, status='no_lexical_evidence'):
    return HybridEvidence('', score, 'Unanalyzed' if score is None else 'Positive', 'Unavailable', status,
                          None, None, None, None, None, None, (), False, False, False, ())


def sample():
    text = 'The room was peculiar.'
    r = HybridAspect('Room', 'General', text, 0, len(text), evidence(),
                     aspect_term='room', aspect_start=4, aspect_end=8)
    diagnostic = NLPDiagnostic('NO_LEXICAL_EVIDENCE', 'Unavailable.', 0, len(text))
    return HybridAnalysis('one', 'partial', (r,), evidence(), text, diagnostics=(diagnostic,))


class FakePredictor:
    model_id = 'test-only'
    policy = RecoveryPolicy(.8, .2)

    def __init__(self, probabilities=None):
        self.calls = 0
        self.probabilities = probabilities or {'Positive': .92, 'Negative': .04, 'Objective': .04}

    def predict(self, aspect, context):
        self.calls += 1
        return self.probabilities


class NeuralRecoveryTests(unittest.TestCase):
    def test_threshold_and_objective_abstention(self):
        policy = RecoveryPolicy(.8, .2)
        self.assertTrue(decide({'Positive': .8, 'Negative': .1, 'Objective': .1}, policy)[1])
        self.assertFalse(decide({'Positive': .6, 'Negative': .2, 'Objective': .2}, policy)[1])
        self.assertFalse(decide({'Positive': .01, 'Negative': .01, 'Objective': .98}, policy)[1])
        self.assertFalse(decide({'Positive': .9, 'Negative': .05, 'Objective': .05}, RecoveryPolicy(enabled=False))[1])

    def test_invalid_probabilities_and_thresholds(self):
        for p in [{'Positive': 1}, {'Positive': float('nan'), 'Negative': 0, 'Objective': 0},
                  {'Positive': .8, 'Negative': .8, 'Objective': 0}]:
            with self.assertRaises(ValueError): decide(p, RecoveryPolicy())
        for value in [True, -1, float('nan'), 1.1]:
            with self.assertRaises(ValueError): RecoveryPolicy(value)

    def test_recovery_preserves_original_output_and_diagnostics(self):
        base = sample()
        result = recover_partial(base, FakePredictor())
        self.assertEqual(len(result.recovered), 1)
        self.assertEqual(result.combined_overall, 'Positive')
        self.assertIsNone(base.records[0].score)
        self.assertEqual(base.aspect_analysis_status, 'partial')
        self.assertEqual(result.original_diagnostics, base.diagnostics)
        self.assertEqual(result.recovery_status, 'neural_assisted')

    def test_complete_unsupported_and_errors_not_routed(self):
        for status in ['complete', 'unsupported', 'processing_error']:
            predictor = FakePredictor()
            result = recover_partial(replace(sample(), aspect_analysis_status=status), predictor)
            self.assertEqual(predictor.calls, 0)
            self.assertFalse(result.recovered)

    def test_scope_ambiguity_and_nonlocal_targets_not_routed(self):
        base = sample()
        variants = [replace(base, diagnostics=(NLPDiagnostic('OUT_OF_SCOPE', 'Excluded', 0, 20),)),
                    replace(base, records=(replace(base.records[0], inherited=True),)),
                    replace(base, records=(replace(base.records[0], aspect_start=0),)),
                    replace(base, records=(replace(base.records[0], category='Price'),)),
                    replace(base, records=(replace(base.records[0], evidence=evidence(status='processing_error')),))]
        for variant in variants:
            predictor = FakePredictor()
            self.assertFalse(recover_partial(variant, predictor).recovered)
            self.assertEqual(predictor.calls, 0)

    def test_model_failure_does_not_become_neutral(self):
        predictor = FakePredictor({'Positive': .9})
        result = recover_partial(sample(), predictor)
        self.assertEqual(result.recovery_status, 'model_error')
        self.assertEqual(result.combined_overall, 'Unanalyzed')

    def test_scored_record_is_not_replaced(self):
        base = sample()
        scored = replace(base.records[0], evidence=evidence(.4, 'scored'))
        predictor = FakePredictor()
        result = recover_partial(replace(base, records=(scored,)), predictor)
        self.assertEqual(result.original_scored, 1)
        self.assertEqual(predictor.calls, 0)

    def test_insufficient_validation_evidence_disables_recovery(self):
        policy, _ = select_gate([2], [[.01, .01, .98]])
        self.assertFalse(policy.enabled)
        policy, summary = select_gate([2]*40, [[.01, .01, .98]]*40)
        self.assertTrue(policy.enabled)
        self.assertEqual(summary['accepted'], 40)
        self.assertEqual(summary['precision'], 1)
        policy, _ = select_gate([0]*40, [[.01, .01, .98]]*40)
        self.assertFalse(policy.enabled)

    def test_recovered_polarity_does_not_erase_opposing_lexical_opinion(self):
        base = sample()
        negative = replace(base.records[0], evidence=replace(evidence(-.4, 'scored'), polarity='Negative'))
        augmented = recover_partial(replace(base, records=(base.records[0], negative)), FakePredictor())
        self.assertEqual(augmented.combined_overall, 'Mixed')


class WebisPreparationTests(unittest.TestCase):
    def record(self):
        return {'text': 'The room was nice.',
                'attributes': {'de.webis.attribute.Hotel': {'id': 1}},
                'annotations': {'de.webis.annotation.Aspect': [{'begin': 4, 'end': 8}],
                                'de.webis.annotation.Statement': [{'begin': 0, 'end': 18, 'polarity': 'POSITIVE'}]}}

    def test_original_substrings_and_human_label(self):
        r = self.record()
        rows, excluded = extract_statements(r, 'one.json')
        self.assertFalse(excluded)
        self.assertEqual(rows[0]['text'], r['text'])
        self.assertEqual(rows[0]['aspect'], 'room')
        self.assertEqual(rows[0]['label'], 'Positive')
        r['annotations']['de.webis.annotation.Statement'][0]['polarity'] = 'OBJECTIVE'
        self.assertEqual(extract_statements(r, 'one.json')[0][0]['label'], 'Objective')

    def test_multi_target_and_invalid_spans_excluded(self):
        r = self.record()
        r['annotations']['de.webis.annotation.Aspect'].append({'begin': 13, 'end': 17})
        rows, excluded = extract_statements(r, 'one.json')
        self.assertFalse(rows)
        self.assertEqual(excluded[0]['reason'], 'multiple_aspects')
        r['annotations']['de.webis.annotation.Statement'][0]['end'] = 999
        self.assertEqual(extract_statements(r, 'one.json')[1][0]['reason'], 'invalid_statement_offsets')

    def test_duplicates_do_not_leak_or_choose_conflicting_labels(self):
        rows, _ = extract_statements(self.record(), 'one.json')
        other = dict(rows[0], label='Negative', source_file='two.json')
        self.assertFalse(deduplicate(rows + [other])[0])
        self.assertEqual(len(deduplicate(rows + rows)[0]), 1)
        self.assertEqual(hotel_split('hotel'), hotel_split('hotel'))


if __name__ == '__main__': unittest.main()
