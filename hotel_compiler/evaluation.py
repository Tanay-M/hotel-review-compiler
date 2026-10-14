"""Measure authored aspect/issue/polarity contracts, without a learned model."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

from .batch import analysis_fingerprint
from .pipeline import analyze_review
from .sentiwordnet import ResourceError


def _metrics(rows: list[dict]) -> dict:
    predicted = gold = true_positive = matched_pairs = exact_reviews = status_matches = 0
    statuses, diagnostics, unknown_words = Counter(), Counter(), Counter()
    errors = []
    for row in rows:
        expected, actual = Counter(map(tuple, row["expected"])), Counter(map(tuple, row["actual"]))
        predicted += sum(actual.values())
        gold += sum(expected.values())
        true_positive += sum((actual & expected).values())
        expected_pairs = Counter()
        actual_pairs = Counter()
        for (category, issue, _), count in expected.items():
            expected_pairs[category, issue] += count
        for (category, issue, _), count in actual.items():
            actual_pairs[category, issue] += count
        matched_pairs += sum((actual_pairs & expected_pairs).values())
        status_matches += row["status"] == row["expected_status"]
        matches = actual == expected and row["status"] == row["expected_status"]
        exact_reviews += matches
        statuses[row["status"]] += 1
        diagnostics.update(row["diagnostic_codes"])
        unknown_words.update(row["unknown_words"])
        if not matches:
            errors.append(row)
    precision = true_positive / predicted if predicted else None
    recall = true_positive / gold if gold else None
    f1 = 2 * true_positive / (predicted + gold) if predicted + gold else None
    def percent(value):
        return round(100 * value, 2) if value is not None else None
    total = len(rows)
    return {
        "reviews": total, "status_counts": dict(statuses),
        "complete_percent": percent(statuses["complete"] / total) if total else None,
        "with_opinions_percent": percent((statuses["complete"] + statuses["partial"]) / total) if total else None,
        "predicted_opinions": predicted, "gold_opinions": gold, "matched_tuples": true_positive,
        "tuple_precision_percent": percent(precision), "tuple_recall_percent": percent(recall), "tuple_f1_percent": percent(f1),
        "polarity_on_matched_category_issue_percent": percent(true_positive / matched_pairs) if matched_pairs else None,
        "exact_review_matches": exact_reviews, "status_matches": status_matches,
        "diagnostic_counts": dict(diagnostics), "unknown_word_counts": dict(unknown_words.most_common()),
        "mismatches": errors,
    }


def evaluate_corpus(path: str | Path) -> dict:
    source = Path(path)
    payload = source.read_bytes()
    corpus = json.loads(payload.decode("utf-8-sig"))
    if not isinstance(corpus, dict) or not isinstance(corpus.get("cases"), list) or not corpus["cases"]:
        raise ValueError("Evaluation corpus needs a nonempty cases array.")
    rows = []
    for index, case in enumerate(corpus["cases"], 1):
        if (not isinstance(case, dict) or not isinstance(case.get("text"), str)
                or case.get("status") not in {"complete", "partial", "unsupported"}
                or not isinstance(case.get("expected"), list)
                or case.get("split") not in {"development", "reserved"}):
            raise ValueError(f"Invalid evaluation case {index}.")
        if any(not isinstance(record, list) or len(record) != 3 or not all(isinstance(v, str) for v in record)
               for record in case["expected"]):
            raise ValueError(f"Invalid gold tuple in evaluation case {index}.")
        result = analyze_review(case["text"], f"eval-{index:03d}")
        rows.append({
            "case_id": f"eval-{index:03d}", "split": case["split"], "family": case.get("family", "unspecified"),
            "text": case["text"], "expected_status": case["status"], "status": result.status,
            "expected": case["expected"], "actual": [[r.category, r.issue, r.polarity] for r in result.records],
            "diagnostic_codes": [d.code for d in result.diagnostics],
            "unknown_words": [t.value for t in result.tokens if t.kind == "WORD"],
        })
    return {
        "schema_version": 1, "source_sha256": sha256(payload).hexdigest(),
        "analysis_fingerprint": analysis_fingerprint(), "description": corpus.get("description", ""),
        "matching_rule": "Multiset of category/issue/polarity triples per review; repeated opinions retain multiplicity. Polarity uses matched category/issue counts; no source-span accuracy is inferred.",
        "scope": "Results apply to this labeled corpus only. Authored/reserved contract cases are not independent real-world accuracy evidence.",
        "all": _metrics(rows),
        "splits": {split: _metrics([r for r in rows if r["split"] == split]) for split in ("development", "reserved")},
        "families": {family: _metrics([r for r in rows if r["family"] == family]) for family in sorted({r["family"] for r in rows})},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate manually labeled compiler contract cases.")
    parser.add_argument("corpus")
    parser.add_argument("--output", type=Path, help="Write a new JSON report; existing files are protected.")
    args = parser.parse_args(argv)
    try:
        report = evaluate_corpus(args.corpus)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("x", encoding="utf-8") as handle:
                json.dump(report, handle, indent=2, ensure_ascii=False)
                handle.write("\n")
    except (OSError, ValueError, TypeError, ResourceError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    for label, metrics in [("all", report["all"]), *report["splits"].items()]:
        print(f"{label}: {metrics['reviews']} reviews | complete {metrics['complete_percent']}% | tuple precision {metrics['tuple_precision_percent']}% | recall {metrics['tuple_recall_percent']}% | exact {metrics['exact_review_matches']}/{metrics['reviews']}")
    print(report["scope"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
