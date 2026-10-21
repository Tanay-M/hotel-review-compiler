"""Authored development contracts, not independent real-world accuracy labels."""
import csv
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from hotel_compiler.hybrid import HybridEngine, analyze_hybrid_review
from hotel_compiler.hybrid_nlp import prepare_text
from hotel_compiler.research_runner import compare_csv

EXTRAS=all(importlib.util.find_spec(p) for p in ('textblob','vaderSentiment','matplotlib'))


@unittest.skipUnless(EXTRAS,'Install research extras.')
class IndependentHybridTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.engine=HybridEngine()

    def analyze(self,text):
        return analyze_hybrid_review(text,engine=self.engine)

    def assert_category(self,text,category,polarity):
        result=self.analyze(text)
        actual=[r for r in result.records if r.category==category]
        self.assertTrue(actual,(text,result.diagnostics))
        self.assertTrue(all(r.polarity==polarity for r in actual),[(r.opinion_expression,r.score) for r in actual])
        return result

    def test_no_baseline_lexer_parser_semantics_or_scorer_is_called(self):
        with (patch('hotel_compiler.front_end.compile_frontend',side_effect=AssertionError('baseline frontend')),
             patch('hotel_compiler.lexer.tokenize',side_effect=AssertionError('baseline lexer')),
             patch('hotel_compiler.parser.parse',side_effect=AssertionError('baseline parser')),
             patch('hotel_compiler.semantics.analyze_semantics',side_effect=AssertionError('baseline semantics')),
             patch('hotel_compiler.pipeline.analyze_review',side_effect=AssertionError('baseline scorer'))):
            self.assert_category('The staff were impeccable.','Staff','Positive')

    def test_unseen_baseline_adjectives_are_not_an_admission_gate(self):
        for word in ['impeccable','phenomenal','superb','exemplary']:
            with self.subTest(word=word):
                result=self.analyze(f'The staff were {word}.')
                self.assertEqual(len(result.records),1)
                self.assertEqual(result.records[0].category,'Staff')
                self.assertGreater(result.records[0].score,0)
                if word=='exemplary':
                    self.assertIsNotNone(result.records[0].evidence.vocabulary_normalization)

    def test_textblob_pos_np_chunks_and_original_spans_are_exposed(self):
        text='The helpful front desk staff welcomed us.'
        result=self.analyze(text)
        self.assertTrue(result.language.noun_phrases)
        self.assertTrue(any(t.pos.startswith('JJ') for t in result.language.tokens))
        self.assertTrue(any(t.chunk.endswith('NP') for t in result.language.tokens))
        for phrase in result.language.noun_phrases:
            self.assertEqual(text[phrase['start']:phrase['end']],phrase['text'])
        for record in result.records:
            self.assertEqual(text[record.start:record.end],record.opinion_expression)
            self.assertEqual(text[record.aspect_start:record.aspect_end],record.aspect_term)

    def test_contrasting_aspects_do_not_share_polarities(self):
        result=self.analyze('The room was wonderful, but the staff were rude!')
        self.assertEqual({(r.category,r.polarity) for r in result.records},{('Room','Positive'),('Staff','Negative')})
        self.assertEqual(result.overall,'Mixed')

    def test_attributive_and_verb_object_patterns(self):
        self.assert_category('Wonderful breakfast and rude staff.','Food','Positive')
        self.assert_category('Wonderful breakfast and rude staff.','Staff','Negative')
        result=self.analyze('I loved the breakfast and hated the room.')
        self.assertEqual([(r.category,r.polarity) for r in result.records],[('Food','Positive'),('Room','Negative')])
        self.assertTrue(all(r.grammar_pattern=='opinion_verb_object' for r in result.records))

    def test_coordinated_subjects_share_the_trailing_opinion(self):
        result=self.analyze('The food and service were excellent.')
        self.assertEqual({(r.category,r.polarity) for r in result.records},{('Food','Positive'),('Service','Positive')})

    def test_repeated_predicate_inherits_subject_inside_sentence(self):
        result=self.analyze('The room was clean and spacious.')
        self.assertEqual(len(result.records),2)
        self.assertEqual(result.records[1].category,'Room')
        self.assertTrue(result.records[1].inherited)
        self.assertGreater(result.aspect_mean_score,0)

    def test_pronoun_resolution_is_limited_to_one_previous_target(self):
        result=self.analyze('The room was spacious. It was clean.')
        self.assertEqual(len(result.records),2)
        self.assertTrue(result.records[1].inherited)
        ambiguous=self.analyze('The food and service were excellent. It was awful.')
        self.assertTrue(any(d.code=='UNRESOLVED_CLAUSE' for d in ambiguous.diagnostics))

    def test_working_negation_and_curly_contractions(self):
        for text in ["The air conditioning wasn't working.",'The air conditioning wasn’t working.',
                     'The Wi-Fi did not work.','The heater cannot work.']:
            with self.subTest(text=text):
                result=self.assert_category(text,'Facilities','Negative')
                self.assertEqual(result.records[0].evidence.domain_rule_id,'equipment_not_functioning')

    def test_domain_negation_is_applied_once(self):
        self.assert_category('The room was not quiet.','Room','Negative')
        self.assert_category('The room was quiet.','Room','Positive')
        self.assert_category('The air conditioning was not broken.','Facilities','Positive')
        self.assert_category('The room had no bedbugs.','Room','Positive')

    def test_missing_facility_and_contextual_comfort(self):
        self.assert_category('No hot water.','Facilities','Negative')
        self.assert_category('A comfy bed.','Room','Positive')
        self.assert_category('The bathroom was spotless.','Room','Positive')

    def test_casing_punctuation_and_emoji_reach_vader(self):
        plain=self.analyze('The staff were good.')
        emphatic=self.analyze('The staff were GOOD!!! :)')
        self.assertGreater(emphatic.whole_text.vader_compound,plain.whole_text.vader_compound)
        self.assertIn('GOOD',emphatic.records[0].evidence.text)
        self.assertIn('!!!',emphatic.records[0].evidence.text)

    def test_unknown_predicate_is_not_a_fabricated_neutral_score(self):
        result=self.analyze('The room was glorp but the staff were helpful.')
        self.assertEqual(result.aspect_analysis_status,'partial')
        self.assertIsNone(result.aspect_mean_score)
        self.assertIsNone(result.records[0].score)
        self.assertGreater(result.records[1].score,0)

    def test_location_stays_out_of_the_six_category_extraction(self):
        result=self.analyze('The location was wonderful.')
        self.assertEqual(result.records,())
        self.assertGreater(result.whole_text.score,0)
        self.assertEqual(result.aspect_analysis_status,'unsupported')

    def test_price_opinion_does_not_become_room_quality_sentiment(self):
        result=self.analyze('The room was expensive but comfortable.')
        self.assertEqual(len(result.records),1)
        self.assertEqual(result.records[0].category,'Room')
        self.assertGreater(result.records[0].score,0)
        self.assertEqual(result.aspect_analysis_status,'partial')

    def test_adjective_safe_is_not_misread_as_the_safe_facility(self):
        result=self.assert_category('The room was safe.','Room','Positive')
        self.assertEqual(len(result.records),1)

    def test_parser_failure_is_visible_and_keeps_whole_text_evidence(self):
        with patch.object(self.engine.parser,'parse',side_effect=RuntimeError('test failure')):
            result=self.analyze('The room was good.')
        self.assertEqual(result.aspect_analysis_status,'processing_error')
        self.assertGreater(result.whole_text.score,0)
        self.assertEqual(result.diagnostics[0].code,'LANGUAGE_PROCESSING_ERROR')

    def test_expanded_contraction_keeps_original_source_mapping(self):
        text="It wasn't good!"
        working,offsets=prepare_text(text)
        self.assertEqual(working,'It was not good!')
        start=working.index('not');a,b=offsets[start]
        self.assertEqual(text[a:b],"wasn't")

    def test_fusion_retains_original_components_and_domain_rule(self):
        record=self.analyze('The room was quiet.').records[0]
        self.assertEqual(record.score,.45)
        self.assertEqual(record.evidence.fusion_rule,'contextual_domain_rule')
        self.assertEqual(record.evidence.domain_rule_id,'room_quiet')
        self.assertIsNotNone(record.evidence.textblob_polarity)
        self.assertIsNotNone(record.evidence.lexical_fusion_score)

    def test_input_validation_and_empty_input(self):
        self.assertEqual(self.analyze('').aspect_analysis_status,'unsupported')
        for text in [None,42]:
            with self.assertRaises(TypeError):self.analyze(text)
        with self.assertRaises(ValueError):self.analyze('a'*10001)
        with self.assertRaises(ValueError):analyze_hybrid_review('good',review_id=' ',engine=self.engine)

    def test_exports_keep_both_independent_opinion_sets_and_grammar_trace(self):
        with TemporaryDirectory() as folder:
            root=Path(folder);source=root/'input.csv';out=root/'out';out.mkdir()
            source.write_text('sr.no,review\n1,The staff were impeccable.\n2,The location was good.\n',encoding='utf-8')
            rows=compare_csv(source,out,self.engine,'authored_development',repeats=0)
            self.assertEqual(rows[0]['extracted_aspects'],0)
            self.assertEqual(rows[0]['hybrid_extracted_aspects'],1)
            with (out/'opinion_results.csv').open(encoding='utf-8-sig',newline='') as handle:opinions=list(csv.DictReader(handle))
            self.assertEqual(len(opinions),1)
            self.assertEqual(opinions[0]['system'],'VADER-TextBlob hybrid')
            for name in ['hybrid_tokens.csv','hybrid_noun_phrases.csv','hybrid_segments.csv']:
                self.assertGreater((out/name).stat().st_size,0)


if __name__=='__main__':unittest.main()
