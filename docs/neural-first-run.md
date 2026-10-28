# First neural recovery experiment — 23 October 2026

Later the same day, the saved model was integrated into the web dashboard. See [the dashboard guide](web-hybrid-demo.md). The experiment below records the training/evaluation run; the later interface does not alter its measured scores.

## What was implemented

An optional fifth processing stage now supplements the existing VADER–TextBlob hybrid. It uses a local MiniLM sentence encoder and logistic-regression classification head to recover missing sentiment for eligible explicit aspects in **Partial** results. The encoder was actually fine-tuned using SetFit contrastive learning; its before/after weight hashes differ. The SentiWordNet compiler, original hybrid scores, diagnostics and statuses are retained.

This is an implementation of established neural methods with selective routing and traceable recovery. It is not a claim that MiniLM, SetFit, contrastive learning or logistic regression is a new algorithm.

## Real data and split

The official [Webis-Tripad-13-Sentiment release](https://zenodo.org/records/3266053) supplies 2,100 real hotel reviews with human statement sentiment and expert aspect spans. The source archive SHA-256 is `d5e7696fceccede81b4300509450fc349a97e881947b22faa0432f26d51a6573`; licence: CC BY 4.0.

The preparation program retained original statements containing exactly one fully contained expert aspect. It removed duplicate inputs and excluded conflicting labels, crossing spans and multiple-aspect statements. No generated/paraphrased reviews, machine-generated labels or star-rating-derived labels were used.

| Split | Statements | Distinct reviews | Hotels |
|---|---:|---:|---:|
| Train | 6,687 | 1,349 | 97 |
| Validation | 1,876 | 392 | 27 |
| Test | 1,235 | 262 | 16 |

Hotels, review hashes and normalized input hashes are disjoint across splits. Classes are **Negative, Objective, Positive**. Objective is a source factual-statement class, not human-labelled neutral aspect sentiment. No prepared inputs exceeded the 128-token limit in this run.

## Actual training run

- Hardware: NVIDIA GeForce RTX 2050, 4 GiB VRAM.
- Encoder: `sentence-transformers/all-MiniLM-L6-v2`, revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`.
- Head: balanced logistic regression fitted on all 6,687 training statements.
- Contrastive adaptation: 768 training statements (256 per class), 256 completed optimizer steps, batch size 4, learning rate 0.00002, CUDA mixed precision, seed 172026.
- Encoder training took **17.33 seconds**; the measured experiment stages took **39.93 seconds** in total, excluding package installation, first imports and subsequent batch evaluation/plot rendering. First-time CUDA setup took substantially longer.
- Peak PyTorch tensor allocation: **536.71 MiB**. This is allocated tensor memory, not total driver/process VRAM use or system RAM.
- Validation selected fine-tuned MiniLM: macro-F1 **0.7167**, versus frozen MiniLM **0.7022**. Test data did not select the checkpoint or acceptance gate.

## Held-out statement classification

| Method | Correct / 1,235 | Accuracy | Macro-F1 |
|---|---:|---:|---:|
| TF-IDF + logistic regression | 874 | 70.77% | 0.6621 |
| Frozen MiniLM + logistic regression | 909 | 73.60% | 0.6960 |
| Fine-tuned MiniLM + logistic regression | 939 | **76.03%** | **0.7236** |

Fine-tuning improved test accuracy by **2.43 percentage points** and macro-F1 by **0.0276** over frozen MiniLM in this single run. No statistical-significance or repeated-seed claim is made. These are selected single-aspect statement results, not full-review completeness or official end-to-end ABSA accuracy.

For the selected model, per-class test F1 was Negative **0.8040**, Objective **0.5701**, Positive **0.7966**. Objective remains the weakest class. The model can confuse factual descriptions with sentiment.

The validation-selected acceptance gate was maximum probability at least **0.60** and top-two probability margin at least **0.30**, with Objective predictions always abstaining. On validation it accepted 1,112 cases at 90.02% empirical precision. With that unchanged gate, it accepted **713/1,235 (57.73%)** test cases; **647/713 (90.74%)** accepted predictions were correct. Thus 66 accepted predictions were still wrong. **90.74% is selective precision, not accuracy on all test statements or a guarantee on Booking reviews.**

## Integration on real Booking demo reviews

The unchanged `dataset/booking_italy_cleaned_demo_500.csv` was evaluated with the selected local checkpoint. Its original hybrid statuses were 44 Complete, 399 Partial and 57 Unsupported.

- 181 unscored aspect records were examined; 132 met routing requirements.
- 21 additional Positive/Negative predictions were accepted across **20 reviews**.
- Of the eligible contexts, 87 were predicted Objective, 21 were below the probability threshold and 3 failed the margin gate.
- 49 records were ineligible: 33 inherited targets, 13 outside Partial reviews, 2 overlapping unresolved/excluded contexts and 1 multiple-target context.
- No model processing errors occurred. All 500 original review texts, row ordinals and decision source spans were verified against the input CSV.

Examples of accepted predictions from original Booking text:

| Original context | Aspect | Neural label |
|---|---|---|
| The bed was squeaky. | bed | Negative |
| The AC quit working | AC | Negative |
| This Roman apartment is a gem! | apartment | Positive |

These demonstrate model outputs, not independently validated Booking gold labels. Spot-checking also exposed questionable outputs: `close proximity to restaurants Nothing I can think of.` was predicted Negative for Food, and `food Sketchy people who run the place` inherited a questionable Food target from extraction. Some nearby-restaurant statements concern Location, outside the six-category scope. The polarity model cannot reliably repair those upstream attachments or recover context lost during segmentation. The gate was not retuned after viewing these examples.

Original completeness statuses remain unchanged. These 20 reviews are marked separately as **neural_assisted**, with existing diagnostics retained. The stage adds opinion predictions within already analyzed reviews; it does not establish a higher full-review coverage/completeness rate. This unannotated Booking sample cannot provide an accuracy estimate for recovery.

## Existing SemEval development comparison

The same previously inspected hotel benchmark adaptation was run with the original crosswalk and scoring rules. Its 148 cases are sentence-category classification cases, not 148 independent hotel reviews. Tuple scores match sets of mapped category–polarity pairs, not full target/opinion quadruples.

| Method | Correct / 148 | Accuracy | Macro-F1 | Tuple-F1 |
|---|---:|---:|---:|---:|
| SentiWordNet | 72 | 48.65% | 0.4037 | 0.5912 |
| VADER–TextBlob hybrid | 85 | 57.43% | 0.3999 | 0.6450 |
| Hybrid + selective neural recovery | 85 | 57.43% | 0.3999 | 0.6450 |

**No improvement on this benchmark was measured.** Of 23 unscored records, 12 were eligible: the model abstained on 10 Objective predictions and 2 below-threshold predictions. The remaining records were inherited targets or outside Partial reviews. No SemEval labels were used for training, checkpoint selection or gate selection. Because this benchmark was already inspected during project development, it remains development evidence rather than a new untouched test set.

Do not compare the 76.03% Webis classification accuracy directly with 48.65%/57.43% SemEval accuracy: the datasets, label definitions and extraction requirements differ.

## Files and reproduction

- Training data: `data/neural/webis-v1/{train,validation,test}.csv` and `manifest.json`.
- Selected model: `output/neural/2026-10-23-webis-v1/models/finetuned/`.
- Training metrics, per-case predictions, confusion counts, training loss, settings and environment lock: `output/neural/2026-10-23-webis-v1/`.
- Publication figures: `fig_heldout_statement_metrics.pdf`, `.svg` and `.png` in the training folder.
- One row per Booking review: `output/neural/2026-10-23-booking500/review_results.csv`.
- Full recovery decision ledger: `output/neural/2026-10-23-booking500/neural_decisions.csv`.
- SemEval metrics/traces: `output/neural/2026-10-23-semeval-development/`.
- Implementation and commands: [neural-recovery.md](neural-recovery.md).

```powershell
.\.venv-neural\Scripts\python.exe -m hotel_compiler.neural_cli compare-csv dataset/booking_italy_cleaned_demo_500.csv --model output/neural/2026-10-23-webis-v1/models/finetuned --output-dir output/neural/my-new-demo --device cuda
```

Use a new output folder. The saved model can also infer on CPU with `--device cpu`; training was performed on the local GPU. There are no paid API calls.

The existing 222 software tests passed, including 12 new neural/data contracts. The actual GPU training run, checkpoint reload and both evaluation commands also completed. Software tests establish implementation contracts, not sentiment correctness. The web UI and IEEE manuscript were not changed in this task, and no GitHub push was performed.

## What this supports and what remains

This pilot establishes a working, inexpensive neural training/recovery path and a modest held-out improvement over frozen embeddings. It does not establish that neural recovery improves the existing SemEval benchmark or solves all Partial reviews. Before claiming end-to-end gains in the paper, obtain fresh human labels for a representative sample of unresolved hotel aspects, including factual and out-of-scope cases. Future changes should be tuned on fresh development data while preserving an untouched final test partition.
