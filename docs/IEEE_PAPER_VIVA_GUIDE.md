# Research Paper Explanation and Viva Preparation

For Tanay Mohta and Aditya Rawat — Team 17

Based on the current paper, **An Auditable Grammar Assisted Hybrid for Aspect Sentiment Analysis of Hotel Reviews**, and the final two-system experiments under `output/experiments/2026-10-21/expanded-sentiwordnet-release/`.

This guide teaches the paper from scratch, follows its sections, explains its equations and results, and supplies answers to likely cross-questions. Teaching examples are identified separately from real dataset observations. The manuscript is not modified by this guide.

## 1. Your opening explanation

### A 30-second introduction

“Our project analyzes hotel reviews aspect by aspect. A review can praise the room and criticize the staff, so one overall sentiment label can hide useful information. We implemented two independent local approaches: a deterministic SentiWordNet compiler and a grammar-assisted VADER–TextBlob hybrid. Both expose their intermediate evidence and failures. Our study compares prediction quality and processing coverage. Hybrid recovers more opinions in our development experiments, while SentiWordNet has higher tuple precision and slightly higher macro-F1.”

### A two-minute explanation

“We first preserve and validate the review text. The SentiWordNet path recognizes configured aspect and opinion phrases, applies deterministic grammar and semantic checks, retrieves a selected WordNet sense, and adjusts its native positive-minus-negative score for domain preference, degree and negation.

“The hybrid independently uses TextBlob's Pattern grammatical annotations and our attachment rules to identify aspect contexts. It scores those contexts using VADER and TextBlob, combines supported evidence, and applies explicit hotel-context rules when applicable. It retains native scores, any vocabulary substitutions and final adjustments.

“Both paths produce aspect-level records, a review summary, five descriptive strength bands, and diagnostics. We distinguish neutral sentiment from unavailable or incomplete analysis.

“On our inspected SemEval adaptation, Hybrid achieves 57.43% accuracy versus SentiWordNet's 48.65%. Its tuple-F1 is higher, but SentiWordNet has slightly higher macro-F1 and tuple precision. On real Booking reviews, many results remain Partial. We therefore claim an auditable architecture and comparative implementation, not a universally superior new sentiment algorithm.”

## 2. Foundations you should understand first

| Term | Meaning in plain language | Hotel example |
|---|---|---|
| NLP | Natural Language Processing: software processing human language | Identifying which hotel feature a complaint concerns |
| Sentiment analysis | Identifying the evaluative direction of text | Positive, Negative or Neutral |
| Opinion mining | A closely related term emphasizing extracting evaluations and their targets | Extracting “rude” about “staff” |
| ABSA | Aspect-Based Sentiment Analysis: sentiment toward particular targets/categories | Room Positive, Staff Negative |
| Aspect term / target | The actual entity being evaluated | “air conditioning” |
| Category | A broader configured grouping | Facilities |
| Opinion expression | Evaluative wording or condition | “wasn't working” |
| Issue | A finer description within a category | Air Conditioning, Noise, Friendliness |
| Lexicon | A dictionary associating entries with lexical or sentiment information | A word/sense with a positive and negative score |
| Polarity | Direction of sentiment | Negative |
| Intensity / strength | Magnitude of a score | Weak Negative versus Strong Negative |
| Subjectivity | A tool's estimate of subjective versus objective expression | An opinion-heavy expression can be highly subjective |
| Confidence | Estimated reliability that a prediction is correct | We do not provide calibrated prediction confidence |
| Rule-based / deterministic | Fixed resources and rules determine outputs for a fixed configuration | Explicit negation changes a SentiWordNet multiplier |
| Heuristic | A practical rule that is useful but not guaranteed correct | A unique nearby pronoun inherits a previous aspect |
| Annotation / gold label | A human-supplied reference answer | A benchmark labels Room as Positive |
| Prediction | Our system's answer | Room as Negative or no answer |
| Baseline | A reference method for comparison | SentiWordNet is a comparator; it is not deliberately restricted to a small vocabulary |
| Pipeline | Sequential processing steps | Text → tokens → structure → aspect evidence → score |
| Provenance | Where information came from and how it was transformed | Dataset row, source span, synset and applied rule |
| Ablation | Removing one component to measure its contribution | The same hybrid with aliases disabled |
| Holdout | Data kept untouched until final evaluation | Fresh annotated reviews after freezing code/resources |

Do not confuse an **aspect dictionary** with a **sentiment dictionary**. Knowing that “kettle” is a hotel aspect does not tell us whether “the kettle was broken” is positive or negative. Conversely, knowing that “excellent” is positive does not determine which aspect it evaluates.

### The six categories

Room, Staff, Service, Food, Cleanliness and Facilities are fixed by our project scope. Location, Price and Value are outside this scope. This is configured category recognition, not automatic discovery of arbitrary new categories.

Category and issue are different. In “The room was clean,” our SentiWordNet output has **category Room** and **issue Cleanliness**. It does not have to move the whole opinion to the category Cleanliness merely because the adjective concerns hygiene. The actual target and configured mapping matter.

## 3. Why the title is appropriate

**An Auditable Grammar Assisted Hybrid for Aspect Sentiment Analysis of Hotel Reviews**

- **Auditable:** a reviewer can inspect the source text, aspect spans, attachment patterns, lexical evidence, substitutions, rules and final score. It does not mean every prediction is correct or externally certified.
- **Grammar Assisted:** grammatical tags/chunks and our attachment rules help associate an opinion with its target. Grammar is not just checked for English correctness; it supplies relationships. We use shallow parsing, not full dependency parsing in the hybrid.
- **Hybrid:** our hybrid combines VADER and TextBlob sentiment evidence with Pattern grammatical information and explicit project logic. Here it means combining lexical tools and rules; it does not imply a neural-plus-symbolic system or a newly trained model.
- **Aspect Sentiment:** we care about sentiment toward a particular hotel feature rather than only the whole review.
- **Hotel Reviews:** this defines the domain, dictionaries, six-category scope and evaluation setting.

The title emphasizes the proposed hybrid, but the paper includes a full SentiWordNet comparator. “Auditable” is a more defensible claim than “highly accurate” or “state of the art.”

## 4. Abstract — what every part means

An abstract is the compressed version of the complete paper: problem, method, data, main results and limitations.

**Problem:** conflicting opinions within a review make one label insufficient.

**Method:** two independent approaches, with source-linked evidence and descriptive strength bands.

**Resources:** the SentiWordNet configuration has 21,181 opinion entries supported by 14,311 source synsets. Entries are not the same thing as independent concepts: multiple terms can refer to the same synset. A large lexicon is not proof of semantic coverage or correctness.

**Annotated result:** 148 eligible sentence-category cases are the denominator for classification. SentiWordNet accuracy is 48.65%; Hybrid accuracy is 57.43%. Macro-F1 and tuple-F1 measure different properties and must also be explained.

**Real-data result:** 3,089 cleaned Italy reviews have no independent aspect gold. The 81.42% and 87.41% values mean at least one aspect was scored, not that those percentages of reviews were correctly understood.

