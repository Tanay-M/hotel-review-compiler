# Sentiment enhancements and IEEE paper plan

Prepared 14 October 2026 for the course report due 15 October 2026.

**Implemented 15 October:** The equal-weight hybrid, five-band labels, source verification and offline runner now exist. See [the current run guide](research-run-guide.md) and [implemented pseudocode](implemented-modules-and-pseudocode.md). Design details below describe the earlier proposal; executable behavior and measured output take precedence. Broad POS-based extraction remains deferred.

## Decision

Updated user decision: compare **two systems**, the existing six-category SentiWordNet compiler and a **VADER–TextBlob hybrid** that uses both tools. Keep each hybrid component's score as trace evidence rather than presenting three primary comparison systems. Add a configurable five-band strength interpretation. A document-level hybrid score must not change compiler completeness. TextBlob grammatical pattern assistance is a separately evaluated extension.

This document is an exploration and implementation plan. VADER and TextBlob were run in an isolated research directory; they are not integrated into the production compiler or WebUI. No runtime source, scoring policy, UI or project dependency declaration was changed in this exploration. Research dependencies are under ignored tmp/sentiment-research-deps. No GitHub push was performed.

## 1 What the three methods actually provide

| Method | Mechanism | Useful output | Main limitation for this project |
|---|---|---|---|
| Existing SentiWordNet compiler | Explicit aspects and grammar; selected synset P/N; domain rules; intensity and negation | Category, issue, opinion span, lexical and adjusted score, diagnostics | Controlled vocabulary and grammar restrict extraction |
| VADER | Valence lexicon plus rules for negation, degree, capitalization, punctuation and contrast | Compound score in [-1,1] and positive/neutral/negative text proportions | A general text score does not associate sentiment with our six aspects; equipment failures may lack sentiment-bearing words |
| TextBlob PatternAnalyzer | Pattern's lexical sentiment implementation | Polarity in [-1,1], subjectivity in [0,1], assessed token groups | General vocabulary, averaging and missing lexical evidence can obscure functional complaints or mixed aspects |
| TextBlob PatternParser or explicit POS tagger | Existing parser/tagger and chunking resources | Noun/adjective/verb tags and shallow phrase chunks | These are syntactic annotations, not automatic hotel issue labels or dependable target-opinion relations |

SentiWordNet is already a lexicon-based resource: VADER is an additional lexicon-based approach, not the first one in this project. SentiWordNet supplies numerical positive, negative and objective evidence for a word sense, rather than only a binary label. The application currently converts the adjusted number to Positive, Negative or Neutral.

Use TextBlob's PatternAnalyzer explicitly. Its NaiveBayesAnalyzer is a different trained movie-review classifier and is outside the proposed scope. POS tagging/noun phrase extraction can use pretrained resources; do not describe the entire TextBlob toolkit as purely hand-written deterministic rules. Specify the chosen component and version. Documentation pages differ about default taggers, so do not rely on an unspecified default.

