import csv
from io import BytesIO, StringIO
import http.client
import json
from pathlib import Path
from threading import Event, Thread
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from hotel_compiler import analyze_review
from hotel_compiler.csv_input import CSVInputError, parse_review_csv, read_review_csv
from hotel_compiler.web import create_server
from hotel_compiler.web_batch import BatchStore


ROOT = Path(__file__).resolve().parents[1]


class BulkWebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = create_server(port=0)
        cls.port = cls.server.server_port
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=15)
        try:
            connection.request(method, path, body=body, headers=headers or {})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def upload(self, payload, query="", headers=None):
        return self.request("POST", "/api/batches" + query, payload, {"Content-Type": "text/csv", **(headers or {})})

    def demo(self, size=12):
        status, _, payload = self.request("GET", f"/api/demo.csv?rows={size}")
        self.assertEqual(status, 200)
        return payload

    def test_in_memory_reader_matches_file_contract_and_original_byte_hash(self):
        path = ROOT / "examples/bulk_demo.csv"
        actual = parse_review_csv(path.read_bytes(), source_name=path.name)
        self.assertEqual(actual, read_review_csv(path))
        for payload in (b"", b"text\nhello\n", b"review_text\n\xff", b'review_text\n"unterminated'):
            with self.subTest(payload=payload), self.assertRaises(CSVInputError):
                parse_review_csv(payload)

    def test_csv_upload_returns_all_rows_without_all_traces_and_same_aggregation(self):
        status, _, payload = self.upload(self.demo())
        self.assertEqual(status, 200)
        result = json.loads(payload)
        self.assertEqual(len(result["rows"]), 12)
        self.assertEqual(result["summary"]["counts"]["complete"], 9)
        self.assertEqual(result["report"]["aggregation"]["views"]["complete_reviews"]["overall_counts"],
                         {"Positive": 3, "Negative": 2, "Mixed": 3, "Neutral": 1})
        self.assertNotIn("trace", result["rows"][0]["analysis"])
        self.assertIsNone(result["rows"][9]["analysis"])
        self.assertEqual(result["rows"][9]["execution_status"], "invalid_input")

    def test_all_500_individual_outputs_and_traces_match_standalone_results(self):
        status, _, payload = self.upload(self.demo(500))
        self.assertEqual(status, 200)
        batch = json.loads(payload)
        self.assertEqual(len(batch["rows"]), 500)
        self.assertEqual(len({row["row_id"] for row in batch["rows"]}), 500)
        for row in batch["rows"]:
            status, _, data = self.request("GET", f"/api/batches/{batch['batch_id']}/reviews/{row['row_number']}")
            self.assertEqual(status, 200)
            detail = json.loads(data)
            self.assertEqual(detail["review_text"], row["review_text"])
            if row["execution_status"] == "analyzed":
                expected = analyze_review(row["review_text"], row["supplied_review_id"] or row["row_id"]).to_dict(include_trace=True)
                self.assertEqual(detail["analysis"], json.loads(json.dumps(expected)))
            else:
                self.assertIsNone(detail["analysis"])

    def test_100_row_csv_and_paper_zip_have_one_review_row_per_input_and_scoped_tables(self):
        batch = json.loads(self.upload(self.demo(100))[2])
        status, headers, payload = self.request("GET", f"/api/batches/{batch['batch_id']}/download/reviews")
        self.assertEqual(status, 200)
        self.assertIn("attachment", headers["Content-Disposition"])
        rows = list(csv.DictReader(StringIO(payload.decode("utf-8-sig"))))
        self.assertEqual(len(rows), 100)
        self.assertEqual(rows[-1]["row_number"], "100")
        self.assertIn("aspect_results", rows[0])
        self.assertIn("Staff / Helpfulness", rows[0]["aspect_results"])
        status, _, payload = self.request("GET", f"/api/batches/{batch['batch_id']}/download/paper")
        self.assertEqual(status, 200)
        with ZipFile(BytesIO(payload)) as archive:
            self.assertEqual(set(archive.namelist()), {"reviews.csv", "aspects.csv", "category_summary.csv", "issue_summary.csv", "overall_summary.csv", "coverage.csv", "run_metadata.csv", "conclusions.txt", "README.txt"})
            self.assertFalse(any(name.endswith(".json") for name in archive.namelist()))
            categories = list(csv.DictReader(StringIO(archive.read("category_summary.csv").decode("utf-8-sig"))))
            self.assertEqual(len(categories), 12)
            self.assertEqual({row["scope"] for row in categories}, {"complete_reviews", "complete_and_partial"})
            absent = next(row for row in categories if row["category"] == "Cleanliness")
            self.assertEqual(absent["equal_review_mean_score"], "")
            metadata = dict(csv.reader(StringIO(archive.read("run_metadata.csv").decode("utf-8-sig"))))
            self.assertEqual(metadata["source_sha256"], batch["input"]["sha256"])
            self.assertIn("Not measured", metadata["accuracy_precision_recall_f1"])

    def test_custom_columns_bom_unicode_multiline_and_formula_safeguards_survive(self):
        payload = '\ufeffid,comment\r\n"=1+1","The AC doesn’t work properly.\nThe staff were helpful."\r\n'.encode("utf-8")
        status, _, body = self.upload(payload, "?text_column=comment&id_column=id", {"X-File-Name": "reviews%20demo.csv"})
        self.assertEqual(status, 200)
        result = json.loads(body)
        self.assertEqual(result["input"]["source_name"], "reviews demo.csv")
        self.assertEqual(result["rows"][0]["supplied_review_id"], "=1+1")
        status, _, downloaded = self.request("GET", f"/api/batches/{result['batch_id']}/download/reviews")
        rows = list(csv.DictReader(StringIO(downloaded.decode("utf-8-sig"))))
        self.assertEqual(rows[0]["supplied_review_id"], "'=1+1")
        self.assertIn("doesn’t", rows[0]["review_text"])

    def test_bad_upload_preserves_previous_run_and_new_success_replaces_it(self):
        previous = json.loads(self.upload(self.demo())[2])["batch_id"]
        self.assertEqual(self.upload(b"bad_header\nreview\n")[0], 400)
        self.assertEqual(self.request("GET", f"/api/batches/{previous}")[0], 200)
        current = json.loads(self.upload(self.demo())[2])["batch_id"]
        self.assertNotEqual(previous, current)
        self.assertEqual(self.request("GET", f"/api/batches/{previous}/reviews/1")[0], 404)

    def test_row_limits_and_route_validation(self):
        oversized = b"review_text\n" + b"Staff helpful.\n" * 1001
        self.assertEqual(self.upload(oversized)[0], 400)
        self.assertEqual(self.upload(self.demo(), "?text_column=review_text&text_column=x")[0], 400)
        self.assertEqual(self.request("GET", "/api/demo.csv?rows=999")[0], 400)
        batch_id = json.loads(self.upload(self.demo())[2])["batch_id"]
        for suffix in ("reviews/0", "reviews/13", "download/unknown", "../README.md"):
            self.assertEqual(self.request("GET", f"/api/batches/{batch_id}/{suffix}")[0], 404)

    def test_upload_type_size_and_foreign_origin_rejected(self):
        self.assertEqual(self.upload(b"", headers={"Content-Length": str(10 * 1024 * 1024 + 1)})[0], 413)
        self.assertEqual(self.upload(b"review_text\nStaff helpful.", headers={"Content-Type": "application/json"})[0], 415)
        self.assertEqual(self.upload(self.demo(), headers={"Origin": "https://foreign.example"})[0], 403)

    def test_explicit_clear_removes_server_memory_and_has_origin_checks(self):
        batch_id = json.loads(self.upload(self.demo())[2])["batch_id"]
        self.assertEqual(self.request("DELETE", f"/api/batches/{batch_id}", headers={"Origin": "https://foreign.example"})[0], 403)
        self.assertEqual(self.request("DELETE", f"/api/batches/{batch_id}")[0], 200)
        self.assertEqual(self.request("GET", f"/api/batches/{batch_id}")[0], 404)
        self.assertEqual(self.request("DELETE", f"/api/batches/{batch_id}")[0], 404)

    def test_other_requests_remain_available_and_parallel_upload_is_rejected(self):
        previous = json.loads(self.upload(self.demo())[2])["batch_id"]
        entered, release = Event(), Event()
        from hotel_compiler.web_batch import analyze_batch

        def waiting(source):
            entered.set()
            if not release.wait(10):
                raise RuntimeError("test upload stalled")
            return analyze_batch(source)

        response = []
        demo = self.demo()
        with patch("hotel_compiler.web_batch.analyze_batch", side_effect=waiting):
            thread = Thread(target=lambda: response.append(self.upload(demo)))
            thread.start()
            try:
                self.assertTrue(entered.wait(5))
                self.assertEqual(self.request("GET", "/api/health")[0], 200)
                self.assertEqual(self.request("GET", f"/api/batches/{previous}/reviews/1")[0], 200)
                self.assertEqual(self.upload(demo)[0], 409)
            finally:
                release.set()
                thread.join(timeout=10)
        self.assertEqual(response[0][0], 200)

    def test_store_failure_releases_lock_and_no_automatic_file_outputs(self):
        store = BatchStore()
        with self.assertRaises(CSVInputError):
            store.submit(b"broken")
        session = store.submit(self.demo())
        self.assertIs(store.get(session.batch.batch_id), session)
        store.clear(session.batch.batch_id)
        with self.assertRaises(KeyError):
            store.get(session.batch.batch_id)

    def test_dashboard_assets_are_packaged_and_user_outputs_are_tables(self):
        status, _, asset = self.request("GET", "/dashboard.js")
        self.assertEqual(status, 200)
        self.assertIn(b"renderReviewTable", asset)
        html = self.request("GET", "/")[2]
        self.assertIn(b"One review. One row.", html)
        self.assertIn(b"Report tables ZIP", html)
        self.assertNotIn(b"Download JSON", html)
        script = self.request("GET", "/app.js")[2]
        self.assertNotIn(b"rawJSON", script)


if __name__ == "__main__":
    unittest.main()
