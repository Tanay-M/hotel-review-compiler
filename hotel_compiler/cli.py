"""Single-review command-line demonstration."""

import argparse
import json
import sys

from .models import AnalysisResult
from .pipeline import analyze_review
from .sentiwordnet import ResourceError


def _report(result: AnalysisResult) -> str:
    lines = [
        "TEAM 17 | HOTEL REVIEW COMPILER", "",
        f"Review: {result.review_text}", f"Review ID: {result.review_id}",
        f"Analysis: {result.status}", "",
    ]
    if result.records:
        rows = [("Category", "Issue", "Opinion", "Polarity", "Score", "Strength")]
        rows.extend((r.category, r.issue, r.opinion_expression, r.polarity, f"{r.score:+.4f}", r.strength) for r in result.records)
        widths = [max(len(row[i]) for row in rows) for i in range(6)]
        for i, row in enumerate(rows):
            lines.append(" | ".join(cell.ljust(width) for cell, width in zip(row, widths)))
            if i == 0:
                lines.append("-+-".join("-" * width for width in widths))
    else:
        lines.append("No supported aspect-opinion records were found.")
    qualifier = " (analyzed clauses only)" if result.status == "partial" else ""
    lines.extend(["", f"Overall: {result.overall}{qualifier}"])
    score = f"{result.review_score:+.6f}" if result.review_score is not None else "Unavailable"
    lines.append(f"Review score: {score} ({result.review_score_scope})")
    lines.append(f"Net score band: {result.net_score_band}")
    if result.diagnostics:
        lines.extend(["", "Diagnostics:"])
        for diagnostic in result.diagnostics:
            lines.append(
                f"  [{diagnostic.stage}/{diagnostic.code}] "
                f"characters {diagnostic.start}:{diagnostic.end}: {diagnostic.message}"
            )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compile a controlled hotel review into aspect-level sentiment records."
    )
    parser.add_argument("review", nargs="?", help="Review text, enclosed in quotes.")
    parser.add_argument("--review-id", help="Optional external review identifier.")
    parser.add_argument("--json", action="store_true", help="Print structured JSON instead of a table.")
    parser.add_argument("--trace", action="store_true", help="Include all compiler stages.")
    args = parser.parse_args(argv)
    # Unicode review text should work in Windows terminals and redirected files.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    try:
        text = args.review
        if text is None:
            text = input("Hotel review: ") if sys.stdin.isatty() else sys.stdin.read()
        result = analyze_review(text, args.review_id)
    except (ValueError, TypeError, ResourceError, EOFError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result.to_dict(include_trace=args.trace), indent=2, ensure_ascii=False))
    else:
        print(_report(result))
        if args.trace:
            print("\nCOMPILER TRACE")
            print(json.dumps(result.to_dict(include_trace=True)["trace"], indent=2, ensure_ascii=False))
    return 0 if result.status == "complete" else 1

