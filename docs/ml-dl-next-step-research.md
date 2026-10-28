# Next ML/DL experiment and paper recommendation

Research date: 23 October 2026. This note compares primary-source methods against the implemented system and saved results. These are recommendations, not implemented extensions or new experiment results. No code, training data, model, or IEEE manuscript was changed during this research. A focused companion prior-art assessment is [routed-novelty-followup.md](routed-novelty-followup.md).

## Recommendation

Begin drafting the paper with the current honest results. If there is time for one additional experiment, prioritize **diagnostic-informed selection after independent reanalysis**, because it directly targets observed destructive replacements and provides a testable contribution. If an explicitly fine-tuned deep-learning model is a faculty requirement, the best next model experiment is a **small category-conditioned transformer pair classifier**, rather than adding an unrelated CNN/LSTM for its name. Do not undertake several architectures and tune them against the already inspected test set.

This is an engineering/research recommendation inferred from our error ledger and the literature below. It is not a promise that either proposal will improve F1 or marks.

## Current evidence that motivates the next step

Authoritative files: `output/neural/2026-10-23-routed-heldout-evaluation/{metrics,per_category_comparison,case_changes}.csv` and `change_summary.json`.

- Overall mapped category–polarity pair micro-F1 improved from **0.4184 to 0.4544**.
- On 1,113 Partial/Unsupported test segments, pair F1 improved from **0.3261 to 0.3970**.
- Exact segment agreement decreased slightly: **0.6058 to 0.6045** overall.
- The routed system recovered **88** correct pairs but lost **56** previously correct pairs. It introduced **205** false pairs and removed **215** prior false pairs.
- Facilities remains weak: routed pair precision **0.1724**, F1 **0.2449** under the approximate Building/Business crosswalk.
- Service F1 declined **0.5520 to 0.5350**. Improvements are not uniform.
- The encoder fine-tuning candidate lost to frozen MiniLM on validation (**0.4170 vs 0.4278** pair F1). Current deployment is frozen deep embeddings plus trained classical ML classifiers.

The first problem to address is therefore not just missed outputs: it is deciding when a new prediction is actually preferable. Category definitions also differ between datasets; a more powerful encoder cannot create a separately annotated Staff class or separate the source's merged Neutral/Mixed labels.

The current test has been inspected. Subsequent decisions informed by its errors make follow-up runs exploratory. Keep the old results as reference, tune using training/development or grouped nested cross-validation, and use a fresh independently human-labelled hotel holdout for confirmatory claims.

## Alternative 1: category-conditioned transformer pair classification

**Recommended model experiment if we want genuine task-specific DL fine-tuning.**

Current architecture encodes a sentence once and feeds the vector to category-specific logistic regressions. Proposed architecture supplies both sentence and candidate category to the transformer:

```text
[CLS] We waited two hours before anyone checked us in. [SEP] Service [SEP]
                                ↓
               small transformer + classification head
                                ↓
             Absent / Negative / Neutral-Mixed / Positive
```

The candidate category is provided by the system, not a gold answer. At inference, evaluate the five supported category candidates independently. A shared classifier may then learn how wording relates to each category while updating transformer weights. No explicit aspect noun needs to be present. For a review with multiple categories, keep multiple accepted category predictions.

