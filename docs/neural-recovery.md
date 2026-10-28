# Optional neural recovery for Partial outputs

**New architecture:** [independent-routed-ml.md](independent-routed-ml.md) implements full-review rerouting for Partial/Unsupported results. This guide documents the earlier opinion-supplement prototype, which remains available separately for comparison.

This stage supplements the independent VADER–TextBlob hybrid. The SentiWordNet compiler and original hybrid predictions, scores, diagnostics and completeness statuses remain available unchanged. It is an additional experiment; the existing paper and web demo are not changed by running it.

The saved model is also available in the dashboard: run `Start_Demo.bat`, select **Hybrid + neural recovery (MiniLM)**, and use **CSV & dashboard → Use real Booking 500**. See [the dashboard guide](web-hybrid-demo.md) for separate neural counts, individual decisions and downloads.

## Architecture and scope

1. Run the existing hybrid on the original review.
2. Route only a **Partial** result with an explicit, locally attached aspect whose sentiment has `no_lexical_evidence`.
3. Reject inherited targets, multiple targets in the context, invalid source spans, out-of-scope categories and overlapping unresolved-clause/complex-negation diagnostics.
4. Encode `aspect: original context` with a small MiniLM encoder; a logistic regression head estimates Negative, Objective and Positive probabilities.
5. Accept only Positive/Negative predictions passing a validation-selected probability and top-two margin gate. Objective and uncertain predictions abstain.
6. Add accepted opinions as **neural recovery**, retaining the original records and diagnostics. The result is `neural_assisted`, not automatically `complete`.

This does not infer missing/implicit aspects, repair arbitrary grammar, or process every unsupported review. It fills a narrower missing-polarity case. Strong/weak sentiment labels are not trained because this dataset does not provide intensity ground truth. `P(Positive) - P(Negative)` is exported as a separate model polarity index, not a SentiWordNet/VADER score or sentiment-strength probability.

## Real training data

