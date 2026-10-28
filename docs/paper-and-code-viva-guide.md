# Complete Paper Explanation and Code Viva Guide

This guide explains the current eight-page paper and maps its claims to implementation files. Paths in the code tables are relative to the project root. Function names are better navigation anchors than line numbers, which can change.

## 1. Opening explanation and title rationale

**Title:** Auditable Aspect Sentiment Analysis of Hotel Reviews with Selective Deep Learning Reanalysis.

- **Aspect sentiment:** We retain what a guest likes/dislikes about Room, Staff, Service, Food, Cleanliness and Facilities rather than only assigning a whole-review sign.
- **Auditable:** Lexical outputs retain source text, offsets, dictionaries/senses, adjustments and diagnostics. Neural outputs retain sentence evidence, probabilities, thresholds and model identity; they do not explain a neural decision as completely as explicit lexical rules do.
- **Selective:** Only Partial/Unsupported Hybrid reviews enter the DL model. Complete Hybrid results stay unchanged; invalid input/component failures remain failures.
- **Reanalysis:** The model reads the original sentences independently. Its selected result replaces the routed Hybrid result, including abstention; it does not simply append extra opinions.

**One-minute viva answer:** “Our project combines compiler-style aspect sentiment analysis, an independent VADER/TextBlob Hybrid, and selective MiniLM reanalysis. The first two preserve lexical evidence; the fifth stage attempts to interpret unresolved Hybrid reviews. We compare category and sentiment predictions with human annotations, measuring both recoveries and regressions. The contribution is a traceable integration with selective neural recovery, not a new transformer architecture.”

## 2. Abstract

The abstract states the problem, three components, key measured results and limits. It describes two separate experiments: SentiWordNet versus Hybrid on mapped SemEval, and Hybrid versus selective DL on mapped Trip-MA. Booking is a real-data coverage demonstration without aspect gold, not an accuracy benchmark.

- SemEval single-polarity classification: 72/148 correct for SentiWordNet (48.65%), 85/148 for Hybrid (57.43%).
- SemEval pair-F1: 0.5912 versus 0.6450.
- Trip-MA all 1,474 segments: pair micro-F1 0.4184 to 0.4993.
- Trip-MA routed 1,113 segments: 0.3261 to 0.4813; 361 other segment outputs remain unchanged.
- Booking demo: 44 of 500 reviews retain Complete Hybrid; 456 route to DL, 383 receive accepted categories and 73 abstain. Accepted does not mean confirmed correct.

**Code:** `hotel_compiler/research_runner.py::evaluate_semeval`; `hotel_compiler/routed_cli.py::evaluate` and `compare_csv`. Actual CSV evidence is under the experiment folders listed below.

## 3. Introduction

The problem is that overall review sentiment can conceal conflicting aspects. “The room was spacious but breakfast was cold” should preserve Room praise and Food criticism. Lexical systems can miss language beyond supported vocabulary/grammar; neural recovery may interpret such language but can also introduce errors.

Source spans are character offsets into the submitted review. Dictionaries recognize phrases, grammars attach opinions to targets, and aspect mappings assign hotel categories. A Room category can have a Cleanliness issue. Human datasets can classify room hygiene under a different category, requiring a declared crosswalk.

Measured recovery is a newly correct category-polarity pair after replacement; regression is a previously correct pair lost. We measured 97 newly correct pairs, 44 lost, net +53. There were also 114 new false pairs and 198 false pairs removed. These are pair counts, not numbers of fully corrected reviews.

**Code:** `models.py` for source-spanned records; `semantics.py` for baseline category/issue rules; `hybrid_nlp.py` for independent mapping/attachment; `routed_cli.py::comparison_details` for change counts.

## 4. Literature Survey

### A. Lexical Resources and Contextual Valence

Earlier work establishes lexical polarity, sense-specific SentiWordNet scores, negation, intensifiers and VADER valence. Pattern provides grammatical/sentiment resources used through TextBlob. The lesson is that a word's dictionary score alone cannot resolve all context. Our five lexical strength bands are descriptive boundaries, not independently validated strength classes.

### B. Aspect Extraction and Targeted Sentiment

Earlier work extracts opinion targets using linguistic rules or learned models. SemEval formalizes annotation tasks. Target-conditioned models motivate pairing text with a category query. Our Absent state is needed because asking about Food does not establish that the sentence mentions Food.

