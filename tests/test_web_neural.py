"""HTTP recovery contracts with a fake model; these are not accuracy tests."""
import csv
import http.client
from io import BytesIO, StringIO
import json
from threading import Thread
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from hotel_compiler.hybrid import HybridDependencyError, default_engine
from hotel_compiler.neural_fallback import RecoveryPolicy
from hotel_compiler.web import create_server
from hotel_compiler.web_neural import NeuralDependencyError


class FakePredictor:
    model_id = 'software-test-only'
    policy = RecoveryPolicy(.8, .2)

    def __init__(self): self.calls = 0

    def predict(self, aspect, context):
        self.calls += 1
        return {'Negative': .95, 'Objective': .03, 'Positive': .02}


class NeuralWebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try: default_engine()
        except HybridDependencyError as error: raise unittest.SkipTest(str(error))
        cls.server = create_server(port=0)
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(5)

    def request(self, method, path, payload=None, content_type='application/json'):
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=30)
        try:
            conn.request(method, path, payload, {'Content-Type': content_type})
            response = conn.getresponse()
            return response.status, response.read()
        finally: conn.close()

    def analyze(self, text):
        return self.request('POST', '/api/analyze', json.dumps({'text': text, 'method': 'hybrid_neural'}))

    def upload(self, payload, method='hybrid_neural'):
        return self.request('POST', '/api/batches?text_column=review&id_column=sr.no&method='+method, payload, 'text/csv')

    def test_neural_additions_do_not_replace_lexical_output_or_status(self):
        with patch('hotel_compiler.web_neural.get_neural_predictor', return_value=FakePredictor()):
            status, body = self.analyze('The room was glorp but the staff were helpful.')
        result = json.loads(body)
        self.assertEqual(status, 200, body)
        self.assertEqual(result['method'], 'hybrid_neural')
        self.assertEqual(result['status'], 'partial')
        self.assertIsNone(result['review_score'])
        self.assertIsNone(result['records'][0]['score'])
        n = result['neural_recovery']
        self.assertEqual(n['recovery_status'], 'neural_assisted')
        self.assertEqual(n['combined_overall'], 'Mixed')
        self.assertEqual(len(n['recovered']), 1)
        self.assertEqual(n['original_diagnostics'], result['diagnostics'])
        self.assertEqual(len(result['trace']['sentiment_evaluation']), len(result['records']))

    def test_complete_and_unsupported_contexts_never_predicted(self):
        predictor = FakePredictor()
        with patch('hotel_compiler.web_neural.get_neural_predictor', return_value=predictor):
            for text in ('The staff were helpful.', 'The location was wonderful.'):
                status, body = self.analyze(text)
                self.assertEqual(status, 200)
                self.assertFalse(json.loads(body)['neural_recovery']['recovered'])
        self.assertEqual(predictor.calls, 0)

    def test_batch_summary_details_and_downloads_preserve_all_rows(self):
        source = b'sr.no,review\nsame,The room was glorp but the staff were helpful.\nsame,The room was glorp but the staff were helpful.\n3,\n'
        predictor = FakePredictor()
        with patch('hotel_compiler.web_neural.get_neural_predictor', return_value=predictor):
            status, body = self.upload(source)
        self.assertEqual(status, 200, body)
        batch = json.loads(body)
        self.assertEqual(len(batch['rows']), 3)
        self.assertEqual(batch['rows'][2]['execution_status'], 'invalid_input')
        self.assertEqual(batch['neural_summary']['added_opinions'], 2)
        self.assertEqual(batch['neural_summary']['assisted_reviews'], 2)
        self.assertEqual(batch['summary']['counts']['partial'], 2)
        self.assertEqual(batch['summary']['counts']['complete'], 0)
        calls = predictor.calls
        status, body = self.request('GET', f"/api/batches/{batch['batch_id']}/reviews/2")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)['analysis']['neural_recovery']['recovered'][0]['model_label'], 'Negative')
        self.assertEqual(predictor.calls, calls)
        status, body = self.request('GET', f"/api/batches/{batch['batch_id']}/download/reviews")
        rows = list(csv.DictReader(StringIO(body.decode('utf-8-sig'))))
        self.assertEqual(len(rows), 3)
        self.assertEqual(len({r['row_id'] for r in rows}), 3)
        self.assertEqual(rows[0]['analysis_status'], 'partial')
        self.assertEqual(rows[0]['review_score'], '')
        self.assertEqual(rows[0]['neural_added_opinions'], '1')
        self.assertEqual(rows[2]['neural_recovery_status'], 'not_analyzed')
        status, body = self.request('GET', f"/api/batches/{batch['batch_id']}/download/paper")
        self.assertEqual(status, 200)
        with ZipFile(BytesIO(body)) as zipped:
            self.assertIn('hybrid_evidence.csv', zipped.namelist())
            self.assertIn('neural_decisions.csv', zipped.namelist())
            ledger = list(csv.DictReader(StringIO(zipped.read('neural_decisions.csv').decode('utf-8-sig'))))
            self.assertEqual(len(ledger), 2)
            self.assertEqual(len({r['row_id'] for r in ledger}), 2)

    def test_missing_model_is_visible_and_does_not_replace_prior_batch(self):
        source = b'sr.no,review\n1,The staff were helpful.\n'
        old = json.loads(self.upload(source, 'hybrid')[1])
        with patch('hotel_compiler.web_neural.get_neural_predictor', side_effect=NeuralDependencyError('Missing model')):
            self.assertEqual(self.analyze('The room was glorp.')[0], 503)
            self.assertEqual(self.upload(source)[0], 503)
        self.assertEqual(self.request('GET', f"/api/batches/{old['batch_id']}")[0], 200)

    def test_neural_assets_are_local_and_capability_is_exposed(self):
        status, body = self.request('GET', '/neural.js')
        self.assertEqual(status, 200)
        self.assertIn(b'renderNeuralDashboard', body)
        status, body = self.request('GET', '/api/config')
        result = json.loads(body)
        self.assertIn('hybrid_neural', result['methods'])
        self.assertIsInstance(result['neural_recovery']['available'], bool)


if __name__ == '__main__': unittest.main()
