# Cleaned real Booking.com reviews for the demo

Start with **booking_italy_cleaned_demo_500.csv**. It contains only `sr.no` and `review`: one logical CSV record per real review. In the website choose **CSV & dashboard → Use real Booking 500** to load and analyze this same file, or upload it manually.

## Source and cleaning

Provider: [Crawl Feeds](https://crawlfeeds.com), [Booking Hotel Reviews Dataset](https://huggingface.co/datasets/crawlfeeds/Booking-Hotel-Reviews-Dataset). License: [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/). The supplied raw file matches the publisher's public release byte for byte; see [attribution](../ATTRIBUTION.md).

The source has 4,367 rows. Body preparation preserves positive/negative feedback wording and excludes titles, ratings, reviewer identity and hotel metadata. Cleaning removes exact standalone N/A/NA/N.A. markers and nonprinting C0 controls, collapses whitespace and trims it. It removes 1,266 blank/missing bodies and 12 exact cleaned-text duplicates, leaving **3,089 unique nonblank reviews**. Ordinary feedback such as “Nothing” remains. No spelling, sentiment, punctuation, sentences or grammar are rewritten to help either analyzer.

The **500-review demo** is a uniform random sample of the 3,089 records with seed **172026**. Selection does not call a model or filter by vocabulary, grammar, predicted label, category or processing success. Both models receive the same text. This inspected development corpus has no independent aspect-sentiment gold labels; it is real demo data, not an untouched accuracy benchmark. Mixed, partial and unsupported outcomes remain visible.

## Files

- `booking_italy_cleaned_demo_500.csv`: recommended demo input.
- `booking_italy_cleaned_all.csv`: all 3,089 reviews; exceeds the UI's 1,000-row limit.
- `booking_italy_cleaned_part_01.csv` through `part_04.csv`: the full corpus in ordered parts of 1,000 / 1,000 / 1,000 / 89. Serial numbers restart in each part.
- `demo_source_map.csv` and `all_source_map.csv`: original source ordinals and original/cleaned text hashes for every exported review.
- `cleaning_audit.csv`: all 4,367 source positions, removal reasons, duplicate references and hashes.
- `cleaning_manifest.json`: source hash, seed, counts and preparation policy.

The original two-column input remains at `../booking_italy/booking_italy_all.csv`. The maps' `source_row` identifies its original `sr.no`. Maps/audit files are evidence; upload only the two-column review inputs.

Preparation: `scripts/prepare_clean_booking_demo.py` and `scripts/build_clean_booking_demo.mjs`. Python produces source-mapped records; the JS builder exports literal input CSVs. The included CSVs can be used without authoring tools.
