"""Language breadth, original-score provenance, and conservative recovery."""
import csv
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
import unittest

from hotel_compiler import analyze_review
from hotel_compiler.batch import analyze_batch
from hotel_compiler.csv_input import read_review_csv
from hotel_compiler.sentiwordnet import load_synsets
from hotel_compiler.vocabulary import load_vocabulary

ROOT = Path(__file__).resolve().parents[1]


class VocabularyExpansionTests(unittest.TestCase):
    def assert_pairs(self, text, expected, status='complete'):
        result = analyze_review(text)
        self.assertEqual(result.status, status, result.diagnostics)
        self.assertEqual([(r.aspect_term,r.opinion_term,r.polarity) for r in result.records],expected)
        for token in result.tokens:
            self.assertEqual(text[token.start:token.end],token.text)
        for record in result.records:
            self.assertTrue(0 <= record.start < record.end <= len(text))
        return result

    def test_wide_vocabulary_preserves_six_categories(self):
        v=load_vocabulary()
        self.assertEqual(v['categories'],['Room','Staff','Service','Food','Cleanliness','Facilities'])
        self.assertGreaterEqual(len(v['opinions']),300)
        self.assertGreaterEqual(len(v['aspects']),300)
        self.assertGreaterEqual(len(load_synsets()),250)
        self.assertNotIn('location',v['aspects'])
        self.assertNotIn('price',v['aspects'])

    def test_every_canonical_opinion_parses_with_original_sentiwordnet_evidence(self):
        v=load_vocabulary(); senses=load_synsets()
        subjects={'Room':'room','Staff':'staff','Service':'service','Food':'food','Cleanliness':'cleanliness','Facilities':'ac'}
        for word,spec in v['opinions'].items():
            aspect=next(iter(spec.get('allowed_aspects',[])), subjects[spec.get('allowed_categories',v['categories'])[0]])
            with self.subTest(word=word,aspect=aspect):
                result=analyze_review(f'The {aspect} was {word}.')
                self.assertEqual(result.status,'complete',result.diagnostics)
                self.assertEqual(len(result.records),1)
                record=result.records[0]
                sense=senses[record.evidence.synset]
                self.assertEqual((record.evidence.positive_score,record.evidence.negative_score),(sense.positive,sense.negative))
                self.assertAlmostEqual(record.evidence.lexical_score,sense.positive-sense.negative)
                self.assertEqual(record.opinion_term,word)
                self.assertTrue(record.evidence.sense_selection)

    def test_all_canonical_adjectives_negate_once_without_changing_source_scores(self):
        v=load_vocabulary()
        subjects={'Room':'room','Staff':'staff','Service':'service','Food':'food','Cleanliness':'cleanliness','Facilities':'ac'}
        for word,spec in v['opinions'].items():
            aspect=next(iter(spec.get('allowed_aspects',[])),subjects[spec.get('allowed_categories',v['categories'])[0]])
            with self.subTest(word=word):
                positive=analyze_review(f'The {aspect} was {word}.').records[0]
                negative=analyze_review(f'The {aspect} was not {word}.').records[0]
                self.assertEqual(negative.score,-positive.score)
                self.assertEqual(negative.evidence.negation_multiplier,-1)
                self.assertEqual(negative.evidence.positive_score,positive.evidence.positive_score)
                self.assertEqual(negative.evidence.negative_score,positive.evidence.negative_score)

    def test_coordination_applies_all_predicates_to_all_subjects(self):
        result=self.assert_pairs('The room and bathroom were clean and spacious.',[
            ('room','clean','Positive'),('room','spacious','Positive'),
            ('bathroom','clean','Positive'),('bathroom','spacious','Positive')])
        self.assertTrue(all(c.form=='coordinated_subjects' for c in result.ast.clauses))
        self.assert_pairs('The room, bathroom and sheets were not clean.',[
            ('room','clean','Negative'),('bathroom','clean','Negative'),('sheets','clean','Negative')])

    def test_coordination_does_not_extend_to_a_new_explicit_subject(self):
        self.assert_pairs('The room and bathroom were clean but the staff were rude.',[
            ('room','clean','Positive'),('bathroom','clean','Positive'),('staff','rude','Negative')])

    def test_prenominal_lists_attach_each_adjective_to_the_named_aspect(self):
        for text in ('A clean and quiet room.','A clean, quiet room.','A clean quiet room.'):
            self.assert_pairs(text,[('room','clean','Positive'),('room','quiet','Positive')])
        result=self.assert_pairs('A very clean and quiet room.',[('room','clean','Positive'),('room','quiet','Positive')])
        self.assertEqual([r.evidence.intensity_multiplier for r in result.records],[1.25,1.0])

    def test_introduction_and_temporal_context_are_retained_in_the_ast(self):
        text='I found the room very clean when we arrived.'
        result=self.assert_pairs(text,[('room','clean','Positive')])
        self.assertEqual([t.value for t in result.ast.clauses[0].context],['i found','when we arrived'])
        self.assertEqual(result.records[0].opinion_expression,'very clean')
        self.assertEqual(text[result.records[0].start:result.records[0].end],text[:-1])
        self.assert_pairs('Overall, the room was clean during our stay.',[('room','clean','Positive')])

    def test_context_does_not_discard_unknown_words_or_other_opinions(self):
        for text in ('The room was clean when we arrived filthy.',
                     'The room was clean during a horrible stay.',
                     'The room was clean to the rude staff.',
                     'The room was clean when we hated it.'):
            with self.subTest(text=text):
                result=analyze_review(text)
                self.assertNotEqual(result.status,'complete')
                self.assertTrue(result.diagnostics)

    def test_possession_attaches_the_opinion_to_the_contained_aspect(self):
        for text in ('The room had a comfortable bed.','The room with a comfortable bed.'):
            result=self.assert_pairs(text,[('bed','comfortable','Positive')])
            self.assertEqual(result.ast.clauses[0].form,'possessive_opinion_before_aspect')
        self.assert_pairs('The room has clean sheets.',[('sheets','clean','Positive')])
        self.assertNotEqual(analyze_review('The room had comfortable.').status,'complete')

    def test_visitor_feeling_requires_an_explicit_target_and_recognized_feeling(self):
        result=self.assert_pairs('I was very pleased with the service.',[('service','pleased','Positive')])
        self.assertEqual(result.ast.clauses[0].form,'experiencer_opinion_target')
        self.assert_pairs('We were disappointed by the room.',[('room','disappointed','Negative')])
        for text in ('I was cold in my room.','I was pleased.','I was pleased with the weather.'):
            with self.subTest(text=text): self.assertNotEqual(analyze_review(text).status,'complete')

    def test_relation_targets_are_bounded_and_unscored(self):
        result=self.assert_pairs('The parking was convenient to the airport.',[('parking','convenient','Positive')])
        self.assertEqual([t.value for t in result.ast.clauses[0].context],['to','the airport'])
        self.assertNotEqual(analyze_review('The parking was convenient to the rude staff.').status,'complete')

    def test_equipment_failure_alias_keeps_the_original_phrase_and_scope(self):
        result=self.assert_pairs('The air conditioning stopped cooling during the night.',[('air conditioning','malfunctioning','Negative')])
        self.assertEqual(result.records[0].opinion_expression,'stopped cooling')
        self.assertEqual(result.records[0].evidence.synset,'a:01092142')
        self.assertTrue(result.records[0].evidence.normalization_rule)
        self.assert_pairs('The shower was leaking.',[('shower','leaky','Negative')])
        for text in ('The staff stopped cooling.','The TV stopped cooling.','The food was leaking.'):
            self.assertEqual(analyze_review(text).status,'unsupported')

    def test_polysemous_safe_is_a_noun_or_adjective_from_its_position(self):
        self.assert_pairs('The safe was broken.',[('safe','broken','Negative')])
        self.assert_pairs('A broken safe.',[('safe','broken','Negative')])
        result=analyze_review('The room was safe.')
        self.assertEqual(result.records[0].opinion_term,'safe')
        self.assertEqual(result.records[0].aspect_term,'room')

    def test_new_aliases_and_multiword_intensity_preserve_unicode_source_positions(self):
        self.assert_pairs('The A/C was working.',[('a/c','working','Positive')])
        result=self.assert_pairs('The room wasn’t a little clean.',[('room','clean','Negative')])
        self.assertEqual(result.records[0].opinion_expression,'not a little clean')
        self.assertEqual(result.records[0].evidence.intensity_multiplier,.75)
        self.assert_pairs('The bread was undercooked.',[('bread','underdone','Negative')])
        self.assert_pairs('The fridge was well maintained.',[('fridge','maintained','Positive')])

    def test_source_anomalies_and_domain_adjustments_remain_distinct(self):
        for text,p,n,polarity in [('The breakfast was fresh.',.375,.625,'Positive'),
                                 ('The food was stale.',.5,.25,'Negative'),
                                 ('The AC was defective.',.5,0,'Negative'),
                                 ('The service was efficient.',.375,.375,'Positive')]:
            with self.subTest(text=text):
                record=analyze_review(text).records[0]
                self.assertEqual((record.evidence.positive_score,record.evidence.negative_score),(p,n))
                self.assertEqual(record.polarity,polarity)
                self.assertEqual(record.evidence.domain_rule_id,'hotel_attribute_preference')
                self.assertTrue(record.evidence.calibration_reason)

    def test_food_and_linen_freshness_use_different_genuine_senses(self):
        food=analyze_review('The breakfast was fresh.').records[0]
        linen=analyze_review('The sheets were fresh.').records[0]
        self.assertEqual((food.evidence.synset,linen.evidence.synset),('a:01067694','a:00418198'))
        self.assertEqual((linen.evidence.positive_score,linen.evidence.negative_score),(0,.75))
        self.assertEqual(linen.issue,'Cleanliness')
        self.assertEqual(linen.polarity,'Positive')
        self.assertEqual(linen.evidence.domain_rule_id,'fresh_linen_preference')

    def test_bedding_cleanliness_is_not_mislabeled_as_comfort(self):
        record=analyze_review('The bed was dirty.').records[0]
        self.assertEqual((record.category,record.issue,record.polarity),('Room','Cleanliness','Negative'))

    def test_unknown_scope_facts_and_bad_modifier_chains_remain_visible(self):
        for text in ('The location was convenient.','The price was high.',
                     'The staff arranged a taxi for us.','The room was not never clean.',
                     'The staff were very extremely helpful.','The room was glorp.'):
            self.assertEqual(analyze_review(text).status,'unsupported',text)
        result=analyze_review('The location was convenient but the staff were helpful.')
        self.assertEqual(result.status,'partial')
        self.assertEqual(len(result.records),1)

    def test_scoring_manifest_covers_every_opinion_with_original_scores(self):
        rows=list(csv.DictReader(StringIO((ROOT/'hotel_compiler/resources/opinion_senses.csv').read_text(encoding='utf-8-sig'))))
        self.assertEqual({r['opinion'] for r in rows},set(load_vocabulary()['opinions']))
        senses=load_synsets()
        for row in rows:
            self.assertEqual(float(row['source_positive']),senses[row['synset']].positive)
            self.assertEqual(float(row['source_negative']),senses[row['synset']].negative)

    def test_unchanged_100_review_input_reaches_target_without_losing_rows(self):
        path=ROOT/'examples/hotel_reviews_100.csv'
        self.assertEqual(sha256(path.read_bytes()).hexdigest(),'3172b6c07e8265c993fb743fd8b577df4d9f4899906ff9671224ab1e7c9a8e14')
        batch=analyze_batch(read_review_csv(path,text_column='review',id_column='sr.no'))
        self.assertEqual(len(batch.rows),100)
        counts=batch.summary()['counts']
        self.assertGreaterEqual(counts['complete'],80)
        self.assertEqual(counts['complete'],88)
        self.assertEqual(counts['processing_error'],0)
        self.assertEqual(counts['invalid_input'],0)

    def test_demo_notes_are_removed_and_the_input_uses_full_width(self):
        html=(ROOT/'hotel_compiler/web_assets/index.html').read_text(encoding='utf-8')
        css=(ROOT/'hotel_compiler/web_assets/styles.css').read_text(encoding='utf-8')
        self.assertNotIn('DEMO NOTES',html)
        self.assertNotIn('notes-card',html)
        self.assertIn('.workspace{display:grid;grid-template-columns:1fr;',css)


if __name__=='__main__': unittest.main()
