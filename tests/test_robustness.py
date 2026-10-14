from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
import zipfile
from unittest.mock import patch

from hotel_compiler import analyze_review
from hotel_compiler.evaluation import _metrics, evaluate_corpus
from hotel_compiler.sentiwordnet import ResourceError, load_synsets
from hotel_compiler.vocabulary import load_vocabulary, validate_vocabulary


ROOT = Path(__file__).resolve().parents[1]


class RobustnessTests(unittest.TestCase):
    def test_authored_contracts_and_reserved_cases(self):
        corpus = json.loads((ROOT / "examples/robustness_cases.json").read_text(encoding="utf-8"))
        self.assertEqual(len(corpus["cases"]), 100)
        for case in corpus["cases"]:
            with self.subTest(text=case["text"], split=case["split"]):
                result = analyze_review(case["text"], "test")
                self.assertEqual(result.status, case["status"], result.diagnostics)
                self.assertEqual(Counter((r.category, r.issue, r.polarity) for r in result.records),
                                 Counter(map(tuple, case["expected"])))
                for token in result.tokens:
                    self.assertEqual(case["text"][token.start:token.end], token.text)

    def test_working_uses_equipment_sense_and_negation_once(self):
        positive = analyze_review("The air conditioning was working.").records[0]
        negative = analyze_review("The air conditioning was not working.").records[0]
        self.assertEqual(positive.evidence.synset, "a:01091728")
        self.assertEqual((positive.evidence.positive_score, positive.evidence.negative_score), (0.25, 0))
        self.assertIsNone(positive.evidence.calibration_reason)
        self.assertEqual((positive.score, negative.score), (0.25, -0.25))
        self.assertEqual(negative.evidence.negation_multiplier, -1)

    def test_aliases_are_visible_and_source_expression_is_not_replaced(self):
        for text, original, canonical in [
            ("The AC works.", "works", "working"),
            ("The lift is out of order.", "out of order", "broken"),
            ("Comfy beds.", "Comfy", "comfortable"),
        ]:
            with self.subTest(text=text):
                result = analyze_review(text)
                record = result.records[0]
                self.assertEqual(record.opinion_expression, original)
                self.assertEqual(record.opinion_term, canonical)
                self.assertIn("opinion_alias:", record.evidence.normalization_rule)
                token = result.ast.clauses[0].opinion
                self.assertEqual(text[token.start:token.end], original)
                self.assertEqual(token.value, canonical)

    def test_auxiliary_contraction_positions_and_readable_negation(self):
        text = "The Wi‑Fi doesn’t work properly, but the staff were helpful."
        result = analyze_review(text)
        self.assertEqual(result.status, "complete", result.diagnostics)
        self.assertEqual([r.polarity for r in result.records], ["Negative", "Positive"])
        self.assertEqual(result.records[0].opinion_expression, "not work properly")
        self.assertEqual(result.ast.clauses[0].auxiliary.value, "does")
        self.assertEqual(result.semantics[0].adverb, "properly")
        for token in result.tokens:
            self.assertEqual(text[token.start:token.end], token.text)
        semantic = result.semantics[0]
        self.assertEqual(text[semantic.opinion_start:semantic.opinion_end], "n’t work properly")

    def test_adjective_before_aspect_has_exact_expression_and_clause_spans(self):
        text = "An extremely helpful receptionist."
        result = analyze_review(text)
        record, semantic = result.records[0], result.semantics[0]
        self.assertEqual(result.status, "complete")
        self.assertEqual(record.opinion_expression, "extremely helpful")
        self.assertEqual(text[record.start:record.end], "An extremely helpful receptionist")
        self.assertEqual(text[semantic.opinion_start:semantic.opinion_end], "extremely helpful")
        self.assertEqual(semantic.syntax_form, "opinion_before_aspect")
        self.assertFalse(semantic.aspect_inherited)

    def test_compatibility_filters_employee_work_and_wrong_domain_phrases(self):
        for text in ("The staff were working.", "The food was functioning.", "The parking works.",
                     "The food was out of order.", "The staff were comfortable."):
            with self.subTest(text=text):
                result = analyze_review(text)
                self.assertEqual(result.status, "unsupported")
                self.assertEqual(result.diagnostics[0].code, "INCOMPATIBLE_OPINION")
                self.assertFalse(result.records)

    def test_invalid_auxiliary_forms_are_rejected(self):
        for text in ("The AC does works.", "The TV did functioning.", "The AC was work.",
                     "The staff did helpful.", "Works AC.", "The AC very works."):
            with self.subTest(text=text):
                result = analyze_review(text)
                self.assertEqual(result.status, "unsupported")
                self.assertTrue(any(d.stage == "syntax" for d in result.diagnostics))
        self.assertEqual(analyze_review("The AC really works.").records[0].score, 0.3125)

    def test_selected_adverbs_are_not_discarded_as_stopwords(self):
        for text in ("The AC was working poorly.", "The staff were helpful properly.",
                     "The room was clean well.", "The fridge works not properly."):
            with self.subTest(text=text):
                self.assertEqual(analyze_review(text).status, "unsupported")
        result = analyze_review("The fridge doesn't work well at all.")
        self.assertEqual(result.status, "complete")
        self.assertEqual(result.records[0].opinion_expression, "not work well at all")
        self.assertEqual(result.records[0].score, -0.25)
        self.assertEqual(result.semantics[0].emphasis, "at all")

    def test_emphasis_requires_negation_and_does_not_flip_or_amplify_twice(self):
        plain = analyze_review("The staff were not helpful.").records[0]
        emphatic = analyze_review("The staff were not helpful at all.").records[0]
        self.assertEqual(plain.score, emphatic.score)
        self.assertEqual(analyze_review("The staff were helpful at all.").diagnostics[0].code, "INVALID_EMPHASIS")

    def test_negation_after_coordination_is_local_and_sentence_ends_reset_context(self):
        result = analyze_review("The WiFi works but doesn't work properly. Working.")
        self.assertEqual(result.status, "partial")
        self.assertEqual([r.polarity for r in result.records], ["Positive", "Negative"])
        self.assertTrue(any(d.code == "MISSING_ASPECT" for d in result.diagnostics))

    def test_semantic_failure_clears_inherited_subject(self):
        result = analyze_review("The AC works but the staff were working and functioning.")
        self.assertEqual(len(result.records), 1)
        self.assertEqual([d.code for d in result.diagnostics], ["INCOMPATIBLE_OPINION", "MISSING_ASPECT"])

    def test_complex_negation_and_unresolved_references_are_not_guessed(self):
        for text in ("The AC does not never work.", "The staff were not only helpful but also polite.",
                     "The TV cannot work.", "It was not working."):
            with self.subTest(text=text):
                self.assertEqual(analyze_review(text).status, "unsupported")
        result = analyze_review("The room was quiet. It was not comfortable.")
        self.assertEqual(result.status, "partial")
        self.assertEqual(len(result.records), 1)

    def test_new_domain_rules_keep_original_sentiwordnet_values(self):
        for text, term, p, n, score, rule in [
            ("The AC was functioning.", "functioning", 0, 0, 0.25, "functioning_equipment"),
            ("The bed was comfortable.", "comfortable", 0, 0.75, 0.5, "physical_room_comfort"),
            ("The room was noisy.", "noisy", 0.375, 0.375, -0.5, "hotel_noise_complaint"),
            ("The room was spacious.", "spacious", 0, 0, 0.25, "room_space_preference"),
        ]:
            with self.subTest(text=text):
                record = analyze_review(text).records[0]
                self.assertEqual(record.opinion_term, term)
                self.assertEqual((record.evidence.positive_score, record.evidence.negative_score), (p, n))
                self.assertEqual(record.score, score)
                self.assertEqual(record.evidence.domain_rule_id, rule)
                self.assertTrue(record.evidence.calibration_reason)

    def test_all_configured_senses_and_aliases_have_valid_targets(self):
        vocabulary = load_vocabulary()
        senses = load_synsets()
        self.assertEqual(len(senses), json.loads((ROOT / "hotel_compiler/resources/provenance.json").read_text())["selected_synsets"])
        self.assertGreaterEqual(len(senses), 250)
        for term, spec in vocabulary["opinions"].items():
            self.assertIn(term, {t.rsplit("#", 1)[0] for t in senses[spec["synset"]].terms})
        for alias, spec in vocabulary["opinion_aliases"].items():
            with self.subTest(alias=alias):
                self.assertIn(spec["canonical"], vocabulary["opinions"])
                self.assertIn(spec["kind"], {"OPINION", "FUNCTION_VERB"})

    def test_bad_shared_vocabulary_is_rejected_before_row_processing(self):
        bad = deepcopy(load_vocabulary())
        bad["opinion_aliases"]["work"]["canonical"] = "missing"
        with self.assertRaisesRegex(ValueError, "canonical opinion alias"):
            validate_vocabulary(bad)
        with patch("hotel_compiler.sentiwordnet.load_vocabulary", side_effect=ValueError("bad alias")):
            with self.assertRaises(ResourceError):
                load_synsets.__wrapped__()
        bad = deepcopy(load_vocabulary())
        bad["opinions"]["comfortable"].pop("calibration_reason")
        with self.assertRaisesRegex(ValueError, "explicit rule ID and reason"):
            validate_vocabulary(bad)

    @unittest.skipUnless((ROOT / "data/vendor/sentiwordnet.zip").exists(), "Official source archive optional")
    def test_subset_rows_are_unchanged_official_source_rows(self):
        resource_dir = ROOT / "hotel_compiler/resources"
        provenance = json.loads((resource_dir / "provenance.json").read_text(encoding="utf-8"))
        archive = ROOT / "data/vendor/sentiwordnet.zip"
        self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), provenance["source_archive_sha256"])
        with zipfile.ZipFile(archive) as zipped:
            original = set(zipped.read("sentiwordnet/SentiWordNet_3.0.0.txt").decode("utf-8").splitlines())
        subset = (resource_dir / "sentiwordnet.tsv").read_text(encoding="utf-8")
        rows = [line for line in subset.splitlines() if line and not line.startswith("#")]
        self.assertEqual(len(rows), provenance["selected_synsets"])
        self.assertTrue(set(rows) <= original)