**Qualification:** the evaluation data were inspected during development. We therefore say development/exploratory results, not unseen-test accuracy.

**Viva answer: What is your abstract saying?**

“We built two traceable aspect-analysis systems, compared them under a declared benchmark mapping, found better hybrid recovery but some SentiWordNet advantages, and identified substantial real-review limitations.”

## 5. Section I — Introduction

### The problem we solve

Consider the authored example:

> The room was clean but the staff were rude.

One whole-review label could lose one of these evaluations. Aspect analysis retains:

| Target | Category | Evaluation |
|---|---|---|
| room | Room | Positive |
| staff | Staff | Negative |

A hotel manager can act on Staff feedback without treating the Room as poor. Operational interpretation means connecting results to a useful hotel-service decision.

### Why two independent systems?

Changing a scorer cannot recover a phrase rejected by an earlier parser. If a parser never emits an opinion about air conditioning, replacing SentiWordNet with VADER at the end still leaves no aspect record to score.

The hybrid therefore builds its own candidates from the original review using Pattern annotations and our own rules. It is not fed SentiWordNet's AST or limited to SentiWordNet's opinion list. Both still use dictionaries and rules; independent does not mean unrestricted.

### Our actual contribution

We contribute the integrated architecture, explicit evidence and failure records, traceable vocabulary adaptation, and reproducible comparative implementation. We did not invent SentiWordNet, VADER, TextBlob, grammatical aspect extraction or weighted averaging. The later novelty assessment in `docs/novelty-prior-art-research.md` gives closer prior-art comparisons; those additional sources have not automatically been added to the manuscript bibliography.

## 6. Section II — Literature Survey

This section explains where our ideas come from and how our work fits the field. It is not a claim that we implemented every cited method. The paper has 30 research works and 33 references total; the remaining references cover software documentation and datasets.

The introductory references establish the motivation: [1] Hu and Liu examine feature-oriented review mining and summarization, whereas [2] Pang, Lee and Vaithyanathan examine document-level sentiment classification. Their contrast explains why our project retains target-specific opinions instead of relying solely on one document label.

### II-A Lexical resources and contextual valence

| References | Main idea | Why it matters here |
|---|---|---|
| [3], [11] SentiWordNet | Positive, negative and objective information is attached to word senses | Provides native scoring evidence, but requires sense selection |
| [4] VADER | A lexicon plus rules captures informal valence and emphasis | Provides contextual sentiment scoring; does not extract hotel targets itself |
| [5] Pattern | Reusable grammatical and sentiment processing tools | Underlies the TextBlob facilities we integrate |
| [7] Hatzivassiloglou and McKeown | Coordinated adjectives provide clues to orientation | Grammar and lexical orientation are related |
| [8] Turney | Adjective/adverb-containing phrases help identify review orientation | Phrase selection matters, not just isolated words |
| [9] Wilson et al. | A word's prior polarity can differ from its contextual polarity | A dictionary lookup alone may be misleading |
| [10] SO-CAL | Lexical sentiment can be adjusted for negation and degree | Our adjustments use established principles |
| [12] NRC-Canada | Sentiment lexicons can support a supervised classification system | Lexicon use is broader than our fixed-rule integration |
| [13], [14] intensity studies | Strength requires its own modeling and evaluation | Our five bands are descriptive, not validated strength accuracy |

**Prior polarity versus contextual polarity:** “working” can describe successful equipment operation; “not working” is a failure. “Small” can be desirable for a queue but undesirable for a room. Dictionary orientation needs context and target interpretation.

### II-B Aspect extraction and targeted sentiment

- [15] double propagation uses linguistic relations to expand opinion words and targets. Our manually configured lexicon/grammar is not that iterative learning algorithm.
- [16] learns subjective extraction patterns through bootstrapping. Here “bootstrapping” means iterative learning from seeds, different from the statistical bootstrap used in our confidence intervals.
- [6], [17], [18] SemEval tasks formalize annotated aspect sentiment. They motivate explicit categories, polarity labels and evaluation scope.
- [19] LSTM models incorporate target information. An LSTM is a neural sequence model with memory mechanisms; we do not train one.
- [20] attention emphasizes information relevant to an aspect. This is learned weighting, not our fixed 0.5 sentiment fusion.
- [21] recursive neural conditional random fields jointly model related extraction decisions. We do not implement that neural structured-prediction architecture.
- [22] gated convolutions select useful local text features. A convolution processes local patterns; a gate regulates what passes through.
- [23] graph convolutions use dependency relations to connect aspect-relevant words. Our shallow chunk relationships are less expressive.
- [24], [25] BERT studies use contextual transformer representations and review-oriented adaptation. BERT can represent context beyond fixed lexicon entries; we do not train or call BERT.

**Question: Why cite neural models if we do not use them?**

“They establish the broader research landscape and show alternatives for target/context understanding. Their published scores are not directly comparable to ours because data, tasks and evaluation protocols differ.”

### II-C Representation and evaluation

- [26] subjectivity selection shows that choosing relevant text affects classification.
- [27] sentiment composition studies how phrase structure changes overall meaning; word averages cannot explain all constructions.
- [28] convolutional sentence classification is another learned representation approach.
- [29], [30] surveys distinguish targets, categories, opinion expressions, tasks and datasets.

The practical lesson is to report **extraction/recovery**, **classification quality**, and **processing availability** separately. One accuracy number cannot answer every question.

## 7. Section III — Architecture and methodology

Methodology means the actual procedure used to turn reviews into outputs and evaluate them. The paper groups the work into four modules; individual compiler phases are grouped inside them. We have not removed lexical or semantic analysis just because the diagram has four modules rather than eight boxes.

```text
Module 1: preserve and validate original review
              |
              +-- SentiWordNet deterministic front end and scoring --+
              |                                                     |
              +-- Independent Pattern grammar + VADER/TextBlob ------+
                                                                    |
Module 4: separate method records, summaries, diagnostics and evaluation
```

This is a conceptual overview, not a promise that the code has one function per diagram block. Gray diagram blocks identify established methods; white blocks identify project integration, not a guarantee of novel algorithms.

### 7.1 Module 1 — Preprocessing and validation

Input can be one review or UTF-8 CSV with `sr.no` and `review`. UTF-8 is a character encoding, not a language detector. CSV parsing supports quoted commas and multiline review fields. Validation checks whether input obeys format and size contracts; it does not establish that the English or sentiment is correct.

We preserve spelling, case, punctuation, negation and row identity. VADER uses cues such as capitalization and punctuation, so aggressively lowercasing everything or deleting stopwords could destroy useful evidence. In particular, removing “not” would reverse the meaning of complaints.

**Runtime and offline cleaning differ:** runtime flags duplicate submitted rows and retains them; offline Italy dataset construction removes exact cleaned duplicates under a recorded policy. These are different stages with different purposes, not inconsistent claims.

