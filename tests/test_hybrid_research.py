"""Policy boundaries, real-library integration, comparable scopes and gold metrics."""
import csv
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from hotel_compiler import analyze_review
from hotel_compiler.hybrid import HybridEngine, HybridPolicy, analyze_hybrid_review
from hotel_compiler.research_data import load_semeval
from hotel_compiler.research_metrics import classification_metrics, clustered_accuracy_interval, map_semeval_category
from hotel_compiler.research_runner import compare_csv, evaluate_semeval
from hotel_compiler.sentiment_policy import SentimentPolicy

EXTRAS = all(importlib.util.find_spec(p) for p in ('vaderSentiment','textblob','matplotlib'))


class StrengthTests(unittest.TestCase):
    def test_all_five_bands_and_inclusive_boundaries(self):
        p=SentimentPolicy()
        expected=[(-1,'Strong Negative'),(-.5,'Strong Negative'),(-.499999,'Weak Negative'),
                  (-.050001,'Weak Negative'),(-.05,'Neutral'),(0,'Neutral'),(.05,'Neutral'),
                  (.050001,'Weak Positive'),(.499999,'Weak Positive'),(.5,'Strong Positive'),(1,'Strong Positive')]
        for score,label in expected:
            with self.subTest(score=score):self.assertEqual(p.strength(score),label)
        self.assertEqual(p.strength(None),'Unavailable')

    def test_invalid_numbers_and_policies_fail(self):
        for value in [float('nan'),float('inf'),True,-1.1,1.1,'0.2']:
            with self.subTest(value=value),self.assertRaises(ValueError):SentimentPolicy().strength(value)
        for neutral,strong in [(.5,.5),(-.1,.5),(.05,1.1),(True,.5),(0,float('nan'))]:
            with self.assertRaises(ValueError):SentimentPolicy(neutral,strong)
        for value in [0,1,-1,float('nan'),True,'0.5']:
            with self.assertRaises(ValueError):HybridPolicy(value)

    def test_mixed_and_missing_stay_distinct_from_net_band(self):
        result=analyze_review('The room was not comfortable but the staff were very helpful.')
        self.assertEqual(result.overall,'Mixed')
        self.assertEqual(result.net_score_band,'Weak Negative')
        self.assertEqual([r.strength for r in result.records],['Strong Negative','Weak Positive'])
        self.assertEqual(result.to_dict()['records'][0]['strength'],'Strong Negative')
        self.assertEqual(analyze_review('The location was ideal.').net_score_band,'Unavailable')


class MetricTests(unittest.TestCase):
    def test_abstentions_are_errors_and_rare_class_recall_is_visible(self):
        rows=[{'gold':'Positive','prediction':'Positive','parent_id':'r1'},
              {'gold':'Negative','prediction':'Unanalyzed','parent_id':'r2'},
              {'gold':'Neutral','prediction':'Positive','parent_id':'r3'},
              {'gold':'Positive','prediction':'Mixed','parent_id':'r4'}]
        m=classification_metrics(rows)
        self.assertEqual(m['accuracy'],.25);self.assertEqual(m['coverage'],.5)
        self.assertEqual(m['conditional_accuracy'],.5)
        self.assertEqual(m['classes'][0]['recall'],0)
        self.assertAlmostEqual(m['macro_f1'],1/6)
        self.assertEqual(clustered_accuracy_interval(rows,seed=5),clustered_accuracy_interval(rows,seed=5))

    def test_empty_metrics_are_unavailable(self):
        self.assertIsNone(classification_metrics([])['accuracy'])
        self.assertEqual(clustered_accuracy_interval([]),(None,None))

    def test_mapping_excludes_prices_and_preserves_room_cleanliness(self):
        self.assertIsNone(map_semeval_category('LOCATION#GENERAL'))
        self.assertIsNone(map_semeval_category('ROOMS#PRICES'))
        self.assertEqual(map_semeval_category('ROOMS#CLEANLINESS'),'Room')
        self.assertEqual(map_semeval_category('HOTEL#CLEANLINESS'),'Cleanliness')
        self.assertEqual(map_semeval_category('SERVICE#GENERAL'),'Service')

    def test_xml_loader_rejects_external_entities(self):
        with TemporaryDirectory() as folder:
            path=Path(folder)/'bad.xml';path.write_text('<!DOCTYPE foo [<!ENTITY x SYSTEM "secret">]><Reviews/>')
            with self.assertRaises(ValueError):load_semeval(path)


