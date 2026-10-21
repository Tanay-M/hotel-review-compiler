# Booking vocabulary development results

**Publication update, October 21:** This report retains the October 18 audit. The newer [paper](../../../../paper/PAPER_README.md) incorporates these coverage results and rerun benchmark/sample experiments. Public review-only inputs and license attribution are in [output/datasets](../../../../datasets/README.md). Detailed source metadata, per-row audit files and code snapshots referenced below remain local; published files contain aggregate evidence and the reviewed vocabulary catalog. The paper's earlier draft is archived locally.

The supplied Crawlfeeds Booking Italy file contains 4,367 source rows.
3,102 contain review-body text; 1,265 have no body after removing literal \N missing markers.
Titles, field headings, ratings, hotel/reviewer identity and other metadata are excluded from model input.
Original positive and negative body fields are joined verbatim with a newline. No spelling or wording is rewritten in the input.
Duplicates and missing-body rows remain in the source row sequence. Source SHA-256: `137cec35ddbd678b2bdb1bc93eccb2e844926c8503d3d7f898e274e387933dbd`.

## What changed

Independent hybrid aspect vocabulary increased from 164 to 671 phrases.
The project-curated catalog contains 497 lexical forms, including explicit inflections and spelling variants.
Known native entries take precedence; category guards prevent unrestricted substitution.
For matched native-unknown terms, the tools score a canonical working copy and retain the original component evidence.
Typography normalization in that scoring copy preserves contraction negation and original character spans.
The original review, sentiment lexicons, six categories, fusion weights and existing contextual-rule values are preserved.
These are vocabulary-development changes; fusion/override ablations remain deferred.

| Measure | Before | After |
|---|---:|---:|
| Source rows retained | 4,367 | 4,367 |
| Nonblank review bodies | 3,102 | 3,102 |
| Missing review bodies | 1,265 | 1,265 |
| Aspect phrases | 164 | 671 |
| Reviewed lexical forms | 0 | 497 |
| Reviews with at least one scored aspect | 2,613 | 2,701 |
| Complete processing | 210 | 244 |
| Partial processing | 2,403 | 2,457 |
| Unsupported processing | 489 | 401 |
| Extracted contexts | 12,437 | 13,953 |
| Scored contexts | 11,041 | 12,584 |
| Unscored contexts | 1,396 | 1,369 |
| Adjective occurrences without lexical lookup support | 2,025 | 1,217 |
| Adjective types without lexical lookup support | 609 | 531 |

Additional scored contexts: **1,543**. Adjective instances without lexical lookup support decrease by **39.9%**.
Some unsupported adjective tokens are factual descriptors, names or tagging errors, not missing sentiment words.
The larger extraction set means scored-context counts cannot be interpreted as an identical-case accuracy comparison.

At least one scored aspect is available for 2,613/3,102 (84.24%)
nonblank bodies before expansion and 2,701/3,102 (87.07%) afterwards.
Complete processing applies to only 244/3,102 (7.87%) afterwards.
Many long reviews contain Location/Price topics or unresolved narrative clauses; useful scored aspects coexist with Partial status.
No unsupported or partial review is relabeled Complete to improve the reported percentages.

## Research interpretation

This corpus was inspected to develop the vocabulary. These are descriptive development measurements, not unseen-test accuracy.
There are no independent aspect-polarity annotations, so accuracy, precision, recall and F1 are not reported.
Canonical substitutions are project interpretations; numerical strengths are not independently calibrated human intensity labels.
The SentiWordNet baseline fingerprint and existing hybrid domain-rule hash match the before snapshot.
The earlier paper experiments and manuscript have not been regenerated or replaced.

## Files to inspect

- `coverage_comparison.csv`: numerical table suitable for reporting coverage with the stated denominators.
- `review_changes.csv`: all 4,367 row-level before/after outcomes.
- `lexical_catalog.csv`: every lexical form, canonical expression, category guard and observed adjective frequency.
- `added_aspect_phrases.csv`: the 507 newly recognized aspect phrases.
- `../after/reviews.csv`: one result per original row.
- `../after/contexts.csv`: original contexts, scores, alias matches and scoring copies.
- `../after/unscored_contexts.csv`: remaining scoring gaps.
- `../before/source_snapshot.zip` and `../after/source_snapshot.zip`: reproducible analysis snapshots.
- `../inputs/booking_italy_part_01.csv` through `booking_italy_part_05.csv`: UI-ready parts of at most 1000 rows.
- `../inputs/booking_italy_all.csv`: all original row IDs and prepared review text; use the audit runner for all rows.
- `../inputs/original_crawlfeeds.csv`: byte-identical original CSV, with its original metadata.

In the UI select Hybrid, then CSV & dashboard. Upload a part with columns `sr.no` and `review`.
Missing-body rows appear as invalid input in the UI and are named `empty_body` in this audit.

## Reproduce

Run `scripts/audit_booking_vocabulary.py SOURCE --output-dir NEW_FOLDER --stage before` with the original snapshot,
then the `after` stage with the expanded snapshot. Both must use the exact same source bytes.
Run `scripts/report_booking_vocabulary.py NEW_FOLDER` after both stages.
The builder `scripts/build_hybrid_vocabulary.py` regenerates the explicit reviewed catalog; it does not learn from ratings.
