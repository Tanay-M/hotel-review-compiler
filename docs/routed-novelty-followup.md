# Routed sentiment recovery: targeted novelty follow-up

Research date: 23 October 2026. This is a focused primary-source assessment, not an exhaustive priority search. Recommendations are research proposals, not implemented features or measured gains. Only this note was written; project code, results and manuscript were not changed.

## Finding

The current system has a credible applied systems contribution, but **routing difficult sentiment cases to a second classifier is established prior art**. Replacing logistic regression with another familiar classifier or adding a transformer does not by itself create a new method. The more promising extension is a precisely defined **diagnostic-conditioned selection policy**: use the compiler/hybrid failure evidence to decide whether an independent category/polarity result should replace the original result or remain unresolved. This is a plausible project-specific contribution if its value is isolated experimentally; it is not a justified claim of being the first learned router or first selective sentiment system.

## Six primary sources and what they rule out

| Source | Verified overlap | Implication for this project |
|---|---|---|
| D. Q. Nguyen, D. Q. Nguyen and S. B. Pham, **A Two-Stage Classifier for Sentiment Analysis**, IJCNLP 2013, pp. 897–901. [ACL record](https://aclanthology.org/I13-1114/), [full paper](https://aclanthology.org/I13-1114.pdf). | A first-stage Naive Bayes sentiment classifier accepts easier documents and rejects difficult documents to a second-stage SVM. The rejection decision uses polarity probabilities and thresholds; the second stage uses additional features. | This is especially close prior art. The broad claim “we apply ML only to reviews the first system cannot classify” is not novel. Our diagnostic states differ from its probability rejection, but that narrower distinction needs an ablation rather than a priority claim. |
| D. Madras, T. Pitassi and R. Zemel, **Predict Responsibly: Improving Fairness and Accuracy by Learning to Defer**, NeurIPS 2018. [Proceedings](https://papers.neurips.cc/paper_files/paper/2018/hash/09d37c08f7b129e96277388757530c72-Abstract.html), [paper](https://proceedings.nips.cc/paper/2018/file/09d37c08f7b129e96277388757530c72-Paper.pdf). | A learner can pass a decision to an external decision maker, and learns to account for downstream decision behavior. | Learned selection among decision makers is established. We can adapt that principle to symbolic versus statistical hotel analysis, but should cite the family and avoid claiming invention of deferral. Their human/fairness setting is not identical to our automated fallback. |
| T. Bolukbasi, J. Wang, O. Dekel and V. Saligrama, **Adaptive Neural Networks for Efficient Inference**, ICML 2017, PMLR 70:527–536. [Proceedings](https://proceedings.mlr.press/v70/bolukbasi17a.html), [paper](https://proceedings.mlr.press/v70/bolukbasi17a/bolukbasi17a.pdf). | Learns early exits and network-selection policies to avoid expensive inference on easy examples, with an explicit cost/quality objective. | Running a more expensive model only when needed is established. A measured quality/latency trade-off remains a useful empirical contribution, but computational savings must be measured rather than inferred from a routing diagram. |
| Y. Geifman and R. El-Yaniv, **SelectiveNet: A Deep Neural Network with an Integrated Reject Option**, ICML 2019, PMLR 97:2151–2159. [Proceedings](https://proceedings.mlr.press/v97/geifman19a.html), [paper](https://proceedings.mlr.press/v97/geifman19a/geifman19a.pdf). | Jointly learns prediction and selection under a coverage objective, evaluating the risk–coverage trade-off. | Abstaining on uncertain neural outputs and reporting accepted-output quality is established. The contribution must concern our specific evidence/policy and measured behavior, not abstention itself. |
| Hugging Face, **SetFit for Aspect Based Sentiment Analysis**, version 1.1.3. [Official guide](https://huggingface.co/docs/setfit/v1.1.3/en/how_to/absa). | The documented pipeline generates aspect candidates with spaCy, filters them with a SetFit model, then predicts aspect polarity using another SetFit model. | Aspect extraction/filtering plus learned sentiment is already a supported framework. Our current category-only neural route is technically different and does not extract target/opinion spans; installing this framework would be an alternative implementation, not automatic novelty. |
| C. Guo, G. Pleiss, Y. Sun and K. Q. Weinberger, **On Calibration of Modern Neural Networks**, ICML 2017, PMLR 70:1321–1330. [Proceedings](https://proceedings.mlr.press/v70/guo17a.html), [paper](https://proceedings.mlr.press/v70/guo17a/guo17a.pdf). | Examines whether predicted confidence corresponds to correctness frequency, and studies post-processing calibration, including temperature scaling. | A classifier probability is not guaranteed correctness and is not sentiment intensity. Calibration can support a more meaningful acceptance policy, but temperature scaling/Platt-style calibration is established and does not establish a novel algorithm. |

The broad ideas in all six sources predate this project. These overlaps do not show that every combination of our diagnostics and source-preserved records has already been implemented, but absence of an identical found system is insufficient to establish global novelty.

## Why a selection policy addresses a measured problem

The saved experiment reports a five-category mapped pair micro-F1 improvement from 0.4184 to 0.4544, but exact segment agreement falls slightly. Its error-change ledger counts **88 newly correct pairs and 56 previously correct pairs lost**; it also introduces 205 false pairs and removes 215 previous false pairs. These are measured project outputs in `output/neural/2026-10-23-routed-heldout-evaluation/`, not statements from the cited papers.

The present router uses only the coarse Hybrid status: every Partial/Unsupported review is reanalysed, and its independent output is selected. A Partial state can mean unknown opinion vocabulary, an unresolved clause, excluded Location/Price content or another failure. Those causes need not benefit equally from replacement. A conditional selection policy directly targets unnecessary destructive replacements, rather than simply demanding more outputs.

## Feasible candidate contribution

Proposed name: **diagnostic-conditioned selective reanalysis**. This is a descriptive method name, not proof of novelty.

Within the already-routed Partial/Unsupported cohort, a small selector could estimate whether the independent prediction is safer to use, whether the original output should be retained, or whether to abstain. Candidate features include diagnostic types/counts, lexical-evidence availability, unresolved-text share, number of extracted categories, original/neural agreement, per-head probability margins and input length. These features are available at inference without reading gold labels. Do not include an oracle feature such as whether the actual test prediction is correct.

An inexpensive logistic regression selector is a realistic first experiment on cached features and outputs. It is ML, not newly trained deep learning. A small multilayer perceptron would be a DL-trained selector, but the method's contribution should remain the routing evidence and decision objective rather than the presence of a neural layer. The current GPU is not needed for a small cached-feature selector.

For a training example, derive retain/replace/abstain supervision from the relative prediction loss of both systems against human gold. Define the loss and tie policy before evaluation. Use **out-of-fold** model predictions when creating selector-training labels; resubstitution predictions from the same classifier fitted on those examples would make the selector overly optimistic. The existing Trip-MA labels can support a mapped segment-level selector experiment, but do not silently relabel that as a newly human-annotated six-category full-review dataset.

The full-review routing requirement can remain: all Partial/Unsupported reviews enter the independent analysis; the selector controls whether its proposed result is trusted as the selected result. However, retaining the original output on an unfavorable replacement changes the current replacement-only policy and must be documented explicitly. It does not imply unioning opinions from both methods.

## Minimum experiments needed to defend it

Compare identical frozen base predictors under:

1. Hybrid alone.
2. Independent model on every input, to expose the strength/cost of the model itself.
3. Current static Partial/Unsupported routing.
4. Confidence-only acceptance/selection.
5. Diagnostic-only selection.
6. Diagnostic plus confidence/disagreement selection.

Use the same gold units, taxonomy and denominators. Report category/polarity pair precision, recall and F1; exact segment agreement; category-level gains/regressions; newly correct/lost correct pairs; false additions; accepted-output error versus coverage; and wall-clock inference cost, including feature extraction and selector overhead. A simpler gate's gain over a confidence-only gate is the key evidence that diagnostics add information.

A review-level policy needs review-level gold aggregation and evaluation defined in advance. Do not optimize a segment-level criterion and present the result as full-review correctness. Preserve separate metrics for implicit cases, background/out-of-scope cases and the failure types that motivated the policy.

The present hotel test set has now been inspected. Reusing it for trying several gates produces exploratory follow-up evidence, not an untouched confirmatory test. Tune on training/development only; reserve a fresh, independently annotated Booking sample for final confirmation. The current five-category crosswalk, Staff→Service pooling, source Neutral/Mixed merge and approximate Facilities mapping remain limitations no gate can erase.

## Recommendation for a near-term paper

If the report deadline is close, the existing implementation plus honest error analysis is stronger than adding an unvalidated larger model for its name. A bounded selector/ablation experiment is more directly connected to observed regressions and a defensible methodology contribution than replacing logistic regression with a CNN/LSTM/SVM and calling that novel. Stop the experiment if it fails to improve validation quality; preserve the negative result.

Safe current wording:

> We implement a source-traceable hotel sentiment framework with explicit analysis diagnostics and selective statistical reanalysis of unresolved reviews, and evaluate prediction quality, recovery and regression trade-offs on a documented mapped hotel holdout.

Potential wording **only after implementing and evaluating the selector**:

> We investigate whether compiler-style failure diagnostics improve selective replacement decisions beyond confidence-only routing in a symbolic–statistical hotel sentiment pipeline.

Avoid “first hybrid sentiment system,” “novel transformer,” “new deep-learning algorithm,” “guaranteed correction of Partial reviews,” or a claim that an extra model necessarily improves marks. The contribution is an experimentally supported design and its scope, not the fact that the project contains ML/DL.
