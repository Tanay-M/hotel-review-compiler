"""Source integrity, deterministic grammar, profile isolation and real-input cleaning."""
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path
import importlib.util
import json
import unittest

from hotel_compiler import analyze_review
from hotel_compiler.compiler_profiles import compiler_profile, current_profile
from hotel_compiler.sentiwordnet import load_synsets
from hotel_compiler.vocabulary import load_vocabulary

ROOT=Path(__file__).resolve().parents[1]


class ExpandedCompilerTests(unittest.TestCase):
    def expanded(self,text):
        result=analyze_review(text,profile='expanded')
        for token in result.tokens:self.assertEqual(text[token.start:token.end],token.text)
        for record in result.records:
            self.assertTrue(0<=record.start<record.end<=len(text))
            self.assertAlmostEqual(record.evidence.lexical_score,record.evidence.positive_score-record.evidence.negative_score)
        return result

    def test_original_resource_bytes_are_preserved(self):
        p=ROOT/'hotel_compiler/resources'
        expected=json.loads((p/'provenance_expanded.json').read_text())['original_resource_hashes']
        for name,digest in expected.items():self.assertEqual(sha256((p/name).read_bytes()).hexdigest(),digest)

    def test_broad_native_lexicon_uses_genuine_lemma_senses(self):
        with compiler_profile('expanded'):
            vocab=load_vocabulary();senses=load_synsets()
            self.assertGreater(len(vocab['opinions']),20000)
            self.assertGreater(len(vocab['aspects']),700)
            self.assertEqual(len(vocab['categories']),6)
            self.assertNotIn('location',vocab['aspects'])
            for word,spec in vocab['opinions'].items():
                native=spec.get('source_lemma',word)
                self.assertIn(native,{t.rsplit('#',1)[0] for t in senses[spec['synset']].terms})

    def test_native_verbs_and_explicit_targets(self):
        for text,aspect,opinion in [('I loved the breakfast.','breakfast','verb_love'),
                                   ('We enjoyed the pool.','pool','verb_enjoy'),
                                   ('The staff helped us.','staff','verb_help')]:
            r=self.expanded(text)
            self.assertEqual(r.status,'complete',r.diagnostics)
            self.assertEqual([(x.aspect_term,x.opinion_term) for x in r.records],[(aspect,opinion)])
            self.assertTrue(r.records[0].evidence.synset.startswith('v:'))
        # A genuine zero lexical score stays zero, never an invented positive.
        self.assertEqual(self.expanded('The staff helped us.').records[0].score,0)

    def test_native_verb_negation_is_applied_once(self):
        pos=self.expanded('We enjoyed the breakfast.').records[0]
        neg=self.expanded('We did not enjoy the breakfast.').records[0]
        self.assertEqual(pos.score,-neg.score)
        self.assertEqual(neg.evidence.negation_multiplier,-1)

    def test_comparatives_keep_original_surface(self):
        r=self.expanded('The room was brighter and quieter.')
        self.assertEqual(r.status,'complete',r.diagnostics)
        self.assertEqual([x.opinion_term for x in r.records],['bright','quiet'])
        self.assertEqual([x.opinion_expression for x in r.records],['brighter','quieter'])
        self.assertTrue(all(x.evidence.normalization_rule.startswith('comparative_lemma:') for x in r.records))

    def test_prenominal_possession_and_comma_lists(self):
        r=self.expanded('A spacious room with comfortable beds.')
        self.assertEqual(r.status,'complete',r.diagnostics)
        self.assertEqual([(x.aspect_term,x.opinion_term) for x in r.records],[('room','spacious'),('beds','comfortable')])
        r=self.expanded('The room was clean, spacious and quiet.')
        self.assertEqual(r.status,'complete',r.diagnostics)
        self.assertEqual([x.aspect_term for x in r.records],['room']*3)

    def test_pronoun_inheritance_is_bounded_and_unambiguous(self):
        r=self.expanded('The room was spacious and it was spotless.')
        self.assertEqual(r.status,'complete',r.diagnostics)
        self.assertEqual([x.aspect_term for x in r.records],['room','room'])
        r=self.expanded('The room was spacious and it was available.')
        self.assertTrue(r.records)
        for text in ['The room was spacious. It was spotless.',"The room was spacious. It's spotless."]:
            r=self.expanded(text)
            self.assertEqual(r.status,'complete',r.diagnostics)
            self.assertEqual([x.aspect_term for x in r.records],['room','room'])
        for text in ['The room and bathroom were spacious and it was spotless.',
                     'The room was spacious. We went out. It was spotless.', 'It was spotless.']:
            r=self.expanded(text)
            self.assertTrue(r.diagnostics,text)
            self.assertNotIn('spotless',[x.opinion_term for x in r.records],text)

    def test_real_review_punctuation_and_conjunctions(self):
        for text in ['Room: spacious, clean and comfortable.','The staff were nice & helpful.']:
            r=self.expanded(text)
            self.assertEqual(r.status,'complete',r.diagnostics)
            self.assertGreaterEqual(len(r.records),2)

    def test_absence_and_correlative_negation(self):
        r=self.expanded('No hot water.')
        self.assertEqual(r.status,'complete',r.diagnostics)
        self.assertEqual(r.records[0].aspect_term,'hot water')
        self.assertLess(r.records[0].score,0)
        self.assertEqual(r.records[0].evidence.normalization_rule,'absence:explicit_not_available')
        r=self.expanded('The room was not only clean but also comfortable.')
        self.assertEqual(r.status,'complete',r.diagnostics)
        self.assertEqual([x.polarity for x in r.records],['Positive','Positive'])
        r=self.expanded('Not all rooms were clean.')
        self.assertTrue(r.diagnostics)
        self.assertFalse(r.records)

    def test_unknown_material_is_not_hidden_to_claim_completeness(self):
        for text in ['The room was clean when we hated it.','The room was clean glorp.',
                     'The location was wonderful.','The price was fantastic.']:
            r=self.expanded(text)
            self.assertNotEqual(r.status,'complete',text)
            self.assertTrue(r.diagnostics,text)

    def test_function_words_and_factual_verbs_are_not_sentiment(self):
        for text in ['I can offer this room.','They kept the room clean.',
                     'The sheets were found stained.','It felt like an elegant apartment.',
                     'The room has amenities such as towels.']:
            r=self.expanded(text)
            terms={x.opinion_term for x in r.records}
            self.assertFalse(terms & {'off','offer','kept','found','such','verb_like'},(text,terms))
        r=self.expanded('They kept the room clean.')
        self.assertIn('clean',[x.opinion_term for x in r.records])

    def test_profiles_do_not_leak_between_requests(self):
        text='A spacious room with comfortable beds.'
        expected={p:analyze_review(text,profile=p).status for p in ['original','expanded']}
        self.assertNotEqual(expected['original'],expected['expanded'])
        def run(profile):
            r=analyze_review(text,profile=profile)
            return profile,r.compiler_profile,r.status,current_profile()
        with ThreadPoolExecutor(max_workers=4) as pool:
            for profile,actual,status,after in pool.map(run,['original','expanded']*12):
                self.assertEqual(profile,actual);self.assertEqual(status,expected[profile]);self.assertEqual(after,'original')
        self.assertEqual(current_profile(),'original')

    def test_cleaning_preserves_words_negation_and_source(self):
        spec=importlib.util.spec_from_file_location('clean_booking',ROOT/'scripts/prepare_clean_booking_demo.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        self.assertEqual(module.cleaned_text('  The AC\twas NOT working.\nN/A\n Staff were nice.  '),
                         'The AC was NOT working. Staff were nice.')
        self.assertEqual(module.cleaned_text('Nothing.\nNothing to dislike.'),'Nothing. Nothing to dislike.')


if __name__=='__main__':unittest.main()
