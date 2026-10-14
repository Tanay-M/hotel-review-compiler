import csv
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from hotel_compiler.batch import analysis_fingerprint, analyze_batch, analyze_csv
from hotel_compiler.csv_input import CSVInputError, CSVLimits, read_review_csv
from hotel_compiler.exports import export_batch
from hotel_compiler.pipeline import analyze_review
from hotel_compiler.sentiwordnet import ResourceError


ROOT = Path(__file__).resolve().parents[1]


class BatchTestCase(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / "tmp"
        scratch.mkdir(exist_ok=True)
        self.temporary = TemporaryDirectory(dir=scratch)
        # Verify this test-owned cleanup target stays inside the workspace.
        Path(self.temporary.name).resolve().relative_to(scratch.resolve())
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def write_csv(self, rows, header=("review_id", "review_text"), name="reviews.csv"):
        path = self.root / name
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(header)
            writer.writerows(rows)
        return path

    def write_raw(self, text):
        path = self.root / "reviews.csv"
        path.write_text(text, encoding="utf-8", newline="")
        return path


class CSVInputTests(BatchTestCase):
    def test_bom_quotes_unicode_and_multiline_preserve_text_and_lines(self):
        text = 'The room wasn’t clean, but the staff were "helpful".\r\nThe food was cold.'
        path = self.write_csv([["r1", text], ["r2", "The staff were helpful."]])
        source = read_review_csv(path)
        self.assertEqual(source.rows[0].review_text, text)
        self.assertEqual((source.rows[0].line_start, source.rows[0].line_end), (2, 3))
        self.assertEqual((source.rows[1].ordinal, source.rows[1].line_start), (2, 4))
        self.assertEqual(len(source.source_sha256), 64)

    def test_optional_ids_custom_columns_and_ignored_metadata(self):
        path = self.write_csv([["The food was delicious.", "5"]], header=("text", "rating"))
        source = read_review_csv(path, text_column="text")
        self.assertIsNone(source.id_column)
        self.assertEqual(source.ignored_columns, ("rating",))
        self.assertIsNone(source.rows[0].supplied_review_id)
        path = self.write_csv([["external", "The food was delicious."]], header=("id", "comment"))
        source = read_review_csv(path, text_column="comment", id_column="id")
        self.assertEqual(source.rows[0].supplied_review_id, "external")

    def test_header_validation_rejects_ambiguous_or_missing_columns(self):
        for text in ("", "review_id,text\nr1,hello\n", "review_text,review_text\na,b\n",
                     "review_text, review_text \na,b\n", "review_text,\na,b\n",
                     "review_text\n"):
            with self.subTest(text=text), self.assertRaises(CSVInputError):
                read_review_csv(self.write_raw(text))
        path = self.write_csv([["hello"]], header=("review_text",))
        with self.assertRaisesRegex(CSVInputError, "selected ID"):
            read_review_csv(path, id_column="missing")
        with self.assertRaises(CSVInputError):
            read_review_csv(path, id_column="review_text")

    def test_invalid_utf8_is_not_silently_replaced(self):
        path = self.root / "bad.csv"
        path.write_bytes(b"review_text\nThe caf\xe9 was good.\n")
        with self.assertRaisesRegex(CSVInputError, "UTF-8"):
            read_review_csv(path)

    def test_malformed_quotes_reject_entire_file(self):
        for text in ('review_text\n"unfinished\n', 'review_text\n"review"garbage\n'):
            with self.subTest(text=text), self.assertRaisesRegex(CSVInputError, "Malformed CSV"):
                read_review_csv(self.write_raw(text))

    def test_empty_blank_and_wrong_width_rows_are_retained(self):
        source = read_review_csv(self.write_raw(
            "review_id,review_text\nr1,\n\nr3\nr4,The staff were helpful.,extra\nr5,The food was delicious.\n"
        ))
        self.assertEqual(len(source.rows), 5)
        self.assertEqual([row.ordinal for row in source.rows], list(range(1, 6)))
        self.assertEqual(source.rows[0].issues[0].code, "EMPTY_REVIEW")
        self.assertEqual({i.code for i in source.rows[1].issues}, {"COLUMN_COUNT", "EMPTY_REVIEW"})
        self.assertEqual(source.rows[3].issues[0].code, "COLUMN_COUNT")
        self.assertFalse(source.rows[4].issues)

    def test_oversized_field_is_row_error_and_csv_limit_is_restored(self):
        before = csv.field_size_limit()
        source = read_review_csv(self.write_csv([["large", "x" * 140_000], ["ok", "The food was delicious."]]))
        self.assertEqual(source.rows[0].issues[0].code, "REVIEW_TOO_LONG")
        self.assertFalse(source.rows[1].issues)
        self.assertEqual(csv.field_size_limit(), before)

    def test_file_and_row_limits_fail_before_analysis(self):
        path = self.write_csv([["a", "The staff were helpful."], ["b", "The food was delicious."]])
        for limits in (CSVLimits(max_file_bytes=10), CSVLimits(max_rows=1)):
            with self.subTest(limits=limits), patch("hotel_compiler.batch.analyze_review") as analyzer:
                with self.assertRaises(CSVInputError):
                    analyze_csv(path, limits=limits)
                analyzer.assert_not_called()
        for invalid in (0, -1, True, 1.5):
            with self.subTest(limit=invalid), self.assertRaises(ValueError):
                CSVLimits(max_rows=invalid)

    def test_duplicate_ids_and_text_are_flagged_without_merging(self):
        source = read_review_csv(self.write_csv([
            ["same", "The staff were helpful."], ["same", "The staff were helpful."],
            ["  ", "The service was average."],
        ]))
        self.assertEqual(len(source.rows), 3)
        self.assertTrue(all(r.duplicate_id and r.duplicate_text for r in source.rows[:2]))
        self.assertFalse(source.rows[2].duplicate_id)
        self.assertIsNone(source.rows[2].supplied_review_id)


class BatchEngineTests(BatchTestCase):
    def test_statuses_counts_progress_and_original_pipeline_equivalence(self):
        path = self.write_csv([
            ["a", "The staff were helpful."],
            ["b", "The room was odd but the staff were helpful."],
            ["c", "The air conditioning was glorp."],
            ["d", ""], ["e", "The service was average."],
        ])
        progress = []
        batch = analyze_csv(path, batch_id="demo", progress=lambda done, total: progress.append((done, total)))
        counts = batch.summary()["counts"]
        self.assertEqual([counts[key] for key in ("submitted", "analyzed", "complete", "partial", "unsupported", "invalid_input")],
                         [5, 4, 2, 1, 1, 1])
        self.assertEqual(batch.summary()["coverage"]["complete_percent"], 50)
        self.assertEqual(batch.summary()["coverage"]["with_opinions_percent"], 75)
        self.assertEqual(progress, [(i, 5) for i in range(1, 6)])
        for row in batch.rows:
            if row.analysis:
                expected = analyze_review(row.source.review_text, row.analysis.review_id)
                self.assertEqual(row.analysis, expected)
        self.assertEqual(batch.rows[2].analysis.overall, "Unanalyzed")
        self.assertEqual(batch.rows[4].analysis.overall, "Neutral")
        self.assertIsNone(batch.rows[3].analysis)

    def test_100_and_500_rows_each_match_single_review_analysis(self):
        reviews = ["The staff were extremely helpful.", "The food was bland; the staff were courteous.",
                   "The air conditioning was broken.", "The service was average.",
                   "The room was odd but the staff were helpful."]
        for size in (100, 500):
            with self.subTest(size=size):
                path = self.write_csv([[f"R{i:04d}", reviews[i % len(reviews)]] for i in range(size)])
                batch = analyze_csv(path, batch_id=f"demo-{size}")
                self.assertEqual(len(batch.rows), size)
                self.assertEqual(len({r.row_id for r in batch.rows}), size)
                for row in batch.rows:
                    self.assertEqual(row.analysis, analyze_review(row.source.review_text, row.source.supplied_review_id))

    def test_row_identity_and_detail_are_independent_of_duplicate_supplied_ids(self):
        batch = analyze_csv(self.write_csv([["id", "The staff were helpful."]] * 2), batch_id="same")
        self.assertNotEqual(batch.rows[0].row_id, batch.rows[1].row_id)
        self.assertEqual(batch.rows[0].analysis.review_id, "id")
        self.assertIs(batch.get_row("same:000002"), batch.rows[1])
        with self.assertRaises(KeyError):
            batch.get_row("missing")

    def test_generated_analysis_id_is_reproducible_with_batch_id(self):
        path = self.write_csv([["The staff were helpful."]], header=("review_text",))
        first = analyze_csv(path, batch_id="stable")
        second = analyze_csv(path, batch_id="stable")
        self.assertEqual(first.rows[0].analysis.review_id, "stable:000001")
        self.assertEqual(first.rows, second.rows)
        self.assertEqual(first.analysis_fingerprint, second.analysis_fingerprint)
        self.assertEqual(first.analysis_fingerprint, analysis_fingerprint())

    def test_expanded_patterns_and_evidence_survive_100_and_500_row_exports(self):
        reviews = ["The AC doesn't work properly.", "An out of order elevator.",
                   "Very rude staff.", "The room was spacious.", "The staff were working."]
        for size in (100, 500):
            with self.subTest(size=size):
                path = self.write_csv([[f"R{i}", reviews[i % len(reviews)]] for i in range(size)])
                batch = analyze_csv(path, batch_id=f"expanded-{size}")
                paths = export_batch(batch, self.root / f"expanded-{size}")
                output = json.loads(paths["batch.json"].read_text(encoding="utf-8"))
                self.assertEqual(len(output["rows"]), size)
                for saved in output["rows"]:
                    expected = analyze_review(saved["review_text"], saved["supplied_review_id"]).to_dict(include_trace=True)
                    self.assertEqual(saved["analysis"], json.loads(json.dumps(expected)))

    def test_no_analyzed_rows_has_no_fabricated_coverage(self):
        batch = analyze_csv(self.write_csv([["id", " "]]))
        coverage = batch.summary()["coverage"]
        self.assertEqual(coverage["denominator_count"], 0)
        self.assertIsNone(coverage["complete_percent"])
        self.assertIsNone(coverage["with_opinions_percent"])

    def test_unexpected_row_failure_does_not_abandon_valid_neighbors(self):
        path = self.write_csv([["a", "The staff were helpful."], ["b", "trigger"], ["c", "The food was delicious."]])

        def analyzer(text, identifier):
            if text == "trigger":
                raise RuntimeError("example failure")
            return analyze_review(text, identifier)

        with patch("hotel_compiler.batch.analyze_review", side_effect=analyzer):
            batch = analyze_csv(path)
        self.assertEqual([r.execution_status for r in batch.rows], ["analyzed", "processing_error", "analyzed"])
        self.assertIn("RuntimeError", batch.rows[1].processing_error)
        self.assertEqual(batch.summary()["counts"]["processing_error"], 1)

    def test_shared_resource_failure_aborts_instead_of_becoming_row_errors(self):
        path = self.write_csv([["a", "The staff were helpful."]])
        with patch("hotel_compiler.batch.load_synsets", side_effect=ResourceError("bad resource")), \
                patch("hotel_compiler.batch.analyze_review") as analyzer:
            with self.assertRaises(ResourceError):
                analyze_csv(path)
            analyzer.assert_not_called()
        with patch("hotel_compiler.batch.analyze_review", side_effect=ResourceError("bad resource")):
            with self.assertRaises(ResourceError):
                analyze_csv(path)

    def test_batch_id_validation_and_no_implicit_exports(self):
        path = self.write_csv([["a", "The staff were helpful."]])
        source = read_review_csv(path)
        for identifier in ("", " ", 12):
            with self.subTest(identifier=identifier), self.assertRaises(ValueError):
                analyze_batch(source, batch_id=identifier)
        analyze_batch(source)
        self.assertEqual(list(self.root.iterdir()), [path])


class BatchExportTests(BatchTestCase):
    def make_batch(self):
        return analyze_csv(self.write_csv([
            ["a", "The food was bland; the staff were courteous."],
            ["b", "The room was odd but the staff were helpful."],
            ["c", "The air conditioning was glorp."], ["d", ""],
        ]), batch_id="exports")

    def test_json_has_every_row_and_trace_csvs_join_by_internal_id(self):
        batch = self.make_batch()
        paths = export_batch(batch, self.root / "exports")
        output = json.loads(paths["batch.json"].read_text(encoding="utf-8"))
        self.assertEqual(output, json.loads(json.dumps(batch.to_dict(include_trace=True))))
        self.assertIn("trace", output["rows"][0]["analysis"])
        self.assertIsNone(output["rows"][3]["analysis"])
        with paths["reviews.csv"].open(encoding="utf-8-sig", newline="") as handle:
            reviews = list(csv.DictReader(handle))
        with paths["aspects.csv"].open(encoding="utf-8-sig", newline="") as handle:
            aspects = list(csv.DictReader(handle))
        self.assertEqual(len(reviews), 4)
        self.assertEqual(len(aspects), 3)
        self.assertTrue(all(a["row_id"] in {r["row_id"] for r in reviews} for a in aspects))
        self.assertEqual(reviews[1]["overall_scope"], "recognized clauses only")
        self.assertEqual(reviews[2]["overall"], "Unanalyzed")
        self.assertEqual(reviews[3]["overall"], "")

    def test_formula_strings_are_escaped_only_in_csv_and_numbers_remain_numeric(self):
        original = "  =HYPERLINK(\"bad\")\nThe staff were helpful."
        batch = analyze_csv(self.write_csv([["\t=1+1", original], ["@id", "Room service was slow."]]))
        paths = export_batch(batch, self.root / "out")
        with paths["reviews.csv"].open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(rows[0]["review_text"], "'" + original)
        self.assertEqual(rows[0]["supplied_review_id"], "'\t=1+1")
        output = json.loads(paths["batch.json"].read_text(encoding="utf-8"))
        self.assertEqual(output["rows"][0]["review_text"], original)
        with paths["aspects.csv"].open(encoding="utf-8-sig", newline="") as handle:
            aspects = list(csv.DictReader(handle))
        slow = next(a for a in aspects if a["opinion_term"] == "slow")
        self.assertEqual(float(slow["score"]), -0.5)
        self.assertEqual(slow["review_id"], "'@id")

    def test_existing_export_is_protected_and_new_files_are_cleaned_on_collision(self):
        batch = self.make_batch()
        destination = self.root / "out"
        destination.mkdir()
        existing = destination / "aspects.csv"
        existing.write_text("keep", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            export_batch(batch, destination)
        self.assertEqual(existing.read_text(encoding="utf-8"), "keep")
        self.assertFalse((destination / "reviews.csv").exists())
        self.assertFalse((destination / "batch.json").exists())

    def test_write_failure_cleans_only_owned_files(self):
        batch = self.make_batch()
        destination = self.root / "out"
        destination.mkdir()
        unrelated = destination / "notes.txt"
        unrelated.write_text("keep", encoding="utf-8")
        with patch("hotel_compiler.exports.json.dump", side_effect=OSError("disk error")):
            with self.assertRaises(OSError):
                export_batch(batch, destination)
        self.assertEqual(list(destination.iterdir()), [unrelated])


class BatchCLITests(BatchTestCase):
    def run_cli(self, path, *args):
        return subprocess.run(
            [sys.executable, "-X", "utf8", "-m", "hotel_compiler.batch_cli", str(path), *args],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30,
        )

    def test_complete_batch_exports_and_prints_paths(self):
        path = self.write_csv([["a", "The food was delicious."]])
        destination = self.root / "out"
        process = self.run_cli(path, "--output-dir", str(destination), "--progress")
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertIn("Complete: 1", process.stdout)
        self.assertIn("Processed 1/1", process.stderr)
        self.assertTrue((destination / "batch.json").exists())

    def test_incomplete_batch_is_exported_with_exit_one(self):
        path = self.write_csv([["a", "The AC cannot work."], ["b", ""]])
        destination = self.root / "out"
        process = self.run_cli(path, "--output-dir", str(destination))
        self.assertEqual(process.returncode, 1, process.stderr)
        self.assertIn("Unsupported: 1", process.stdout)
        self.assertIn("Invalid: 1", process.stdout)
        self.assertTrue((destination / "batch.json").exists())

    def test_invalid_files_and_arguments_report_error_without_traceback(self):
        path = self.write_raw("wrong_header\nhello\n")
        for arguments in ([], ["--max-rows", "0"]):
            with self.subTest(arguments=arguments):
                process = self.run_cli(path, "--output-dir", str(self.root / "out"), *arguments)
                self.assertEqual(process.returncode, 2)
                self.assertIn("Error:", process.stderr)
                self.assertNotIn("Traceback", process.stderr)
        self.assertFalse((self.root / "out").exists())

    def test_existing_results_are_not_overwritten(self):
        path = self.write_csv([["a", "The staff were helpful."]])
        destination = self.root / "out"
        self.assertEqual(self.run_cli(path, "--output-dir", str(destination)).returncode, 0)
        before = (destination / "batch.json").read_bytes()
        second = self.run_cli(path, "--output-dir", str(destination))
        self.assertEqual(second.returncode, 2)
        self.assertIn("already exists", second.stderr)
        self.assertEqual((destination / "batch.json").read_bytes(), before)

    @unittest.skipUnless(sys.platform == "win32", "Windows-only launcher")
    def test_windows_batch_launcher(self):
        path = self.write_csv([["a", "The staff were helpful."]])
        destination = self.root / "out"
        process = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
             str(ROOT / "scripts" / "batch.ps1"), str(path), "--output-dir", str(destination)],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30,
        )
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertTrue((destination / "batch.json").exists())


if __name__ == "__main__":
    unittest.main()
