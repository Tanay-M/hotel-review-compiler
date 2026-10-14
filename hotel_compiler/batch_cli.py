"""Terminal entry point for CSV batches and explicit result exports."""

import argparse
import sys

from .batch import analyze_csv
from .csv_input import CSVLimits
from .exports import export_batch
from .reporting import build_report, render_report
from .sentiwordnet import ResourceError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze hotel review CSVs; export individual results and evidence-backed summaries.")
    parser.add_argument("csv_file", help="CSV with a review_text header by default.")
    parser.add_argument("--output-dir", required=True, help="Destination for individual CSV/JSON outputs, summary.json, and report.txt; existing files are protected.")
    parser.add_argument("--text-column", default="review_text", help="Review text header (default: review_text).")
    parser.add_argument("--id-column", default="review_id", help="ID header (default review_id may be absent).")
    parser.add_argument("--batch-id", help="Optional batch ID for reproducible row identities.")
    parser.add_argument("--max-rows", type=int, default=1_000, help="Maximum data rows (default: 1000).")
    parser.add_argument("--progress", action="store_true", help="Print progress every 25 rows and at completion.")
    parser.add_argument("--include-partial", action="store_true", help="Also display a separate recognized-opinions view including partial reviews; primary scope remains complete reviews.")
    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    def report_progress(done: int, total: int) -> None:
        if done % 25 == 0 or done == total:
            print(f"Processed {done}/{total} reviews", file=sys.stderr)

    try:
        batch = analyze_csv(
            args.csv_file, text_column=args.text_column, id_column=args.id_column,
            limits=CSVLimits(max_rows=args.max_rows), batch_id=args.batch_id,
            progress=report_progress if args.progress else None,
        )
        paths = export_batch(batch, args.output_dir, include_partial_report=args.include_partial)
    except FileExistsError:
        print("Error: An export file already exists. Choose a different --output-dir; existing results were preserved.", file=sys.stderr)
        return 2
    except (OSError, ValueError, TypeError, ResourceError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    summary = batch.summary()
    counts = summary["counts"]
    print(f"TEAM 17 | CSV BATCH {batch.batch_id}")
    print(f"Submitted: {counts['submitted']} | Analyzed: {counts['analyzed']} | Invalid: {counts['invalid_input']} | Processing errors: {counts['processing_error']}")
    print(f"Complete: {counts['complete']} | Partial: {counts['partial']} | Unsupported: {counts['unsupported']} | Opinions: {counts['extracted_opinions']}")
    coverage = summary["coverage"]
    if coverage["denominator_count"]:
        print(f"Complete coverage: {coverage['complete_percent']:.2f}% of {coverage['denominator_count']} analyzed rows; not measured accuracy.")
    else:
        print("Coverage: unavailable; no rows were analyzed.")
    print(f"Duplicate text rows: {counts['duplicate_text_rows']} | Duplicate ID rows: {counts['duplicate_id_rows']} (retained separately)")
    print(f"Analysis time: {batch.elapsed_seconds:.3f}s")
    print(render_report(build_report(batch), include_partial=args.include_partial), end="")
    for name, path in paths.items():
        print(f"{name}: {path.resolve()}")
    # Incomplete batches still export usable rows. Code 2 means no complete
    # export; code 1 signals that some rows need inspection.
    return 1 if any(counts[key] for key in ("invalid_input", "processing_error", "partial", "unsupported")) else 0


if __name__ == "__main__":
    raise SystemExit(main())
