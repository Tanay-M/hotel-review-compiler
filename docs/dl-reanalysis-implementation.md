# Fine tuned deep learning reanalysis of unresolved hotel reviews

Implemented and trained on 23 October 2026. The current dashboard uses checkpoint `minilm-dl-pair-ed2d9d623f83` under **Hybrid → fine-tuned DL reanalysis**. This report and the accompanying CSV/PDF/SVG figures are ready to support the IEEE paper revision. The main IEEE manuscript now incorporates this fifth-stage DL extension; see output/paper for the revised Word/PDF.

## What this adds

The hybrid runs first. Only a review with **Partial or Unsupported** hybrid status is sent to the independent DL model. The model processes **all original sentences of that selected review**, including language that has no recognized hybrid aspect/opinion term. Complete reviews retain the hybrid result; validation errors and processing errors remain failures. This uses the existing status gate, with no diagnostic-aware learned selector.

The DL result becomes the selected result for that routed review. It is not appended to the hybrid's opinions. Original hybrid records, statuses, scores and diagnostics remain available for comparison. An accepted prediction is not relabelled Complete or human-verified. An abstention remains unavailable, rather than silently becoming Neutral.

The previous frozen MiniLM representation plus logistic regression was ML using a deep representation. The current model **fine-tunes the transformer encoder and a neural classification head together**, so this implementation is supervised **deep learning**. It is a small transformer classifier, not a generative/chat LLM.

## Architecture and learning

For every sentence u, the same transformer receives a pair `(u, category description)` for each of eight categories. A shared four-class softmax head predicts **Absent, Negative, Neutral/Mixed, Positive**. The category description conditions the prediction: one sentence can be positive about Room and negative about Service. There are eight category queries, not eight separately trained transformer networks.

Five queries produce in-scope categories: Room, Cleanliness, Service, Food and Facilities. Excluded, Other and NotRelated queries represent background. Staff is pooled into Service because this training source does not separately annotate Staff. Location and Value are excluded. Neutral/Mixed is the source's merged class; it is not pure Neutral. No labels for Strong/Weak intensity were invented.

For category c: `p = softmax(f_theta(u, q_c))`. Let `y = argmax(p)`. Accept only when y is not Absent, `p[y] >= tau_c`, and c is in scope. Thresholds are selected on validation data. This estimates category-specific sentiment without matching the old compiler vocabulary.

Training minimizes weighted cross-entropy `L = mean(-w_y * log(p_y))` over labelled sentence/category pairs. In implementation the weighted cross-entropy reduction normalizes by the sum of target weights within each minibatch. The optimizer updates both the encoder and neural head. Class weights are proportional to `sqrt(N/(4*n_y))`, then normalized to mean one, reducing the dominance of Absent examples.

```text
Algorithm 5  Independent DL reanalysis
Input: original review x; hybrid H; trained theta; thresholds tau
Output: selected result Y
1: if H.status not in {Partial, Unsupported}: return H
2: Y <- empty
3: for u in Sentences(x):
4:     for c in Categories:
5:         p <- Softmax(Transformer_theta(u, Query[c]))
6:         y <- ArgMax(p)
7:         if InScope(c) and y != Absent and p[y] >= tau[c]:
8:             Y <- Y union {(c, y, u, p)}
9: return Aggregate(Y) if Y != empty else Abstain
```

No text is silently truncated: a sentence whose category pair exceeds 160 WordPiece tokens remains unavailable with a length warning. Source offsets identify whole sentence evidence; the model does not learn exact target or opinion spans.

## Human supervision and split protocol

Training uses the Trip-MA English author release, commit `a9f47df668d3e2ec37bb13e04d1005fb1623d91d`. Original category/polarity annotations provide the labels, including explicit and implicit opinions. The release serializes surface tokens/POS/lemmas: conversion detokenizes the original surface tokens, rather than writing replacement reviews. Source serialization and hashes are retained. The author repository does not establish an explicit redistribution licence, so downloaded/prepared training data remain local and ignored by Git.

| Split | Segments | Parent reviews | Hotels |
|---|---:|---:|---:|
| Training | 2,040 | 180 | 157 |
| Validation | 602 | 42 | 39 |
| Test | 1,474 | 111 | 103 |

The published test partition is retained. Thirty-six source training reviews sharing hotels with test were removed before deriving validation. Hotel IDs, review IDs and normalized text do not overlap across prepared splits. Two overlength training segments are excluded, leaving **2,038 training segments and 16,304 sentence/category pairs**. Validation and test retain all rows in metric denominators. Unannotated category entries are Absent under the source annotation scheme.

**AI-labelled training examples used: 0.** Human-labelled data were already available and produced an improvement. AI assistance could propose extra training labels, but those would be AI-generated silver labels, not human gold, and would need a separate experiment. They are not needed to substantiate this result. Neither predictions nor review ratings supply the gold test labels.

