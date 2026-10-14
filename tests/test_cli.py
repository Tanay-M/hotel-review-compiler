import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args, input_text=None):
    return subprocess.run(
        [sys.executable, "-X", "utf8", "-m", "hotel_compiler", *args],
        cwd=ROOT, input=input_text, capture_output=True, text=True, encoding="utf-8",
        timeout=20,
    )


class CommandLineTests(unittest.TestCase):
    def test_json_trace_is_machine_readable(self):
        process = run_cli("The room was not clean, but the staff were very helpful.", "--json", "--trace", "--review-id", "demo")
        self.assertEqual(process.returncode, 0, process.stderr)
        output = json.loads(process.stdout)
        self.assertEqual(output["overall"], "Mixed")
        self.assertEqual(len(output["trace"]["syntax_analysis"]["clauses"]), 2)

    def test_partial_output_uses_exit_one_and_preserves_results(self):
        process = run_cli("The room was odd but the staff were helpful.", "--json")
        self.assertEqual(process.returncode, 1)
        self.assertEqual(json.loads(process.stdout)["records"][0]["category"], "Staff")

    def test_text_report_mentions_partial_scope(self):
        process = run_cli("The room was odd but the staff were helpful.")
        self.assertIn("analyzed clauses only", process.stdout)
        self.assertIn("Diagnostics:", process.stdout)

    def test_standard_input_and_unicode_are_supported(self):
        process = run_cli("--json", input_text="The room wasn’t clean.")
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(json.loads(process.stdout)["records"][0]["polarity"], "Negative")

    def test_invalid_input_has_no_traceback(self):
        process = run_cli("room clean", "--review-id", "")
        self.assertEqual(process.returncode, 2)
        self.assertIn("Error:", process.stderr)
        self.assertNotIn("Traceback", process.stderr)

    @unittest.skipUnless(sys.platform == "win32", "Windows-only launcher")
    def test_windows_launcher_finds_a_usable_runtime(self):
        process = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
             str(ROOT / "scripts" / "run.ps1"), "The room was clean.", "--json"],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=20,
        )
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(json.loads(process.stdout)["records"][0]["category"], "Room")


if __name__ == "__main__":
    unittest.main()