**Source span:** character offsets identifying text in the original review. In our running example, `room` occupies `[4,8)`: characters 4 through 7 with the end excluded, using zero-based indexing. Offsets let us highlight the target and recover exact original wording. A working-copy expansion can change length, so mappings back to original offsets must be retained.

**Algorithm 1 in plain English:** decode and map fields, retain the original row, validate it, record duplicate/validation diagnostics, and send each valid original review independently to both paths. Invalid rows remain visible in reporting.

### 7.2 Module 2 — Lexical and grammatical analysis

#### SentiWordNet front end

**Lexical analysis** identifies meaningful units and their types. For example, “air conditioning” should be recognized as a multiword target. Longest matching prefers the longest configured phrase at a position so “front desk staff” is not unnecessarily split into competing shorter entries.

Our current configuration has 772 aspect phrases, 21,181 opinion entries and 752 aliases. An alias maps a configured surface expression to an internal recognized expression. This is controlled vocabulary handling, not automatic synonym understanding.

**Syntax analysis** recognizes supported structures such as:

| Structure | Teaching example | What is attached |
|---|---|---|
| Predicate | The room was clean | clean → room |
| Attributive adjective | A spacious room | spacious → room |
| Coordinated opinions | The room was clean and comfortable | both opinions → room |
| Coordinated targets | The room and bathroom were clean | clean shared under a valid target pattern |
| Verb with object | I loved the breakfast | loved → breakfast |
| Scoped negation | The AC was not working | negation belongs to the equipment opinion |
| Bounded reference | The room was large. It was clean | explicit reference may inherit one unambiguous target |

These illustrate supported rule families; arbitrary combinations are not guaranteed to parse.

The predictive parser recognizes controlled patterns. An **AST**, Abstract Syntax Tree, retains relevant clause structure without every surface detail. Our clause records store targets, opinions, modifiers, negation and spans. They are not a complete linguistic parse of unrestricted English.

**Bounded recovery** tries additional controlled patterns after strict parsing fails. It can recover useful explicit opinions and retain unknown material as diagnostics. Recovery is not permission to invent missing subjects or sentiment.

**Morphology** handles forms such as comparative/superlative adjectives under guards. A naive stemmer might turn “offer” into “off” by stripping `er`, producing false sentiment. Guards restrict which transformations are allowed.

#### Independent hybrid front end

TextBlob PatternParser provides grammatical annotations; our project code uses them for aspect attachment.

| UI term | Explanation | Example |
|---|---|---|
| Sentence | A detected sentence-sized group of text | The room was clean. |
| POS | Part of Speech, a grammatical word class | room: noun; clean: adjective |
| Phrase chunk | A shallow group of related tokens | noun phrase “the helpful staff” |
| NP | Noun Phrase | the large room |
| VP | Verb Phrase | was working |
| Adjective chunk | Adjective expression, possibly with degree words | very comfortable |
| Preposition chunk | Group marking a preposition or prepositional relation in the parser output | wording involving “in”, “with” or “near”; boundaries depend on the parser |
| Source span | Original-text start/end offsets | exact positions of “room” |

POS/chunks come from the language tool. Category lookup, attachment choices, exclusions, source alignment, diagnostics and bounded inheritance are our rules. VADER does not supply POS tags or hotel-category recognition.

A **chunk** is a shallow local grouping. A **dependency parse** explicitly connects words by grammatical relations such as subject/object. We do not claim a full dependency parser in this hybrid. Grammatical annotations can be wrong; having a tag is not proof of understanding.

**Algorithm 2 in plain English:** run each front end independently, identify its targets and opinion candidates, attach them under that front end's rules, and keep unresolved material. Hybrid does not inherit the SentiWordNet parser's successes or failures.

### 7.3 Module 3 — Semantic attachment and scoring

**Semantic analysis** here means interpreting a supported opinion in our configured hotel domain. It checks target compatibility, selects categories/issues and associates opinion evidence with a target. It is not unrestricted human-like understanding.

#### What SentiWordNet actually is

WordNet groups words by meaning into **synsets**, sets representing a shared sense. “Cold” can describe temperature or interpersonal behavior; choosing a sense matters. SentiWordNet adds positive and negative scores to WordNet synsets.

For a selected sense:

```text
P = native positive score
N = native negative score
O = 1 - P - N       objective component
L = P - N           signed lexical polarity
```

P and N are taken from the source resource. They are not created by our parser and are not the probability that our classification is correct. The source row is retained unchanged.

Our resource has 14,311 selected source synsets supporting 21,181 opinion entries. Multiple words can share one synset. Configured hotel senses take precedence; other native entries use a first lemma-ranked sense policy. This is a deterministic selection policy, not automatic contextual word-sense disambiguation.

**Actual verified example:** for “clean” in the Room example, P=0.5 and N=0.375. Therefore O=0.125 and L=0.125. A colloquially strong word need not receive a strong numeric score in the selected sense. Do not replace awkward native values with an invented intuitive score.

#### Equation 1 — SentiWordNet final score

```text
s_SWN = clip(D × m × n, -1, +1)
```

- D: domain score; normally L, unless an explicit hotel rule replaces it.
- m: degree/intensity multiplier; ordinarily 1 without a modifier.
- n: negation multiplier, +1 ordinarily and -1 for supported negation.
- clip: values below -1 become -1; above +1 become +1; values inside stay unchanged.

**Actual AC example:** “working” has P=.25, N=0, hence L=.25; no domain replacement is recorded here, m=1, n=-1. Final score = .25×1×(-1) = **-.25**, Weak Negative.

**Arithmetic-only modifier example:** if D=.4, m=1.25, n=-1, then final score=-.5. These assumed numbers teach the equation; they are not an observed dataset prediction.

Clipping bounds scores but does not make them probabilities or calibrate them. Simple sign inversion also cannot fully model constructions such as “not bad,” sarcasm or complex multiple negation.

#### What VADER contributes

VADER means **Valence Aware Dictionary and sEntiment Reasoner**. It combines a valence lexicon with rules for sentiment cues. We use its compound score and retain its positive, neutral and negative proportions.

The compound score is bounded in [-1,1]. It is not simply positive proportion minus negative proportion and is not prediction confidence. Its native contextual behavior includes ordinary negation, degree modifiers and emphasis. Our code calls the implementation rather than inventing those library rules.

#### What TextBlob contributes

TextBlob is a Python NLP interface. In this project we use PatternParser for grammar and PatternAnalyzer for sentiment. It provides polarity in [-1,1], subjectivity in [0,1], and assessed expressions. Pattern is the underlying language-processing toolkit; TextBlob exposes these components.

We do not train TextBlob's movie-review classifier. We do not use automatic translation, general spell correction or every possible TextBlob feature. We use the capabilities relevant to this architecture.

**Subjectivity .7 does not mean 70% confidence.** It concerns the character of the expression, not whether our target attachment or sentiment decision is correct.

#### Guarded scoring copies

The hybrid has 671 aspect phrases and a catalog of 497 reviewed lexical forms. That catalog is not the entire VADER/TextBlob lexicon. For eligible native-unknown expressions, a category-approved canonical form can be used in a separate scoring copy. Native-known forms take precedence. The original text, substitution spans/reasons and original/effective scores remain recorded. Whole-text substitutions require approval across all six categories.