### C. Representation and Evaluation

LSTM, CNN and transformer literature motivates contextual representations. We use pretrained MiniLM and fine-tune it; we do not implement every architecture in the survey or train distillation. Trip-MA supplies human hotel annotations. Different annotation tasks demand different metrics and mappings.

**Viva answer:** “The survey explains our choices and positions the work. Lexical tools motivate traceable scoring, ABSA work motivates target-category analysis, and compact transformers motivate local neural reanalysis. We do not claim to have implemented all cited methods.”

**Paper source:** `docs/conference_manuscript.md`; references assembled by `scripts/build_conference_paper.py::bibliography`, with saved metadata under `output/paper/sources/`.

## 5. Proposed Systems and Algorithms

See `docs/architecture-viva-explanation.md` and Q8 of the continuing notebook for every diagram block. The following connects the five algorithms to executable logic.

### A. Preprocessing and validation / Algorithm 1

Decode CSV, retain row ID/text, validate structure and lengths, flag duplicates, and preserve problems. Return retained records rather than quietly dropping problematic rows. Original text enables later evidence reconstruction.

**Open:** `csv_input.py::read_review_csv` and `parse_review_csv`; `front_end.py::compile_frontend` for single-review validation. Offline cleaning is separate: `scripts/prepare_clean_booking_demo.py::cleaned_text` and `prepare`.

**Explain the logic:** “The CSV adapter interprets rows; it does not calculate sentiment. It checks limits, retains identity and passes text to analysis. Offline cleaning removes empty markers/duplicates but does not rewrite opinions or select reviews because they score well.”

### B. Lexical and grammatical analysis / Algorithm 2

Baseline: tokenize with longest phrase matching, parse supported target/opinion structures, recover bounded useful fragments, then resolve semantic targets. Hybrid: use Pattern POS/chunks, independent aspect matching, clause segmentation and project attachment rules. These are separate front ends.

**Open baseline:** `lexer.py::tokenize`; `parser.py::ReviewParser` and `parse`; `expanded_parser.py::recover` and `parse_expanded`.

**Open Hybrid:** `hybrid_nlp.py::analyze_language`, `_mentions`, `_segments`, `_opinion_indexes`.

**Explain the logic:** “We identify targets and candidate opinions, then use their grammatical relationship to attach the opinion. Preceding adjectives attach forward; following predicates attach backward under supported rules. Ambiguity remains visible.”

Baseline resources: `resources/domain_expanded.json` (772 aspect phrases, 21,181 opinion entries, 752 aliases); `vocabulary.py` loads/checks them. Hybrid resources: `resources/hybrid_domain.json` and `hybrid_vocabulary.json` (671 aspect phrases and 497 alias forms). Inventory size is not proof of correctness.

### C. Semantic attachment and sentiment scoring / Algorithm 3

Baseline maps category/issue, checks compatibility and chooses configured senses. Read positive P and negative N from the SentiWordNet resource. Lexical score L=P-N; objective score O=1-P-N. Explicit hotel preferences take precedence; expanded lemmas otherwise use first lemma-ranked senses.

**Equation 1:** `s = clip(D*m*n, -1, 1)`. D is the domain-adjusted score, defaulting to L; m is the degree multiplier; n is -1 for scoped negation or +1 otherwise. Clip bounds the result. This is a deterministic rule, not a probability.

**Open:** `semantics.py::analyze_semantics`, `sentiwordnet.py::evaluate`, and `resources/sentiwordnet_expanded.tsv`.

Hybrid scores extracted contexts through both libraries. Original casing/punctuation and native results remain inspectable. Guarded aliases affect only explicit scoring copies. Context rules are project additions.

**Equation 2:** `Lh = (w*eV*V + (1-w)*eT*T)/(w*eV + (1-w)*eT)`, with w=0.5. eV/eT indicate usable lexical evidence. Both tools supported: average; one supported: keep that score; neither: Unavailable. A component exception remains an error.

**Open:** `hybrid.py::HybridEngine._score_native`, `score_text`, `score_aspect`; `hybrid_vocabulary.py::normalize_opinions`; `hybrid_nlp.py::domain_adjustment`.

