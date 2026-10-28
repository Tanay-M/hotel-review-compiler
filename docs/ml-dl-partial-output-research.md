# CPU friendly learned fallback for partial hotel review analysis

Research date: 23 October 2026. This is a design recommendation based on primary sources, not a new experiment. No model was downloaded, no training was run, and neither project predictions nor the IEEE manuscript was changed. Model sizes below describe weight files rather than total installed packages, working RAM or runtime.

## Recommendation

**Hardware update, 23 October 2026:** after the user identified their GPU, a read-only `nvidia-smi` query confirmed NVIDIA GeForce RTX 2050 with 4,096 MiB VRAM and 3,955 MiB free at that instant. The earlier inspection covered CPU and system RAM only; absence of an external GPU did not mean absence of a usable local GPU. This changes the preferred next experiment: a small-batch MiniLM encoder fine-tuning pilot using SetFit is now a realistic candidate, alongside the frozen-encoder baseline below. This is a feasibility judgment, not a successful training or memory benchmark. The 8 GB system RAM constraint still applies.

For the GPU pilot, use source-preserved target-context inputs, human polarity labels, short sequences (initially 96–128 tokens), embedding batch size 4 initially, a capped contrastive-pair budget, mixed precision where supported, and development-based early stopping or a small epoch budget. Confirm CUDA/PyTorch compatibility and measure peak VRAM before increasing batch size. SetFit updates the encoder during contrastive fine-tuning even if its final classifier is logistic regression, so it constitutes actual local neural fine-tuning. Full two-model SetFitABSA remains a separate, more complex extraction expansion. [Official training arguments](https://huggingface.co/docs/setfit/reference/trainer), [SetFit overview](https://huggingface.co/docs/setfit/main/index).

The remaining CPU-first recommendation is retained as the baseline and lowest-resource alternative, not as a claim that this laptop cannot fine-tune a small neural encoder.

Add an optional **diagnostic routed neural fallback** after the existing analysis, beginning with a frozen `sentence-transformers/all-MiniLM-L6-v2` encoder and a small supervised classifier. Use the learned stage only for unresolved, in-scope aspect contexts, preserve already accepted lexical outputs, and abstain when the learned result is insufficiently reliable. This is a proposed systems contribution, not a newly invented neural architecture.

The first prototype should use logistic regression on cached embeddings. If a locally trained neural component is specifically required, compare a small multilayer perceptron (MLP) head on the same frozen embeddings. That makes the distinction explicit: the representation is pretrained deep learning; logistic regression is classical supervised ML; an MLP head is a trainable neural classifier. Scikit-learn supports both classifier families, and SetFit documentation separately describes pretrained embedding bodies and classification heads. [Logistic regression](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html), [MLP classifier](https://scikit-learn.org/stable/modules/generated/sklearn.neural_network.MLPClassifier.html), [SetFit classification heads](https://huggingface.co/docs/setfit/v1.1.3/en/how_to/classification_heads).

## What must be recovered

Partial is a processing state, not a sentiment class. A sentence may have a recognized target but unavailable sentiment; another may have an unresolved target; another may discuss intentionally excluded Price or Location. These need different actions. A sentiment classifier alone does not discover every missing aspect. The fallback must not assign an entire mixed review's label to each of its aspects or turn an out-of-scope mention into Room just to increase completeness.

Proposed eligible cases are explicit, known aspects whose opinion expression or sentiment remains unresolved. Recovering implicit categories, such as assigning a waiting narrative to Service when no service noun appears, requires a separately trained category/relevance stage. Such additions need category labels and absent/out-of-scope examples. They are not provided automatically by a generic sentence embedding or a target-conditioned sentiment checkpoint. SetFitABSA itself explicitly separates candidate generation, candidate filtering, and polarity classification. [Official ABSA guide](https://huggingface.co/docs/setfit/v1.1.3/en/how_to/absa).

## Local implementation and saved output audit

Read-only inspection on 23 October 2026 found an Intel Core i5-11400H (6 cores, 12 logical processors), 8,297,709,568 bytes of installed RAM (approximately 7.73 GiB), and approximately 0.80 GiB free at the inspection instant. This is a reason to start with small CPU inference batches and cached features, freeing memory before a pilot. It is not an inference speed or training benchmark. The 90.9 MB weight file does not represent the full Python/framework installation or peak process memory.

The existing hybrid exposes source-linked candidates and diagnostic spans in `hotel_compiler/hybrid_nlp.py`; `hotel_compiler/hybrid.py` preserves sentiment availability, errors, original records, and strict status/mean policies. The SentiWordNet orchestrator is `hotel_compiler/pipeline.py`. A fifth stage can consume these records and diagnostics as an optional adapter, without rewriting either scoring engine. Planned code could live in a separate `hotel_compiler/neural_fallback.py`; that file has not been created.

Counts below were computed from the **saved** `output/experiments/2026-10-21/expanded-sentiwordnet-release/booking-cleaned500/diagnostics.csv` and `review_results.csv`. These are distinct review counts, not numbers of diagnostic occurrences, and diagnostic groups overlap. No reviews were rerun or relabeled.

| Hybrid diagnostic in the 500-review cohort | Reviews affected | Consequence for the proposed stage |
|---|---:|---|
| UNRESOLVED_CLAUSE | 425 | Determine whether this is a missed in-scope opinion, factual narrative, or unsupported content; polarity alone is insufficient |
| NO_LEXICAL_EVIDENCE | 126 | Most direct initial use case: an attached context lacks usable lexical sentiment |
| OUT_OF_SCOPE | 248 | Keep Price/Location/Value outside the agreed six categories |
| OUT_OF_SCOPE_PRICE_OPINION | 9 | Do not misassign value judgements to a supported category |
| COMPLEX_NEGATION | 2 | Test scope explicitly; do not assume neural inference resolves it |

Of the 399 Hybrid Partial reviews, 18 have only out-of-scope diagnostic codes; 223 have at least one out-of-scope diagnostic; 381 have at least one non-scope diagnostic. These counts describe the current heuristic diagnostics, not independently verified error causes. In-scope recovery must not erase remaining excluded-topic or unresolved warnings.

The SentiWordNet counts on the same saved cohort are: UNSUPPORTED_CLAUSE 462; UNRESOLVED_CLAUSE 306; MISSING_ASPECT 147; INCOMPATIBLE_OPINION 30; EMPTY_CLAUSE 15. Its diagnostic categories differ from Hybrid's and cannot be interpreted as matched error labels.

Keep the initial experiment narrow: recover polarity for explicit, unambiguously attached aspects in Partial outputs. If useful, add learned category relevance for remaining clauses as a second increment. A classifier returning only a category does not establish an extracted target span; preserve the clause as evidence and label any category inference explicitly. Multiple targets or opposing sentiments still need separate contexts or abstention. Dependency replacement, neural sequence tagging, and automatic repair of every Partial review would expand scope substantially.

## Options

| Option | What it actually learns or supplies | Fit for this project | Important limit |
|---|---|---|---|
| Frozen MiniLM + logistic regression | Pretrained deep semantic features; a small trained polarity/relevance classifier | Recommended first prototype; cache vectors and train only the head on CPU | Needs human labels; generic embeddings are not a ready-made sentiment model |
| Frozen MiniLM + small MLP | Same fixed deep features; trained nonlinear classification head | Sensible controlled neural-head comparison | More hyperparameters and overfitting risk; improvement is not guaranteed |
| Full SetFit / SetFitABSA | Contrastive encoder fine-tuning followed by classifier training; ABSA adds candidates and a second model | Good later option if the frozen encoder underperforms | More training, dependencies, and data preparation; explicit candidate coverage remains a bottleneck |
| Pretrained target-conditioned transformer | Polarity for a supplied aspect and its sentence, without local fine-tuning | Useful exploratory comparator or fallback if RAM permits | Does not independently solve target extraction; model training may overlap benchmarks |
| Small CNN or BiLSTM trained locally | A task-specific sequence classifier | Technically possible, but lower priority | More annotation, training decisions, and tuning; a whole-sentence classifier is still not ABSA |
| TF-IDF + logistic regression / SVM | Classical lexical ML | Cheap baseline to check whether deep features add value | Not DL; lexical features may miss paraphrases |

The comparison above is an engineering judgment for the user's constraints. It is not a published ranking or measured laptop benchmark. Neural sentence classifiers are established: Kim's CNN work uses word vectors and a simple convolutional classifier, while a later sensitivity study shows that architecture and regularization choices matter. These papers do not show that training a new CNN on our small hotel set will outperform pretrained representations. [Kim, 2014](https://aclanthology.org/D14-1181/), [Zhang and Wallace, 2017](https://aclanthology.org/I17-1026/).

## Why MiniLM is the first choice

The official MiniLM card describes a short-text encoder producing 384-dimensional embeddings, with default truncation beyond 256 word pieces. It declares Apache-2.0 and approximately 22.7 million parameters. Its `model.safetensors` file is 90.9 MB; the repository's much larger total includes alternative deployment formats, which do not all need downloading. The encoder is intended for semantic representation, not native three-way or five-way hotel sentiment classification. [Model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2), [official files](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/tree/main).

Keep the encoder frozen: compute vectors once in small batches, save them, and train heads using those vectors. The expected resource advantage over end-to-end transformer training follows from avoiding encoder gradient/optimizer state; it must still be measured on this laptop. Use short source-preserved clauses, not blind truncation of long reviews. Sentence Transformers supports CPU inference and optional ONNX/OpenVINO acceleration; dynamic int8 quantization is an optional later optimization, not a required first step. [Inference documentation](https://www.sbert.net/docs/sentence_transformer/usage/efficiency.html).

An illustrative target-conditioned input is `air conditioning : The air conditioning never managed to cool the room.` This template is a proposed feature representation, not an already observed prediction. For multiple targets, create separate target-context examples. Contrastive sentence encoders are established representation learners, and classification quality must be validated for the specific task rather than inferred from semantic-search results. [Sentence-BERT](https://aclanthology.org/D19-1410/), [Sentence Transformers training overview](https://www.sbert.net/docs/sentence_transformer/training_overview.html).

Do not call the frozen-vector prototype “SetFit training.” Full SetFit updates the encoder through contrastive examples and subsequently trains a classifier. Its default head is logistic regression; an optional differentiable head is linear, not automatically a deep MLP. A custom MLP on frozen vectors is our implementation choice. [SetFit conceptual guide](https://huggingface.co/docs/setfit/main/en/conceptual_guides/setfit), [head documentation](https://huggingface.co/docs/setfit/v1.1.3/en/how_to/classification_heads).

## SetFitABSA as the next option

SetFitABSA has three stages: spaCy noun-based candidates, a learned aspect filter, and a learned polarity classifier. It requires labeled `text`, `span`, `label`, and `ordinal` fields, and can use a smaller spaCy model such as `en_core_web_sm`. Its own example training logs are not laptop timing guarantees. The introduction recommends a GPU to keep its two-model training time low, which makes it less attractive than a frozen encoder for the immediate deadline. Its reported restaurant/laptop benchmark results cannot be copied as hotel-project results. [ABSA documentation](https://huggingface.co/docs/setfit/v1.1.3/en/how_to/absa), [authors' introduction](https://huggingface.co/blog/setfit-absa).

## Pretrained aspect sentiment models

`yangheng/deberta-v3-base-absa-v1.1` is an MIT-tagged, target-conditioned polarity candidate. Its safetensors weights alone occupy 738 MB, plus tokenizer/runtime and working memory. That is substantially larger than the MiniLM file. The direct classifier takes sentence and aspect; the separate end-to-end PyABSA example on the card should not be confused with this classifier discovering aspects by itself. [Model card](https://huggingface.co/yangheng/deberta-v3-base-absa-v1.1), [files](https://huggingface.co/yangheng/deberta-v3-base-absa-v1.1/tree/main).

The current card includes marketing claims and an internally surprising example: the positive food clause is illustrated with a Negative result. Treat this as a documentation-quality concern, not proof that the model always reverses labels. Validate tokenizer pairing, `id2label`, simple positive/negative/neutral cases, mixed-aspect cases, domain transfer, and checkpoint revision before adopting it. Do not promise its advertised accuracy on this project. With constrained free RAM, it is not the first implementation choice.

A community DistilBERT ABSA card also exists (`Steeve2ml/globatrend-absa-english-classifier`, MIT, about 67M parameters), trained on restaurant aspect pairs. Its author reports limitations on long multi-aspect reviews. This demonstrates availability of smaller target classifiers, not sufficient evidence to prefer that checkpoint for hotels. Its approximately 268 MB float32 weight footprint is an arithmetic estimate from parameters, not a verified download measurement. [Author model card](https://huggingface.co/Steeve2ml/globatrend-absa-english-classifier).

## Proposed fallback contract

1. Keep the original method result, its status and all diagnostics.
2. Route eligible unresolved contexts by diagnostic reason; excluded topics, malformed rows and component errors remain distinguishable.
3. Supply the target and bounded original context to the learned classifier.
4. Accept a recovered category-polarity record only when validation-selected relevance, probability and ambiguity criteria pass; otherwise abstain.
5. Deduplicate by review, source span and target/category so the fallback does not count an existing opinion twice.
6. Retain the learned record's source span, model revision, predicted probabilities, threshold and recovery reason.
7. Report lexical output and augmented output separately. “Neural-assisted” must not silently mean “Complete.”

A simple gate is `accept = in_scope AND target_valid AND p_max >= tau AND margin >= delta`. Thresholds must be chosen using development labels and then frozen. Softmax values can be poorly calibrated; a high number is not automatically an empirically accurate confidence estimate. A validation threshold, calibration analysis and a risk-versus-coverage curve are more defensible than an arbitrary 0.8 threshold. [Guo et al., 2017](https://proceedings.mlr.press/v70/guo17a.html), [SelectiveNet](https://proceedings.mlr.press/v97/geifman19a).

Three-way model probabilities are not sentiment strength. `p(Positive)=0.98` does not establish Strong Positive. Preserve the current five bands for the lexical scores; expose neural polarity and confidence separately until strength is independently labeled or an explicit surrogate score policy is declared. An expected polarity `p(Positive)-p(Negative)` can be reported as a model-derived index, but its intervals would remain descriptive and would not validate five-class intensity accuracy.

## Data and paper evidence

Training needs human-labeled examples. Booking ratings or existing VADER/SentiWordNet outputs are not aspect-polarity ground truth. Proposed starting work is a few hundred real target-context annotations, including neutral, difficult negatives, in-scope paraphrases and absent/out-of-scope cases; that number is a pilot budget, not a statistically guaranteed sufficient sample. Maintain class support tables and report uncertainty. Add labels until learning curves stabilize rather than promising a fixed recovery percentage.

Split by parent review before extracting snippets; keep duplicates and near-duplicates out of different splits. Preserve a final untouched real-hotel test set. Existing inspected SemEval examples can remain development evidence, but must not also become a new untouched test claim after they inform training or thresholds. For any off-the-shelf ABSA model, record declared fine-tuning corpora and check train/test overlap. Broadly pooled ABSA checkpoints may already have used SemEval-related material, so a fresh manually annotated hotel set is preferable for the main new claim.

Recommended comparisons are the current SentiWordNet pipeline, current VADER–TextBlob Hybrid, Hybrid plus fallback, and the learned classifier alone on the same eligible target set. Add a TF-IDF head baseline if feasible. Report end-to-end category-polarity precision/recall/F1 and accuracy, fallback acceptance and correctness, abstention, errors introduced, per-class metrics, and CPU latency/memory. Separate real annotated accuracy from unannotated Booking processing coverage. An increase in completion or number of predictions alone is not evidence of better sentiment understanding.

## Novelty position

Combining rules with learned sentiment is established, as are few-shot ABSA and neural rejection. SelectiveNet explicitly studies a reject option, SetFitABSA learns aspect and polarity decisions, and an earlier sentiment paper combines rule-based and supervised classifiers. Therefore “we added MiniLM/DL,” “we combined lexicons with ML,” or “we use a confidence threshold” is not defensible as a new general algorithm. [SelectiveNet](https://proceedings.mlr.press/v97/geifman19a), [SetFitABSA](https://huggingface.co/blog/setfit-absa), [Prabowo and Thelwall, 2009](https://doi.org/10.1016/j.joi.2009.01.003).

A narrower proposed contribution is **a diagnostic-routed, source-preserving, CPU-deployable fallback that recovers eligible omissions while retaining lexical evidence and abstentions**. Treat that as a designed application architecture. Stronger novelty or effectiveness claims require a controlled ablation of routing, thresholding and head choice, an untouched annotated test set, and measured trade-offs. This focused search does not establish that no prior system uses the same combination.

## Staged implementation decision

First audit why outputs are Partial. Then annotate and split an eligible pilot set, freeze current lexical systems, compare TF-IDF/logistic regression with frozen MiniLM/logistic regression, and optionally add a tiny MLP using identical data. Integrate only if recovery precision and end-to-end quality justify its cost. Consider full SetFitABSA or an aspect-conditioned transformer later if the remaining bottleneck is identified and enough RAM/data are available. This sequence is intended to minimize complexity and paid-compute requirements; no elapsed-time or accuracy guarantee is made.