This broadens practical lexical support without rewriting the submitted review. It remains manual adaptation: a canonical substitute can distort intensity or be wrong in context.

#### Equation 2 — evidence-aware fusion

```text
L_h = [w eV V + (1-w) eT T] / [w eV + (1-w) eT]
```

- V: effective VADER compound score.
- T: effective TextBlob polarity.
- w=.5: fixed VADER weight; TextBlob's weight is 1-w=.5.
- eV and eT: indicators, 1 when that component supplies lexical evidence, otherwise 0.

If both have evidence, this becomes (V+T)/2. If only one has evidence, its supported score is retained without dilution by an unsupported zero. If neither has evidence, the lexical fusion is unavailable: never divide by zero. If either component fails during execution, the error is retained rather than silently treating it as no evidence.

VADER evidence uses nonzero positive/negative proportions; TextBlob evidence uses the presence of assessments. Thus a zero TextBlob polarity can still be supported neutral evidence. Zero and missing are different states.

**Actual clean-room context:** V=.4019 and T=.3666667. Fusion=(.4019+.3666667)/2=.38428335, rounded to **.384283**.

**Arithmetic-only one-component example:** V=.6 with evidence, T=0 without evidence. Fusion=.6, rather than a naive average of .3. This explains the policy; its accuracy benefit has not been isolated by ablation.

The shared range [-1,1] does not prove identical calibration between tools. The .5 weight is a transparent default, not a learned optimal parameter.

#### Domain overrides

Hotel-context rules can replace hybrid fusion when configured conditions match. Opposing rule signs in one context prevent an override. These are our explicit semantic interpretations, not native library outputs.

Two verified cases:

| Context | Lexical evidence | Final Hybrid value | Explanation |
|---|---|---:|---|
| The rooms were quiet. | VADER has no valenced evidence; TextBlob assesses quiet with polarity 0; fusion 0 | +.45 | `room_quiet` interprets quiet as favorable for a room |
| The air conditioning wasn't working. | Both lexical-evidence flags are false; fusion unavailable | -.70 | `equipment_not_functioning` supplies an explicit failure interpretation |

The second case is important: **no lexical evidence does not prevent an independently configured domain rule from supplying a score**, as long as there was no component execution error. The trace distinguishes the rule-derived result from unavailable lexical fusion.

For the current SentiWordNet quiet-room example, final score is +.25 from its configured native sense, with no calibration override recorded. When explaining the paper's general discussion of hotel preference, do not claim that this particular trace changed a native quiet score: the actual trace is authoritative.

**Algorithm 3 in plain English:** score SentiWordNet opinions with native senses and explicit multipliers; independently score Hybrid contexts with native tools, guarded copies, evidence-aware fusion and applicable domain rules. Retain the derivation, not just the final number.

### 7.4 Module 4 — Synthesis and final records

#### Five labels and exact boundaries

| Score s | Descriptive band |
|---|---|
| s ≤ -.50 | Strong Negative |
| -.50 < s < -.05 | Weak Negative |
| -.05 ≤ s ≤ +.05 | Neutral |
| +.05 < s < +.50 | Weak Positive |
| s ≥ +.50 | Strong Positive |
| No usable final score | Unavailable |

Exactly -.05 and +.05 are Neutral; exactly -.5 and +.5 are Strong. The intervals are a project policy, not a learned fact or a confidence scale. Evaluation collapses Strong/Weak Positive to Positive and Strong/Weak Negative to Negative because our benchmark provides three-class polarity, not strength gold.

#### Equation 3 — one score for a review

```text
R_i = (H_i1 + H_i2 + ... + H_im) / m_i
```

i identifies a review; j identifies one retained scored opinion/context; m_i is the count included under that method's mean policy; H_ij is its final sentiment score. It is a bounded arithmetic mean, not min-max scaling or a probability. There can be more than one opinion in a clause, so the denominator is not necessarily the number of sentences or clauses.

Policies differ:

- SentiWordNet averages retained scored opinions, including on Partial results. This is a mean of recognized opinions, not a guarantee of full-review coverage.
- Hybrid returns an aspect mean only when all extracted contexts have scores. If one is unscored, the mean is unavailable. A mean can still exist for Partial analysis when all extracted contexts are scored but other diagnostics remain.
- Hybrid whole-text sentiment is separately scored on the full review; it is not substituted for missing aspect sentiment.

For the running example, current outputs are:

| Method | Room | Staff | Aspect mean | Overall label |
|---|---:|---:|---:|---|
| SentiWordNet | +.125 | -.625 | -.250000 | Mixed |
| Hybrid | +.384283 | -.379400 | +.002441 | Mixed |

The near-zero Hybrid mean must not erase the two opposing opinions. **Mixed describes coexistence; Neutral describes a score band.** They answer different questions. Rounding is to six decimal places where implemented; last-place differences can reflect the exact rounding sequence.

#### Dashboard category mean

First average category opinions within each review, then average those review means across reviews that contribute that category:

```text
CategoryMean_c = (1 / number of contributing reviews)
                 × sum of each review's mean for category c
```

Example: Review 1 Room scores .125 and .25 give .1875. Review 2 Room score -.75 gives -.75. Category mean=(.1875-.75)/2=**-.28125**, displayed as -.2813. Each contributing review gets equal weight, rather than verbose reviews dominating through more opinion mentions. Missing categories are not inserted as zero.

#### Status versus polarity

| Status | What it means | What it does not establish |
|---|---|---|
| Complete | Candidates/records exist, required scores are available, and no unresolved/scope diagnostic is detected | Every human opinion was extracted correctly |
| Partial | Some usable opinions coexist with diagnostics or missing candidate scores | The entire result is useless or entirely incorrect |
| Unsupported | No scored aspect under the implemented rules, absent a higher-priority analysis failure | Neutral sentiment |
| Invalid input | Input violates CSV/text validation contracts | A negative review |
| Processing error | Parser/scorer execution failed under the relevant analysis path | An ordinary unknown word |

The low-level SentiWordNet function raises certain invalid-argument/resource errors; adapters retain per-row outcomes. Hybrid also has explicit grammatical/component error paths. A separately retained whole-text result should not be mistaken for a successful aspect analysis.

**Algorithm 4 in plain English:** preserve independent results and failures, summarize under each policy, export all review rows, and evaluate against human labels only when they exist.

## 8. Section IV — Data and implementation results

### 8.1 There are multiple evaluation units

Review: one guest feedback record. Sentence: a subdivision of that review. Classification case: one eligible sentence/category combination. Opinion annotation: one human-marked evaluation. Tuple: a category/polarity pair for a sentence after mapping/deduplication.

These counts are different. Never say “148 reviews” for the classification benchmark.

### 8.2 Dataset roles