### D. Adjustment and final records / Algorithm 4

Apply documented adjustments once, retain opinion records and calculate allowed summaries. Baseline negation belongs to parsed scope; do not apply its extra flip again to Hybrid scores. The five lexical bands are Strong Negative <=-0.5, Weak Negative between -0.5 and -0.05, Neutral inclusive -0.05 to +0.05, Weak Positive between +0.05 and +0.5, Strong Positive >=+0.5.

**Equation 3:** `Ri = sum(Hij)/mi`, mean final opinion score for review i with mi retained scores. Missing evidence remains unavailable. Baseline Partial means cover recognized opinions only; Hybrid exposes the aspect mean only if every extracted context is scored. Dashboard category means average within review and then across reviews, giving each contributing review equal weight.

Positive and Negative evidence together retain Mixed, even if the mean cancels. Complete means no detected diagnostics and required scores available; it is not verified accuracy. Partial retains useful scores with unresolved evidence; Unsupported has no scored aspect.

**Open:** `pipeline.py::analyze_review` for baseline status/overall label; `models.py::AnalysisResult.review_score`; `sentiment_policy.py::SentimentPolicy`; `hybrid.py::analyze_hybrid_review` and `HybridAnalysis` for Hybrid status/mean. `research_runner.py` and `routed_cli.py` implement evaluation/export aspects summarized by Algorithm 4; the pseudocode is a high-level description, not a single literal function.

### E. Independent DL reanalysis / Algorithm 5

Gate on Hybrid Partial/Unsupported. Split the original review into sentences. Pair each sentence with eight category descriptions, run shared MiniLM and a shared four-state classification head, then apply category thresholds. Emit only accepted in-scope categories. Keep other Hybrid reviews unchanged and retain evidence separately.

**Equation 4:** `pc = softmax(f_theta(u, qc))`. u is a sentence, qc a category query, theta learned parameters. The encoder/head produce four scores; softmax turns them into probabilities summing to one. The states are Absent, Negative, Neutral/Mixed and Positive.

**Equation 5:** Weighted cross-entropy penalizes low probability assigned to the known training class. Sum `-w_y*log(p_y)` over a minibatch and divide by the summed target weights. State weights are proportional to square-root inverse frequency, normalized to mean one, because Absent dominates. This loss trains parameters; F1 evaluates outputs and selects settings, not the gradient loss.

**Equation 6:** `d = (p_positive-p_negative)/(p_positive+p_negative)` for accepted positive/negative predictions. It is relative direction belief, not calibrated intensity. Neutral/Mixed makes aggregate indices unavailable under current policy. Category indices average sentences, and review indices average categories when available.

**Open routing:** `routed_model.py::reanalyze_review` and `decode_heads`.

**Open current DL implementation:** `dl_pair.py::LocalDLModel.predict_many` for inference and `train` for encoder/head fine-tuning. Queries are defined in `QUERIES`. `web_routed.py::route_demo` connects this flow to the demo.

**Important:** `routed_training.py::train` is an earlier trainer, not the current MiniLM fine-tuning implementation used for the reported DL model. Its `metrics` and `choose_thresholds` helpers are reused by the current trainer. Open `dl_pair.py::train` when asked how the paper's model was trained.

## 6. Results and Implementation

### A. Dataset description

SemEval: 30 reviews/266 sentences/339 opinions. Scope mapping excludes 141 annotations; 198 mapped annotations yield 162 unique pairs and 148 unambiguous polarity cases. These are a declared adaptation, not official target-span benchmark scores.

Trip-MA: prepared train/validation/test have 2,040/602/1,474 segments. Two long training segments are excluded, leaving 2,038 usable. Splits are disjoint by hotel/review/text after preparation. Eight queries give 16,304 pairs: 14,318 Absent, 1,244 Positive, 466 Negative and 276 Neutral/Mixed. Staff is pooled into Service; Building/Business approximately maps to Facilities. Those differences limit comparison.

Booking Italy: 4,367 raw rows minus 1,266 empty bodies and 12 duplicates = 3,089. The 500 demo is nested. The random 200-review sample comes from a separate large real hotel-review source. Booking has no human aspect gold here.

