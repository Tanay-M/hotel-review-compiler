# Candidate training datasets for neural hotel sentiment recovery

Implementation update: the later Webis acquisition, training and evaluation are documented in [neural-first-run.md](neural-first-run.md). The inventory below records the earlier research state before that implementation.

Research date: 23 October 2026. Sources below were checked against dataset authors, original papers and release metadata. These are candidate supervision sources, not new project experiments. No corpus was saved to the project, no model was trained, and the paper was not changed. Small public source files and one 2.9 MB archive were inspected in memory to verify format and labels.

## Webis Tripad Sentiment Corpus 2013

**Strong hotel-domain candidate for polarity training, with an aspect-category caveat.** The authors release 2,100 English hotel reviews, with human statement-level Positive, Negative and Objective sentiment and expert-annotated aspect mentions. It is not merely a table of star ratings. [Author dataset page](https://webis.de/data/webis-tripad-13-sentiment.html), [official Zenodo release](https://zenodo.org/records/3266053).

The official ZIP contains 2,100 per-review JSON files. Inspection confirms `text`, review/hotel metadata, `de.webis.annotation.Statement` records containing `begin`, `end`, and `polarity`, and `de.webis.annotation.Aspect` records containing aspect offsets. The inspected aspect records contain spans, not our six category names or explicit aspect–polarity relation IDs. Statement containment can supply candidate target-context training pairs, but multi-aspect cases need review rather than blindly assigning statement sentiment to every target. Objective is not automatically identical to our Neutral definition.

The Zenodo API explicitly returns `metadata.license.id = cc-by-4.0`. The archive is about 2.9 MB and is JSON, not a ready-to-upload review-only CSV. Attribution is required. [Release API](https://zenodo.org/api/records/3266053), [download](https://zenodo.org/records/3266053/files/corpus-webis-tripad-13-sentiment.zip?download=1).

No predefined train/dev/test split was established in this inspection. Create and preserve a documented split by parent review, preferably by hotel where feasible, before extracting statements. Do not infer sentence-level labels from the numeric review rating. Preserve source statement offsets.

## Trip-MA / English part of Trip-MAML

**Strong candidate for hotel category-conditioned learning, with a merged-label caveat.** The paper reports 442 English hotel reviews, 5,799 sentences, and 4,810 sentences containing at least one opinion. These are different counts, not 5,799 independent reviews. Its sentence annotations can contain multiple category labels. The English portion is Trip-MA; the Italian and Spanish additions are not appropriate as direct training text for an English-only model. [Original paper](https://aclanthology.org/D15-1302.pdf), [author repository](https://github.com/diegma/trip-maml).

Eleven categories include Rooms, Cleanliness, Value, Service, Location, Check-in, Business, Food, Building, Other and NotRelated. Rooms/Cleanliness/Food/Service have useful overlap; Facilities needs a reviewed crosswalk and Staff is not separately labelled. Value and Location remain outside our agreed scope. Do not force every original label into one of the six categories.

The three sentiment classes are Positive, Negative and **Neutral/Mixed**. The third deliberately combines neutral with opposing opinions and must not be silently treated as clean Neutral gold. Options are to retain its original class for a separate experiment, use positive/negative examples for an initial transfer stage, or human-adjudicate third-class cases under our policy. [English annotation README](https://github.com/diegma/trip-maml/blob/main/EN/README.md).

The official English release provides `english_training.json` and `english_test.json`, containing 258 and 111 JSON Lines review records respectively. This matches the README's split of the 369 singly annotated reviews; the remaining 73 shared reviews belong to the paper's agreement analysis. Do not claim all 442 are in these two files. Each inspected record has `segments` and parallel `segmentLabels`, with category-to-code mappings such as `ROOMS: p`; segments use token/POS/lemma-like serialization rather than untouched plain review strings. A faithful converter and documented code mapping are needed. [Training file](https://raw.githubusercontent.com/diegma/trip-maml/main/EN/english_training.json), [test file](https://raw.githubusercontent.com/diegma/trip-maml/main/EN/english_test.json).

No explicit dataset LICENSE file was found in the repository tree or the inspected READMEs. Public availability and a citation request do not establish unrestricted redistribution permission. Record this limitation and verify terms before incorporating a redistributable copy. Preserve the provided test partition; derive development data from training reviews rather than tune on test.

## Lower-priority alternative HOSSemEval-EB23

The author repository describes 7,012 Booking.com hostel-review records with categories Amenity, Branding, Experience, Facility, Loyalty and Service. Those are not our six categories. Although it provides aspect-oriented annotations and model data layouts, its taxonomy requires substantial mapping and is therefore not the fastest first dataset for the proposed fallback. Human annotation details, release licence and record/split granularity need further validation before selection. [Author repository](https://github.com/dtseedx/HOSSemEval-EB23).

## Recommendation from the checked hotel sources

Webis is the clearer first acquisition for hotel-domain source text, human statement sentiment, source offsets and an explicit CC BY 4.0 release. It still needs extraction, an Objective/Neutral policy, and category mapping or reviewed explicit-aspect selection. Trip-MA provides richer direct category supervision but needs a faithful token-text converter, a Neutral/Mixed policy and licensing clarification. Neither is a plug-and-play, perfectly matched six-category gold table.

Keep training data and held-out reviews separate. Existing project predictions must not be relabelled as human ground truth. The original inspected SemEval hotel data should retain its development role if it informs model choice or thresholds. A small newly human-checked Booking test set remains valuable for judging the actual Partial-output recovery task.

## Existing project inventory

The local inventory was read directly on 23 October 2026. No training/validation/test dataset for the proposed neural stage has yet been prepared, and no locally trained sentiment model exists yet.

| Local source | Verified size and labels | Valid role |
|---|---|---|
| `data/vendor/real-hotel-research/semeval2015_hotels.xml` | 30 parent reviews, 266 sentences, 339 original human opinion annotations: 243 Positive, 84 Negative, 12 Neutral; 264 have explicit non-NULL targets | Valid small supervised source or development benchmark, but already inspected during this project's development; not a new untouched test set |
| `dataset/semeval_hotel_benchmark_266.csv` | The 266 review sentences; no gold columns in this UI input | Labels must be joined from original XML, not inferred from the CSV or system predictions |
| `dataset/full_corpus/booking_italy_cleaned_all_3089.csv` | 3,089 unique nonblank real review bodies; columns `sr.no,review` | Human annotation pool and demonstration input; not ready supervised aspect training data |
| `dataset/booking_italy_cleaned_demo_500.csv` and four parts | Nested sample / ordered partitions of the same cleaned corpus | Not additional independent labelled datasets |
| `dataset/real_booking_random_200.csv`, `real_booking_curated_100.csv` | Real prepared review inputs without aspect gold; curated sample intentionally selected for demonstration | Annotation candidates or demo; no independent accuracy labels |
| `output/datasets/tripadvisor_original_20491.csv` | 20,491 rows, `Review,Rating` only | Possible weak document-level supervision from ratings; rating is not a Room/Staff/Service opinion label |
| Synthetic demo/load/regression CSVs | Authored/repeated examples, including intentionally invalid inputs | Software tests only; not organic hotel evidence |

The paper's 148 mapped sentence-category classification cases are a subset/adaptation of the original SemEval annotations, not 148 independent reviews or a separate training corpus. They include only four Neutral gold cases after mapping. The original hotel release is test data in the SemEval task; the original task page lists restaurant/laptop training sources but not hotel training data. Its role must be declared honestly if reused for our new model. [Original SemEval data page](https://alt.qcri.org/semeval2015/task12/index.php?id=data-and-tools).

## SemEval 2014 Restaurants in SetFit format

This is the most directly usable **format** for a SetFit aspect-sentiment pilot, although it is restaurant-domain data. The official SetFit maintainer's adapter identifies human annotations from SemEval 2014 and exposes `text`, `span`, `label`, `ordinal`. Its current card and repository API report **3,693 training aspect examples and 1,134 test aspect examples**, not that many distinct reviews. Revision checked: `8885372fe73256f96bb60f65b550538ac5c26047`. Source files are Parquet and can be converted to training CSV without rewriting text or labels. [Dataset card](https://huggingface.co/datasets/tomaarsen/setfit-absa-semeval-restaurants), [metadata](https://huggingface.co/api/datasets/tomaarsen/setfit-absa-semeval-restaurants), [original task paper](https://aclanthology.org/S14-2004/).

It contains Positive, Negative, Neutral and Conflict. A three-polarity experiment must explicitly exclude or separately model Conflict; do not call Conflict Neutral. Preserve its test split and create validation data from training with source grouping where available. It is useful for transferable target-dependent polarity and Food/Service language, but does not directly supply Room/Facilities coverage or our six-category annotations. Do not copy the dataset card's example of selecting checkpoints on its test set into our final evaluation protocol.

The inspected adapter card does not declare a dataset licence. Its loader/code/model licences must not be substituted for source-data terms. Use the original research source and retain attribution; validate redistribution terms before adding a public raw-data copy. This candidate has not been downloaded into the project.

## Additional candidate not yet selected

HAMOS v4 is described by its Mendeley publisher as 8,796 multilingual hotel reviews, 23,995 aspect-category-opinion-polarity quadruples, hotel-disjoint train/validation/test partitions, JSON/JSONL/CSV, and CC BY 4.0. Those are release-description claims. The English-only counts, annotation process, schema and actual files were not verified in this pass; therefore this note does not certify it as a ready human-gold training source or recommend mixing it into reported experiments yet. [Publisher release](https://data.mendeley.com/datasets/x46f4y4fpr/4).

## Practical training plan

1. Acquire and convert Webis to source-preserved statement/target records, documenting category and Objective/Neutral policy. Resolve ambiguous multi-target statements rather than propagate labels blindly.
2. Use the official restaurant training split for an optional transfer pilot with clearly documented polarity labels; evaluate hotel-domain transfer separately.
3. Consider Trip-MA for category-conditioned learning after its token serialization, merged Neutral/Mixed label and terms are resolved. Keep its published test partition untouched.
4. Freeze resource mappings and group train/validation/test by original reviews (or hotels where feasible). Choose thresholds on validation only.
5. Evaluate the current lexical systems and augmented system on the same fresh, independently labelled hotel holdout, with a separate analysis of previously unresolved contexts. Reviews already inspected for vocabulary should not be claimed as unseen text.

These datasets primarily support polarity. None of the three selected sources directly establishes our Strong/Weak five-band labels as human intensity ground truth. Training metadata/labels belong in separate internal tables; faculty upload CSVs can remain review-only inputs.