| Cohort | Size used | Gold aspect sentiment? | Purpose |
|---|---:|---|---|
| SemEval hotel source | 30 parent reviews, 266 sentences | Yes, mapped human opinions | Classification and category-polarity recovery |
| Earlier Booking random sample | 200 reviews | No | Processing coverage |
| Cleaned Booking Italy | 3,089 unique nonblank bodies | No | Real-review coverage and vocabulary development |
| Italy demo subset | 500 of those 3,089 | No | Reproducible real-data demonstration and coverage |

The 500 is nested in the 3,089; do not add them and claim 3,589 independent unique Italy reviews. The earlier curated 100 is not an experimental arm in the current paper. The published 515,738-record source is a source corpus, not our evaluated sample size.

### 8.3 What “real” and “cleaned” mean

The Italy file is a published Crawlfeeds Booking export supplied by the user. We preserve source correspondence and record hashes/maps. This verifies correspondence to dataset bytes, not personal verification of every guest or authenticity of every original review.

Preparation:

```text
4,367 source rows
- 1,266 empty bodies after the declared cleanup
-    12 exact cleaned duplicates
= 3,089 retained reviews
```

Cleanup removes explicit missing markers, standalone N/A variants and nonprinting controls, and normalizes whitespace. It retains original sentiment wording, spelling, case, punctuation and negation. Ordinary feedback such as “Nothing” is not automatically missing. Original positive/negative body fields are joined; ratings, titles, names and field headings are excluded from analyzed text.

The demo's 500 reviews use uniform random sampling with seed 172026. The seed makes selection repeatable; it does not improve sentiment accuracy. No filtering by analyzer success, score, grammar compatibility or vocabulary coverage is used for that sample.

**Question: Can we claim the text is byte-for-byte unchanged?**

“The cleaned text is not byte-identical because documented marker removal, whitespace cleanup, field joining and deduplication occurred. We did not author, paraphrase or sentiment-edit the reviews, and source maps retain the derivation.”

### 8.4 SemEval mapping

We adapt the benchmark to six project categories:

| Benchmark label | Project evaluation category |
|---|---|
| ROOMS | Room |
| FACILITIES or ROOMS_AMENITIES | Facilities |
| FOOD_DRINKS | Food |
| SERVICE | Service |
| HOTEL with CLEANLINESS attribute | Cleanliness |
| Predicted Staff | Collapsed into Service for evaluation |
| Price attributes, Location, other HOTEL opinions | Outside the declared mapping |

Counts:

```text
339 original opinion annotations
- 141 outside scope
= 198 mapped original annotations
→ 162 unique coarse category/polarity pairs
→ 137 sentences with at least one mapped opinion
→ 148 unambiguous sentence/category classification cases
```

The arrows are transformations, not repeated subtraction. Multiple original annotations can collapse to one pair. A sentence can generate several category cases. If a coarse category has conflicting gold polarities in a sentence, those pairs remain in tuple evaluation but that category is excluded from single-polarity classification.

The evaluator runs methods on sentence text and uses gold afterward to score them; gold does not supply the predicted aspect inside the pipeline. It evaluates only the declared eligible sentences. This is an adapted task, not the official full SemEval leaderboard protocol. Cross-sentence reference capabilities are not fully exercised by sentence-by-sentence evaluation.

### 8.5 What each implementation result tells us

Module 1 validates and retains rows/source evidence. Splitting the Italy corpus into 1,000/1,000/1,000/89 handles the interface limit; it is not a machine-learning train/test split.

Module 2 emits different record sets. On random 200, SentiWordNet emits 516 opinions and Hybrid 626 contexts. On Italy demo 500, the counts are 1,307 and 2,166. More records indicate broader candidate extraction, not proven correctness; the units also differ between methods.

Module 3 demonstrates traceable scores and explicit rules. Quiet-room and equipment-failure examples show why a final hybrid score need not equal raw library polarity.

Module 4 reports coverage:

| Cohort | SentiWordNet Complete / Partial / Unsupported | Hybrid Complete / Partial / Unsupported |
|---|---|---|
| Random 200 | 4 / 152 / 44 | 70 / 101 / 29 |
| Italy demo 500 | 10 / 393 / 97 | 44 / 399 / 57 |
| Full cleaned Italy 3,089 | 51 / 2,464 / 574 | 246 / 2,454 / 389 |

Full Italy any-aspect coverage:

```text
SentiWordNet: (51 + 2464) / 3089 = 81.42%
Hybrid:      (246 + 2454) / 3089 = 87.41%
```

Full Italy completeness: 51/3089=1.65%; 246/3089=7.96%. These are much lower because having one usable aspect is easier than having no detected unresolved material. No invalid-input or processing-error outcomes occur in these retained experimental cohorts.

The 210 authored software tests check implementation contracts; they are not 210 human-annotated real-world accuracy cases. The latest paper contains no controlled runtime result, so do not quote timings from older configurations.

## 9. Section V — Metrics from scratch

### 9.1 Why accuracy alone is insufficient

A system can be precise on the few cases it answers while failing to answer most cases. A positive-heavy dataset can also reward predicting Positive very frequently. We therefore report all-case accuracy, classification coverage, conditional accuracy, per-class F1, macro-F1 and tuple metrics.

### 9.2 Equation 4 — accuracy and classification coverage

```text
N = all eligible classification cases = 148
C = correct three-class predictions
S = cases receiving a Positive, Neutral or Negative prediction

Accuracy = C / N
ClassificationCoverage = S / N
ConditionalAccuracy = C / S
```

| Count/measure | SentiWordNet | Hybrid |
|---|---:|---:|
| Eligible N | 148 | 148 |
| Correct C | 72 | 85 |
| Three-class answers S | 81 | 94 |
| Wrong three-class answers S-C | 9 | 9 |
| Missing/Mixed N-S | 67 | 54 |
| Accuracy | 72/148 = 48.65% | 85/148 = 57.43% |
| Classification coverage | 81/148 = 54.73% | 94/148 = 63.51% |
| Conditional accuracy | 72/81 = 88.89% | 85/94 = 90.43% |

The count decomposition is exact, but does not mean Hybrid recovered precisely the same cases SentiWordNet missed: their answered subsets differ. All-case accuracy counts Missing/Mixed as failures for this specific single-polarity task.

The 90.43% value is not our overall accuracy. It excludes unanswered/conflicting cases and must be described as conditional accuracy.

**Percentage points:** 57.4324%-48.6486%=8.7838 percentage points, rounded to **8.78 percentage points**. This is not the same as an 8.78% relative increase.

### 9.3 TP, FP and FN

Choose one class, for example Negative, and treat other gold labels as not-Negative:

- True Positive (TP): predicted Negative and gold Negative.
- False Positive (FP): predicted Negative but gold another class.
- False Negative (FN): gold Negative but prediction another class, Mixed or missing.
- True Negative (TN): neither gold nor prediction is Negative under the chosen binary view. TN is not used directly in F1.

These terms apply to each class separately in a multiclass problem.

### 9.4 Precision

```text
Precision = TP / (TP + FP)
```

“Of the cases I called Negative, how many were really Negative?”

