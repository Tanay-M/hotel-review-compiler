"""Create repeatable synthetic CSV batches; not an accuracy benchmark corpus."""

import argparse
import csv
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate 100/500-row demo CSVs from the small mixed-outcome fixture.")
    parser.add_argument("--rows", type=int, default=100, help="Number of reviews, from 1 to 1000 (default: 100).")
    parser.add_argument("--output", type=Path, required=True, help="New CSV filename; existing files are protected.")
    args = parser.parse_args()
    if not 1 <= args.rows <= 1_000:
        parser.error("--rows must be between 1 and 1000")
    try:
        with (ROOT / "examples" / "bulk_demo.csv").open(encoding="utf-8-sig", newline="") as handle:
            reviews = [row["review_text"] for row in csv.DictReader(handle)]
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["review_id", "review_text"])
            for index in range(args.rows):
                writer.writerow([f"DEMO-{index + 1:04d}", reviews[index % len(reviews)]])
    except OSError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    print(f"Created {args.rows} synthetic reviews: {args.output.resolve()}")
    print("Includes repeated text, partial/unsupported reviews, and empty rows; this is not real-world accuracy evidence.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
