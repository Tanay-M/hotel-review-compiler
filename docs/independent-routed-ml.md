# Independent ML/DL reanalysis of unresolved reviews

Historical ML experiment. The dashboard now defaults to the [fine-tuned DL successor](dl-reanalysis-implementation.md); this report preserves the earlier model and measurements.

Implemented and tested on 23 October 2026. This is the proposed fifth stage for the project; the IEEE paper has **not** been modified yet.

## What changed from the first neural prototype

The first model only supplied sentiment for aspect contexts already attached by the hybrid. This implementation routes **each Partial or Unsupported review** into an independent model that processes **all original sentences**. It predicts category and category-specific sentiment without requiring a hybrid vocabulary match, parsed clause, or aspect record. It can therefore classify an implicit Service complaint.

```text
Original review → VADER–TextBlob hybrid → routing decision
                                      ├─ Complete → retain hybrid result
                                      ├─ Partial / Unsupported → original full review
                                      │                           ↓
                                      │                sentence segmentation
                                      │                           ↓
                                      │                MiniLM sentence embeddings
                                      │                           ↓
                                      │                trained category/polarity heads
                                      │                           ↓
                                      │                independent selected result
                                      └─ Invalid / component error → report failure
```

The independent result **replaces the selected analysis for that review**; it does not union its predictions with hybrid opinions. The original hybrid remains available for comparison. A neural abstention does not quietly reuse hybrid predictions or become Neutral. A model error remains visible.

An actual saved-model example is `We waited two hours before anyone checked us in.` The hybrid status is Unsupported; the independent model predicts **Service / Negative**, with model direction index approximately **−0.6653**. This is an illustrative prediction, not a separately human-labelled test example.

## Model and supervision

We trained eight independent four-state logistic regression heads on MiniLM sentence embeddings. Each head predicts **Absent, Negative, Neutral/Mixed, Positive** for a category. Five heads produce supported categories; three heads identify Excluded, Other and NotRelated background. Multiple categories can be predicted for a sentence.

This is a supervised ML classifier using a pretrained deep transformer representation. A SetFit encoder fine-tuning experiment was also completed and retained, but **validation selected the frozen encoder with trained heads**. It would be incorrect to describe the deployed checkpoint as the winning fine-tuned encoder.

