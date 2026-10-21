# Hybrid vocabulary expansion using Booking Italy reviews

Implemented 18 October 2026. The SentiWordNet baseline, six categories, fusion
weights, score bands and existing contextual-rule values are preserved.
Fusion/override ablations remain deferred as requested.

The supplied Crawlfeeds file contains 4,367 rows: 3,102 have nonblank review-body
text and 1,265 contain only missing markers in both body fields. Review titles,
ratings, reviewer identity and field headings are excluded from model input.
Nonmissing positive and negative body fields are joined verbatim by a newline.
Rows and duplicates remain present; source IDs and byte/text hashes are retained.

## Changes

- Hybrid aspect phrases: **164 to 671**, including owner/owners, kitchen,
  communication, luggage storage, room furnishings, bathroom fittings, food
  varieties and appliances.
- **497 reviewed lexical forms** cover synonyms, explicit inflections and
  spelling variants. Forms already recognized natively retain native handling.
- Category guards restrict lexical substitutions. Polite maps to courteous for
  Staff/Service, and reliable maps to trustworthy for the permitted categories.
  These are project-curated interpretations, not additional original dictionary
  entries or a formal vocabulary standard.
- Unknown expressions remain unavailable. Factual descriptors are not assigned
  positive scores merely to increase completion. Price/Location and generic
  whole-hotel praise are not forced into the six categories.
- Ambiguous nouns such as cleaner retain noun/adjective checks. Water taxi is
  excluded from Facilities matching so its word water is not misclassified.

## Scoring and trace

Grammar and source spans use the original review. A matched native-unknown form
can be replaced in a separate scoring copy. Both sentiment tools then use the
existing fusion policy. Typographic apostrophes in that copy are normalized for
contraction scope. Original component evidence, effective scoring text, aliases,
effective component scores, fusion and final contextual adjustment are retained.

The UI Scoring tab and hybrid evidence downloads display this distinction.
No library lexicon, SentiWordNet value or existing domain-rule score changes.
Subjectivity is not confidence. Strength after synonym normalization is descriptive
rather than independently calibrated human sentiment intensity.

## Development measurements

| Measure | Before | After |
|---|---:|---:|
| Scored aspect contexts | 11,041 | 12,584 |
| Nonblank bodies with a scored aspect | 2,613 | 2,701 |
| Complete processing | 210 | 244 |
| Partial processing | 2,403 | 2,457 |
| Unsupported processing | 489 | 401 |
| Adjective occurrences without lexical lookup support | 2,025 | 1,217 |

Unrecognized adjective occurrences decrease 39.9%. Some remaining occurrences
are factual descriptors, names or POS errors rather than sentiment words.
The extraction sets differ, so context-count gains are not accuracy.
At least one aspect is scored for 87.07% of the 3,102 nonblank bodies afterwards;
only 7.87% meet the strict whole-review completeness heuristic. Long narratives
and out-of-scope topics still cause Partial status.

This is an inspected vocabulary development corpus. Independent aspect sentiment
gold labels are absent, so accuracy/F1 and unseen generalization are not measured.
The October 21 paper update reruns the annotated benchmark and the earlier
100/200-review samples with the expanded hybrid; see the [paper notes](../output/paper/PAPER_README.md).
The previous manuscript remains archived locally. Booking Italy itself has only
the hybrid before/after audit; it has not yet been compared against SentiWordNet.

## Files and reproduction

Open [the generated report](../output/experiments/2026-10-18/booking-vocabulary/report/README.md)
for tables, source provenance, per-row changes, lexical catalog, remaining gaps,
and PDF/SVG/PNG figures. Its inputs folder has the full two-column CSV and five
UI-ready parts of at most 1,000 rows, preserving every source row ordinal.
Upload a part using `sr.no` and `review` in the hybrid CSV screen.

Public copies are included under [output/datasets/booking_italy](../output/datasets/booking_italy/),
with [attribution and license information](../output/datasets/ATTRIBUTION.md).
The original source bytes match the publisher's Hugging Face release exactly.
Raw reviewer metadata and the local original source archive are not published.

Code:

- `hotel_compiler/hybrid_vocabulary.py`: guarded matching and scoring-copy normalization.
- `hotel_compiler/resources/hybrid_vocabulary.json`: vocabulary catalog and provenance.
- `hotel_compiler/hybrid_nlp.py`: merged aspect lookup and lexical disambiguation.
- `hotel_compiler/hybrid.py`: native scoring/fusion with original and effective evidence.
- `scripts/build_hybrid_vocabulary.py`: explicit catalog builder, not a model learner.
- `scripts/audit_booking_vocabulary.py`: source preparation and full-corpus audit.
- `scripts/report_booking_vocabulary.py`: comparison tables and scientific figures.
- `tests/test_hybrid_vocabulary.py`: preservation, guards, negation and scoring contracts.

Use the before source snapshot for the before audit stage, expanded snapshot for
the after stage, and identical source bytes. Each run creates new evidence folders
and protects prior results. The report includes exact reproduction commands.