Sources: [original VADER paper](https://ojs.aaai.org/index.php/ICWSM/article/view/14550), [official VADER implementation](https://github.com/cjhutto/vaderSentiment), [TextBlob API](https://textblob.readthedocs.io/en/stable/api_reference.html), [TextBlob analyzer options](https://textblob.readthedocs.io/en/stable/advanced_usage.html), [Pattern paper](https://www.jmlr.org/papers/v13/desmedt12a.html), [SentiWordNet 3.0 paper](https://aclanthology.org/L10-1531/).

## 2 Measured exploratory examples

These are actual outputs obtained locally, with vaderSentiment 3.3.2 and TextBlob 0.19.0. No gold annotation is available for this experiment, so disagreements are observations, not accuracy results.

| Original review | Compiler final review mean | Compiler interpretation | VADER compound | TextBlob polarity |
|---|---:|---|---:|---:|
| The room was clean. | +0.125000 | Complete, Positive | +0.4019 | +0.366667 |
| The room was extremely clean! | +0.187500 | Complete, Positive | +0.5081 | +0.458333 |
| The staff were rude. | -0.625000 | Complete, Negative | -0.4588 | -0.300000 |
| The room was not comfortable, but the staff were very helpful. | -0.093750 | Complete, Mixed | +0.5087 | 0.000000 |
| The air conditioning was not working. | -0.250000 | Complete, Negative | 0.0000 | 0.000000 |
| The room was cold. | -0.750000 | Complete, Negative | 0.0000 | -0.600000 |
| The location was excellent. | Unavailable | Unsupported, Unanalyzed | +0.5719 | +1.000000 |
| The room has two chairs. | Unavailable | Unsupported, Unanalyzed | 0.0000 | 0.000000 |

Interpretation:

- The mixed example remains two aspect opinions in the compiler. Its negative Room complaint and positive Staff praise must remain inspectable even when a mean is close to zero. The other methods have different general-text interpretations.
- The current compiler now supports the equipment failure example. A lexicon score of zero from the other methods does not prove the complaint is neutral.
- Location is outside the agreed six categories. A positive external score can still be displayed as whole-text evidence without declaring aspect extraction complete.
- Even similar scores refer to different scales. A compiler score of +0.125 is not evidence that VADER's +0.4019 is more accurate, and score magnitude is not confidence.

Files: [nine illustrative results](../output/research/sentiment-exploration-2026-10-14/illustrative_comparison.csv), [100 authored review comparisons](../output/research/sentiment-exploration-2026-10-14/authored_100_comparison.csv), [PatternParser examples](../output/research/sentiment-exploration-2026-10-14/pattern_parser_examples.txt), [versions and input provenance](../output/research/sentiment-exploration-2026-10-14/READ_ME.txt). The 100-review comparison is still development-sample exploration.

## 3 Five-band interpretation of the existing final score

Suggested initial policy, configurable and unvalidated: neutral boundary a=0.05; strong boundary b=0.50. Apply to each final adjusted opinion score s, after clipping and rounding. Retain the numeric score and the existing polarity field.

| Score interval | New strength label |
|---|---|
| -1 <= s <= -0.50 | Strong Negative |
| -0.50 < s < -0.05 | Weak Negative |
| -0.05 <= s <= +0.05 | Neutral |
| +0.05 < s < +0.50 | Weak Positive |
| +0.50 <= s <= +1 | Strong Positive |

These five labels are our interpretation policy, not official SentiWordNet classes or VADER's standard five classes. Validate boundaries against independent human intensity labels if five-class accuracy is reported. Otherwise present a descriptive distribution and identify the thresholds. VADER's standard three-way rule uses compound >=+0.05 for positive, <=-0.05 for negative, and values strictly between for neutral; this differs at the boundary from our compiler's inclusive neutral interval. Record these conventions rather than changing baselines silently.

Example from the submitted report: not comfortable scores -0.500000 and would be Strong Negative; very helpful scores +0.312500 and would be Weak Positive. Their mean is -0.093750. Preserve overall Mixed; show the numeric mean's band as Weak Negative with a label such as Net score band. Do not replace Mixed with Weak Negative. Partial results retain recognized-opinions-only scope; absent evidence remains Unavailable, never Neutral by default.

Do not apply the same strong threshold to all methods and claim equivalent psychological intensity. If external five-band views are added, label them separately and validate method-specific thresholds. TextBlob subjectivity and VADER proportions are not confidence probabilities.

## 4 Integration design

Preserve the current eight-block diagram. Add a scoring comparison side branch that receives original text after validation, plus source clause spans where supported. It contains VADER and TextBlob PatternAnalyzer. Extend final reporting with strength bands, comparison evidence and disagreement markers. The core syntax and semantic blocks still decide aspect coverage and diagnoses.

### First implementation part

1. Add a strength classifier in a small scoring-policy module, with configurable neutral/strong boundaries and exact boundary tests. Extend existing aspect records and review summary with descriptive strength/net-band fields.
2. Add a local sentiment_methods.py adapter that initializes VADER and PatternAnalyzer once. Each method returns method/version, score, optional subjectivity/proportions, scope and failure/evidence notes.
3. Score the complete original review for the secondary review-level outputs. Preserve capitalization, punctuation, modifiers and negations, since they affect these methods. Never feed compiler-normalized aliases into the independent raw-text baseline.
4. For aspect comparisons, use an explicitly scoped source clause/context. A clause with multiple aspects cannot safely supply distinct aspect sentiment just because a whole-clause score exists. Mark it shared context or omit the aspect comparison; use single-target contexts for the initial fair polarity experiment.
5. Do not multiply the VADER or TextBlob result by our intensity and negation weights again. Each analyzer already interprets modifiers according to its own rules.
6. Keep compiler status independent of external method availability. External errors must not erase primary results. Store method failures explicitly and do not replace failed/unavailable scores with zero.
7. Extend tabular CSV exports before UI work. Keep exactly one main row per review; retain a linked opinion table for all aspect results. Record dataset hashes, rules, package versions, analysis scope and threshold policy with each run.
8. Add a small UI comparison table and five-band chart after the backend/export changes pass verification. Keep current coverage, traces and per-review drill-down.

Suggested per-review columns: row ID; review; compiler status; supported aspects; compiler overall; compiler review score; net score band; score scope; VADER compound and native label; TextBlob polarity and subjectivity; method disagreement; diagnostics. Suggested opinion table additions: final score strength; original clause; external score/context scope if eligible. The original input CSV remains sr.no and review only.

Current change locations: hotel_compiler/models.py for record fields, sentiwordnet.py for adjusted-score interpretation, pipeline.py for orchestration, reporting.py and batch output writers for tables, web.py and web_assets/app.js for display, evaluation.py for labeled experiments. Prefer a separate adapter over embedding library-specific code throughout the parser.

### Second implementation part if justified by evaluation

Use TextBlob's explicitly chosen parser/tagger to suggest candidates such as noun phrase + copula + adjective, adjective + noun, and known equipment + failure verb. Pass candidates through our existing category, aspect and negation guards. Preserve source spans, record which rule accepted them and keep unaccepted language diagnosed. POS tags alone cannot reliably bind multiple opinions to multiple aspects.

Evaluate candidate extraction precision and recall independently. Do not automatically accept every noun/adjective or describe arbitrary English as supported. This extension is less suitable than scoring comparison for the next-day deadline.

### Defining the requested hybrid

The hybrid combines VADER and TextBlob only; it does not absorb the SentiWordNet baseline. A transparent starting candidate is H = w*VADER_compound + (1-w)*TextBlob_polarity, initially w=0.5, with both tools receiving the same original context. This is a proposed heuristic, not an implemented or validated result. Scores have different calibration despite the shared range, so develop the rule separately from the held-out test and publish its limitations. Define failures and missing lexical evidence explicitly rather than treating every zero as reliable neutrality or subjectivity as confidence. Preserve component scores, scope and disagreements. Optional component-only ablations can explain the hybrid while the paper's main comparison remains two systems. No LLM is required.

## 5 Two proposed contribution algorithms

These are design pseudocode, not claims that the extensions are already implemented.

### Algorithm 1 Evidence-preserving strength classification

```text
Input: compiled aspect records, compiler status, neutral boundary a, strong boundary b
Require: 0 <= a < b <= 1
For each aspect record:
    preserve original lexical evidence and final adjusted score s
    if s <= -b: strength = Strong Negative
    else if s < -a: strength = Weak Negative
    else if s <= a: strength = Neutral
    else if s < b: strength = Weak Positive
    else: strength = Strong Positive
If records are empty:
    review score and net band = Unavailable
Else:
    review score = arithmetic mean of final opinion scores
    net band = apply the same interval policy to that mean
    keep Mixed if positive and negative aspect opinions coexist
    keep the existing complete/partial coverage scope
Return aspect results, strength, review mean, net band, overall and scope
```

### Algorithm 2 Scoped multi-lexicon comparison and reporting

```text
Input: validated original review text, compiled aspect results and diagnostics
Run VADER once on the original full text
Run TextBlob PatternAnalyzer once on the original full text
Keep method versions, scales, analyzer outputs and failures separately
For each eligible source context with exactly one evaluative aspect target:
    score the unchanged context with each baseline
    attach target ID and context scope for the comparison task
    avoid applying compiler negation/intensity a second time
Determine polarity disagreements only between comparable scopes
Preserve compiler status and every unsupported-language diagnostic
Emit one review-table row, linked aspect evidence and run metadata
Aggregate method-specific results using explicitly documented denominators
Return tables suitable for inspection and reproducible experiments
```

## 6 Paper structure aligned with the faculty outline

Possible title: An Explainable Compiler-Based Framework for Aspect-Level Hotel Review Sentiment Analysis. If the comparison extension is completed, the title may mention Multi-Lexicon Evaluation. Do not claim a novel VADER/TextBlob algorithm; these are established methods. The project's contribution is the implemented interpreter, explicit scope/evidence, domain adaptation and experimentally assessed extensions.

| Paper section | Planned content |
|---|---|
| Abstract | Problem, method, dataset, measured findings and limitation; add final numbers only after evaluation |
| 1 Introduction | Why overall hotel scores obscure aspect complaints; project motivation and contributions |
| 2.1 Lexicon-based sentiment and valence rules | SentiWordNet, VADER, contextual polarity and Pattern |
| 2.2 Aspect extraction and sentiment classification | Rule extraction and ABSA literature; neural work discussed only as background |
| 2.3 Evaluation, intensity and practical limitations | Annotation, datasets, intensity, abstention/coverage and reproducibility |
| 3 Proposed System | Editable architecture, equations, explicit module inputs and outputs |
| 3.1 Module 1 Input preparation and lexical analysis | Architecture blocks 1–2; CSV and token evidence |
| 3.2 Module 2 Syntax and semantic aspect interpretation | Blocks 3–4; supported grammar, issue rules, diagnostics |
| 3.3 Module 3 Sentiment evidence and strength | Blocks 5–7 plus completed comparison extension; Algorithm 1 |
| 3.4 Module 4 Result synthesis and experimental reporting | Block 8, review mean, batch/dashboard/export; Algorithm 2 |
| 4.1 Dataset description | Authored versus real reviews, unique counts, length, provenance, labels and splits |
| 4.2–4.5 Module results | Tokens/AST, extracted targets, score evidence/comparisons, batch summaries; explain each table's inference |
| 5 Performance and metrics | Matched-task baselines, gold-label metrics, coverage, runtime, ablations and errors |
| 6 Conclusion | Supported findings and limitations; TextBlob extraction assistance stays future scope if unfinished |
| References | Synthesized discussion backed by approximately 30 relevant verified papers, numbered IEEE references |

Four manuscript modules group the eight implementation blocks; the architecture and software do not need a disruptive rewrite. Detailed eight-block explanation can remain in the supporting report.

IEEE and APA are separate reference styles. For IEEE conference format use the official Word conference template and numbered IEEE references, unless faculty explicitly requests a custom APA variant. Preserve the faculty's section content while applying template heading conventions. Sources: [IEEE authoring templates](https://conferences.ieeeauthorcenter.ieee.org/write-your-paper/authoring-tools-and-templates/), [IEEE paper structure](https://conferences.ieeeauthorcenter.ieee.org/write-your-paper/structure-your-paper/), [IEEE reference guide](https://journals.ieeeauthorcenter.ieee.org/wp-content/uploads/sites/7/IEEE_Reference_Guide.pdf).

The [30-paper candidate reading list](sentiment-literature-reading-list.md) is a bibliography preparation aid, not an already written 30-paper survey. Verify every final citation's author/title/year/venue/pages/DOI, use published versions where available, and synthesize methods, limitations and relevance instead of merely listing titles. Cite the actual uploaded base paper once its authoritative metadata is extracted; do not invent its citation from the document filename.

## 7 Minimum defensible experimental design

### Datasets and annotation

Keep the authored 100-review sample as development/demo evidence, and the existing authored contracts as implementation validation. Obtain an independent representative set of naturally occurring English hotel reviews with documented provenance and permission. A feasible target is 100–200 distinct reviews for the course report, but sample size alone does not ensure validity. Keep duplicates across splits out. Do not tune vocabulary or thresholds on the final evaluation set.

Annotate gold category, aspect/opinion context and positive/negative/neutral sentiment. Document the annotation guide, who labeled, disagreement resolution and uncertain cases. Two independent annotators with an agreement measure are preferable; if only one is available, disclose it. Review-level labels and aspect-level labels are separate. Star ratings are document-level proxies and are not automatically aspect ground truth. To claim five-class accuracy, annotate strength independently; labels generated from our own thresholds are not gold truth.

Existing authored gold cases can supply clearly labeled contract metrics today, but cannot substitute for independent real-review accuracy. Gold-label files remain separate from the two-column user input CSV.

### Comparable tasks and baselines

1. End-to-end aspect extraction: evaluate our compiler against gold aspect/opinion labels, reporting tuple precision, recall and F1. VADER/TextBlob alone cannot extract our six categories, so do not present their lack of extraction as an unfair zero score comparison.
2. Matched aspect-polarity task: supply the same independently selected single-target context to raw SentiWordNet, VADER, TextBlob and the domain-adjusted compiler. State that gold context is supplied and that this evaluates scoring, not full extraction. Explain how raw SentiWordNet selects senses and aggregates terms. Multi-target cases need a separate documented protocol.
3. End-to-end system evaluation: score the compiler's own extracted contexts, include omitted gold opinions in recall, and report supported/partial/unsupported counts. Conditional polarity accuracy on extracted targets is a secondary metric, not whole-system accuracy.
4. Whole-review sentiment is an optional separate comparison. The existing compiler has Mixed while common baseline labels have three classes. Define a shared labeling/task protocol before claiming comparable accuracy; do not silently map Mixed or Unanalyzed to Neutral.

Recommended metrics: polarity accuracy and macro-F1 on the matched classification task; per-class precision/recall; confusion matrices; extraction precision/recall/F1; coverage/abstention rates and denominators. Report runtime after warm-up over repeated runs, with hardware/software, batch sizes 100 and 500, and timing scope. Use confidence intervals or disclose a small test set's uncertainty.

### Tables and figures

- Dataset composition table: source, domain/language, unique reviews, split and label counts.
- Methods table: input scope, lexical resource, adjustments and whether aspects are extracted.
- Matched-task results table: sample count, accuracy, macro-F1, missing predictions and scope.
- Main comparison table: SentiWordNet compiler versus the implemented VADER–TextBlob hybrid. Optional ablations: compiler domain/modifier rules and the hybrid's individual components.
- Coverage table and bar plot: complete/partial/unsupported, clearly separate from accuracy.
- Strength distribution chart: counts under published thresholds, with Mixed and missing evidence shown separately.
- Confusion matrix and method disagreement table with representative explanations.
- Repeated runtime plot with spread, rather than one dashboard timing value.

Use CSV tables and standalone, legible plotting-tool figures for the manuscript rather than dashboard screenshots. Keep the full one-row-per-review table as supporting evidence; put a small representative subset in the paper. No invented result percentages, no unmeasured claim that a combined method is best, and no confidence interpretation of sentiment magnitudes.

## 8 Order of work for the next-day deadline

1. Freeze the evaluation task and labeling guide; start independent annotation before tuning.
2. Implement strength labels and the two local sentiment adapters, then update CSV exports and targeted tests.
3. Freeze versions/thresholds and run comparable baseline, extraction and runtime experiments.
4. Produce result tables, graphs and error analysis. If independent labels cannot be obtained, explicitly frame the manuscript as implementation and descriptive evaluation; do not fill an accuracy table with coverage.
5. Write the manuscript in the faculty's order and IEEE Word template, including two completed contribution algorithms and an updated editable diagram. Clearly distinguish implemented features from future work.
6. Add UI comparison polish after backend and evidence are ready. Broader POS-based extraction can remain future scope; the requested VADER–TextBlob hybrid is part of the main implementation plan.

This plan prioritizes usable evidence for the paper over adding several unevaluated features immediately before the deadline.