This is an established ABSA formulation: Sun, Huang and Qiu (2019) convert aspect sentiment analysis into sentence-pair classification with an auxiliary aspect sentence. Thus using this formulation is an alternative model, **not a novel algorithm invented by this project**. [NAACL paper](https://aclanthology.org/N19-1035/)

Cross-encoders jointly process two texts and can produce multiclass labels; the official documentation distinguishes that from a one-score retrieval reranker. We would train a category/polarity classifier, not download a search relevance checkpoint and call its relevance score sentiment. [Sentence Transformers CrossEncoder](https://sbert.net/docs/package_reference/cross_encoder/model.html), [training guide](https://www.sbert.net/docs/cross_encoder/training_overview.html)

Proposed practical configuration: reuse the small MiniLM transformer, initialize a four-class head, start with a 128-token limit and batch size 2–4, mixed precision, and 1–3 epochs with validation-based checkpoint selection. Freeze lower layers initially if needed. These are candidate settings, not tested optimal settings. The RTX 2050's 4 GiB VRAM is plausibly sufficient for this small pilot based on our prior local MiniLM training allocation of about 480 MiB; actual paired-classifier peak memory and speed must be measured. No exact runtime promise is justified before profiling. Pairing increases examples/inference work roughly with the number of category candidates.

Unlike the earlier contrastive run, supervised cross-entropy directly optimizes the desired category-conditioned state. That different objective is a reason to test it; the fact that one contrastive fine-tune failed does not establish that all supervised transformer fine-tuning will fail. Nor does it establish this alternative will win. Official Transformers supports sequence-classification fine-tuning. [Text-classification guide](https://huggingface.co/docs/transformers/tasks/sequence_classification)

Train on human source labels and their absent-category complements. Include random background negatives and confusable in-scope/out-of-scope examples from training; do not generate fake hotel reviews and present them as real labels. Hold the taxonomy and source split fixed. All category-state training limitations remain: Staff pooled under Service, Neutral/Mixed merged, Facilities approximately mapped.

## Alternative 2: diagnostic-informed result selection

**Recommended bounded extension for a stronger methodological story.**

All Partial/Unsupported reviews can still enter the independent model, as requested. A small post-reanalysis selector then chooses the whole-review result:

```text
Partial / Unsupported review → independent category model
                                      ↓
             diagnostic and prediction comparison features
                                      ↓
                  use neural / retain hybrid / abstain
```

It does not append opinions from the two methods. Retaining the hybrid means retaining its Partial status and explicitly labelling that no safe replacement was selected. Abstention remains an unresolved result.

Potential features, available without gold labels at inference: diagnostic types/counts, missing lexical evidence, excluded-topic flags, fraction of unresolved text, original/neural category agreement, model margins/entropy, and text length. The selector can be logistic regression or a small decision tree on cached features; no GPU is needed. This is ML. A multilayer perceptron would be a trainable neural selector, but the neural layer itself would not establish novelty.

Derive training targets by comparing both candidate outputs with human gold under a predeclared loss, for example missed and false category–polarity pairs, with a fixed tie policy. Train the selector using **out-of-fold base-model predictions** grouped by review/hotel, not predictions made on the same data used to fit those base models. Otherwise its apparent ability to choose the winner is optimistic. Source labels and routing units must remain aligned: a segment-level gate does not establish whole-review correctness without a documented review aggregation/evaluation protocol.

For the user-requested full-review workflow, aggregate available diagnostics and candidate category outputs at review level, train/evaluate selection against aggregated human review labels, and report sentence-level metrics separately. Alternatively begin with a clearly labelled segment-level pilot; do not quietly call its segments full reviews.

Novelty is possible only as a **specific, empirically supported design contribution**: test whether compiler-style failure diagnostics improve decisions beyond ordinary confidence thresholds. Two-stage sentiment classification already exists—Nguyen et al. route rejected sentiment documents from Naive Bayes to SVM. Learned deferral and reject-option prediction also predate us. [Nguyen et al., 2013](https://aclanthology.org/I13-1114/), [SelectiveNet, 2019](https://proceedings.mlr.press/v97/geifman19a.html)

Required comparisons: hybrid alone, neural on all inputs, current status-only routing, confidence-only selection, diagnostic-only selection, and diagnostics plus confidence. Report quality and the cost of all stages. If the selector uses neural probabilities, it runs after neural inference and cannot claim to save that inference within the routed cohort. A separate pre-inference gate would be needed for additional compute savings there.

The critical evidence is not that the new gate exists, but that its diagnostics add value on a fair held-out comparison. If it does not beat confidence-only selection or a simpler policy, report that limitation rather than claim diagnostic novelty.

## Other feasible options, in priority order

| Option | ML/DL distinction | Benefit to test | Limitation and priority |
|---|---|---|---|
| Calibration and improved validation design | Statistical probability post-processing | More meaningful acceptance probabilities; potentially fewer damaging predictions | Calibration is not guaranteed to improve classification F1, does not turn confidence into sentiment intensity, and is established methodology. High value for selection quality. |
| Small MLP on frozen MiniLM vectors | Trained neural classifier on frozen deep features | Nonlinear boundaries without fine-tuning the transformer | Easy CPU/small-GPU pilot; can overfit limited data. No automatic novelty or superiority over logistic regression. |
| Linear SVM or regularized LR feature ablation | Classical ML | Cheap check that a complicated neural head is necessary | Useful comparator, not a headline novel method. SVM margins require care if displayed as probabilities. |
| LoRA on a small category-conditioned encoder | Parameter-efficient DL fine-tuning | Reduce the number of trainable parameters | LoRA is a training technique, not a new sentiment method or guaranteed accuracy increase. Probably unnecessary before testing simpler lower-layer freezing on a small encoder. |
| Hotel-domain masked-language pretraining | Additional unsupervised DL training | Adapt representations to domain language | More work and less direct supervision; cannot supply missing category labels. Not a first next step with a short report timeline. |
| New CNN/BiLSTM trained from scratch | DL | Additional architecture baseline | No demonstrated advantage here over pretrained representations, larger data/training burden, and not inherently novel. Low priority. |

Probability calibration has established methods and requires calibration data independent of classifier fitting; with small per-class counts, flexible calibration can overfit. Use review-grouped training/development predictions and inspect reliability/Brier/log-loss in addition to F1. [Installed-version scikit-learn calibration documentation](https://scikit-learn.org/1.7/modules/calibration.html), [Guo et al., 2017](https://proceedings.mlr.press/v70/guo17a.html)

The MLP alternative is a standard supervised neural network, supported by the existing scikit-learn environment; a custom PyTorch head can additionally expose dropout and explicit training logs. Its proposed benefit here is a hypothesis. [MLP documentation](https://scikit-learn.org/1.7/modules/neural_networks_supervised.html)

LoRA trains low-rank adaptation weights while retaining pretrained weights, reducing adaptation parameters. We have not implemented or benchmarked it here. [Official PEFT explanation](https://huggingface.co/docs/peft/main/en/conceptual_guides/lora)

Domain-adaptive pretraining is supported by prior research across several domains including reviews, but those reported benefits are not our measured hotel results. Do not put their improvements into our results table. If later attempted, keep held-out hotels/text out of adaptation and test its incremental value. [Gururangan et al., 2020](https://aclanthology.org/2020.acl-main.740/)

## Data improvements that a model switch cannot replace

The current human-labelled source does not match all six original categories or distinguish Neutral from Mixed. A fresh six-category human-labelled hotel evaluation sample, including factual content and excluded Location/Price, would strengthen the paper more than another unvalidated model name. Choose a representative sample; preserve source text and annotate category, sentiment, implicit/explicit expression and relevant spans. Use more than one annotator on a shared subset if feasible and report disagreement/adjudication.

Development annotations and final evaluation labels must be separate. Human-reviewing only favorable recovered predictions would bias precision. Include lost predictions, false additions, abstentions and reviews without in-scope opinions. Existing machine predictions may help prioritize annotation, but remain suggestions, not human ground truth.

## Defensible novelty and paper framing

Current defensible claim: an auditable hotel-analysis architecture with explicit failure states and independently evaluated statistical reanalysis. It is an applied systems contribution, not the invention of MiniLM, lexicon fusion, aspect sentiment, or fallback routing.

Potential stronger research question, only after the proposed experiment:

> Do compiler-style failure diagnostics improve selective replacement of unresolved hotel-review predictions compared with confidence-only and unconditional reanalysis policies?

That question is measurable, tied to this project's compiler design, and tests an actual mechanism. A possible paper title after a successful diagnostic-selection study is **Diagnostic-Guided Selective Reanalysis for Auditable Hotel-Review Sentiment Analysis**. The descriptive title is not proof of worldwide novelty. A targeted search cannot establish a first-ever claim.

Draft introduction, literature, existing architecture, datasets and current limitations now. Leave the final contribution claim and results tables open for one bounded experiment if time allows. If the deadline is immediate, stop at the current measured system and present the alternatives as future work. Do not add a weakly validated model merely to use the term DL.

## Minimal next experiment and stopping rule

1. Freeze the existing checkpoint and recorded results; agree on mapped task versus new six-category annotations.
2. Generate grouped out-of-fold predictions from the training data to support calibration/selector training. Keep test labels out of feature and threshold selection.
3. Compare the simplest diagnostic/selection policies. If actual DL training is specifically desired, run one category-conditioned small-transformer comparator, preserving the current ML fallback.
4. Select using development performance, with false additions, lost correct predictions and exact agreement reported alongside pair F1. Avoid choosing only the metric that improved.
5. Confirm the frozen choice on new human-labelled hotel data where possible. Otherwise state that the previously inspected benchmark is exploratory follow-up evidence; grouped nested cross-validation can provide additional internal estimates, not a substitute for external validation.
6. If no clear development benefit appears, keep the existing model and write the paper around the negative finding and documented trade-offs. No model name or routing scheme guarantees a higher mark or a publishable novelty claim.
