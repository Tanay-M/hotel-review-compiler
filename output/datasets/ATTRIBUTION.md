# Dataset attribution and changes

Dataset licenses apply separately to their respective data, including prepared subsets. Do not assume a project-code license grants additional data rights.

## Booking Italy — Crawl Feeds

Creator/provider: [Crawl Feeds](https://crawlfeeds.com). Source: [Booking.com Hotel Reviews Dataset, publisher release](https://huggingface.co/datasets/crawlfeeds/Booking-Hotel-Reviews-Dataset), revision `f39ceeede7b9d8a824909ebe88a7723ad31fa6c5`, verified October 21, 2026. License: [Creative Commons Attribution-NonCommercial 4.0 International](https://creativecommons.org/licenses/by-nc/4.0/).

The published source CSV matches the supplied original exactly (SHA-256 `137cec35ddbd678b2bdb1bc93eccb2e844926c8503d3d7f898e274e387933dbd`). Changes for these derivatives: select only nonmissing positive/negative body fields, join them with newline, add a serial ordinal, and split the resulting full table into ordered UI upload parts. Source field headings and reviewer/hotel metadata are not retained. All 4,367 source positions, including 1,265 missing-body positions and duplicates, remain. No review wording is generated or rewritten. Use for research and other non-commercial purposes under the stated license; no affiliation or endorsement is implied.

## Booking 515K samples — Jiashen Liu

Creator: Jiashen Liu. Source: [515K Hotel Reviews Data in Europe](https://www.kaggle.com/datasets/jiashenliu/515k-hotel-reviews-data-in-europe). Publisher metadata verified October 21, 2026: [CC0 1.0 Public Domain dedication](https://creativecommons.org/publicdomain/zero/1.0/).

`real_hotel_demo_100.csv` and `real_hotel_random_200.csv` are selected subsets, not the complete corpus. Preparation trims outer field whitespace, omits exact missing-feedback placeholders and joins original retained feedback fields. Sampling and deduplication are documented in [the sampling protocol](../../docs/real-review-sampling.md). Minimal source maps identify original source row positions and text hashes. No synthetic reviews replace original text.

## TripAdvisor — Andrew M. V.

Publisher: Andrew M. V. (`andrewmvd`). Source: [Trip Advisor Hotel Reviews](https://www.kaggle.com/datasets/andrewmvd/trip-advisor-hotel-reviews). Publisher metadata verified October 21, 2026: [Creative Commons Attribution-NonCommercial 4.0 International](https://creativecommons.org/licenses/by-nc/4.0/).

`tripadvisor_original_20491.csv` is extracted unchanged from the downloaded archive; it contains original `Review,Rating` fields. It is included as an optional research source and was not used for the current paper's reported results. Ratings are proxy review labels, not aspect-polarity gold annotations. Research/non-commercial use remains subject to its license. No endorsement is implied.
