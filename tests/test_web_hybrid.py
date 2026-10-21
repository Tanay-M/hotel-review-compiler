"""End-to-end UI contracts for the independent hybrid and retained CSV traces."""
import csv
from dataclasses import asdict
import http.client
from io import BytesIO, StringIO
import json
from threading import Thread
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from hotel_compiler.hybrid import HybridDependencyError, analyze_hybrid_review, default_engine
from hotel_compiler.web import create_server


class HybridWebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            default_engine()
        except HybridDependencyError as error:
            raise unittest.SkipTest(str(error))
        cls.server = create_server(port=0)
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(5)

    def request(self, method, path, body=None, content_type="application/json"):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=30)
        try:
            connection.request(method, path, body, {"Content-Type": content_type})
            response = connection.getresponse()
            return response.status, response.read()
        finally:
            connection.close()

    def analyze(self, text, method="hybrid"):
        return self.request("POST", "/api/analyze", json.dumps({"text": text, "review_id": "demo", "method": method}))

    def upload(self, payload, method="hybrid"):
        return self.request("POST", f"/api/batches?method={method}&text_column=review&id_column=sr.no", payload, "text/csv")

    def test_http_hybrid_matches_research_evidence_without_baseline_calls(self):
        text = "The air conditioning wasn't working, but the staff were helpful."
        expected = analyze_hybrid_review(text, "demo")
        with patch("hotel_compiler.web.analyze_review", side_effect=AssertionError("Baseline must not run")):
            status, payload = self.analyze(text)
        actual = json.loads(payload)
        self.assertEqual(status, 200)
        self.assertEqual(actual["method"], "hybrid")
        self.assertEqual(actual["review_score"], expected.aspect_mean_score)
        self.assertEqual(actual["status"], expected.aspect_analysis_status)
        self.assertEqual(actual["overall"], "Mixed")
        self.assertEqual(actual["trace"]["language"], json.loads(json.dumps(asdict(expected.language))))
        self.assertEqual(actual["whole_text"], json.loads(json.dumps(asdict(expected.whole_text))))
        self.assertEqual(actual["trace"]["sentiment_evaluation"], json.loads(json.dumps([asdict(r.evidence) for r in expected.records])))

    def test_missing_contexts_stay_unavailable_in_tables_aggregation_and_downloads(self):
        source = b"sr.no,review\n1,The room was glorp but the staff were helpful.\n2,The location was wonderful.\n3,\n"
        status, payload = self.upload(source)
        self.assertEqual(status, 200, payload)
        batch = json.loads(payload)
        self.assertEqual(len(batch["rows"]), 3)
        self.assertEqual(batch["method"], "hybrid")
        row = batch["rows"][0]
        self.assertEqual(row["analysis"]["status"], "partial")
        self.assertIsNone(row["analysis"]["review_score"])
        self.assertIsNone(row["analysis"]["records"][0]["score"])
        self.assertEqual(batch["rows"][1]["analysis"]["status"], "unsupported")
        self.assertGreater(batch["rows"][1]["analysis"]["whole_text"]["score"], 0)
        self.assertEqual(batch["rows"][2]["execution_status"], "invalid_input")
        groups = batch["report"]["aggregation"]["views"]["complete_and_partial"]["categories"]
        room = next(g for g in groups if g["category"] == "Room")
        self.assertEqual(room["mentioned_reviews"], 0)
        self.assertIsNone(room["average_score"])
        status, payload = self.request("GET", f"/api/batches/{batch['batch_id']}/download/reviews")
        self.assertEqual(status, 200)
        rows = list(csv.DictReader(StringIO(payload.decode("utf-8-sig"))))
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["review_score"], "")
        self.assertEqual(rows[0]["method"], "hybrid")
        self.assertIn("Unavailable", rows[0]["aspect_results"])
        status, archive = self.request("GET", f"/api/batches/{batch['batch_id']}/download/paper")
        self.assertEqual(status, 200)
        with ZipFile(BytesIO(archive)) as zipped:
            evidence = list(csv.DictReader(StringIO(zipped.read("hybrid_evidence.csv").decode("utf-8-sig"))))
            self.assertEqual(len(evidence), 2)
            self.assertEqual(evidence[0]["final_score"], "")
            self.assertIn(b"hybrid", zipped.read("run_metadata.csv"))

    def test_every_csv_row_has_matching_stored_research_trace_and_clear_works(self):
        lines = ["sr.no,review"] + [f"{i},The staff were helpful." for i in range(1, 101)]
        status, payload = self.upload("\n".join(lines).encode())
        self.assertEqual(status, 200)
        batch = json.loads(payload)
        self.assertEqual(len(batch["rows"]), 100)
        self.assertEqual(batch["summary"]["counts"]["complete"], 100)
        self.assertNotIn("trace", batch["rows"][0]["analysis"])
        for ordinal in (1, 50, 100):
            status, detail = self.request("GET", f"/api/batches/{batch['batch_id']}/reviews/{ordinal}")
            self.assertEqual(status, 200)
            actual = json.loads(detail)["analysis"]
            self.assertEqual(actual["trace"]["sentiment_evaluation"][0]["score"],
                             analyze_hybrid_review("The staff were helpful.").records[0].score)
        self.assertEqual(self.request("DELETE", f"/api/batches/{batch['batch_id']}")[0], 200)
        self.assertEqual(self.request("GET", f"/api/batches/{batch['batch_id']}")[0], 404)

    def test_invalid_methods_and_missing_dependencies_are_visible_and_preserve_batch(self):
        source = b"sr.no,review\n1,The staff were helpful.\n"
        batch = json.loads(self.upload(source, "sentiwordnet")[1])
        for method in ("unknown", None, [], 5):
            self.assertEqual(self.analyze("The room was clean.", method)[0], 400)
        self.assertEqual(self.upload(source, "unknown")[0], 400)
        with patch("hotel_compiler.web_analysis.default_engine", side_effect=HybridDependencyError("Install research dependencies")):
            self.assertEqual(self.upload(source)[0], 503)
        self.assertEqual(self.request("GET", f"/api/batches/{batch['batch_id']}")[0], 200)
        self.assertEqual(self.request("GET", "/api/health")[0], 200)


if __name__ == "__main__":
    unittest.main()