The test benchmark had already been inspected during earlier project experiments. This is a follow-up exploratory comparison on a fixed split, not a newly untouched benchmark. This run selected its epoch and thresholds exclusively using validation, with no test-driven adjustment. A fresh independent human-annotated evaluation remains necessary for strong generalization claims.

## Training settings and hardware

| Setting | Actual value |
|---|---|
| Base transformer | sentence-transformers/all-MiniLM-L6-v2, pinned revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` |
| Epochs / selected epoch | 3 / 3 |
| Encoder / head learning rate | 0.00002 / 0.0002 |
| Optimizer | AdamW; weight decay 0.01; gradient clipping 1.0 |
| Batch / accumulation / effective batch | 8 / 2 / 16 |
| Maximum pair length | 160 WordPiece tokens; no silent truncation |
| Schedule | Linear decay, 10% warmup |
| Random seed | 172026 |
| Optimizer steps | 3,057 |
| Device | NVIDIA GeForce RTX 2050 |
| Total recorded training and validation time | 248.0 seconds |
| Peak allocated PyTorch tensor memory | 510.1 MiB; not total GPU/process memory |

Validation joint pair F1 rose from 0.4052 at epoch 1 to 0.4764 at epoch 2 and 0.5037 at epoch 3. Checkpoint selection used the highest validation joint pair micro-F1. Saved encoder parameter hashes differ before and after training, verifying actual encoder updates. Library versions, data hashes, class weights, queries, thresholds and checkpoint file hashes are saved in the run metadata. A single seed/run does not establish multi-seed stability.

## Matched benchmark results

These are **category–polarity pair** metrics, not overall review accuracy. A pair such as `(Service, Negative)` matches only if category and polarity both equal the human mapped annotation. Precision is matched/predicted; recall is matched/gold; F1 is their harmonic mean. Missing predictions count against recall. Background-only segments remain in the test denominator. Exact segment match requires identical predicted and gold sets, including empty sets, and is affected by the many background segments.

| Scope / method | Precision | Recall | Pair micro-F1 | Exact segment match |
|---|---:|---:|---:|---:|
| All 1,474 / Hybrid | 40.41% | 43.37% | 41.84% | 60.58% |
| All 1,474 / Hybrid + frozen-encoder ML | 43.30% | 47.79% | 45.44% | 60.45% |
| All 1,474 / Hybrid + fine-tuned DL | 49.20% | 50.69% | 49.93% | 64.72% |
| Routed 1,113 / Hybrid | 34.79% | 30.68% | 32.61% | 67.57% |
| Routed 1,113 / Hybrid + frozen-encoder ML | 41.09% | 38.41% | 39.70% | 67.39% |
| Routed 1,113 / Hybrid + fine-tuned DL | 53.89% | 43.48% | 48.13% | 73.05% |

Across all test segments, DL routing improves F1 by **8.09 percentage points**. On the Partial/Unsupported subset it improves F1 by **15.52 points**. There are 724 in-scope gold pairs overall and 414 on the routed subset. The selected pipeline retains all 361 non-routed hybrid outputs unchanged.

Relative to the hybrid, there are **97 newly correct pairs and 44 lost correct pairs**, a net gain of 53. It also introduces 114 new false pairs and removes 198 previous false pairs. These losses must not be omitted. A paired parent-review cluster bootstrap with 1,000 resamples gives a descriptive 95% interval of **4.94 to 11.67 F1 percentage points** for the all-test DL-minus-hybrid difference; this does not repair development reuse or establish universal superiority.

Four of five mapped categories improve, while **Facilities F1 falls from 18.54% to 13.89%**. Cleanliness gains partly reflect ontology alignment: the hybrid often calls room hygiene Room, whereas Trip-MA uses Cleanliness. A post-hoc sensitivity analysis merging Room/Cleanliness on both sides still shows all-test F1 increasing from 44.20% to 51.47%. This additional analysis uses the same predictions and no refitting; it is not an independent test.

Do not compare these Trip-MA results directly with the old SemEval 148-case three-polarity accuracy or its different pair taxonomy. Report them as a separate experiment. This model has no trained five-band intensity labels, and its probability scores must not be presented as validated sentiment strength.

## Real Booking demonstration

All 500 real cleaned Booking reviews are retained. Hybrid produces 44 Complete, 399 Partial and 57 Unsupported. Exactly **456 Partial/Unsupported reviews** enter DL analysis, while 44 retain hybrid. DL yields accepted categories for **383 reviews**, abstains on **73**, and has no model errors in this run. Booking has no independent category-polarity labels, so these numbers are **coverage and routing counts, not accuracy or confirmed completeness**. DL produces slightly fewer accepted reviews than the earlier ML route (383 versus 387), while its labelled-benchmark F1 is higher.

An authored illustrative input, `We waited two hours before anyone checked us in.`, is Unsupported in the hybrid and receives Service/Negative from DL. The live checkpoint returns a direction index of approximately -0.7427. It is a demonstration example, not an additional human-labelled test case.

## What the DL score means

For an accepted Positive/Negative prediction, the direction index is `(p_positive - p_negative)/(p_positive + p_negative)`. Its range is [-1, 1]. This describes the model's relative positive/negative belief, **not lexicon sentiment magnitude, a star rating or calibrated intensity**. Neutral/Mixed has no direction index. Category indices average accepted sentence indices; the review index averages category indices equally. If any accepted category includes the merged Neutral/Mixed class, the aggregate index remains unavailable. Opposing accepted category labels retain Mixed even if the mean cancels. The UI keeps this index separate from the original lexical Mean index.

## Defensible contribution and viva explanation

Suggested paper title: **Auditable Aspect Sentiment Analysis of Hotel Reviews with Selective Deep Learning Reanalysis**.

The defensible applied contribution is the integration of source-traceable compiler and hybrid outputs with an independently trained category-conditioned DL stage that reanalyses only unresolved reviews, preserves original evidence, and reports both recovered and damaged predictions. The model can recognize implicit opinions without matching the hybrid's vocabulary. The reported comparison and controlled routing make this an explainable project extension.

Do not claim invention of transformers, sentence-pair ABSA, hybrid fallback or a globally new algorithm. Category-conditioned BERT pair classification predates this project [Sun et al., 2019]. Calling this a project-specific integration and measured extension is more defensible than claiming first-of-its-kind novelty.

**Viva:** “We fine-tuned a small transformer on human-labelled hotel sentences. For each category it learns whether the sentence is absent, positive, negative or neutral/mixed. Only reviews left Partial or Unsupported by our hybrid are sent to it. It reads their original text independently, so it can recover implicit complaints. Our measured pair F1 improves, but not every category or review improves.”

## Reproducible commands

```powershell
.venv-neural\Scripts\python.exe -m hotel_compiler.dl_pair --data-dir data/neural/tripma-routed-v1 --output-dir output/neural/NEW-DL-RUN --epochs 3 --device cuda
.venv-neural\Scripts\python.exe -m hotel_compiler.routed_cli evaluate --data-dir data/neural/tripma-routed-v1 --model output/neural/NEW-DL-RUN/models/best --output-dir output/neural/NEW-DL-TEST --device cuda
.venv-neural\Scripts\python.exe -m hotel_compiler.routed_cli compare-csv --input dataset/booking_italy_cleaned_demo_500.csv --model output/neural/NEW-DL-RUN/models/best --output-dir output/neural/NEW-DL-BOOKING --device cuda
.venv-neural\Scripts\python.exe scripts/build_dl_evidence.py
```

Choose a new output directory for every experiment; existing evidence is protected. Running a new training experiment does not silently change the dashboard checkpoint. `HOTEL_COMPILER_ROUTED_MODEL` can select another explicit model directory before restarting the demo. Inference uses CUDA when available and CPU otherwise; set `HOTEL_COMPILER_ROUTED_DEVICE=cpu` to force CPU.

## Files for review

- Training and local DL inference: `hotel_compiler/dl_pair.py`.
- Whole-review routing and independent aggregation: `hotel_compiler/routed_model.py`.
- Frozen-checkpoint matched evaluation: `hotel_compiler/routed_cli.py`.
- Source conversion and disjoint splits: `hotel_compiler/routed_data.py`.
- Dashboard checkpoint loading: `hotel_compiler/web_routed.py`.
- Human train/validation/test tables: `data/neural/tripma-routed-v1/` (local, ignored by Git).
- Model, training settings and weight update proof: `output/neural/2026-10-23-dl-pair-human-v1/`.
- All 1,474 test predictions and original human mapped labels: `output/neural/2026-10-23-dl-pair-evaluation/predictions.csv`.
- All 500 Booking selected results: `output/neural/2026-10-23-dl-pair-booking500/review_results.csv`.
- Paper-ready tables, three vector graphs and evidence manifest: `output/neural/2026-10-23-dl-paper-evidence/`.

## Primary sources for the paper extension

- Sun, Huang and Qiu (2019), Utilizing BERT for Aspect-Based Sentiment Analysis via Constructing Auxiliary Sentence: https://aclanthology.org/N19-1035/
- Wang et al. (2020), MiniLM: Deep Self-Attention Distillation for Task-Agnostic Compression of Pre-Trained Transformers: https://arxiv.org/abs/2002.10957
- Trip-MA / Trip-MAML author release and original paper: https://github.com/diegma/trip-maml and https://aclanthology.org/D15-1302/
- Hugging Face sequence classification implementation documentation: https://huggingface.co/docs/transformers/tasks/sequence_classification