**Open:** `research_data.py::load_semeval`, `research_runner.py` category mapping imports, `routed_data.py::prepare` and `mapped_labels`, `scripts/prepare_clean_booking_demo.py::prepare`. Show provenance manifests when asked about authenticity or split construction.

### B-E. Processing observations

Retained rows preserve source identity and diagnostics. The full Italy corpus runs in four upload-sized parts: 1,000/1,000/1,000/89. More opinion candidates do not prove better predictions: the methods define candidates differently.

The benchmark sentence “The rooms were quiet” uses a baseline hotel preference and Hybrid room_quiet rule (+0.45). The equipment-failure example demonstrates the configured -0.70 context rule. Authored examples explain behavior; they are not extra human-labelled benchmark cases.

Any-aspect coverage on all Italy reviews is 81.42% baseline and 87.41% Hybrid, but Complete status is only 1.65% and 7.96%. Do not present coverage as classification accuracy.

**Open:** `research_runner.py::compare_csv` for running both methods and saving coverage; `exports.py` for per-row and per-aspect export; `models.py` and `hybrid.py` for trace payloads.

### F. DL training and execution

The reported run fine-tunes encoder and head for three epochs. Validation pair-F1 is 0.4052, 0.4764 and 0.5037, selecting epoch 3. AdamW uses encoder learning rate 0.00002 and head rate 0.0002; effective batch size 16 comes from batch 8 with two-step gradient accumulation. Other settings: weight decay .01, 10% warmup, clipping 1.0, seed 172026. Training/validation took 248 seconds on RTX 2050; reported 510.1 MiB is peak allocated tensor memory, not total GPU/process usage.

An epoch is one pass over training examples. A learning rate controls update size. Weight decay discourages overly large weights. Warmup gradually raises the learning rate; accumulation combines gradients before an update; clipping limits excessively large gradient updates. Validation selects settings; test data estimates performance afterward. All reported supervision was human source annotation, not AI labels.

**Open:** `dl_pair.py::train`; measured settings/epoch evidence under `output/neural/2026-10-23-dl-pair-human-v1/`.

## 7. Performance and Metrics

### A. What each metric measures

- **Polarity accuracy:** correct/148 eligible cases; Missing/Mixed count as errors. Strong/weak labels collapse to sign.
- **Conditional accuracy:** correct/scored cases; it uses a selected subset, so it should not replace all-case accuracy.
- **Precision:** TP/predicted pairs. **Recall:** TP/gold pairs. **Pair-F1:** `2*TP/(predicted+gold)`.
- **Macro-F1:** average Positive, Negative and Neutral class F1 equally; rare Neutral gets equal class weight.
- **Micro-F1:** pool pair counts before calculating F1; not the average of review F1 values.
- **Exact segment match:** entire predicted pair set equals gold, including empty sets. Background-only segments can make this look high.
- **Coverage:** output availability, not correctness.
- **Bootstrap interval:** resample whole parent reviews, recompute scores and inspect variability. This respects within-review dependence better than resampling each sentence separately; it does not eliminate development bias.

### B. SentiWordNet versus Hybrid on SemEval

| Measure | SentiWordNet | Hybrid | Interpretation |
|---|---:|---:|---|
| Correct / cases | 72/148 | 85/148 | Hybrid recovers 13 additional correct eligible labels. |
| Accuracy | 48.65% | 57.43% | +8.78 percentage points. |
| Pair precision | .7232 | .6828 | Baseline is more selective/precise on emitted pairs. |
| Pair recall | .5000 | .6111 | Hybrid recovers more gold pairs. |
| Pair-F1 | .5912 | .6450 | Hybrid has better precision/recall balance. |
| Macro-F1 | .4037 | .3999 | Baseline is slightly higher; Hybrid is not best on every metric. |

There are 103 Positive, 41 Negative and only 4 Neutral cases. Baseline recovers one Neutral case; Hybrid none. Equal weighting of Neutral helps explain the macro-F1 reversal. Four cases are insufficient for a stable Neutral-performance claim.

**Open:** `research_runner.py::evaluate_semeval`; saved `output/experiments/2026-10-21/expanded-sentiwordnet-release/semeval-development/metrics.csv` and `predictions.csv`.

### C. Selective DL evaluation on Trip-MA

