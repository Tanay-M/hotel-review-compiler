# Real review samples and the two-system comparison

Prepared 14 October 2026.

**Publication update, October 21:** This document records the original sampling stage; its implementation-status statements describe that date. Both systems are now implemented. Reviewed Booking samples, Booking Italy inputs and the optional TripAdvisor CSV are now versioned with [attribution](../output/datasets/ATTRIBUTION.md); raw archives and detailed local metadata maps remain ignored. SemEval text/XML is excluded pending redistribution permission. See the [current dataset index](../output/datasets/README.md) and [updated paper](../output/paper/PAPER_README.md).

## Main systems

The paper will compare two systems:

1. The existing SentiWordNet compiler.
2. A hybrid using VADER and TextBlob together.

The hybrid's component scores can be retained for explanations and optional ablations. They are not three main comparison systems. The fusion policy and strength thresholds still need implementation and validation. No scoring or WebUI changes are made by sample preparation.

## Where to open the data

Open `output/datasets/` in the project folder. Double-click a CSV in Excel, or open it in Codex. CSV stores one logical record per review; embedded newlines are quoted so they remain in the same cell.

| File | Contents | Intended use |
|---|---|---|
| real_hotel_demo_100.csv | 100 selected original Booking.com feedback records, only sr.no and review | A clearly scoped demonstration of the supported aspect language |
| real_hotel_random_200.csv | 200 random eligible Booking.com feedback records, only sr.no and review | Broader behavior/coverage testing; gold labels would still be needed for aspect accuracy |
| semeval_hotels_266_sentences.csv | All 266 original sentences from the 30-review hotel benchmark, only sr.no and review | Readable input view; XML and source IDs retain the authoritative annotations and review grouping |
| tripadvisor_original_20491.csv | Unchanged extracted source CSV with Review and Rating | View the full 20,491-row rating dataset; not the two-column demo input |

The original large Booking dataset stays compressed in `data/vendor/real-hotel-research/booking_515k.zip`. No 515,738-row expanded CSV is required for our experiment. Other raw files are the TripAdvisor ZIP and SemEval XML in the same raw-source folder.

## What was selected for the demo

The demonstration is intentionally restricted to short, explicit aspect-predicate language and configured opinion vocabulary. It is not a random population sample and is not a basis for claiming real-world accuracy.

The reproducible preparation script is `scripts/prepare_real_review_samples.py`, seed 17102026. It streams the source archive and preserves source row references. Original feedback fields are retained separately in provenance. Input preparation trims surrounding whitespace and removes exact No Positive/No Negative missing-field placeholders. It does not repair spelling, invent punctuation or rewrite sentiment.

The broad pool removes blank/nonalphabetic feedback, reviews over 10,000 characters and duplicate text under case/whitespace normalization. There are 494,579 unique eligible feedback records from 515,738 source rows; 20,914 were duplicate normalized texts and 245 had no alphabetic feedback. This pool is not independently language-verified.

For the demo, require:

- Exactly one substantive supplied feedback field, preserved in full.
- Length 15–180 characters and 3–30 whitespace-separated words.
- A whole-text form consisting of an optional The, an explicit aspect, a copula (is/are/was/were), optional configured modifier forms and one canonical opinion word.
- An aspect from one of six lexical selection groups, with no explicit location/price/value expressions from the published exclusion pattern.
- No non-ASCII alphabetic characters. This is a simple scope heuristic, not reliable English language identification.
- The final opinion word must appear in the current controlled canonical vocabulary. This is an explicit model-informed demonstration restriction, not evidence of generalization.

Source records are reservoir-sampled within lexical groups, shuffled and selected under these quotas: Room 20, Staff 20, Service 15, Food 20, Cleanliness 2, Facilities 23. These groups guide sampling; they are not independent gold category annotations. For example, facilities keywords can overlap the compiler's aspect taxonomy. Every input still contains only the serial number and original review text.

A broader content-only pilot was inspected first and produced 72 complete and 28 unsupported results. That informed the decision to make the demo's vocabulary restriction explicit. The pilot and its source map remain in `output/datasets/provenance/content_only_pilot_100.csv` and `content_only_pilot_100_sources.csv`. Do not claim the final criteria were registered before this pilot or use this demo as an untouched test set. The script does not call a sentiment method to accept or reject individual source records.

## Separate random sample and benchmark

The 200-review sample is selected from the broad eligible pool without applying the demo's vocabulary, grammar, length-to-180, category or location/price restrictions. It is random conditional on the documented basic eligibility and deduplication. Its parent source rows do not overlap the final demo. Exact normalized full texts are unique across the samples. It may contain unsupported topics, missing punctuation, mixed aspects and language noise; retain those rather than dropping unfavorable results.

The full SemEval benchmark is also retained. Its 266 rows are sentences, not 266 independent reviews. Parent review IDs and sentence IDs are stored in provenance, and the original XML preserves all gold annotations. Group by the original 30 reviews for splitting and uncertainty estimates. Any taxonomy adaptation must be declared separately.

Use the curated 100 reviews to demonstrate current capabilities. Use gold-labeled, consistently scoped evaluation to compare the two systems in the paper. The random sample supports broader coverage/error analysis until annotated. Published metrics must specify the actual selected population and cannot describe curated demo coverage as accuracy on the original 515K corpus.

## Provenance and verification

`output/datasets/provenance/` contains separate source maps, source field contents, original reviewer scores, source row IDs and review hashes. These details are not added to the two-column inputs. `selection_summary.csv` records the seed, counts, vocabulary hash and restrictions. The original download hashes and dataset statistics remain in `output/research/real-datasets-2026-10-14/`.

Verification checks the CSV headers, row counts, serial numbers, nonempty text, duplicate handling, source IDs and exact source-text reconstruction. The original TripAdvisor extraction is unchanged byte-for-byte from its archive member. Sample files use UTF-8 with BOM for Excel compatibility. Raw datasets and generated samples remain ignored by Git; the script and protocol can be versioned without publishing source reviews.

After final selection, the unchanged compiler processed **97 complete and 3 unsupported** demo reviews. The 97 extracted opinions comprise 63 Positive, 32 Negative and 2 Neutral results. All 100 input rows remain in the file, including the three unsupported examples. These are processing/coverage counts on the deliberately scoped demo, not independently labeled accuracy. No further sample filtering followed this check. Counts are saved in `output/datasets/provenance/demo_processing_coverage.csv`.
