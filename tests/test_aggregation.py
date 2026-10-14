import csv
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from hotel_compiler.aggregation import aggregate_batch
from hotel_compiler.batch import analyze_csv
from hotel_compiler.exports import export_batch
from hotel_compiler.reporting import build_report, render_report, reporting_fingerprint


ROOT = Path(__file__).resolve().parents[1]


class AggregationTests(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / "tmp"
        scratch.mkdir(exist_ok=True)
        self.temp = TemporaryDirectory(dir=scratch)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def batch(self, reviews):
        path = self.root / "reviews.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["review_id", "review_text"])
            writer.writerows(["same-id", review] for review in reviews)
        return analyze_csv(path, batch_id="demo")

    def primary(self, batch):
        return aggregate_batch(batch)["views"]["complete_reviews"]

    def group(self, view, category, issue=None):
        groups = view["categories"] if issue is None else view["issues"]
        return next(group for group in groups if group["category"] == category and group["issue"] == issue)

    def test_opinions_do_not_inflate_review_counts_and_mixed_is_preserved(self):
        batch = self.batch(["The room was clean and dirty and quiet.", "The room was clean.", "The service was average."])
        view = self.primary(batch)
        room = self.group(view, "Room")
        self.assertEqual(view["eligible_reviews"], 3)
        self.assertEqual(view["overall_counts"], {"Positive": 1, "Negative": 0, "Mixed": 1, "Neutral": 1})
        self.assertEqual(room["mentioned_reviews"], 2)
        self.assertEqual(room["extracted_opinions"], 4)
        self.assertEqual(room["polarity_counts"], {"Positive": 1, "Negative": 0, "Mixed": 1, "Neutral": 0})
        self.assertEqual(room["negative_mention_reviews"], 1)
        self.assertEqual(room["negative_mention_percent"], 50)
        cleanliness = self.group(view, "Room", "Cleanliness")
        self.assertEqual(cleanliness["negative_mention_reviews"], 1)
        self.assertEqual(cleanliness["polarity_counts"]["Mixed"], 1)

    def test_average_gives_each_review_equal_weight_and_does_not_determine_label(self):
        batch = self.batch(["The staff were helpful and helpful and helpful.", "The staff were rude."])
        staff = self.group(self.primary(batch), "Staff")
        first = batch.rows[0].analysis.records[0].score
        second = batch.rows[1].analysis.records[0].score
        self.assertEqual(staff["average_score"], round((first + second) / 2, 6))
        self.assertNotEqual(staff["average_score"], round((3 * first + second) / 4, 6))
        mixed = self.batch(["The room was clean and not clean."])
        room = self.group(self.primary(mixed), "Room")
        self.assertEqual(room["average_score"], 0)
        self.assertEqual(room["polarity_counts"]["Mixed"], 1)
        self.assertEqual(room["polarity_counts"]["Neutral"], 0)

    def test_partial_results_are_separate_and_invalid_unsupported_errors_are_excluded(self):
        batch = self.batch(["The staff were helpful.", "The room was odd but staff were rude.", "The AC cannot work.", "", "The food was delicious."])
        batch = replace(batch, rows=(*batch.rows[:4], replace(batch.rows[4], execution_status="processing_error", analysis=None, processing_error="example")))
        aggregation = aggregate_batch(batch)
        primary, secondary = aggregation["views"].values()
        self.assertEqual(primary["eligible_reviews"], 1)
        self.assertEqual(primary["overall_counts"]["Positive"], 1)
        self.assertEqual(secondary["eligible_reviews"], 2)
        self.assertEqual(secondary["overall_counts"]["Negative"], 1)
        self.assertEqual(aggregation["coverage"]["counts"]["processing_error"], 1)
        self.assertEqual(aggregation["coverage"]["coverage"]["complete_percent"], 33.33)
        self.assertEqual(aggregation["primary_complete_share_submitted_percent"], 20)
        self.assertTrue(aggregation["limited_primary_coverage"])

    def test_duplicate_text_and_caller_ids_keep_distinct_internal_identities(self):
        batch = self.batch(["The AC was broken."] * 2)
        issue = self.group(self.primary(batch), "Facilities", "Air Conditioning")
        self.assertEqual(issue["negative_mention_reviews"], 2)
        self.assertEqual(issue["negative_mention_row_ids"], ["demo:000001", "demo:000002"])
        self.assertEqual(batch.summary()["counts"]["duplicate_text_rows"], 2)
        self.assertTrue(any("Duplicates retained" in note for note in build_report(batch)["notes"]))

    def test_not_mentioned_categories_are_unavailable_not_neutral(self):
        view = self.primary(self.batch(["The staff were helpful."]))
        room = self.group(view, "Room")
        self.assertEqual(room["evidence_status"], "not_mentioned")
        self.assertEqual(room["polarity_counts"]["Neutral"], 0)
        self.assertIsNone(room["average_score"])
        self.assertIsNone(room["negative_mention_percent"])
        self.assertTrue(all(value is None for value in room["polarity_percent"].values()))

    def test_no_complete_rows_never_falls_back_to_partial_or_zero_averages(self):
        batch = self.batch(["The room was odd but staff were helpful.", "Unknown words.", ""])
        report = build_report(batch)
        primary = report["aggregation"]["views"]["complete_reviews"]
        self.assertEqual(primary["eligible_reviews"], 0)
        self.assertTrue(all(group["average_score"] is None for group in primary["categories"]))
        self.assertEqual(report["conclusions"]["complete_reviews"][0]["code"], "NO_ELIGIBLE_REVIEWS")
        self.assertIn("No completely analyzed reviews", render_report(report))
        self.assertNotIn("Secondary:", render_report(report))
        self.assertIn("Secondary:", render_report(report, include_partial=True))

    def test_empty_eligible_sets_have_null_percentages(self):
        batch = self.batch([""])
        view = self.primary(batch)
        self.assertTrue(all(value is None for value in view["overall_percent"].values()))
        self.assertEqual(view["complaint_ranking"], [])
        empty = replace(batch, rows=())
        self.assertIsNone(aggregate_batch(empty)["primary_complete_share_submitted_percent"])

    def test_low_support_threshold_is_explicit_and_boundary_is_inclusive(self):
        low = self.group(self.primary(self.batch(["The AC was broken."] * 4)), "Facilities")
        enough = self.group(self.primary(self.batch(["The AC was broken."] * 5)), "Facilities")
        self.assertEqual(low["evidence_status"], "low_support")
        self.assertEqual(enough["evidence_status"], "supported")
        self.assertIn("Support is low", render_report(build_report(self.batch(["The AC was broken."]))))

    def test_coverage_warning_uses_submitted_rows_even_when_analyzed_coverage_is_full(self):
        batch = self.batch(["The staff were helpful.", "", "", "", ""])
        report = build_report(batch)
        self.assertEqual(batch.summary()["coverage"]["complete_percent"], 100)
        self.assertEqual(report["aggregation"]["primary_complete_share_submitted_percent"], 20)
        self.assertTrue(any("Limited primary coverage" in note for note in report["notes"]))
        report = build_report(self.batch(["The staff were helpful."] * 4 + ["Unknown."]))
        self.assertEqual(report["aggregation"]["primary_complete_share_submitted_percent"], 80)
        self.assertFalse(report["aggregation"]["limited_primary_coverage"])

    def test_complaint_ranks_keep_ties_and_count_frequency_not_score_severity(self):
        batch = self.batch(["The WiFi was broken.", "The AC was broken.", "The room was dirty.", "The WiFi was broken.", "The AC was broken."])
        ranking = self.primary(batch)["complaint_ranking"]
        self.assertEqual([group["rank"] for group in ranking], [1, 1, 3])
        text = render_report(build_report(batch))
        self.assertIn("tie for the highest", text)
        self.assertIn("frequency, not severity", text)

    def test_every_metric_and_conclusion_evidence_resolves_to_retained_records(self):
        batch = self.batch(["The room was clean and dirty; staff were rude.", "The AC was broken.", "The room was odd but staff were helpful."])
        report = build_report(batch)
        for scope, view in report["aggregation"]["views"].items():
            for group in view["categories"] + view["issues"]:
                for evidence in group["evidence"]:
                    row = batch.get_row(evidence["row_id"])
                    self.assertIn(row.row_id, view["eligible_row_ids"])
                    for index in evidence["record_indices"]:
                        record = row.analysis.records[index]
                        self.assertEqual(record.category, group["category"])
                        if group["issue"]:
                            self.assertEqual(record.issue, group["issue"])
                self.assertEqual(sum(group["polarity_counts"].values()), group["mentioned_reviews"])
            for conclusion in report["conclusions"][scope]:
                self.assertTrue(set(conclusion["row_ids"]) <= set(view["eligible_row_ids"]))
                for row_id in conclusion["row_ids"]:
                    self.assertIsNotNone(batch.get_row(row_id).analysis)
                if conclusion["code"] == "ISSUE_COMPLAINT":
                    self.assertEqual(conclusion["count"], len(conclusion["row_ids"]))
                    for row_id in conclusion["row_ids"]:
                        self.assertTrue(any(record.category == conclusion["category"] and record.issue == conclusion["issue"] and record.polarity == "Negative" for record in batch.get_row(row_id).analysis.records))

    def test_positive_and_neutral_categories_follow_core_presence_convention(self):
        cases = json.loads((ROOT / "examples/robustness_cases.json").read_text(encoding="utf-8"))["cases"]
        batch = self.batch([case["text"] for case in cases])
        view = self.primary(batch)
        for row in batch.rows:
            if row.analysis.status != "complete":
                continue
            category_names = {record.category for record in row.analysis.records}
            if len(category_names) == 1:
                category = self.group(view, category_names.pop())
                self.assertIn(row.row_id, category["polarity_row_ids"][row.analysis.overall])

    def test_reporting_never_calls_the_compiler_or_mutates_batch(self):
        batch = self.batch(["The staff were helpful.", "The AC was broken."])
        snapshot = batch.to_dict(include_trace=True)
        with patch("hotel_compiler.batch.analyze_review", side_effect=AssertionError("must not reanalyze")), patch("hotel_compiler.pipeline.analyze_review", side_effect=AssertionError("must not reanalyze")):
            report = build_report(batch)
            self.assertEqual(report, build_report(batch))
        self.assertEqual(batch.to_dict(include_trace=True), snapshot)
        self.assertEqual(report["reporting_fingerprint"], reporting_fingerprint())
        self.assertEqual(report["analysis_fingerprint"], batch.analysis_fingerprint)

    def test_100_and_500_row_counts_and_evidence_remain_consistent(self):
        patterns = ["The room was clean and dirty.", "Staff were helpful.", "Unknown.", "The room was odd but staff were rude.", ""]
        for size in (100, 500):
            with self.subTest(size=size):
                batch = self.batch([patterns[i % 5] for i in range(size)])
                report = build_report(batch)
                primary, secondary = report["aggregation"]["views"].values()
                self.assertEqual(primary["eligible_reviews"], size * 2 // 5)
                self.assertEqual(secondary["eligible_reviews"], size * 3 // 5)
                self.assertEqual(primary["overall_counts"]["Mixed"], size // 5)
                self.assertEqual(self.group(primary, "Room")["negative_mention_reviews"], size // 5)
                self.assertEqual(self.group(primary, "Staff")["negative_mention_reviews"], 0)
                self.assertEqual(self.group(secondary, "Staff")["negative_mention_reviews"], size // 5)
                paths = export_batch(batch, self.root / str(size))
                saved = json.loads(paths["summary.json"].read_text(encoding="utf-8"))
                self.assertEqual(saved, report)

    def test_five_exports_preserve_individual_outputs_and_add_both_report_scopes(self):
        batch = self.batch(["The AC was broken.", "The room was odd but staff were helpful."])
        paths = export_batch(batch, self.root / "out", include_partial_report=True)
        self.assertEqual(set(paths), {"reviews.csv", "aspects.csv", "batch.json", "summary.json", "report.txt"})
        self.assertEqual(json.loads(paths["batch.json"].read_text(encoding="utf-8")), json.loads(json.dumps(batch.to_dict(include_trace=True))))
        self.assertEqual(set(json.loads(paths["summary.json"].read_text(encoding="utf-8"))["conclusions"]), {"complete_reviews", "complete_and_partial"})
        self.assertIn("Secondary:", paths["report.txt"].read_text(encoding="utf-8"))

    def test_report_collision_preserves_existing_file_and_cleans_new_outputs(self):
        batch = self.batch(["The AC was broken."])
        directory = self.root / "out"
        directory.mkdir()
        existing = directory / "report.txt"
        existing.write_text("keep", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            export_batch(batch, directory)
        self.assertEqual(list(directory.iterdir()), [existing])
        self.assertEqual(existing.read_text(encoding="utf-8"), "keep")

    def test_reporting_failure_cleans_all_created_outputs_and_keeps_unrelated_files(self):
        batch = self.batch(["Staff were helpful."])
        directory = self.root / "out"
        directory.mkdir()
        unrelated = directory / "notes.txt"
        unrelated.write_text("keep", encoding="utf-8")
        with patch("hotel_compiler.exports.build_report", side_effect=ValueError("example")):
            with self.assertRaises(ValueError):
                export_batch(batch, directory)
        self.assertEqual(list(directory.iterdir()), [unrelated])

    def test_cli_reports_primary_and_optional_partial_scope_with_original_exit_codes(self):
        batch = self.batch(["The AC was broken.", "The room was odd but staff were helpful."])
        for include in (False, True):
            directory = self.root / f"cli-{include}"
            args = [sys.executable, "-X", "utf8", "-m", "hotel_compiler.batch_cli", str(self.root / "reviews.csv"), "--output-dir", str(directory)]
            if include:
                args.append("--include-partial")
            process = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30)
            self.assertEqual(process.returncode, 1, process.stderr)
            self.assertIn("Among 1 completely analyzed reviews", process.stdout)
            self.assertEqual("Secondary:" in process.stdout, include)
            self.assertTrue((directory / "summary.json").exists())


if __name__ == "__main__":
    unittest.main()
