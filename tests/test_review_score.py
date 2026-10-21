"""Review means stay consistent across core, HTTP, CLI and CSV/report outputs."""
import csv
from io import BytesIO, StringIO
import http.client
import json
from math import fsum
from threading import Thread
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from hotel_compiler import analyze_review
from hotel_compiler.aggregation import aggregate_batch
from hotel_compiler.batch import analyze_batch
from hotel_compiler.cli import _report
from hotel_compiler.csv_input import parse_review_csv
from hotel_compiler.exports import batch_csv_bytes
from hotel_compiler.paper_tables import paper_archive
from hotel_compiler.reporting import build_report
from hotel_compiler.web import create_server


MIXED = 'The room was not clean, but the staff were very helpful.'


class ReviewScoreTests(unittest.TestCase):
    def test_mixed_review_mean_preserves_individual_source_scores_and_label(self):
        result = analyze_review(MIXED)
        self.assertEqual(result.review_score, 0.09375)
        self.assertEqual(result.review_score_scope, 'complete review')
        self.assertEqual(result.overall, 'Mixed')
        self.assertEqual([r.score for r in result.records], [-0.125, 0.3125])
        self.assertEqual(result.records[0].evidence.positive_score, 0.5)
        self.assertEqual(result.records[0].evidence.negative_score, 0.375)

    def test_equal_opinion_weights_instead_of_equal_category_weights(self):
        result = analyze_review('The room was clean and quiet but the staff were rude.')
        self.assertEqual(len(result.records), 3)
        expected = round(fsum(r.score for r in result.records) / 3, 6)
        self.assertEqual(result.review_score, expected)
        room_mean = fsum(r.score for r in result.records if r.category == 'Room') / 2
        staff_mean = next(r.score for r in result.records if r.category == 'Staff')
        self.assertNotEqual(result.review_score, round((room_mean + staff_mean) / 2, 6))

    def test_zero_mixed_mean_is_distinct_from_neutral_and_missing_evidence(self):
        mixed = analyze_review('The staff were helpful but the room was not spacious.')
        neutral = analyze_review('The service was average.')
        unsupported = analyze_review('The location was convenient.')
        self.assertEqual((mixed.review_score, mixed.overall), (0.0, 'Mixed'))
        self.assertEqual((neutral.review_score, neutral.overall), (0.0, 'Neutral'))
        self.assertEqual((unsupported.review_score, unsupported.overall), (None, 'Unanalyzed'))

    def test_partial_scope_and_empty_input(self):
        partial = analyze_review('The room was glorp but the staff were helpful.')
        self.assertEqual(partial.status, 'partial')
        self.assertEqual(partial.review_score, 0.25)
        self.assertEqual(partial.review_score_scope, 'recognized opinions only')
        empty = analyze_review(' ')
        self.assertIsNone(empty.review_score)
        self.assertEqual(empty.review_score_scope, 'unavailable')

    def test_single_opinion_and_clipped_extremes(self):
        for text, expected in [('The room was clean.', 0.125),
                               ('The staff were extremely excellent.', 1.0),
                               ('The staff were not extremely excellent.', -1.0)]:
            with self.subTest(text=text):
                result = analyze_review(text)
                self.assertEqual(result.review_score, expected)
                self.assertTrue(-1 <= result.review_score <= 1)

    def test_compact_and_trace_serializations_and_cli_expose_the_same_mean(self):
        result = analyze_review(MIXED, 'score-demo')
        for traced in (False, True):
            payload = result.to_dict(include_trace=traced)
            self.assertEqual(payload['review_score'], result.review_score)
            self.assertEqual(payload['review_score_scope'], 'complete review')
        self.assertIn('Review score: +0.093750 (complete review)', _report(result))
        self.assertIn('Review score: Unavailable (unavailable)', _report(analyze_review(' ')))

    def test_batch_error_rows_export_blank_scores_and_primary_means_stay_category_specific(self):
        source = parse_review_csv(
            ('sr.no,review\n1,"'+MIXED+'"\n2,The room was glorp but the staff were helpful.\n'
             '3,The location was convenient.\n4,\n5,Simulated processing failure.\n').encode(),
            text_column='review', id_column='sr.no',
        )
        def analyze(text, identifier):
            if text == 'Simulated processing failure.':
                raise RuntimeError('simulated failure')
            return analyze_review(text, identifier)
        with patch('hotel_compiler.batch.analyze_review', side_effect=analyze):
            batch = analyze_batch(source, batch_id='score-export')
        rows = list(csv.DictReader(StringIO(batch_csv_bytes(batch).decode('utf-8-sig'))))
        self.assertEqual(len(rows), 5)
        self.assertEqual([r['review_score'] for r in rows], ['0.09375', '0.25', '', '', ''])
        self.assertEqual([r['review_score_scope'] for r in rows],
                         ['complete review', 'recognized opinions only', 'unavailable', 'unavailable', 'unavailable'])
        report = build_report(batch)
        groups = {g['category']: g for g in aggregate_batch(batch)['views']['complete_reviews']['categories']}
        self.assertEqual(groups['Room']['average_score'], -0.125)
        self.assertEqual(groups['Staff']['average_score'], 0.3125)
        with ZipFile(BytesIO(paper_archive(batch, report))) as archive:
            exported = list(csv.DictReader(StringIO(archive.read('reviews.csv').decode('utf-8-sig'))))
            self.assertEqual(exported, rows)
            self.assertIn(b'review_score_method', archive.read('run_metadata.csv'))


class ReviewScoreHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = create_server(port=0)
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def request(self, method, path, data=None, content_type=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        try:
            connection.request(method, path, data, {'Content-Type': content_type} if content_type else {})
            response = connection.getresponse()
            return response.status, response.read()
        finally:
            connection.close()

    def test_single_api_includes_score_and_unavailable_is_null(self):
        for text, expected in [(MIXED, 0.09375), ('The location was convenient.', None)]:
            with self.subTest(text=text):
                status, body = self.request('POST', '/api/analyze', json.dumps({'text': text}), 'application/json')
                self.assertEqual(status, 200)
                result = json.loads(body)
                self.assertEqual(result['review_score'], expected)

    def test_upload_detail_and_download_share_review_score_and_scope(self):
        payload = ('sr.no,review\n1,"'+MIXED+'"\n2,The room was glorp but the staff were helpful.\n3,\n').encode()
        status, body = self.request('POST', '/api/batches?text_column=review&id_column=sr.no', payload, 'text/csv')
        self.assertEqual(status, 200)
        batch = json.loads(body)
        self.assertEqual(batch['rows'][0]['analysis']['review_score'], 0.09375)
        self.assertEqual(batch['rows'][1]['analysis']['review_score_scope'], 'recognized opinions only')
        self.assertIsNone(batch['rows'][2]['analysis'])
        status, body = self.request('GET', f'/api/batches/{batch["batch_id"]}/reviews/1')
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)['analysis']['review_score'], 0.09375)
        status, body = self.request('GET', f'/api/batches/{batch["batch_id"]}/download/reviews')
        self.assertEqual(status, 200)
        rows = list(csv.DictReader(StringIO(body.decode('utf-8-sig'))))
        self.assertEqual(rows[0]['review_score'], '0.09375')
        self.assertEqual(rows[2]['review_score'], '')


if __name__ == '__main__':
    unittest.main()
