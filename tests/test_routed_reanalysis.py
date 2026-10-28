"""Independent routing/data contracts. Fake predictions are not accuracy evidence."""
import csv
import http.client
from io import BytesIO, StringIO
import json
from threading import Thread
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from hotel_compiler.routed_data import HEADS, STATES, mapped_labels, surface_text
from hotel_compiler.routed_model import decode_heads, reanalyze_review, sentence_spans
from hotel_compiler.routed_training import choose_thresholds, metrics
from hotel_compiler.hybrid import HybridDependencyError, default_engine
from hotel_compiler.web import create_server


def distribution(label='Absent'):
    return {s: .94 if s == label else .02 for s in STATES}


class FakeModel:
    model_id = 'contract-test-only'
    thresholds = {c: .5 for c in HEADS}
    def __init__(self): self.calls = []
    def predict_many(self, texts):
        self.calls.extend(texts)
        values = []
        for text in texts:
            p = {c: distribution() for c in HEADS}
            p['Service'] = distribution('Negative')
            values.append(p)
        return values


class RoutedContracts(unittest.TestCase):
    def test_source_label_mapping_preserves_implicit_and_ambiguous_labels(self):
        self.assertEqual(mapped_labels({'SERVICE':'in', 'LOCATION':'ip'}), {'Service':'Negative','Excluded':'Positive'})
        self.assertEqual(mapped_labels({'SERVICE':'n','CHECKIN':'p'}), {'Service':'Neutral/Mixed'})
        self.assertEqual(mapped_labels({'ROOMS':'ix'}), {'Room':'Neutral/Mixed'})
        with self.assertRaises(ValueError): mapped_labels({'ROOMS':'neutral'})

    def test_source_token_reconstruction_is_documented_not_generated(self):
        self.assertEqual(surface_text('The//The room/n/room was/v/be nice/a/nice .//.'), 'The room was nice.')
        with self.assertRaises(ValueError): surface_text('unserialized')

    def test_original_sentence_spans_unicode_and_newlines(self):
        text = '  Café was nice.\nWe waited two hours!  '
        spans = list(sentence_spans(text))
        self.assertEqual([text[s:e] for s,e in spans], ['Café was nice.', 'We waited two hours!'])

    def test_partial_and_unsupported_process_all_text_without_hybrid_records(self):
        for status in ('partial','unsupported'):
            model = FakeModel()
            text = 'An excellent arrival. We waited two hours.'
            result = reanalyze_review(text,status,model)
            self.assertEqual(model.calls, ['An excellent arrival.','We waited two hours.'])
            self.assertEqual(result.selected_method,'independent_neural')
            self.assertEqual(result.route_status,'reanalyzed')
            self.assertTrue(all(r['category']=='Service' for r in result.records))
            self.assertTrue(all(text[r['start']:r['end']]==r['context'] for r in result.records))
            self.assertLess(result.review_index,0)

    def test_complete_and_processing_error_do_not_route(self):
        for status in ('complete','processing_error','invalid_input'):
            model = FakeModel(); result= reanalyze_review('Anything.',status,model)
            self.assertFalse(model.calls)
            self.assertEqual(result.selected_method,'hybrid')

    def test_neutral_mixed_does_not_get_fake_neutral_score_or_strength(self):
        model=FakeModel()
        def predict(texts):
            p={c:distribution() for c in HEADS};p['Room']=distribution('Neutral/Mixed');return [p]
        model.predict_many=predict
        result=reanalyze_review('The room had contrasting feedback.','partial',model)
        self.assertEqual(result.overall,'Mixed/uncertain')
        self.assertIsNone(result.review_index)
        self.assertNotIn('strength', result.records[0])

    def test_out_of_scope_is_not_relabelled_room(self):
        model=FakeModel()
        def predict(texts):
            p={c:distribution() for c in HEADS};p['Excluded']=distribution('Positive');return [p]
        model.predict_many=predict
        result=reanalyze_review('The location was lovely.','unsupported',model)
        self.assertEqual(result.route_status,'abstained')
        self.assertFalse(result.records)

    def test_prediction_failure_stays_model_error(self):
        model=FakeModel(); model.predict_many=lambda texts: (_ for _ in ()).throw(RuntimeError('failed'))
        result=reanalyze_review('Anything.','partial',model)
        self.assertEqual(result.route_status,'model_error')
        self.assertEqual(result.overall,'Unanalyzed')
        self.assertIsNone(result.review_index)

    def test_length_abstention_keeps_missing_sentence_visible(self):
        model=FakeModel();model.predict_many=lambda texts:[None]*len(texts)
        result=reanalyze_review('Long sentence.','partial',model)
        self.assertEqual(result.route_status,'abstained')
        self.assertEqual(result.warnings[0]['code'],'NEURAL_LENGTH_LIMIT')

    def test_metrics_penalize_false_positives_on_background(self):
        result=metrics([{('Room','Positive')},set()],[{('Room','Positive')},{('Room','Positive')}])
        self.assertEqual(result['precision'],.5)
        self.assertEqual(result['recall'],1)
        self.assertAlmostEqual(result['pair_micro_f1'],2/3)

    def test_thresholds_do_not_learn_from_absent_test_argument(self):
        values=[{c: distribution('Positive') if c=='Room' else distribution() for c in HEADS}]
        selected=choose_thresholds([{'Room':'Positive'}],values)
        self.assertEqual(len(selected),len(HEADS))
        decoded=decode_heads(values[0],selected)
        self.assertTrue(next(d for d in decoded if d['category']=='Room')['accepted'])
        values[0]['Room']['Absent']=True
        with self.assertRaises(ValueError): decode_heads(values[0],selected)


class RoutedHTTPContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try: default_engine()
        except HybridDependencyError as e: raise unittest.SkipTest(str(e))
        cls.server=create_server(port=0);cls.thread=Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join(5)
    def request(self,method,path,body=None,content_type='application/json'):
        c=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=30)
        try:
            c.request(method,path,body,{'Content-Type':content_type});r=c.getresponse();return r.status,r.read()
        finally:c.close()

    def test_separate_analysis_is_not_an_append_to_existing_opinions(self):
        model=FakeModel()
        with patch('hotel_compiler.web_routed.get_model',return_value=model):
            status,body=self.request('POST','/api/analyze',json.dumps({'method':'hybrid_routed','text':'The room was glorp but the staff were helpful.'}))
        self.assertEqual(status,200,body);r=json.loads(body)
        self.assertEqual(r['status'],'partial')
        self.assertIsNone(r['records'][0]['score'])
        self.assertEqual(r['overall'],'Positive')
        self.assertEqual(r['routed_analysis']['overall'],'Negative')
        self.assertEqual(r['routed_analysis']['selected_method'],'independent_neural')
        self.assertNotIn('neural_recovery',r)

    def test_csv_exports_and_retained_detail_have_independent_results(self):
        payload=b'sr.no,review\n1,We waited two hours.\n2,The staff were helpful.\n3,\n'
        with patch('hotel_compiler.web_routed.get_model',return_value=FakeModel()):
            status,body=self.request('POST','/api/batches?method=hybrid_routed&text_column=review&id_column=sr.no',payload,'text/csv')
        self.assertEqual(status,200,body);batch=json.loads(body)
        self.assertEqual(len(batch['rows']),3)
        self.assertEqual(batch['routed_summary']['routed_reviews'],1)
        self.assertEqual(batch['routed_summary']['retained_hybrid'],1)
        url=f"/api/batches/{batch['batch_id']}"
        status,body=self.request('GET',url+'/reviews/1')
        self.assertEqual(json.loads(body)['analysis']['routed_analysis']['categories'][0]['category'],'Service')
        status,body=self.request('GET',url+'/download/reviews')
        rows=list(csv.DictReader(StringIO(body.decode('utf-8-sig'))))
        self.assertEqual(rows[0]['selected_method'],'independent_neural')
        self.assertEqual(rows[1]['selected_method'],'hybrid')
        self.assertEqual(rows[2]['selected_method'],'invalid_input')
        status,body=self.request('GET',url+'/download/paper')
        with ZipFile(BytesIO(body)) as zipped:
            self.assertIn('independent_neural_decisions.csv',zipped.namelist())
            self.assertIn('hybrid_evidence.csv',zipped.namelist())


if __name__=='__main__':unittest.main()