@unittest.skipUnless(EXTRAS,'Install research extras for library/plot integration tests.')
class HybridIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.engine=HybridEngine()

    def test_fusion_is_computed_from_both_real_tools(self):
        evidence=self.engine.score_text('The room was very good!')
        self.assertEqual(evidence.score,round((evidence.vader_compound+evidence.textblob_polarity)/2,6))
        self.assertEqual(evidence.status,'scored');self.assertTrue(evidence.textblob_assessments)

    def test_neutral_evidence_and_no_evidence_are_not_conflated(self):
        missing=self.engine.score_text('The room has two chairs.')
        self.assertIsNone(missing.score);self.assertEqual(missing.status,'no_lexical_evidence')
        neutral=self.engine.score_text('daily')
        self.assertEqual(neutral.score,0);self.assertEqual(neutral.polarity,'Neutral')
        self.assertTrue(neutral.textblob_has_evidence)

    def test_negation_applied_by_libraries_only_and_baseline_not_mutated(self):
        text='The room was not very good.'
        base=analyze_review(text,'x');old=base.to_dict(include_trace=True)
        result=analyze_hybrid_review(text,'x',compiled=base,engine=self.engine)
        direct=self.engine.score_text(base.semantics[0].opinion_expression)
        self.assertEqual(result.records[0].score,direct.score)
        self.assertLess(direct.score,0);self.assertEqual(base.to_dict(include_trace=True),old)

    def test_partial_unsupported_and_whole_text_have_separate_scopes(self):
        partial=analyze_hybrid_review('The room was glorp but the staff were helpful.',engine=self.engine)
        self.assertEqual(partial.aspect_analysis_status,'partial')
        unsupported=analyze_hybrid_review('The location was excellent.',engine=self.engine)
        self.assertEqual(unsupported.aspect_analysis_status,'unsupported')
        self.assertIsNone(unsupported.aspect_mean_score)
        self.assertGreater(unsupported.whole_text.score,0)

    def test_hybrid_does_not_depend_on_sentiwordnet_scoring(self):
        with patch('hotel_compiler.pipeline.evaluate',side_effect=AssertionError('baseline evaluator must not run')):
            result=analyze_hybrid_review('The room was clean.',engine=self.engine)
        self.assertEqual(len(result.records),1)

    def test_component_failure_does_not_silently_become_single_tool_fallback(self):
        with patch.object(self.engine.textblob,'analyze',side_effect=RuntimeError('example')):
            e=self.engine.score_text('very good')
        self.assertIsNone(e.score);self.assertEqual(e.status,'processing_error')
        self.assertIsNotNone(e.vader_compound);self.assertTrue(e.errors)

    def test_lexically_absent_component_does_not_dilute_available_evidence(self):
        e=self.engine.score_text('The room was cold.')
        self.assertEqual(e.vader_compound,0)
        self.assertEqual(e.score,round(e.textblob_polarity,6))
        self.assertEqual(e.fusion_rule,'textblob_evidence_only')

    def test_input_limits_and_mismatched_compiler_context(self):
        for text in [None,100]:
            with self.assertRaises(TypeError):self.engine.score_text(text)
        with self.assertRaises(ValueError):self.engine.score_text('a'*10001)
        with self.assertRaises(ValueError):
            analyze_hybrid_review('Different text.',compiled=analyze_review('The room was clean.'),engine=self.engine)

    def test_export_preserves_invalid_rows_and_writes_real_figures(self):
        with TemporaryDirectory() as folder:
            root=Path(folder);source=root/'input.csv'
            source.write_text('sr.no,review\n1,The room was clean.\n2,The location was excellent.\n3,\n',encoding='utf-8')
            output=root/'out';output.mkdir()
            rows=compare_csv(source,output,self.engine,'authored_development',repeats=0)
            self.assertEqual(len(rows),3);self.assertEqual(rows[2]['execution_status'],'invalid_input')
            self.assertIsNone(rows[1]['compiler_mean']);self.assertGreater(rows[1]['hybrid_whole_text_score'],0)
            for name in ['review_results.csv','opinion_results.csv','run_metadata.csv','INFERENCES.md',
                         'fig_strength.pdf','fig_strength.svg','fig_availability.png']:
                self.assertGreater((output/name).stat().st_size,0)
            with (output/'review_results.csv').open(encoding='utf-8-sig',newline='') as f:
                self.assertEqual(len(list(csv.DictReader(f))),3)
            self.assertIn('No independent sentiment gold labels', (output/'INFERENCES.md').read_text())

    def test_gold_evaluation_includes_missing_predictions_and_exclusions(self):
        xml='''<Reviews><Review rid="r1"><sentences>
        <sentence id="s1"><text>The room was clean.</text><Opinions><Opinion category="ROOMS#CLEANLINESS" polarity="positive"/></Opinions></sentence>
        <sentence id="s2"><text>The location was excellent.</text><Opinions><Opinion category="LOCATION#GENERAL" polarity="positive"/></Opinions></sentence>
        </sentences></Review><Review rid="r2"><sentences>
        <sentence id="s3"><text>Wow the service absolutely dazzled us.</text><Opinions><Opinion category="SERVICE#GENERAL" polarity="positive"/></Opinions></sentence>
        </sentences></Review></Reviews>'''
        with TemporaryDirectory() as folder:
            root=Path(folder);source=root/'gold.xml';source.write_text(xml)
            output=root/'out';output.mkdir()
            metrics=evaluate_semeval(source,output,self.engine,bootstrap_repeats=100)
            self.assertEqual(len(metrics),2)
            self.assertEqual([r['cases'] for r in metrics],[2,2])
            self.assertEqual([r['accuracy'] for r in metrics],[.5,1.0])
            self.assertTrue((output/'fig_confusion.pdf').exists())


if __name__=='__main__':unittest.main()
