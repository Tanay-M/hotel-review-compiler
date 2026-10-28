# Faculty demonstration datasets

Start with **booking_italy_cleaned_demo_500.csv** for the real-data demonstration.
Open CSV & dashboard, choose SentiWordNet or Hybrid, and upload a file. The page detects the standard `sr.no,review` headers and the earlier `review_id,review_text` demo headers; no manual column fields are needed.

These CSVs are inputs used for demonstrations, authored regression/load tests, vocabulary development and evaluation; they were not used as labelled DL training data. MiniLM was separately fine-tuned using human-labelled Trip-MA segments, documented in `../docs/dl-reanalysis-implementation.md`. Downloaded/prepared Trip-MA training and test text remains local. Output scores, metrics and source-map CSVs are deliberately not mixed into the upload folder.

| Input | Rows | Role |
|---|---:|---|
| `booking_italy_cleaned_demo_500.csv` | 500 | Real Booking Italy; random cleaned demo subset |
| `booking_italy_cleaned_part_01.csv` | 1,000 | Real Booking Italy; consecutive part of full cleaned corpus |
| `booking_italy_cleaned_part_02.csv` | 1,000 | Real Booking Italy; consecutive part of full cleaned corpus |
| `booking_italy_cleaned_part_03.csv` | 1,000 | Real Booking Italy; consecutive part of full cleaned corpus |
| `booking_italy_cleaned_part_04.csv` | 89 | Real Booking Italy; consecutive part of full cleaned corpus |
| `real_booking_curated_100.csv` | 100 | Real older Booking source; intentionally curated demonstration |
| `real_booking_random_200.csv` | 200 | Real older Booking source; random eligible sample |
| `semeval_hotel_benchmark_266.csv` | 266 | Real benchmark sentences; human annotations remain in original XML |
| `synthetic_reviews_100.csv` | 100 | Authored synthetic examples; not organic reviews |
| `synthetic_bulk_regression.csv` | 12 | Authored regression examples; includes deliberately invalid rows |
| `synthetic_ui_demo_12.csv` | 12 | Authored UI demo; includes deliberate invalid-input cases |
| `synthetic_load_test_100.csv` | 100 | Repeated authored cases used for bulk tests |
| `synthetic_load_test_500.csv` | 500 | Repeated authored cases used for bulk tests |
| `full_corpus/booking_italy_cleaned_all_3089.csv` | 3,089 | Same cleaned Italy corpus; exceeds 1000-row UI limit |

## Important distinctions

- The four cleaned Italy parts contain 1,000, 1,000, 1,000 and 89 reviews. They reconstruct the same 3,089-review corpus; the random 500 is a subset, not additional independent data.
- The file in `full_corpus/` is for offline analysis or viewing in a spreadsheet. It exceeds the website's 1,000-row limit; upload the parts individually.
- Booking Italy is the cleaned derivative: missing markers/control characters and whitespace were processed, blank bodies and exact cleaned duplicates removed. Review wording was not paraphrased or selected based on successful analysis.
- The older real Booking 100/200 are separate previously used samples. The curated 100 intentionally favors explicit language and is not an unbiased accuracy test.
- SemEval input contains the 266 original sentences. Gold annotations are in `data/vendor/real-hotel-research/semeval2015_hotels.xml`, not in the upload CSV. The paper evaluates only the declared mapped scope of 148 classification cases; a whole-file UI run is not that gold-label evaluation.
- Synthetic files are authored/repeated cases. Some include blank text/duplicate IDs intentionally to exercise diagnostics. Never present them as organic reviews.
- The downloaded 20,491-row TripAdvisor source was not used in the paper's reported comparison and is not included as a claimed test set.
- These are copies: original sources remain in place and byte equality is verified in `manifest.json`.
- Dataset attribution and license details: `../output/datasets/ATTRIBUTION.md` and `../data/README.md`. SemEval is a local demonstration copy; redistribution permission has not been established. Do not publish it merely because it is present here.