Source: [Webis-Tripad-13-Sentiment, Zenodo](https://zenodo.org/records/3266053), 2,100 real TripAdvisor reviews, CC BY 4.0. Source/archive checksums and the conversion policy are recorded in `data/neural/webis-v1/manifest.json`.

The converter retains exact source substrings with one expert-annotated aspect fully within a human-labelled statement. It does not invent review text or sentiment labels. Statements with no aspect, multiple aspects or crossing aspect boundaries are excluded. Duplicate inputs are removed; conflicting duplicate labels are excluded. Hotels, review hashes and normalized input hashes do not overlap across splits.

| Split | Statements | Hotels | Negative | Objective | Positive |
|---|---:|---:|---:|---:|---:|
| Train | 6,687 | 97 | 2,845 | 1,028 | 2,814 |
| Validation | 1,876 | 27 | 771 | 298 | 807 |
| Test | 1,235 | 16 | 643 | 168 | 424 |

These are **statement counts**, not independent full-review counts. The source Objective label means an objective statement; it must not be presented as an annotated neutral aspect opinion. Token sequences longer than 128 tokens are recorded and not silently truncated. They remain unavailable/errors in full-split classification metrics.

## Training protocol

- Base encoder: `sentence-transformers/all-MiniLM-L6-v2`, pinned immutable revision; six transformer layers.
- Comparator 1: TF-IDF unigram/bigram features plus balanced logistic regression.
- Comparator 2: frozen pretrained MiniLM plus the same classifier.
- Neural adaptation: SetFit contrastive fine-tuning on up to 256 human examples per class, 256 optimizer steps, batch size 4, mixed precision on CUDA. Refit the classifier on all admitted training statements afterward.
- Choose frozen versus fine-tuned checkpoint using **validation macro-F1**; ties prefer frozen. Encoder fingerprints verify weights actually changed.
- Choose the acceptance gate only on validation: maximize accepted Positive/Negative predictions subject to at least 30 accepted and empirical precision at least 90%. Disable recovery if no candidate meets the target. This is empirical selective precision, not a calibrated guarantee.
- Freeze settings before evaluating held-out test labels. Report accuracy, macro-F1, per-class precision/recall/F1, confusion counts, acceptance precision, GPU memory and time.

The selected Webis test task is different from the existing SemEval aspect extraction/category-polarity evaluation. Their scores must not be placed in the same accuracy column as if the tasks were identical. Booking demo recovery counts measure availability, not accuracy, because those reviews have no human aspect labels. The inspected SemEval data remains development evidence, not a new untouched test set.

## Run from the project root (PowerShell)

Use the isolated `.venv-neural` environment. It keeps heavy deep-learning dependencies out of the existing demo environment.

```powershell
py -3.12 -m venv .venv-neural
.\.venv-neural\Scripts\python.exe -m pip install torch==2.7.1 --index-url https://download.pytorch.org/whl/cu128
.\.venv-neural\Scripts\python.exe -m pip install -r requirements-neural.txt
.\.venv-neural\Scripts\python.exe -m pip install -e ".[research]"
.\.venv-neural\Scripts\python.exe -m pip check
```

The first command is only needed if the environment does not exist. If the large official CUDA wheel stalls, `python scripts/download_neural_cuda.py` downloads it in resumable verified chunks; install the completed local wheel using pip. No separate CUDA toolkit installation is needed for that wheel.

```powershell
.\.venv-neural\Scripts\python.exe -m hotel_compiler.neural_cli prepare-webis --output-dir data/neural/webis-v1
.\.venv-neural\Scripts\python.exe -u -m hotel_compiler.neural_cli train --data-dir data/neural/webis-v1 --output-dir output/neural/my-training-run --device cuda
```

Use a **new output directory** for each preparation/training/evaluation run. Existing evidence is protected from overwrite. Preparation downloads the official source archive if absent. Network access is required for first-time dependencies, source data and the pinned pretrained encoder. After training, inference uses local manifested checkpoint files and does not call a paid API.

Read `frozen_settings.json` to see `selected_model`, then use its `models/frozen` or `models/finetuned` folder:

```powershell
.\.venv-neural\Scripts\python.exe -m hotel_compiler.neural_cli compare-csv dataset/booking_italy_cleaned_demo_500.csv --model output/neural/my-training-run/models/finetuned --output-dir output/neural/my-booking-run --device cuda
.\.venv-neural\Scripts\python.exe -m hotel_compiler.neural_cli evaluate-semeval data/vendor/real-hotel-research/semeval2015_hotels.xml --model output/neural/my-training-run/models/finetuned --output-dir output/neural/my-semeval-run --device cuda
```

Change `finetuned` to `frozen` if that is the validation-selected checkpoint. Both remain available for audit. CSV input defaults to `sr.no` and `review`; column flags allow other names. Invalid rows remain in the output. Original IDs and a unique row ordinal are retained.

## Code and outputs to show faculty

| Purpose | File |
|---|---|
| Source validation, annotations, duplicates and hotel-disjoint splitting | `hotel_compiler/neural_data.py` |
| Encoder training, frozen/classical comparators, validation gate and held-out metrics | `hotel_compiler/neural_training.py` |
| Eligibility, abstention, local model integrity checks and non-destructive recovery | `hotel_compiler/neural_fallback.py` |
| Batch comparisons and SemEval development evaluation | `hotel_compiler/neural_cli.py` |
| Software contracts, source integrity and recovery invariants | `tests/test_neural_recovery.py` |

Training produces `metrics.csv`, `predictions.csv`, `per_class_metrics.csv`, `confusion_counts.csv`, `length_exclusions.csv`, `timings.csv`, model files/manifests, selected settings and a publication-ready PDF/SVG/PNG comparison figure. Batch inference produces one row per review in `review_results.csv`, opinion-level outputs and a decision ledger showing why recovery accepted, abstained or did not route.

The completed pilot and its measured results are in [neural-first-run.md](neural-first-run.md). Passing software tests does not demonstrate sentiment accuracy. A neural model can perform worse than a frozen or lexical method; all measured results must be retained.