Hybrid Negative TP=10, FP=1: precision=10/11=.9091. SentiWordNet Negative TP=6, FP=0: precision=1.0. Perfect precision on only six predictions does not mean the model found all complaints.

### 9.5 Recall

```text
Recall = TP / (TP + FN)
```

“Of all real Negative cases, how many did I find?”

There are 41 gold Negative cases. Hybrid recall=10/41=.2439; SentiWordNet recall=6/41=.1463. Both miss many negative cases, even though precision among the emitted negative predictions is high.

### 9.6 F1 score

```text
F1 = 2 × Precision × Recall / (Precision + Recall)
   = 2TP / (2TP + FP + FN)
```

It is the harmonic mean, which penalizes imbalance: high precision cannot compensate fully for low recall. For Hybrid Negative: TP=10, FP=1, FN=31, so F1=20/(20+1+31)=**.3846**. If a class has no correct predictions, its F1 can be zero; our implementation handles undefined zero-denominator precision/F1 with zero.

F1 is not accuracy and .3846 is not “38.46% of all reviews correct.” It summarizes one precision/recall tradeoff.

### 9.7 Macro-F1 and class imbalance

```text
MacroF1 = (F1_Negative + F1_Neutral + F1_Positive) / 3
```

Each class gets equal weight even if support differs. **Support** means the number of gold examples of that class.

| Class | Gold support | SentiWordNet F1 | Hybrid F1 |
|---|---:|---:|---:|
| Negative | 41 | .255319 | .384615 |
| Neutral | 4 | .200000 | .000000 |
| Positive | 103 | .755814 | .815217 |
| Macro average | 148 total | .403711 | .399944 |

SentiWordNet correctly predicts one Neutral case; Hybrid predicts none. That Neutral F1 term is weighted equally with the Positive and Negative terms, explaining SentiWordNet's slight macro-F1 advantage despite lower overall accuracy. It is not evidence of generally reliable neutral recognition: four cases are too few.

**Micro versus macro versus weighted F1:** macro averages classes equally; weighted F1 averages class F1 by gold support; micro pools TP/FP/FN across classes first. We report fixed three-class macro-F1. Do not assume micro-F1 equals accuracy when missing predictions are retained outside the fixed predicted classes; that familiar identity requires particular complete single-label conditions.

### 9.8 An important extra cross-question: the majority baseline

This is a teaching calculation from the reported class support, not an additional implemented paper experiment. If one simply answers Positive for every one of the 148 supplied classification cases, accuracy would be 103/148=**69.59%**. Its macro-F1 would be approximately **.2736**: Positive F1=206/(206+45)=.8207, the other two class F1 values zero.

This shows why our 57.43% accuracy is not by itself evidence of a strong three-class classifier. Our macro-F1 is higher than this trivial calculation, but accuracy is lower. Moreover, a constant classifier on gold-specified category cases does not extract hotel targets, so it is not a complete end-to-end ABSA comparator or a computed tuple baseline.

If challenged, say: “The positive imbalance makes an always-Positive classifier a necessary contextual baseline for classification. Our current paper compares two complete pipelines and does not establish state-of-the-art classification. A stronger evaluation should explicitly add simple baselines and a fresh balanced annotation set.” Do not hide this limitation.

### 9.9 Category-polarity tuple metrics

A tuple here is a pair such as (Room, Positive), compared within its sentence. It is not an exact opinion text span or issue label. Repeated identical pairs within one sentence are deduplicated, but observations in different sentences remain separate.

Teaching example:

```text
Gold:      {(Room, Positive), (Staff, Negative)}
Predicted: {(Room, Positive), (Food, Positive)}
Matched:   {(Room, Positive)}
Precision = 1/2; Recall = 1/2; F1 = 1/2
```

An aspect with the wrong polarity is not a matching pair. Its predicted pair contributes a false positive and the absent gold pair a false negative.

Actual results:

| Quantity | SentiWordNet | Hybrid |
|---|---:|---:|
| Gold pairs | 162 | 162 |
| Predicted pairs | 112 | 145 |
| Matched pairs | 81 | 99 |
| Tuple precision | 81/112 = .7232 | 99/145 = .6828 |
| Tuple recall | 81/162 = .5000 | 99/162 = .6111 |
| Tuple-F1 | 162/(112+162) = .5912 | 198/(145+162) = .6450 |

In general tuple-F1=2×matched/(predicted+gold), equivalent to the harmonic mean of tuple precision/recall.

**Why 99 matched tuples but only 85 correct classifications?** They are different evaluation units and scopes. Classification reduces opinions into one label for each unambiguous sentence/category case; opposite predictions can create Mixed and count as incorrect. Tuple matching can still match one member of an ambiguous/multiple-polarity set. Tuple evaluation also includes gold coarse categories with conflicting labels that are excluded from classification.

### 9.10 Bootstrap confidence intervals

Sampling uncertainty means a result from a small sample may vary if different reviews had been selected. We approximate that variation with resampling:

1. Group eligible cases by their original parent review.
2. Sample parent-review groups with replacement, keeping their cases together.
3. Recompute accuracy on each resample.
4. Repeat 1,000 times.
5. Use roughly the 2.5th and 97.5th percentiles as interval endpoints.

With replacement means the same review can appear several times in one resample and another not at all. This is statistical bootstrap, not retraining or creation of new organic reviews.

We use clusters because sentences within one review can be correlated. Treating all 148 cases as independent would ignore that structure. Cases are nested within 30 source parent reviews, but the implemented bootstrap samples groups represented among the eligible classification cases, not empty parents with no eligible case.

SentiWordNet interval: **39.31%-60.00%**. Hybrid: **48.99%-65.73%**.

A 95% confidence interval is not “95% probability each prediction is correct,” and it does not fix development-data reuse. Separate interval overlap is not itself a formal paired significance test. We have not run such a test, so we do not claim statistically significant superiority.

## 10. How to explain every table and figure

| Item | What to say | Main inference |
|---|---|---|
| Fig. 1 | Preserve/validate text and source identity before independent analysis | Input integrity and traceability |
| Fig. 2 | Two different grammatical front ends | Extraction changes as well as scoring |
| Fig. 3 | Native SentiWordNet evidence versus independent hybrid evidence/copies | Final scores have inspectable derivations |
| Fig. 4 | Method-specific adjustments, synthesis, status and evaluation | Output includes limitations, not only polarity |
| Table I | Distinguishes datasets, units and annotation availability | Do not claim accuracy on unlabeled Booking data |
| Table II | Full cleaned Italy and nested 500 status counts | Any-aspect coverage is much higher than completeness |
| Fig. 5 | Stacked status counts on 3,089 cleaned reviews | Most useful results still require inspection |
| Fig. 6 | Status counts on random 200 | Hybrid has fewer unsupported rows, with different heuristics |
| Table III | Accuracy, coverage, intervals and tuple metrics | Hybrid recovery gain with precision/class-balance tradeoffs |
| Fig. 7 | Visualizes accuracy, macro-F1 and tuple-F1 | Different metrics favor different systems |
| Table IV | F1 and support by class | Positive imbalance and weak neutral/negative recovery |
| Fig. 8 | Class F1 comparison | Neutral contribution explains macro-F1 reversal |

