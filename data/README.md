# Dataset sources and redistribution

The repository includes prepared real review inputs in [output/datasets](../output/datasets/README.md). They retain source wording under the documented preparation rules, not generated review text. CSVs include `sr.no,review`, except the optional original TripAdvisor table (`Review,Rating`). Source files, raw reviewer metadata, local absolute paths and credentials are excluded. Dataset licenses are independent of any project-code license.

| Source | Published inputs | License and use |
|---|---|---|
| [Jiashen Liu, 515K Hotel Reviews Data in Europe](https://www.kaggle.com/datasets/jiashenliu/515k-hotel-reviews-data-in-europe) | Curated 100 and random 200; minimal source-row/hash maps | Publisher metadata: CC0 Public Domain. Curated sample is model-informed, not random accuracy evidence. |
| [Crawl Feeds, Booking Hotel Reviews Dataset](https://huggingface.co/datasets/crawlfeeds/Booking-Hotel-Reviews-Dataset) | Booking Italy: 4,367 rows / 3,102 nonblank bodies, plus five upload parts | Publisher's dataset-specific release: [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/); research/non-commercial use. Attribute [Crawl Feeds](https://crawlfeeds.com). |
| [Andrew M. V., Trip Advisor Hotel Reviews](https://www.kaggle.com/datasets/andrewmvd/trip-advisor-hotel-reviews) | Original extracted 20,491-row Review/Rating table | Publisher metadata: [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/). Optional source; not used for the current paper's reported experiments. |
| [SemEval-2015 Task 12 Hotels](https://alt.qcri.org/semeval2015/task12/index.php?id=data-and-tools) | Aggregate metrics and scope counts; raw XML and sentence CSV excluded | Original dataset redistribution permission has not been established. Download through the original task or the documented mirror for local reproduction. A mirror's loader-code license does not establish a data license. |

## Publisher verification, October 21, 2026

The Crawlfeeds public CSV at revision `f39ceeede7b9d8a824909ebe88a7723ad31fa6c5` matches the user-supplied CSV byte for byte: SHA-256 `137cec35ddbd678b2bdb1bc93eccb2e844926c8503d3d7f898e274e387933dbd`. The publisher's dataset card explicitly declares CC BY-NC 4.0. This dataset-specific public release is the attribution/licensing basis for these prepared review-only inputs, rather than assuming all commercial Crawlfeeds exports may be republished. No reviewer-name, country, hotel-address, source-ID, or URL columns from the raw export are included.

Booking preparation removes only missing-body markers and joins retained positive/negative text with a newline; see [the sampling protocol](../docs/real-review-sampling.md) and [vocabulary audit](../docs/hybrid-vocabulary-expansion.md). Empty Booking Italy rows and duplicates remain. Canonical substitutions happen only inside the hybrid's scoring copy, not in these input CSVs. This corpus was inspected for vocabulary development; it has no independent aspect-polarity gold labels.

## Obtain raw sources for local reproduction

Create `data/vendor/real-hotel-research/` locally and download the following without adding them to Git:

| Local filename | Source | Expected SHA-256 |
|---|---|---|
| `booking_515k.zip` | [Kaggle download](https://www.kaggle.com/api/v1/datasets/download/jiashenliu/515k-hotel-reviews-data-in-europe) | `6ad6a0e7e13e202528ccc88843243a92c0f4499ab1b2e5f8ec9f22216ef2617d` |
| `tripadvisor_20k.zip` | [Kaggle download](https://www.kaggle.com/api/v1/datasets/download/andrewmvd/trip-advisor-hotel-reviews) | `f57df85e500da8d3b435a1086e8c9daf2a9367ddfbdb87dc08afadec54bd84b9` |
| `semeval2015_hotels.xml` | [Documented XML mirror](https://huggingface.co/datasets/alexcadillon/SemEval2015Task12/resolve/main/ABSA15_Hotels_Test.xml) | `afb995c6e2993b4c5f18fbd053b7169e080cd745308209ead3014de3ec648283` |

Hashes identify the downloaded versions, not an upstream authenticity guarantee. If files change upstream, preserve and record the new version rather than silently claiming identical experiments. See [the research runner guide](../docs/research-run-guide.md). Detailed local source maps needed by `verify-data` can be rebuilt by `scripts/prepare_real_review_samples.py` after obtaining its three raw sources.