| Scope | Hybrid | Selected Hybrid/DL | Inference |
|---|---:|---:|---|
| All 1,474 segments pair-F1 | .4184 | .4993 | +8.09 F1 points overall. |
| Routed 1,113 segments pair-F1 | .3261 | .4813 | +15.52 F1 points where DL intervenes. |

The other 361 outputs stay unchanged. Correct pair matches rise from 314 to 367 overall. Four mapped categories improve; Facilities falls from .1854 to .1389. A paired review bootstrap gives a descriptive F1-gain interval of +4.94 to +11.67 points. It is evidence for improvement in this setting, not guaranteed improvement for every review.

**Open:** `routed_cli.py::evaluate` and `comparison_details`; `routed_training.py::metrics`; `output/neural/2026-10-23-dl-pair-evaluation/metrics.csv`, `predictions.csv`, `change_summary.json`, `per_category_comparison.csv`.

### D. Validity and limitations

Data informed development and benchmarks were previously inspected. Results are exploratory, not untouched independent-holdout claims. There is one seed/run and no controlled component ablation. Approximate category mappings, pooled Staff, merged Neutral/Mixed and unvalidated strength bands limit interpretation. First-ranked senses, shallow grammar, implicit language, pronouns and sarcasm remain difficulties. DL can lose good Partial predictions; a wrong Complete Hybrid prediction bypasses DL. Better overall F1 does not prove each component caused the gain or that the system generalizes universally.

An ablation would remove one component, such as an alias catalog or context rule, and rerun the same evaluation to isolate its contribution. A fresh human-labelled held-out hotel cohort and repeated training seeds would strengthen evidence. No such unperformed result should be claimed.

## 8. Graphs, tables and conclusion

Fig. 1 is a programmatically drawn explanatory architecture. Fig. 2 reads saved SemEval metrics; Fig. 3 reads saved Trip-MA metrics. They are Python-produced figures, not AI-invented result illustrations. Metric code produces measurements; plotting code only visualizes them.

**Open:** `scripts/paper_figures.py::charts`, `scripts/build_dl_paper_assets.py::build`, and `scripts/verify_paper_graph_provenance.py::verify`. The last checks saved predictions/counts and plotted values. Approved architecture comes from `scripts/build_approved_paper_architecture.py`, using `build_architecture_approval.py`. `scripts/build_conference_paper.py` assembles Word prose, algorithms, equations, figures and saved tables; it does not train the model.

**Conclusion to faculty:** “Hybrid improves category-polarity recovery over our SentiWordNet pipeline on the declared SemEval task. Selective MiniLM further improves unresolved Hybrid results on a separate Trip-MA task, with measurable regressions. We preserve source evidence, method identity and abstentions. Our contribution is the implemented integration and measured tradeoff, with explicit limits rather than a claim of a new state-of-the-art model.”

## 9. Code files to open during the viva