class EvaluationTests(unittest.TestCase):
    def test_multiset_metrics_do_not_collapse_repeated_opinions(self):
        report = _metrics([{
            "expected": [["Staff", "Quality", "Positive"], ["Staff", "Quality", "Positive"]],
            "actual": [["Staff", "Quality", "Positive"], ["Staff", "Quality", "Negative"]],
            "expected_status": "complete", "status": "complete", "diagnostic_codes": [], "unknown_words": [],
        }])
        self.assertEqual(report["matched_tuples"], 1)
        self.assertEqual(report["tuple_precision_percent"], 50)
        self.assertEqual(report["tuple_recall_percent"], 50)
        self.assertEqual(report["polarity_on_matched_category_issue_percent"], 50)
        self.assertEqual(report["exact_review_matches"], 0)

    def test_no_gold_opinions_has_no_fabricated_accuracy(self):
        report = _metrics([{
            "expected": [], "actual": [], "expected_status": "unsupported", "status": "unsupported",
            "diagnostic_codes": ["UNSUPPORTED_CLAUSE"], "unknown_words": ["glorp"],
        }])
        self.assertIsNone(report["tuple_precision_percent"])
        self.assertIsNone(report["tuple_recall_percent"])
        self.assertIsNone(report["polarity_on_matched_category_issue_percent"])
        self.assertEqual(report["exact_review_matches"], 1)

    def test_corpus_reports_splits_matching_rule_and_scope(self):
        report = evaluate_corpus(ROOT / "examples/robustness_cases.json")
        self.assertEqual(report["splits"]["development"]["reviews"], 70)
        self.assertEqual(report["splits"]["reserved"]["reviews"], 30)
        self.assertEqual(report["all"]["exact_review_matches"], 100)
        self.assertIn("not independent real-world", report["scope"])
        self.assertIn("Multiset", report["matching_rule"])

    @unittest.skipUnless(sys.platform == "win32", "Windows-only launcher")
    def test_evaluation_launcher_exports_and_protects_existing_report(self):
        scratch = ROOT / "tmp"
        scratch.mkdir(exist_ok=True)
        with TemporaryDirectory(dir=scratch) as folder:
            Path(folder).resolve().relative_to(scratch.resolve())
            output = Path(folder) / "evaluation.json"
            command = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                       str(ROOT / "scripts/evaluate.ps1"), str(ROOT / "examples/robustness_cases.json"),
                       "--output", str(output)]
            first = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["all"]["exact_review_matches"], 100)
            before = output.read_bytes()
            second = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30)
            self.assertEqual(second.returncode, 2)
            self.assertEqual(output.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
