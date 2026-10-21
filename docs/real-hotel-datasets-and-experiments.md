# Real hotel datasets and paper experiments

**Historical acquisition notes (October 14).** Implementation-status statements below describe the acquisition stage. For the implemented systems, October 21 experiment results and publication files, use the [current run guide](research-run-guide.md), [paper notes](../output/paper/PAPER_README.md), and [public dataset index](../output/datasets/README.md). Selected inputs are now published under their source licenses; raw archives and unconfirmed-permission benchmark text remain local.

Verified 14 October 2026. Research and acquisition only: the production compiler, WebUI, project dependencies and scoring strategies have not been changed in this step.

Latest preparation update: readable files now exist in `output/datasets/`, including a 100-review vocabulary-scoped Booking demo and a separate 200-review random sample. See [the sampling protocol](real-review-sampling.md) for exact selection rules, the original pilot, source maps and the two-system SentiWordNet versus VADER–TextBlob hybrid decision. The recommendations below distinguish the full source datasets from these prepared subsets.

## Recommendation

Use **SemEval-2015 Task 12 Hotels** for the primary aspect-polarity benchmark and **Trip Advisor Hotel Reviews** for a larger review-rating comparison. Keep **515K Hotel Reviews Data in Europe** as a third, optional robustness and scale dataset. Two carefully defined experiments are preferable to three incompatible accuracy percentages.

All three source files were downloaded successfully without authentication and inspected locally. Their raw data remains under ignored `data/vendor/real-hotel-research/`; no raw dataset was added to Git or pushed. The files have not been passed through the current compiler for a performance comparison in this research step.

| Dataset | Verified contents | Labels available | Best paper use |
|---|---|---|---|
| SemEval-2015 Hotels | 30 reviews, 266 sentences, 339 annotated opinions | Human aspect/entity-attribute, target and positive/negative/neutral annotations | Primary aspect-polarity evaluation and an explicitly adapted extraction evaluation |
| Trip Advisor Hotel Reviews | 20,491 rows; Review and Rating columns | Customer ratings 1–5; no aspect annotations | Larger-scale review sentiment comparison using clearly identified rating-derived proxy labels |
| 515K Hotel Reviews Data in Europe | 515,738 rows; 17 columns | Positive/negative feedback fields and numeric reviewer score; no equivalent aspect gold labels | Generalization, lexical coverage, paired-feedback analysis and batch runtime |

## 1 SemEval-2015 Task 12 Hotels

