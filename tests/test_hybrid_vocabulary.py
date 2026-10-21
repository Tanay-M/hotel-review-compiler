"""Vocabulary expansion contracts; authored examples are not accuracy labels."""
import csv
from dataclasses import asdict
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from hotel_compiler.hybrid import HybridDependencyError, HybridEngine, analyze_hybrid_review
from scripts.audit_booking_vocabulary import read_source, prepare


class BookingPreparationTests(unittest.TestCase):
    def test_original_fields_missing_markers_and_metadata_separation(self):
        with TemporaryDirectory() as folder:
            source = Path(folder) / 'original.csv'
            with source.open('w', encoding='utf-8-sig', newline='') as f:
                w = csv.writer(f)
                w.writerow(['positive_review_text', 'negative_review_text', 'review_title', 'rating', 'uniq_id'])
                w.writerow(['Helpful owner, great service.\nOriginal line.', r'\N', 'Terrible', '1', 'id1'])
                w.writerow([r'\N', r'\N', 'Exceptional', '10', 'id2'])
                w.writerow(['Nothing', ' No complaints. ', 'Superb', '9', 'id3'])
            rows = read_source(source)
            self.assertEqual(rows[0]['review'], 'Helpful owner, great service.\nOriginal line.')
            self.assertEqual(rows[1]['review'], '')
            self.assertEqual(rows[2]['review'], 'Nothing\n No complaints. ')
            root = Path(folder) / 'out'
            prepare(source, root, rows)
            with (root / 'inputs/booking_italy_all.csv').open(encoding='utf-8-sig', newline='') as f:
                exported = list(csv.DictReader(f))
            self.assertEqual([r['review'] for r in exported], [r['review'] for r in rows])
            self.assertEqual(list(exported[0]), ['sr.no', 'review'])
            self.assertEqual((root / 'inputs/original_crawlfeeds.csv').read_bytes(), source.read_bytes())

    def test_ui_parts_retain_all_source_ordinals_and_blanks(self):
        with TemporaryDirectory() as folder:
            source = Path(folder) / 'original.csv'
            source.write_text('positive_review_text,negative_review_text\n' + 'Good room,\\N\n' * 1001, encoding='utf-8')
            rows = read_source(source); root = Path(folder) / 'out'; prepare(source, root, rows)
            parts = sorted((root / 'inputs').glob('booking_italy_part_*.csv'))
            sizes = []
            for part in parts:
                with part.open(encoding='utf-8-sig', newline='') as f: sizes.append(len(list(csv.DictReader(f))))
            self.assertEqual(sizes, [1000, 1])
            prepare(source, root, rows)  # Identical rerun verifies the source.
            source.write_text('changed', encoding='utf-8')
            with self.assertRaises(ValueError): prepare(source, root, rows)


class HybridVocabularyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try: cls.engine = HybridEngine()
        except HybridDependencyError as error: raise unittest.SkipTest(str(error))

    def analyze(self, text): return analyze_hybrid_review(text, engine=self.engine)

    def test_recurring_real_vocabulary_gaps_receive_native_canonical_evidence(self):
        for text, category in [
            ('The staff were friendly and polite.', 'Staff'),
            ('The Wi-Fi was fast and reliable.', 'Facilities'),
            ('The owner was knowledgeable and accommodating.', 'Staff'),
            ('The kitchen was well-equipped.', 'Food'),
            ('The breakfast was tasty and plentiful.', 'Food'),
            ('The communication was informative.', 'Service'),
        ]:
            with self.subTest(text=text):
                result = self.analyze(text)
                self.assertEqual(result.aspect_analysis_status, 'complete')
                self.assertTrue(result.records)
                self.assertTrue(all(r.category == category and r.score > 0 for r in result.records))
                self.assertTrue(any(r.evidence.vocabulary_normalization for r in result.records))

    def test_original_native_evidence_and_source_spans_are_preserved(self):
        text = 'The owner wasn’t very polite.'
        record = self.analyze(text).records[0]
        self.assertLess(record.score, 0)
        self.assertEqual(text[record.start:record.end], record.opinion_expression)
        self.assertEqual(text[record.aspect_start:record.aspect_end], record.aspect_term)
        normal = record.evidence.vocabulary_normalization
        original = normal['original_evidence']
        self.assertEqual(original, asdict(self.engine._score_native(record.opinion_expression)))
        self.assertEqual(original['vader_compound'], 0)
        self.assertIn('courteous', normal['scoring_text'])
        for m in normal['matches']:
            self.assertEqual(record.opinion_expression[m['start']:m['end']], m['original'])
        self.assertIsNone(self.engine._score_native('polite').score)

    def test_category_guards_unknown_words_facts_and_out_of_scope_stay_visible(self):
        self.assertIsNone(self.engine.score_aspect('The room was polite.', 'Room').score)
        self.assertIsNone(self.engine.score_text('polite').score)  # No category supplied.
        for text in ['The room was glorp.', 'The room has two chairs.']:
            result = self.analyze(text)
            self.assertFalse(any(r.score is not None for r in result.records))
        for text in ['The location was wonderful.', 'The water taxi was convenient.']:
            self.assertEqual(self.analyze(text).records, ())

    def test_new_aspect_nouns_do_not_capture_comparative_adjectives(self):
        cleaner = self.analyze('The cleaner was helpful.')
        self.assertEqual([r.category for r in cleaner.records], ['Staff'])
        room = self.analyze('The room was cleaner.')
        self.assertEqual([r.category for r in room.records], ['Room'])
        self.assertGreater(room.records[0].score, 0)

    def test_existing_domain_rules_and_fusion_weights_are_retained(self):
        for text, score in [('The room was spacious.', .5), ('The room was quiet.', .45),
                            ('The air conditioning was not working.', -.7)]:
            self.assertEqual(self.analyze(text).records[0].score, score)
        e = self.engine.score_aspect('The staff were polite.', 'Staff')
        self.assertEqual(self.engine.policy.vader_weight, .5)
        self.assertEqual(e.lexical_fusion_score, round((e.vader_compound + e.textblob_polarity) / 2, 6))

    def test_normalization_does_not_hide_component_failures(self):
        with patch.object(self.engine.textblob, 'analyze', side_effect=RuntimeError('component failure')):
            evidence = self.engine.score_aspect('The staff were polite.', 'Staff')
        self.assertEqual(evidence.status, 'processing_error')
        self.assertIsNone(evidence.score)
        self.assertIsNone(evidence.vocabulary_normalization)


if __name__ == '__main__': unittest.main()