| Faculty asks | Open | Logic to explain |
|---|---|---|
| Overall baseline execution | `hotel_compiler/pipeline.py::analyze_review` | Compile front end, score semantic records, assign status/overall, return traceable result. |
| Stage ordering and input checks | `hotel_compiler/front_end.py::compile_frontend` | Validate text, tokenize, parse, perform semantics, combine diagnostics. |
| CSV ingestion | `hotel_compiler/csv_input.py::parse_review_csv` | Decode/map/validate rows, preserve duplicates and identities. |
| Lexical scanning and phrases | `hotel_compiler/lexer.py::tokenize` | Scan source spans, longest-match entries and classify tokens. |
| Baseline syntax rules | `hotel_compiler/parser.py::ReviewParser` | Supported clause productions and recovery boundaries. |
| Expanded grammar | `hotel_compiler/expanded_parser.py::recover` | Bounded extra structures, shared subjects and explicit absence. |
| Category and issue decisions | `hotel_compiler/semantics.py::analyze_semantics` | Resolve targets, enforce guards, map category/issue and retain spans. |
| SentiWordNet computation | `hotel_compiler/sentiwordnet.py::evaluate` | P/N, sense preference, domain/degree/negation and clipping. |
| Baseline recognized words | `hotel_compiler/resources/domain_expanded.json` | Configured aspects, opinions, aliases, senses and rules. |
| Native P/N values | `hotel_compiler/resources/sentiwordnet_expanded.tsv` | Synset sentiment records; resource data, not learned parameters. |
| Select current baseline vocabulary | `hotel_compiler/compiler_profiles.py` and `vocabulary.py` | Profile selection and validated resource loading; paper treats expanded implementation as SentiWordNet. |
| Label thresholds | `hotel_compiler/sentiment_policy.py::SentimentPolicy` | Three polarity signs and five descriptive strength bands. |
| Final records and mean | `hotel_compiler/models.py::AnalysisResult` | Mean of retained scores, scope label and trace serialization. |
| Independent Hybrid grammar | `hotel_compiler/hybrid_nlp.py::analyze_language` | POS/chunks, aspect mentions, segmentation and directional attachment. |
| Hybrid scoring and fusion | `hotel_compiler/hybrid.py::HybridEngine` | Call libraries, check evidence, fuse and apply domain rules. |
| Hybrid processing status | `hotel_compiler/hybrid.py::analyze_hybrid_review` | Count scored contexts and combine diagnostics; keep component errors explicit. |
| Hybrid vocabulary | `hotel_compiler/resources/hybrid_domain.json`, `hybrid_vocabulary.json` | Separate categories, phrases, hotel rules and alias forms. |
| Alias handling | `hotel_compiler/hybrid_vocabulary.py::normalize_opinions` | Category-guarded scoring-copy changes with original evidence retained. |
| DL routing and output | `hotel_compiler/routed_model.py::reanalyze_review` | Status gate, original sentences, independent neural outputs and abstention. |
| Neural acceptance/direction | `hotel_compiler/routed_model.py::decode_heads` | Argmax state, category threshold and model direction index. |
| Actual DL training | `hotel_compiler/dl_pair.py::train` | Pair encoding, weighted loss, optimizer, backpropagation, validation and saved checkpoint. |
| DL inference | `hotel_compiler/dl_pair.py::LocalDLModel.predict_many` | Load saved model, tokenize category pairs, batch inference and softmax. |
| Training labels and splits | `hotel_compiler/routed_data.py::prepare` | Human annotation mapping, hotel-disjoint splits and leakage guards. |
| Validation thresholds/metrics | `hotel_compiler/routed_training.py::choose_thresholds` and `metrics` | Validation threshold search and exact pair-count formulas; avoid its older train function for current DL explanation. |
| SemEval interpretation | `hotel_compiler/research_data.py::load_semeval` and `research_runner.py::evaluate_semeval` | Read annotations, map scope, compare predicted/gold pairs and eligible labels. |
| Trip-MA comparison/recovery | `hotel_compiler/routed_cli.py::evaluate`, `comparison_details` | Same-segment Hybrid/DL comparison, metrics and new/lost pairs. |
| Real Booking cleaning | `scripts/prepare_clean_booking_demo.py::prepare` | Preserve wording, remove unusable bodies/exact duplicates, sample deterministically. |
| Website routing | `hotel_compiler/web.py`, `web_analysis.py`, `web_routed.py` | HTTP handling, method adapter, model loading and selective route invocation. |
| Dashboard | `hotel_compiler/web_assets/dashboard.js`, `hybrid.js`, `routed.js` | Display method outputs/traces and summaries; scientific training is not done in the browser. |
| CSV export | `hotel_compiler/exports.py::export_batch` | One result per submitted row, separate aspect exports and retained diagnostics. |
| Graph evidence | `scripts/verify_paper_graph_provenance.py::verify` | Recheck predictions/counts, metric CSVs and SVG bar labels. |
| Paper generation | `scripts/build_conference_paper.py::build` | Typeset prose, pseudocode, native equations and saved results. |

## 10. How to explain a code function

Use four statements: (1) input, (2) main decision/loop, (3) output, (4) failure/limitation. Example for `reanalyze_review`: “It takes original text and Hybrid status. It returns without neural processing unless the status is Partial/Unsupported. Otherwise it splits sentences, predicts category pairs and applies thresholds. It returns accepted category evidence or abstention and preserves model/length failures.”

**Recommended eight-file opening order:** pipeline.py -> lexer.py -> parser.py -> semantics.py -> sentiwordnet.py -> hybrid_nlp.py -> hybrid.py -> routed_model.py. Open dl_pair.py next if asked about training; open the evaluation programs and result CSVs when asked to justify performance. Do not try to explain the entire repository line by line.