Source: the [Trip-MA English author release](https://github.com/diegma/trip-maml/tree/main/EN), pinned commit `a9f47df668d3e2ec37bb13e04d1005fb1623d91d`. Its [annotation README](https://github.com/diegma/trip-maml/blob/main/EN/README.md) documents human category/polarity labels and explicit/implicit expressions. No system outputs, star ratings or generated examples supply our labels.

The source contains **258 training reviews and 111 test reviews**. The published text is token/POS/lemma serialization. We recover the original surface tokens and detokenize them; this is **not an untouched raw-text release**. Original serialization, source labels and source hashes are retained in the prepared CSVs.

No explicit dataset licence was found in the author repository. Source downloads and prepared training data remain local/ignored; this implementation does not add them to a public repository.

### Category and label compatibility

| Source annotation | Model output / treatment |
|---|---|
| ROOMS | Room |
| CLEANLINESS | Cleanliness |
| SERVICE, CHECKIN | Service |
| FOOD | Food |
| BUILDING, BUSINESS | Facilities, a broad documented crosswalk |
| LOCATION, VALUE | Excluded; never forced into a supported category |
| OTHER, NOTRELATED | Separate background heads |
| p / ip | Positive; explicit and implicit retained |
| n / in | Negative; explicit and implicit retained |
| x / ix | **Neutral/Mixed**, retained as the source merged class |

**The dataset has no separately labelled Staff class.** Staff-related judgements are pooled within Service; we do not invent Staff training labels or claim six-category supervision. The original hybrid still has six categories. Separate learned Staff output requires additional reviewed human labels. Conflicting source categories merged into one output category become Neutral/Mixed.

The category definitions differ from the original hybrid: for example, the hybrid can label a clean room as Room, while Trip-MA annotates Cleanliness. Facilities versus Building/Business is also approximate. The benchmark is a mapped evaluation, not an official six-category ABSA result.

## Splits and leakage checks

We retained the official test partition, removed 36 training reviews whose hotels occur in the official test set, and derived validation from the remaining training hotels using a fixed hash. Text duplicates crossing splits and conflicting duplicate labels were excluded. Hotel IDs, review IDs and normalized text hashes are disjoint across all three prepared partitions.

| Split | Segments | Reviews | Hotels |
|---|---:|---:|---:|
| Train | 2,040 | 180 | 157 |
| Validation | 602 | 42 | 39 |
| Test | 1,474 | 111 | 103 |

Three long training segments were excluded by the 128-token limit, leaving **2,037 head-training examples**. Long inputs remain unavailable in test evaluation and visible as warnings during inference. They are not silently truncated or dropped from metric denominators.

The base encoder is `sentence-transformers/all-MiniLM-L6-v2`, immutable revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`. This run starts from the base encoder, not the earlier supervised Webis checkpoint. The Webis test labels do not enter this training run.

## Training and selection

- Balanced logistic regression heads are fitted on the training split.
- Each head's probability threshold is selected using validation category–polarity F1.
- The alternative SetFit adaptation used 671 training segments, 384 completed steps, batch size 4 and CUDA mixed precision. Encoder before/after hashes confirm actual weight updates.
- Validation pair micro-F1: frozen MiniLM **0.4278**, fine-tuned MiniLM **0.4170**, TF-IDF classifier **0.4144**. Thus the deployed neural-representation checkpoint is **frozen MiniLM + trained heads**.
- Settings and thresholds were written before test scoring. They were not changed after viewing the results.
- The RTX 2050 completed the measured training/comparison stages in about **36.25 seconds**, excluding environment setup/first imports. Peak allocated PyTorch tensor memory was approximately **480.11 MiB**; this is not total process VRAM or system RAM.

## Held-out comparison against the hybrid

Both methods see the same 1,474 source test segments. The hybrid is run first to determine routing; Complete segments keep its output. Partial/Unsupported segments are independently reanalysed. Evaluation includes segments with no in-scope gold category, so false additions count against precision. These are segments from 111 test reviews, not 1,474 independent reviews.

A pair is **(mapped category, sentiment)**. Exact pair equality is required. Neutral and Mixed are combined for this dataset only because its human labels combine them. These scores are not the old SemEval scores and cannot replace those numbers without identifying the new dataset/task.

| Evaluation scope | Method | Precision | Recall | Pair micro-F1 |
|---|---|---:|---:|---:|
| All 1,474 test segments | Hybrid | 0.4041 | 0.4337 | 0.4184 |
| All 1,474 test segments | Routed pipeline | **0.4330** | **0.4779** | **0.4544** |
| 1,113 Partial/Unsupported segments | Hybrid | 0.3479 | 0.3068 | 0.3261 |
| Same 1,113 segments | Routed pipeline | **0.4109** | **0.3841** | **0.3970** |

The routed system improves overall pair F1 by **0.0360** and unresolved-subset F1 by **0.0709**. Correct matched pairs increased from 314 to 346 out of 724 gold pairs. Across changed predictions, the model recovered 88 previously missed correct pairs but lost 56 previously correct pairs. It introduced 205 false pairs and removed 215 previous false pairs. These regressions must remain part of the results.

Exact segment agreement **did not improve**: 0.6058 → 0.6045 overall, and 0.6757 → 0.6739 on routed segments. Pair-level improvement therefore does not mean every review or whole segment became more accurate. There is no supported claim that all Partial reviews are now correct or Complete.

A paired bootstrap by source review gives an approximate 95% interval **[0.0098, 0.0626]** for the overall pair-F1 difference under this fixed mapping/run. This captures resampling uncertainty, not training-seed variation, taxonomy validity or generalization to all hotels. It is one experiment, not repeated-seed evidence.

### Additional taxonomy sensitivity check

After observing the taxonomy mismatch, we also merged Room and Cleanliness **for both methods and gold labels**, without retraining or changing predictions/thresholds. This is an additional sensitivity analysis, not the originally selected training objective.

| Scope | Hybrid F1 | Routed F1 |
|---|---:|---:|
| All test segments, merged accommodation/hygiene | 0.4420 | 0.4711 |
| Partial/Unsupported subset, same merge | 0.3464 | 0.4031 |

The direction of the pair-F1 gain persists, but this does not eliminate the remaining Facilities crosswalk limitation. Service F1 declines in the five-category analysis (0.5520 → 0.5350); improvements are not uniform across categories. Per-category metrics and all case changes are exported.

## Real Booking demo results

On the unchanged 500-review Booking CSV:

- Original hybrid: 44 Complete, 399 Partial, 57 Unsupported.
- **456** Partial/Unsupported reviews were independently routed; 44 Complete reviews retained the hybrid.
- **387** routed reviews received at least one accepted category result; **69** abstained.
- Within the original 399 Partial reviews, **359** received independent category results and 40 abstained. Within 57 Unsupported reviews, 28 received results and 29 abstained.
- The neural category results are selected for routed reviews; original hybrid opinions are not appended to them.

The **387 is not an accuracy or completeness count**. The sample has no human category/polarity gold labels, and some model predictions are wrong. The held-out Trip-MA experiment above is the evidence for pair-level improvement. Booking remains a demonstration and annotation candidate pool.

## Scores and labels

For an accepted Positive/Negative category prediction, let its four-way classifier probabilities be `Ppos`, `Pneg`, `Pneutral/mixed`, `Pabsent`. The displayed **model direction index** is:

`I = (Ppos − Pneg) / (Ppos + Pneg)`

This lies in [-1, 1] and indicates the model's relative Positive/Negative preference. **It is not a calibrated sentiment-intensity score, confidence percentage, star rating, SentiWordNet score or VADER compound score.** Class balancing also affects the probabilities. No strong/weak intensity labels are claimed from this dataset.

Within each review, average accepted sentence indices per category, then average the category means equally. A category with accepted Neutral/Mixed evidence has no numeric index, making the overall review index unavailable too. An unavailable index is not zero. Opposing predicted labels retain Mixed even when their numeric mean cancels. The merged Neutral/Mixed source class is displayed as Mixed/uncertain rather than being silently called Neutral.

## Web demonstration

1. Run `Start_Demo.bat` and open `http://127.0.0.1:8000/`; refresh an already open page.
2. Choose **Hybrid → independent ML/DL reanalysis**.
3. Select **CSV & dashboard → Use real Booking 500**.
4. The top independent-analysis panel reports routed/results/abstained counts and neural category summaries. Use **Show reanalyzed reviews** to filter individual rows.
5. Each row identifies the selected method, category predictions, overall label and index type. Expand Original hybrid for comparison; **View result & trace** shows selected neural evidence and the retained original hybrid trace.
6. The independent evidence includes original sentence spans, every head probability, acceptance decisions and excluded/background classifications. Legacy lexical charts/Mean index remain labelled comparison evidence; model indices are not averaged into them.

The saved model loads locally and inference uses CPU. No hosted LLM, paid API, online inference or database is needed. Model files are hash-verified. The server keeps one batch in memory, so restarting clears the live batch; download evidence when needed.

## Files and commands

| Purpose | Location |
|---|---|
| Human-source conversion, crosswalk and split checks | `hotel_compiler/routed_data.py` |
| Training heads/encoder, comparators and validation thresholds | `hotel_compiler/routed_training.py` |
| Independent inference, routing, sentence spans and score | `hotel_compiler/routed_model.py` |
| Held-out comparisons, metrics, graphs and CSV inference | `hotel_compiler/routed_cli.py` |
| Web runtime and independent-result adapter | `hotel_compiler/web_routed.py` |
| Dashboard presentation | `hotel_compiler/web_assets/routed.js` |
| Data/routing/HTTP/export software contracts | `tests/test_routed_reanalysis.py` |
| Prepared labelled data | `data/neural/tripma-routed-v1/` |
| Saved selected checkpoint | `output/neural/2026-10-23-independent-routed-v1/models/frozen/` |
| Training evidence and alternative checkpoints | `output/neural/2026-10-23-independent-routed-v1/` |
| Held-out comparison, per-case errors and figures | `output/neural/2026-10-23-routed-heldout-evaluation/` |
| One row per Booking review and decision ledger | `output/neural/2026-10-23-routed-booking500/` |

For a concise table with the selected method/overall/index explicitly identified, open `output/neural/2026-10-23-routed-booking500/selected_review_results.csv`. Original training source hashes and current hardened inference/export source snapshots are retained separately in the training output folder. Runtime hardening adds explicit model-error handling and stricter probability validation without changing successful model predictions.

```powershell
.\.venv-neural\Scripts\python.exe -m hotel_compiler.routed_cli prepare --output-dir data/neural/my-new-prepared-data
.\.venv-neural\Scripts\python.exe -m hotel_compiler.routed_cli train --data-dir data/neural/tripma-routed-v1 --output-dir output/neural/my-new-training-run --device cuda
.\.venv-neural\Scripts\python.exe -m hotel_compiler.routed_cli evaluate --data-dir data/neural/tripma-routed-v1 --model output/neural/2026-10-23-independent-routed-v1/models/frozen --output-dir output/neural/my-new-evaluation --device cpu
.\.venv-neural\Scripts\python.exe -m hotel_compiler.routed_cli compare-csv --input dataset/booking_italy_cleaned_demo_500.csv --model output/neural/2026-10-23-independent-routed-v1/models/frozen --output-dir output/neural/my-new-booking-run --device cpu
```

Use a fresh output directory; existing evidence is protected. Preparation requires NLTK for detokenization, already installed in `.venv-neural`. Heavy dependencies remain separate from the original demo environment. All 240 Python tests passed, including 13 new independent-routing contracts; the CSV upload JavaScript contract, isolated renderer contracts and live saved-model 500-row API check also passed. Passing software tests is not sentiment accuracy evidence.

## Before adding the fifth stage to the paper

This pilot supports a defensible claim of **measured pair-level improvement on a documented mapped hotel holdout**. It does not establish a new neural architecture, better calibrated sentiment intensity, six separately supervised categories or higher exact-review accuracy. The paper should describe the routed architecture, data/crosswalk, validation-only selection, gains and regressions together. A fresh human-labelled Booking holdout with the project's exact six-category definitions remains the strongest next validation step.
