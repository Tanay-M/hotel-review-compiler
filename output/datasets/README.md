# Real hotel review inputs

**New demo:** [Cleaned Booking reviews](booking_cleaned/README.md) include a 500-review random demo, all 3,089 unique nonblank reviews, four UI-ready parts and source maps. Use **CSV & dashboard → Use real Booking 500** in the website. Neither wording nor selection is altered to make a model succeed.

These are real source reviews, not authored examples. Open CSVs in Excel or upload the two-column inputs using `sr.no` and `review` in the WebUI. See [source attribution](ATTRIBUTION.md) and [dataset licenses/acquisition](../../data/README.md).

| File | Rows | Purpose |
|---|---:|---|
| [real_hotel_demo_100.csv](real_hotel_demo_100.csv) | 100 | Curated Booking.com demonstration; intentionally short, explicit language. Both systems were run. |
| [real_hotel_random_200.csv](real_hotel_random_200.csv) | 200 | Random eligible Booking.com sample. Both systems were run; no independent aspect gold. |
| [booking_italy/booking_italy_all.csv](booking_italy/booking_italy_all.csv) | 4,367 | Supplied Crawlfeeds corpus: 3,102 nonblank bodies, 1,265 retained missing-body rows. Hybrid vocabulary development, not yet compared against SentiWordNet. |
| [booking_italy/booking_italy_part_01.csv](booking_italy/booking_italy_part_01.csv) through `part_05.csv` | 1,000 / 1,000 / 1,000 / 1,000 / 367 | Same Booking Italy rows in five ordered UI-ready files; no additional examples. |
| [tripadvisor_original_20491.csv](tripadvisor_original_20491.csv) | 20,491 | Optional original `Review,Rating` source table. Not part of the paper's reported experiments or the two-column UI format. |

The full Booking Italy file exceeds the UI's 1,000-row limit; use one part at a time. Empty rows receive input diagnostics and are retained rather than being rewritten. Original positive/negative body text is joined under the documented missing-field rules; titles, ratings and reviewer metadata are absent from model inputs. The hybrid may normalize an internal scoring copy; these CSVs retain the prepared original wording.

`public_manifest.json` records file hashes, counts, columns, source revision and licenses. `public_provenance/` contains minimal source-row/hash maps for the 100/200 samples, excluding hotel/reviewer metadata. Detailed local maps and raw upstream archives remain ignored. `scripts/prepare_public_datasets.py` reproduces this publication export after the local preparation steps.

The curated 100 is not an unbiased accuracy test. None of the Booking inputs provides independently annotated aspect sentiment, so processing coverage must not be called accuracy. The paper's accuracy/F1 uses a declared adaptation of SemEval annotations. Its raw XML and readable sentence CSV are not redistributed because data redistribution permission has not been established; [download instructions](../../data/README.md) support local reproduction. Original local files remain available.

See [sampling details](../../docs/real-review-sampling.md), [vocabulary development](../../docs/hybrid-vocabulary-expansion.md), and [the current paper](../paper/PAPER_README.md).