Sources: [official task data page](https://alt.qcri.org/semeval2015/task12/index.php?id=data-and-tools), [benchmark paper](https://aclanthology.org/S15-2082/), [accessible mirror](https://huggingface.co/datasets/alexcadillon/SemEval2015Task12).

The official hotel task supplied aspect and target information for polarity prediction. Use that distinction when comparing scoring with end-to-end extraction. The mirror XML was downloaded and inspected; its provenance has not been authenticated against an official-file checksum. The mirror's loader leaves the dataset license unspecified; its Apache script license does not establish the data license. Consult original distribution terms before redistributing the raw XML.

Local file: `data/vendor/real-hotel-research/semeval2015_hotels.xml`.

Additional counts measured from the downloaded XML:

| Property | Count |
|---|---:|
| Positive opinion annotations | 243 |
| Negative opinion annotations | 84 |
| Neutral opinion annotations | 12 |
| Implicit NULL targets | 75 |
| Sentences with multiple opinions | 71 |

### Fit and limits

This is the strongest option for an aspect-based paper because it provides independent annotations rather than our own expected answers. Its ontology is not identical to our six categories, and it contains implicit targets and contextual language outside our grammar. The small number of reviews and rare neutral examples limit generalization and five-class threshold validation.

Preserve the original gold labels. Define a mapping based on annotation meaning, not current predictions: examples include ROOMS to Room, FOOD_DRINKS to Food, and relevant FACILITIES or ROOMS_AMENITIES labels to Facilities. SERVICE does not identify our Staff and Service distinction automatically. Cleanliness may appear as an attribute of a room, facility or hotel, so never map every CLEANLINESS annotation to our standalone Cleanliness category blindly. HOTEL#GENERAL, LOCATION and price annotations have no automatic one-to-one match with our agreed taxonomy. Document ambiguous and out-of-scope annotations and report the counts before scoring.

Evaluate mapped scope and full-benchmark applicability separately. Do not select only sentences that our parser successfully handles and describe the resulting accuracy as full-dataset performance. Count omitted in-scope gold opinions in extraction recall. Keep original issue labels alongside our mapped labels so the mapping is auditable.

For scoring-only comparison, initially use independently defined contexts containing one annotated opinion. This reduces cross-aspect contamination, but the selected sample count and exclusion rule must be published. Do not simply repeat a whole-sentence VADER score for every target in a multi-opinion sentence. Keep multi-opinion sentences for a separate error/generalization analysis. Any use of supplied gold target/context must be stated as an oracle-context scoring experiment, not full aspect extraction.

The benchmark's neutral convention includes mild evaluations and is not identical to a zero lexical score. Examine that annotation definition when interpreting neutral errors. Neither the neutral examples nor the three-class labels establish Strong/Weak gold truth.

Freeze current software and mapping rules before an evaluation run. This is a test-only hotel benchmark, so do not tune vocabulary or strength thresholds on its outcomes and continue calling it unseen evaluation. Use separate development data for tuning. Bootstrap uncertainty by review rather than treating all opinions as independent reviews.

## 2 Trip Advisor Hotel Reviews

Original distribution: [andrewmvd on Kaggle](https://www.kaggle.com/datasets/andrewmvd/trip-advisor-hotel-reviews).

Local archive: `data/vendor/real-hotel-research/tripadvisor_20k.zip`. Direct Kaggle download succeeded without sign-in. Publisher API metadata reports **CC BY-NC 4.0**. Preserve source attribution and the stated license with research provenance.

Actual CSV has exactly `Review,Rating`. All 20,491 stripped review strings were distinct in this inspection. Five reviews exceed our current 10,000-character input limit; log their handling explicitly rather than silently truncating or omitting them.

| Original rating | Reviews |
|---|---:|
| 1 | 1,421 |
| 2 | 1,793 |
| 3 | 2,184 |
| 4 | 6,039 |
| 5 | 9,054 |

A possible three-class proxy policy is ratings 1–2 negative, 3 neutral and 4–5 positive. This produces 3,214 negative, 2,184 neutral and 15,093 positive rows before filtering. The majority-positive baseline is about 73.66%, illustrating why accuracy alone is inadequate. Publish macro-F1 and per-class support alongside accuracy. A balanced sample is useful as a separate stress test, but its accuracy must not be presented as representing the original prevalence.

These are rating-derived labels, not human aspect-sentiment labels. A four-star review can contain a negative room complaint. The existing Mixed field cannot be compared directly with three rating classes. Define a separate review-net classification field and an explicit class-boundary policy, while preserving Mixed for aspect interpretation. Name results **rating-label agreement** or **proxy-label classification**, rather than independently verified aspect accuracy.

Some supplied text is visibly normalized and fragmentary, as seen in the initial row. It should not be described as a guaranteed untouched transcript. That can disadvantage controlled grammar and remove cues used by VADER. Retain the supplied text for all methods, document its condition and do not invent missing punctuation or rewrite reviews to suit the parser.

For an initial next-day experiment, use a reproducible random 1,000-review sample before any output-based selection. Retain the original label distribution or report a separate stratified sample explicitly. If a development/test split is needed, split before tuning; when grouped hotel/reviewer IDs are absent, disclose that hotel/user-level leakage cannot be fully checked. Keep all versions of each review together, and deduplicate across any datasets used for development and evaluation where possible.

A five-class rating mapping (1 strong negative through 5 strong positive) is only a rating-intensity proxy. It is not independent confirmation that the text expresses the same five sentiment strengths. Report the proposed score bands descriptively unless separately labeled strength data supports classification metrics.

## 3 515K Hotel Reviews Data in Europe

Original distribution: [Jiashen Liu on Kaggle](https://www.kaggle.com/datasets/jiashenliu/515k-hotel-reviews-data-in-europe).

Local archive: `data/vendor/real-hotel-research/booking_515k.zip`. Direct Kaggle download succeeded without sign-in. Publisher API metadata reports **CC0 Public Domain**. Do not substitute a mirror's different license claim for the original distribution metadata.

The CSV includes `Positive_Review`, `Negative_Review`, `Reviewer_Score`, hotel fields and dates. Inspection found 127,890 exact `No Negative` placeholders and 35,946 exact `No Positive` placeholders after trimming/case normalization. None of the paired text lengths exceeded the current 10,000-character limit under the inspection's two-character join convention. There are 1,492 distinct hotel-name strings; this is not necessarily the number of unique properties, so use a documented property identifier rather than assuming names are unique.

Retain each source row as one hotel stay/review record. Do not count the positive and negative fields as independent people or randomly split the two sides across development and test sets. For combined-review analysis, join non-placeholder fields under one parent ID without adding words such as Positive/Negative to the model input. Preserve both original fields in research provenance so component-level experiments can be reproduced.

Feedback fields are useful weak supervision, not perfect sentiment labels. No Negative means missing negative feedback, not negative sentiment. Other phrases such as Nothing need contextual handling rather than blanket relabeling. Some text is fragmentary, and a feedback side can mention multiple topics or even contain sentiment opposite to its field heading.

Recommended use: a reproducible 1,000-review robustness sample and timed 100/500/1,000-review runs using the analysis core or offline runner. These measure behavior on a large real corpus; they do not by themselves establish aspect accuracy. A randomly selected, independently annotated subset could later provide aspect gold labels.

## Proposed evaluation outputs

User decision: compare **two systems**, the **existing SentiWordNet compiler** and a **VADER–TextBlob hybrid** using both tools. Keep VADER and TextBlob component outputs for explanations and optional ablations, not as three primary systems. Preserve current compiler behavior/version as the baseline before adding the five-band reporting policy. Define the hybrid rule on development data and freeze it before testing; do not assume its accuracy improves merely because it combines two tools.

| Experiment | Evidence | Main outputs |
|---|---|---|
| Aspect-polarity benchmark | SemEval human annotations, documented eligible contexts and taxonomy mapping | Accuracy, macro-F1, per-class precision/recall/F1, support, confusion matrices |
| Aspect extraction | Gold labels under explicit mapping; compiler predictions | Category/target precision, recall and F1, unmatched targets, coverage and errors |
| Whole-review proxy comparison | TripAdvisor customer ratings and published mapping | Rating-label agreement, macro-F1, majority-class baseline, scored/abstained denominators |
| Robustness and performance | Booking sample or fixed TripAdvisor sample | Complete/partial/unsupported counts, analysis coverage, repeated runtime and throughput |
| Five-band reporting | Declared score thresholds, separately for the intended method/scope | Strength count table/plot; intensity accuracy only with independent intensity gold labels |

VADER and TextBlob alone do not extract our categories. Do not assign them zero extraction F1 and call our system better. Compare their polarity on the same eligible input context, and evaluate our extraction as a separate task. If a score is unavailable, retain abstention. Report conditional accuracy among scored examples plus coverage and correct/submitted counts; a method must not improve headline performance simply by dropping harder cases. Multi-opinion matching and three-class labels must be specified before evaluation.

## Paper tables and graphs to generate after implementation

1. **Dataset table:** original rows, sampled rows, unique parent reviews, label distribution, source, exclusions, length and provenance.
2. **Comparison table:** each method's task, test size, accuracy/agreement, macro-F1, coverage and repeated runtime. Never mix aspect gold accuracy and rating-proxy agreement in one undifferentiated ranking.
3. **Grouped metric bars:** accuracy and macro-F1 for a single shared task, including the majority baseline and sample support.
4. **Confusion matrices:** same class order and denominator for all methods; retain raw counts alongside normalized views.
5. **Coverage bars:** complete, partial, unsupported, invalid and failed for the compiler; keep this separate from sentiment correctness.
6. **Runtime graph:** fixed random sets of 100, 500 and 1,000 reviews, warm-up and at least five measured runs, with hardware, version, timing scope and spread. Bypass UI upload limits through a documented offline experiment, rather than silently changing the demo's limits.
7. **Strength distributions:** five labels and unscored counts, while retaining Mixed and partial-score scope in supporting results.
8. **Error table:** a small, representative selection of negation, contrast, multi-aspect text, implicit targets and functional complaints, with original labels and each method's output.

Export metric tables as CSV and scientific figures as vector PDF/SVG plus 300-dpi PNG where useful. Every figure needs an inference in the manuscript. Keep one row per original review in the main result table, linked opinion rows for aspect details, and source/gold labels separate from the two-column demonstration input. Preserve parent IDs if sentences or fields are analyzed separately.

## Status and next implementation sequence

Completed: source search, direct downloads, schema/count inspection, label/access/license metadata checks and file hashes. No sentiment metrics on these real datasets have been computed, and the five-band policy is not integrated yet.

Recommended next sequence after dataset selection: freeze baseline and experiment protocol; build dataset adapters and gold/proxy label separation; add VADER/TextBlob adapters and strength labels; run identical-input experiments; export tables and publication figures; then write measured results into the IEEE paper. UI work remains deferred.

Inspection evidence: `output/research/real-datasets-2026-10-14/source_manifest.csv` and `verified_dataset_statistics.csv`. Dataset counts in this report are measured from the downloaded files, not inferred from marketing titles. A local SHA-256 identifies the downloaded artifact; it does not by itself establish authenticity or an upstream guarantee.
