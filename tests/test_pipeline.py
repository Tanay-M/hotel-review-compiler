import json
from pathlib import Path
import unittest

from hotel_compiler import analyze_review


class CompilerTests(unittest.TestCase):
    def test_plan_example_keeps_opposite_aspect_sentiments(self):
        result = analyze_review(
            "The room was not clean, but the staff were very helpful.", "demo"
        )
        self.assertEqual(result.status, "complete")
        self.assertEqual(result.overall, "Mixed")
        self.assertEqual(
            [(r.category, r.issue, r.opinion_term, r.polarity) for r in result.records],
            [("Room", "Cleanliness", "clean", "Negative"),
             ("Staff", "Helpfulness", "helpful", "Positive")],
        )
        self.assertAlmostEqual(result.records[0].score, -0.125)
        self.assertAlmostEqual(result.records[1].score, 0.3125)
        self.assertEqual(result.records[0].review_id, "demo")
        self.assertTrue(result.tokens)
        self.assertEqual(len(result.ast.clauses), 2)
        self.assertEqual(len(result.semantics), 2)

    def test_documented_examples_cover_all_six_categories(self):
        examples = json.loads(
            (Path(__file__).resolve().parents[1] / "examples" / "reviews.json").read_text(encoding="utf-8")
        )
        categories = set()
        for example in examples:
            with self.subTest(review=example["text"]):
                result = analyze_review(example["text"])
                self.assertEqual(result.status, "complete", result.diagnostics)
                self.assertEqual(result.overall, example["overall"])
                self.assertEqual(
                    [[r.category, r.issue, r.polarity] for r in result.records],
                    example["expected"],
                )
                categories.update(r.category for r in result.records)
        self.assertEqual(categories, {"Room", "Staff", "Service", "Food", "Cleanliness", "Facilities"})

    def test_negation_stops_at_the_next_clause(self):
        result = analyze_review("The room was not clean but the staff were helpful.")
        self.assertEqual([r.polarity for r in result.records], ["Negative", "Positive"])
        self.assertEqual([s.negated for s in result.semantics], [True, False])

    def test_intensifier_strength_and_score_clipping(self):
        plain = analyze_review("The staff were helpful.").records[0]
        strong = analyze_review("The staff were extremely helpful.").records[0]
        capped = analyze_review("The staff were extremely excellent.").records[0]
        self.assertAlmostEqual(plain.score, 0.25)
        self.assertAlmostEqual(strong.score, 0.375)
        self.assertEqual(capped.score, 1.0)
        self.assertEqual(capped.evidence.unclipped_score, 1.5)

    def test_unknown_opinion_is_unsupported_instead_of_neutral(self):
        result = analyze_review("The room was glorp.")
        self.assertEqual(result.status, "unsupported")
        self.assertEqual(result.overall, "Unanalyzed")
        self.assertFalse(result.records)
        self.assertTrue(any(t.kind == "WORD" and t.text == "glorp" for t in result.tokens))
        self.assertIn("glorp", result.diagnostics[0].message)

    def test_valid_clause_survives_an_unsupported_neighbor(self):
        result = analyze_review("The room was glorp but the staff were helpful.")
        self.assertEqual(result.status, "partial")
        self.assertEqual([(r.category, r.polarity) for r in result.records], [("Staff", "Positive")])
        self.assertEqual(result.diagnostics[0].code, "UNSUPPORTED_CLAUSE")

    def test_recovery_does_not_assign_an_opinion_to_a_stale_aspect(self):
        result = analyze_review("The room was clean but the weather was odd and dirty.")
        self.assertEqual(len(result.records), 1)
        self.assertEqual(result.records[0].opinion_term, "clean")
        self.assertTrue(any(d.code == "MISSING_ASPECT" for d in result.diagnostics))

    def test_aspect_is_not_inherited_across_sentences(self):
        result = analyze_review("The room was dirty. Helpful.")
        self.assertEqual(result.status, "partial")
        self.assertEqual(len(result.records), 1)
        self.assertTrue(any(d.code == "MISSING_ASPECT" for d in result.diagnostics))

    def test_two_independent_sentences_remain_complete(self):
        result = analyze_review("The room was clean. The staff were rude.")
        self.assertEqual(result.status, "complete")
        self.assertEqual(result.overall, "Mixed")

    def test_missing_or_repeated_modifiers_do_not_silently_parse(self):
        for text in ["The room was not never clean.", "The staff were very extremely helpful.", "The room was not."]:
            with self.subTest(review=text):
                result = analyze_review(text)
                self.assertEqual(result.status, "unsupported")
                self.assertTrue(result.diagnostics)

    def test_dangling_connectors_are_reported(self):
        result = analyze_review("The room was clean but")
        self.assertEqual(result.status, "partial")
        self.assertEqual(result.diagnostics[-1].code, "MISSING_CLAUSE")

    def test_empty_input_has_a_structured_diagnostic(self):
        result = analyze_review("  ")
        self.assertEqual(result.status, "unsupported")
        self.assertEqual(result.diagnostics[0].code, "EMPTY_INPUT")

    def test_input_type_size_and_id_are_validated(self):
        with self.assertRaises(TypeError):
            analyze_review(None)
        with self.assertRaises(ValueError):
            analyze_review("x" * 10_001)
        with self.assertRaises(ValueError):
            analyze_review("room clean", "")

    def test_source_positions_survive_unicode_and_multiword_aspects(self):
        text = "The Wi‑Fi wasn’t very reliable, but the room was clean."
        result = analyze_review(text)
        self.assertEqual(result.status, "complete")
        self.assertEqual(result.review_text, text)
        for token in result.tokens:
            self.assertEqual(text[token.start:token.end], token.text)
        self.assertEqual(result.records[0].category, "Facilities")
        self.assertEqual(result.records[0].opinion_expression, "not very reliable")
        for record in result.records:
            self.assertTrue(text[record.start:record.end])

    def test_unicode_lowercasing_does_not_shift_offsets(self):
        text = "İstanbul was lovely but the staff were helpful."
        result = analyze_review(text)
        self.assertEqual(result.status, "partial")
        for token in result.tokens:
            self.assertEqual(text[token.start:token.end], token.text)
        self.assertEqual(result.records[0].category, "Staff")

    def test_slow_service_exposes_original_and_domain_scores(self):
        result = analyze_review("Room service was slow.")
        record = result.records[0]
        self.assertEqual(record.category, "Service")
        self.assertEqual(record.evidence.synset, "a:00980527")
        self.assertEqual(record.evidence.lexical_score, 0.0)
        self.assertEqual(record.score, -0.5)
        self.assertIn("zero lexical sentiment", record.evidence.calibration_reason)
        # The service-specific rule must not classify unrelated categories.
        self.assertEqual(analyze_review("The food was slow.").records[0].score, 0.0)

    def test_neutral_means_a_supported_zero_score(self):
        result = analyze_review("The service was average.")
        self.assertEqual(result.status, "complete")
        self.assertEqual(result.records[0].score, 0.0)
        self.assertEqual(result.overall, "Neutral")

    def test_json_and_trace_have_distinct_public_contracts(self):
        result = analyze_review("The room was clean.", "r-17")
        compact = result.to_dict()
        traced = result.to_dict(include_trace=True)
        self.assertNotIn("trace", compact)
        self.assertNotIn("evidence", compact["records"][0])
        self.assertEqual(compact["records"][0]["review_id"], "r-17")
        self.assertEqual(
            set(traced["trace"]),
            {"lexical_analysis", "syntax_analysis", "semantic_analysis", "sentiment_evaluation", "intermediate_representation"},
        )
        self.assertEqual(traced["trace"]["intermediate_representation"], compact["records"])
        self.assertEqual(json.loads(json.dumps(traced))["review_id"], "r-17")


if __name__ == "__main__":
    unittest.main()
