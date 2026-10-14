import http.client
import json
from pathlib import Path
import subprocess
import sys
from threading import Thread
import unittest

from hotel_compiler import analyze_review
from hotel_compiler.web import MAX_BODY_BYTES, create_server


ROOT = Path(__file__).resolve().parents[1]


class WebDemoTests(unittest.TestCase):
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
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            connection.request(method, path, body=body, headers=headers or {})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def analyze(self, text, review_id="demo-web"):
        return self.request("POST", "/api/analyze", json.dumps({"text": text, "review_id": review_id}).encode("utf-8"), {"Content-Type": "application/json"})

    def test_browser_assets_are_served_with_the_correct_types(self):
        for path, content_type in [("/", "text/html"), ("/app.js", "text/javascript"), ("/styles.css", "text/css"), ("/favicon.svg", "image/svg+xml")]:
            with self.subTest(path=path):
                status, headers, payload = self.request("GET", path)
                self.assertEqual(status, 200)
                self.assertTrue(headers["Content-Type"].startswith(content_type))
                self.assertTrue(payload)
                self.assertEqual(headers["Cache-Control"], "no-store")

    def test_web_result_and_trace_match_the_public_compiler(self):
        text = "The room was not clean, but the staff were very helpful."
        status, _, payload = self.analyze(text)
        self.assertEqual(status, 200)
        expected = json.loads(json.dumps(analyze_review(text, "demo-web").to_dict(include_trace=True)))
        self.assertEqual(json.loads(payload), expected)

    def test_unicode_is_preserved_by_the_web_adapter(self):
        text = "The Wi‑Fi wasn’t very reliable."
        status, _, payload = self.analyze(text)
        result = json.loads(payload)
        self.assertEqual(status, 200)
        self.assertEqual(result["review_text"], text)
        self.assertEqual(result["records"][0]["opinion_expression"], "not very reliable")

    def test_partial_unsupported_and_empty_reviews_remain_valid_results(self):
        for text, expected in [
            ("The room was odd but the staff were helpful.", "partial"),
            ("The room was glorp.", "unsupported"),
            ("", "unsupported"),
        ]:
            with self.subTest(text=text):
                status, _, payload = self.analyze(text)
                self.assertEqual(status, 200)
                result = json.loads(payload)
                self.assertEqual(result["status"], expected)
                self.assertTrue(result["diagnostics"])

    def test_demo_configuration_exposes_actual_vocabulary(self):
        status, _, payload = self.request("GET", "/api/config")
        result = json.loads(payload)
        self.assertEqual(status, 200)
        self.assertEqual(len(result["categories"]), 6)
        self.assertEqual(result["aspects"]["room service"]["category"], "Service")
        self.assertEqual(result["opinions"]["clean"]["issue"], "Cleanliness")
        self.assertTrue(result["examples"])
        self.assertEqual(result["opinion_aliases"]["work"]["canonical"], "working")
        self.assertIn("does", result["auxiliaries"])

    def test_expanded_language_and_new_evidence_match_core_over_http(self):
        for text in ("The AC doesn't work properly.", "An out of order elevator.",
                     "A comfortable bed.", "The staff were working."):
            with self.subTest(text=text):
                status, _, payload = self.analyze(text)
                self.assertEqual(status, 200)
                expected = json.loads(json.dumps(analyze_review(text, "demo-web").to_dict(include_trace=True)))
                self.assertEqual(json.loads(payload), expected)

    def test_malformed_json_and_wrong_types_get_readable_errors(self):
        for payload in [b"{", b"[]", b'{"text":42}', b'{"review_id":"r"}', b'\xff']:
            with self.subTest(payload=payload):
                status, _, body = self.request("POST", "/api/analyze", payload, {"Content-Type": "application/json"})
                self.assertEqual(status, 400)
                self.assertTrue(json.loads(body)["error"])

    def test_request_and_review_size_limits_are_enforced(self):
        status, _, payload = self.analyze("x" * 10_001)
        self.assertEqual(status, 400)
        self.assertIn("10,000", json.loads(payload)["error"])
        status, _, _ = self.request("POST", "/api/analyze", b"x" * (MAX_BODY_BYTES + 1), {"Content-Type": "application/json"})
        self.assertEqual(status, 413)

    def test_non_json_requests_are_rejected(self):
        status, _, _ = self.request("POST", "/api/analyze", "room clean", {"Content-Type": "text/plain"})
        self.assertEqual(status, 415)

    def test_static_routing_does_not_expose_project_files(self):
        for path in ["/../README.md", "/hotel_compiler/resources/domain.json", "/.git/config", "/does-not-exist"]:
            with self.subTest(path=path):
                status, _, _ = self.request("GET", path)
                self.assertEqual(status, 404)

    def test_foreign_host_and_origin_are_rejected(self):
        status, _, _ = self.request("GET", "/", headers={"Host": "unrelated.example"})
        self.assertEqual(status, 400)
        status, _, _ = self.request("POST", "/api/analyze", b'{"text":"room clean"}', {
            "Content-Type": "application/json", "Origin": "https://unrelated.example",
        })
        self.assertEqual(status, 403)

    def test_same_review_id_does_not_create_hidden_persistence(self):
        first = json.loads(self.analyze("The room was clean.", "same-id")[2])
        second = json.loads(self.analyze("The staff were rude.", "same-id")[2])
        self.assertEqual(first["records"][0]["category"], "Room")
        self.assertEqual(second["records"][0]["category"], "Staff")
        self.assertEqual(len(second["records"]), 1)
        self.assertEqual(self.request("GET", "/api/reviews")[0], 404)

    def test_server_is_local_only(self):
        with self.assertRaises(ValueError):
            create_server("0.0.0.0", 0)

    @unittest.skipUnless(sys.platform == "win32", "Windows-only launcher")
    def test_windows_web_launcher_forwards_options(self):
        process = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "scripts" / "serve.ps1"), "--help"],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=20,
        )
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertIn("web demo", process.stdout)
        self.assertIn("--port", process.stdout)


if __name__ == "__main__":
    unittest.main()