A plotted value of .574 is approximately 57.4%, not .574%. F1 axes usually use decimals in [0,1]. Stacked bars show counts and denominators; colors do not imply confidence.

## 11. Section VI — Conclusion and defensible inferences

1. Hybrid answers more eligible benchmark cases and recovers more gold category-polarity pairs in this development comparison.
2. Broader extraction introduces additional errors: SentiWordNet has higher tuple precision.
3. Hybrid is not better on every metric: SentiWordNet has slightly higher macro-F1.
4. Vocabulary size alone is insufficient; word senses, context and attachment remain bottlenecks.
5. Real reviews remain difficult: full-corpus completeness is low even though any-aspect coverage exceeds 80%.
6. Auditability helps inspect errors and rules; it does not guarantee correctness.
7. We need frozen resources, fresh human annotation and controlled component tests before stronger generalization claims.

Do not conclude that VADER/TextBlob are universally better than SentiWordNet or that the exact .5 fusion caused the gain. The study compares full pipelines, including different vocabularies, grammar and some aspect mappings.

## 12. Threats to validity and honest defence

| Professor's challenge | Defensible answer |
|---|---|
| Is your test set unseen? | No. The benchmark was inspected during development, so our reported numbers are exploratory development measurements. |
| Did you train a model? | We trained no new hotel model. We use existing lexical/language resources plus project dictionaries and rules. The resources themselves have prior construction/training histories. |
| Why not say fully unsupervised? | Our system needs no new training labels to execute, but manually curated domain rules and inspected benchmark feedback make “no supervision of any kind” misleading. |
| Why do category dictionaries differ? | They evolved independently, retaining some original mappings. We disclose that this is a full-pipeline comparison, not a controlled scorer-only experiment. |
| Is Complete proof of correctness? | No. It means no implemented diagnostic detected an unresolved condition; undetected omissions and wrong attachments can remain. |
| Did gold labels leak into predictions? | The evaluator reads gold after prediction, not as model input. However, prior inspection influenced development, so the benchmark is not an untouched holdout. |
| Are the two kinds of leakage the same? | No. Direct input leakage and development/test contamination are different; avoiding ratings in input does not erase prior benchmark inspection. |
| Does 497 mean Hybrid has only 497 opinion words? | No. It is our reviewed adaptation catalog in addition to native library dictionaries. |
| Is 21,181 bigger and therefore better? | More native entries increase lexical availability but may introduce factual or wrong-sense matches. Better coverage is not automatically better accuracy. |
| Why only six categories? | It is a declared project scope. Location and Price remain diagnosed rather than forced into unsuitable categories. |
| Why choose ±.05 and ±.5? | They are fixed operational/descriptive policies; ±.5 strength is not validated by human intensity annotations. The exact neutral boundaries follow our implementation. |
| Are the scores probabilities? | No. They are tool/resource-dependent sentiment indices. Equal numeric ranges do not establish equal calibration. |
| Can a domain rule score missing lexical evidence? | Yes; it is explicitly identified as a project rule-derived score, with unavailable native fusion retained. Execution failure still remains an error. |
| Is this scientifically novel? | The strongest contribution is the specific auditable architecture, guarded adaptation policy, evidence/failure semantics and empirical comparison. The broad component ideas already exist. |
| Is it fair to compare published BERT accuracy with ours? | No, unless datasets, splits, labels and scoring protocol match. Our literature survey is context, not a reproduced leaderboard. |
| Why no neural baseline? | The current scope emphasizes an inspectable local compiler/lexicon system. This limits claims relative to modern ABSA methods. |
| Do you handle all negation? | No. Supported scopes and bounded patterns exist; complex, quantified and ambiguous negation remain limitations. |
| Is the result statistically significant? | Not established. We report point estimates and cluster intervals without a paired significance test. |

### Why the comparison is useful despite limitations

It demonstrates a working compiler-style analysis system, makes resource and attachment decisions inspectable, preserves adverse outcomes and measures more than attractive demo examples. That is a valid engineering and exploratory empirical contribution. It should not be inflated into a claim that current real-world accuracy is solved.

## 13. Questions about compiler design

**Is this a conventional programming-language compiler?**

No. It is compiler-inspired text analysis. A normal compiler translates a programming language into another representation or executable code. We translate supported review expressions into structured aspect sentiment records. Our final IR is data for analysis, not machine code.

**What is the intermediate representation?**

Typed token, clause/AST, semantic and final aspect records. They separate stages and retain source links, so a failure can be traced to recognition, parsing, attachment or scoring.

**What is syntax versus semantics?**

Syntax recognizes structural patterns, such as a subject and predicate. Semantics interprets that structure in the hotel domain: which category an aspect belongs to, whether an opinion is compatible and which issue/sense applies.

**What does error recovery mean?**

Retaining valid analyzable parts while recording unsupported material and resuming at supported boundaries/patterns. It is not silently treating the entire review as correct.

**Does the hybrid implement all the same phases?**

It performs corresponding language-processing tasks through a different implementation: Pattern tokens/chunks, project segmentation/attachment/category mapping, library scoring and record synthesis. It does not use our SentiWordNet predictive AST. Avoid saying both are identical compiler implementations.

**Does token classification prove word sense?**

No. A lexical match or POS tag does not resolve contextual meaning. First-ranked sense selection and shallow attachment remain imperfect.

**What are terminals, nonterminals and a grammar production?**

Terminals are the input token types a grammar consumes; nonterminals name intermediate structures such as a clause or opinion phrase. A production says how a structure can be formed from smaller pieces. An illustrative rule is `Clause → Aspect Copula Opinion`; it explains the design but is not a verbatim complete specification of our parser. Natural language is ambiguous, so our controlled grammar deliberately covers only supported patterns. Do not claim a formally proved complete LL(1) grammar for unrestricted English merely because the parser uses predictive logic.

## 14. Code map for “show me where you implemented it”

Paths are relative to the project root. These are useful locations, not a claim that every concept occupies only one file.

| Responsibility | Code/resource |
|---|---|
| SentiWordNet public analysis orchestration and processing status | `hotel_compiler/pipeline.py`: `analyze_review` |
| Shared compiler front-end processing | `hotel_compiler/front_end.py` |
| Longest matching, lexical classification and morphology | `hotel_compiler/lexer.py` |
| Controlled predictive grammar | `hotel_compiler/parser.py` |
| Additional bounded grammar/recovery | `hotel_compiler/expanded_parser.py`: `parse_expanded`, `recover` |
| SentiWordNet category/issue binding and semantic guards | `hotel_compiler/semantics.py`: `analyze_semantics` |
| Native sense scoring and adjustments | `hotel_compiler/sentiwordnet.py` |
| Current SentiWordNet vocabulary/resource/provenance | `hotel_compiler/resources/domain_expanded.json`, `sentiwordnet_expanded.tsv`, `provenance_expanded.json` |
| Current compiler profile selection | `hotel_compiler/compiler_profiles.py` |
| Hybrid grammar, spans, target attachment and domain rules | `hotel_compiler/hybrid_nlp.py`: `analyze_language`, `domain_adjustment` |
| Hybrid tools, fusion, evidence and summary | `hotel_compiler/hybrid.py`: `HybridEngine._score_native`, `score_text`, `score_aspect`, `analyze_hybrid_review` |
| Guarded scoring-copy vocabulary adaptation | `hotel_compiler/hybrid_vocabulary.py`: `normalize_opinions`; `resources/hybrid_vocabulary.json` |
| Hybrid category dictionaries/domain patterns | `hotel_compiler/resources/hybrid_domain.json` |
| Five strength bands and Mixed policy | `hotel_compiler/sentiment_policy.py`: `SentimentPolicy`, `overall_polarity` |
| Accuracy, class F1, cluster intervals and category crosswalk | `hotel_compiler/research_metrics.py` |
| Full comparison runner, SemEval tuple metrics and exports | `hotel_compiler/research_runner.py`: `compare_csv`, `evaluate_semeval` |
| Cleaned real-data construction | `scripts/prepare_clean_booking_demo.py` |
| Full cleaned-corpus paired run | `scripts/compare_clean_booking_corpus.py` |
| Paper prose and automated figures/tables | `docs/conference_manuscript.md`; `scripts/build_conference_paper.py`, `paper_figures.py` |
| Web entry points | `hotel_compiler/web.py`, `web_analysis.py`, `web_batch.py`, `web_assets/` |

The current paper calls the broad compiler simply SentiWordNet. Some filenames/CLI flags retain the implementation profile name `expanded`; that is not a third approach in the paper. Original configuration files remain for reproducibility, but do not quote their old results as current paper results.

## 15. A practical demo script

1. Open `Start_Demo.bat` in the project root. It delegates to `scripts/open_demo.ps1`, which launches/opens the local demo. Use the browser address printed by the launcher rather than assuming a port if it selects another.
2. Select the current broad SentiWordNet configuration where the UI exposes compiler profiles, and compare it with Hybrid.
3. Enter **The room was clean but the staff were rude.** Explain target attachment, separate scores and Mixed despite a near-zero hybrid mean.
4. Enter **The air conditioning wasn't working.** Show the different score derivations: native SentiWordNet negation versus an explicit hybrid equipment rule.
5. Enter **The rooms were quiet.** Show native zero hybrid lexical fusion and the +.45 Room rule, alongside SentiWordNet's +.25 native score.
6. Upload `output/datasets/booking_cleaned/booking_italy_cleaned_demo_500.csv`. It contains identifiers and real cleaned review text; no gold labels or processing results are required as input.
7. Open one Complete, one Partial and one Unsupported row. Explain why these are processing statuses rather than verified correctness.
8. Show the consolidated dashboard and then the supporting individual rows. Explain that category means aggregate only contributing reviews and do not measure accuracy.

The three typed examples above were rerun against the current code while preparing this guide. They are authored instructional examples, not extra independent test cases added to the paper.

## 16. Research improvements you can explain as future work

- Freeze code/resources and annotate fresh hotel reviews without success-based selection. Prefer two independent annotators, documented guidelines, disagreement adjudication and agreement reporting.
- Split by parent review and control duplicates so related text does not cross evaluation splits.
- Hold extracted contexts fixed for VADER-only, TextBlob-only and fusion comparisons. These are experimental configurations, not necessarily three user-facing project systems.
- Remove aliases, context overrides and attachment features separately to establish their contributions. This is deferred ablation work, not a completed experiment.
- Validate whether Complete flags correspond to full human-judged coverage.
- Add explicit strength annotation before reporting five-class accuracy. Fine-grained gold must distinguish weak/strong, not merely use our own thresholds as ground truth.
- Evaluate fresh category extensions such as Location/Price under an explicit ontology rather than relabeling them into current categories.
- Consider richer parsing or learned contextual approaches if the project scope later allows it; they still need independent evaluation and source evidence.

## 17. Final revision sheet

Memorize these accurately:

| Item | Value/answer |
|---|---|
| Systems in the paper | SentiWordNet versus VADER–TextBlob Hybrid |
| Categories | Six: Room, Staff, Service, Food, Cleanliness, Facilities |
| SentiWordNet resource | 772 aspects; 21,181 opinion entries; 752 aliases; 14,311 source synsets |
| Hybrid additions | 671 aspect phrases; 497 reviewed lexical forms, plus native tool lexicons |
| Main gold denominator | 148 eligible sentence/category cases |
| Source parent reviews | 30; source sentences 266 |
| SentiWordNet accuracy / macro-F1 / tuple-F1 | 48.65% / .4037 / .5912 |
| Hybrid accuracy / macro-F1 / tuple-F1 | 57.43% / .3999 / .6450 |
| Accuracy gap | 8.78 percentage points |
| Higher tuple precision | SentiWordNet |
| Higher tuple recall | Hybrid |
| Neutral support | Only four cases |
| Full cleaned Italy size | 3,089 |
| Full Italy any-score coverage | 81.42% SWN; 87.41% Hybrid |
| Full Italy completeness | 1.65% SWN; 7.96% Hybrid |
| Neutral band | Inclusive [-.05,+.05] |
| Strong cutoffs | Inclusive ≤-.5 and ≥+.5 |
| Fusion weight | .5, fixed and untuned |
| Is subjectivity confidence? | No |
| Is Complete validated correctness? | No |
| Is Booking coverage accuracy? | No |
| Is SemEval untouched? | No, development evidence |
| Were any new hotel models trained? | No |
| Novelty claim | Auditable architecture, traceable adaptation and explicit evidence/failure semantics; not invented underlying tools |

### Closing answer

“The study shows that broader grammatical and lexical recovery can improve the availability of aspect sentiment, but also creates precision and interpretation tradeoffs. Our architecture makes those decisions and failures visible. The current evidence supports that engineering contribution and exploratory comparison; stronger generalization and component-effect claims require fresh annotations and controlled experiments.”

## 18. Reading and evidence paths

- Current paper: `output/paper/Team_17_IEEE_Conference_Paper.docx` and `.pdf`.
- Authoritative benchmark: `output/experiments/2026-10-21/expanded-sentiwordnet-release/semeval-development/metrics.csv`, `per_class_metrics.csv`, `predictions.csv`, `confusion_counts.csv`, `annotation_scope.csv`.
- Italy coverage: same release root, `booking-all/coverage.csv` and `booking-cleaned500/coverage.csv`.
- Real-data preparation: `output/datasets/booking_cleaned/cleaning_manifest.json`, source maps and cleaning audit.
- Complete paper bibliography: `output/paper/references.json`; reference numbers in this guide refer to the current manuscript.
- Prior-art novelty assessment: `docs/novelty-prior-art-research.md`.

No results were changed or new accuracy claims produced in preparing this guide. Worked arithmetic beyond the paper, such as the constant-Positive teaching baseline, is explicitly labeled as an additional explanatory calculation.
