# Research Paper Viva Questions and Answers

Team 17 | Tanay Mohta and Aditya Rawat | Updated 28 October 2026

This Markdown file is the continuing Q&A notebook. It includes the earlier abstract questions and the introduction questions. Future questions should be appended here; the Word notebook is no longer updated.

## Q1. What is selective deep learning reanalysis?

**Paper section:** Abstract

### Key explanation

- Selective means only Hybrid reviews marked Partial or Unsupported enter the deep learning stage. Complete reviews retain Hybrid; invalid inputs and component failures are not silently reanalysed.
- Reanalysis means the model independently reads every original sentence in the routed review. It does not receive only unmatched words, and it does not append predictions to the Hybrid opinion list.
- The DL result replaces the selected analysis for that routed review, including abstention when no category is accepted. Original Hybrid evidence remains available.
- Complete is a processing status, not proof that the review is correct. Selective routing can improve some cases and harm others.

### Answer to faculty

> We apply our fine-tuned deep learning model only to reviews the Hybrid system marks Partial or Unsupported. It rereads their original text independently and produces category-sentiment results or abstains; Complete Hybrid reviews are retained.

## Q2. What are a MiniLM classifier, encoder and neural head?

**Paper section:** Abstract

### Key explanation

- MiniLM is a compact pretrained transformer language model. In this project we initialize from all-MiniLM-L6-v2 and fine-tune it for classification; it is not a generative chatbot.
- Input is a sentence paired with a category description, for example a review sentence plus the Service query. The tokenizer converts the pair into numeric tokens.
- The encoder learns contextual numerical representations of the paired text. The classification head turns that representation into scores for Absent, Negative, Neutral/Mixed and Positive.
- Softmax converts output scores into probabilities summing to one. An accepted category must satisfy its validation-selected threshold; probability is not guaranteed correctness or sentiment intensity.
- The same encoder and head are reused across eight queries: five hotel categories and three background groups. Staff is pooled into Service in the DL taxonomy. Both encoder and head were fine-tuned on human-labelled Trip-MA data.

### Answer to faculty

> The MiniLM encoder converts the review sentence and category query into a contextual representation. A small neural classification head predicts whether that category is absent or has negative, neutral/mixed or positive sentiment. We fine-tuned both parts for hotel reviews.

## Q3. What is polarity accuracy?

**Paper section:** Abstract

### Key explanation

- Polarity means sentiment direction: Positive, Negative or Neutral in the SemEval classification comparison.
- Polarity accuracy = correct single-polarity predictions / all eligible sentence-category cases x 100. The denominator is 148 cases, not 148 whole reviews.
- SentiWordNet: 72/148 x 100 = 48.65%. Hybrid: 85/148 x 100 = 57.43%. Missing or Mixed predictions count as errors because the selected gold cases expect one label.
- Strong/Weak Positive collapse to Positive and Strong/Weak Negative to Negative for this three-label metric. We do not claim independently evaluated five-band accuracy.

### Answer to faculty

> Polarity accuracy measures how often the predicted sentiment direction matches the human annotation. On 148 eligible sentence-category cases, SentiWordNet correctly labels 72 and Hybrid correctly labels 85, giving 48.65% and 57.43%.

## Q4. Explain the SemEval pair-F1 and Trip-MA deep learning improvement statement.

**Paper section:** Abstract

### Key explanation

- A category-polarity pair is an item such as (Room, Positive) or (Service, Negative), associated with a particular sentence or segment. Both category and polarity must match the gold annotation.
- Precision = TP/(TP+FP); recall = TP/(TP+FN); F1 = 2PR/(P+R) = 2TP/(2TP+FP+FN). TP is a correct predicted pair, FP an extra or wrong pair, and FN a missing gold pair.
- SemEval pair evaluation has 162 gold pairs. SentiWordNet matches 81 of 112 predictions: F1 = 2 x 81/(112+162) = 0.5912. Hybrid matches 99 of 145 predictions: F1 = 2 x 99/(145+162) = 0.6450. Its 148-case polarity accuracy is a separate calculation.
- Trip-MA is a separate mapped experiment on 1,474 annotated test segments. Across all segments, Hybrid matches 314 pairs and the selective pipeline matches 367: micro-F1 rises from 0.4184 to 0.4993, an increase of 0.0809 or 8.09 F1 percentage points.
- Of those segments, 1,113 are Partial/Unsupported and enter DL; the other 361 outputs remain unchanged. Within the routed subset, correct pairs rise from 127 to 180 and F1 rises from 0.3261 to 0.4813: 15.52 F1 percentage points.
- Micro-F1 pools pair counts before calculation; it is not average review F1 or the percentage of correctly analysed reviews. F1 of 0.4993 does not mean 49.93% review accuracy.
- The cohorts and category mappings differ, so SemEval SentiWordNet scores cannot be directly ranked against Trip-MA DL scores. Results show recovery in this exploratory evaluation, not guaranteed correction of every Partial review; Facilities F1 declines.

### Answer to faculty

> On SemEval, Hybrid improves sentiment-label accuracy and category-polarity pair recovery over SentiWordNet. Separately, on Trip-MA, sending only unresolved Hybrid segments to our fine-tuned model raises overall pair-F1 from 0.4184 to 0.4993; within the routed subset it rises from 0.3261 to 0.4813. These are F1 improvements, not whole-review accuracy percentages.

## Q5. What is a source span? Explain with an example.

**Paper section:** Introduction

### Key explanation

- A source span records the start and end character positions of a piece of evidence in the original submitted review. It is not a sentiment score.
- For "The room was clean.", zero-based span [4, 8) identifies "room" and [13, 18) identifies "clean". The start is included; the end is excluded. The full sentence has span [0, 19).
- Offsets allow the interface and exported evidence to show which words supported a token, aspect, opinion, clause or diagnostic. Working copies must remain aligned to the original text.
- Lexical pipelines retain token/opinion/context spans. The DL stage supplies original sentence evidence, not independently verified exact target/opinion spans.

### Answer to faculty

> A source span is the location of supporting text in the original review, stored as start and end character positions. It lets us trace a prediction to its evidence and highlight the exact text. The DL component retains sentence evidence rather than claiming exact opinion extraction.

## Q6. What different dictionaries, grammars and aspect mappings do the two pipelines use?

**Paper section:** Introduction

### Key explanation

- Dictionary means a collection of recognized words/phrases and associated information. Grammar means rules for connecting words into aspect-opinion structures. Aspect mapping means assigning an identified target to a hotel category.
- SentiWordNet pipeline: resources/domain_expanded.json defines 772 aspect phrases, 21,181 opinion entries, 752 aliases and modifier/compatibility rules. resources/sentiwordnet_expanded.tsv supplies native synset positive/negative scores. Our project dictionary chooses a synset; SentiWordNet itself does not choose hotel categories.
- Hybrid pipeline: resources/hybrid_domain.json plus resources/hybrid_vocabulary.json supply a separate 671-phrase aspect inventory and 497-form lexical-alias catalog. VADER has its own valence lexicon and contextual rules; TextBlob Pattern sentiment has its own polarity/subjectivity lexicon. Scoring-copy aliases are explicit project additions, not new native lexicon entries.
- Baseline grammar uses our token classes, predictive parser and bounded recovery rules in lexer.py, parser.py and expanded_parser.py. It handles patterns such as "The room was spacious", "spacious room", coordinated targets, supported opinion verbs and explicit absence. It does not parse unrestricted English.
- Hybrid grammar uses TextBlob PatternParser for POS tags and shallow phrase chunks. Our hybrid_nlp.py segments clauses, matches aspect phrases and attaches preceding adjectives, following predicates and supported opinion verbs. VADER supplies sentiment rules, not this grammatical front end. The two pipelines do not share a parser.
- For "The room was spacious", the baseline matches configured ASPECT and OPINION entries and parses their relationship. Hybrid uses noun/adjective/POS/chunk evidence plus our attachment rules, then scores the extracted context using its sentiment tools. Recognition does not guarantee either tool has a usable score.
- Examples of configured aspect mappings include room -> Room, breakfast -> Food and air conditioning -> Facilities. These are project ontology choices rather than categories learned by SentiWordNet or automatically supplied by VADER.
- In "The room was clean", the baseline can return category Room with issue Cleanliness: category and issue are different fields. Hybrid also recognizes room as Room; a human benchmark may instead categorize room hygiene under Cleanliness. Shared category names therefore do not guarantee identical annotation conventions.
- The paper compares complete pipelines whose vocabularies, extraction rules and category conventions differ. Its performance difference cannot be attributed solely to one sentiment dictionary.

### Answer to faculty

> The baseline uses our controlled hotel vocabulary, compiler parser and SentiWordNet synset scores. Hybrid uses a separate aspect dictionary, TextBlob grammatical parsing, our attachment rules and VADER/TextBlob sentiment resources. Both use hotel category mappings, but their extraction and mapping decisions can differ. We therefore compare full pipelines, not just scoring dictionaries.

## Q7. What are measured recovery and regression?

**Paper section:** Introduction

### Key explanation

- Recovery means a correct gold category-polarity pair appears after DL reanalysis when Hybrid previously missed it. Regression means a pair Hybrid previously predicted correctly is lost after replacement. These are measured by comparing both outputs with human annotations for the same segment.
- Illustrative recovery: human gold (Service, Negative), Hybrid missing, DL (Service, Negative). Illustrative regression: human gold (Room, Positive), Hybrid (Room, Positive), replacement loses or changes that prediction. These examples explain definitions; they are not additional measured test cases.
- The saved Trip-MA comparison reports 97 newly correct pairs and 44 previously correct pairs lost: net correct-pair gain = 97 - 44 = 53. Overall matched pairs rise from 314 to 367.
- The selected pipeline also introduces 114 false pairs and removes 198 previous false pairs. F1 accounts for both missed gold pairs and incorrect predictions; it is not determined by net correct-pair gain alone.
- Overall pair-F1 rises from 0.4184 to 0.4993, but Facilities F1 falls from 0.1854 to 0.1389. Higher overall F1 does not mean every category or routed review improves.
- These are category-polarity pair counts, not numbers of corrected whole reviews. A review or segment can contain multiple pairs. Complete status is not an independent correctness label.

### Answer to faculty

> We measure recovery as newly correct category-sentiment pairs after DL, and regression as previously correct pairs lost after replacement. On Trip-MA we gained 97 correct pairs and lost 44, a net gain of 53. We report both improvements and harms rather than assuming DL always helps.

## Q8. Explain the full architecture diagram, every stage and block, for faculty questioning.

**Paper section:** Architecture

### Key explanation

- Five online processing stages are supported by separate offline training and evaluation flows.
- SentiWordNet and Hybrid are independent lexical pipelines. Only Partial/Unsupported Hybrid reviews enter independent neural reanalysis.
- See the detailed block-by-block explanation below, including inputs, outputs, examples and short viva answers.

### How to introduce the architecture

We have five processing stages, with two independent lexical pipelines and a selective neural follow-up. A preprocesses the review. B extracts grammatical structures, C attaches categories and scores sentiment, and D produces records, aggregates and processing status. The baseline uses our compiler parser and SentiWordNet. Hybrid uses Pattern grammar with VADER/TextBlob sentiment. Only Partial/Unsupported Hybrid reviews enter E, which independently rereads their original sentences using fine-tuned MiniLM. Offline training and evaluation are supporting flows, not additional online review-processing stages.

The detailed retention/failure decision section was removed from the drawing for presentation. The implementation still retains Complete Hybrid results and preserves invalid/component failures; its behavior did not change.

### A. Preprocessing and Validation

**Input:** original review text or CSV rows. **Output:** validated or flagged rows, identities, original text and source-aligned working views.

| Block | Process and explanation |
|---|---|
| SemEval Hotels | 266 annotated sentences provide review text for lexical comparison; labels are kept separately for evaluation. Only 148 eligible sentence-category cases enter the polarity-accuracy calculation. |
| Booking Sample | The 200-review real sample supplies unlabelled text for processing-coverage testing. |
| Booking Italy | The cleaned corpus contains 3,089 real reviews; the 500-review demo is a subset, not an additional independent corpus. |
| Trip-MA Test | The 1,474 held-out prepared text segments supply inference inputs for the Hybrid-versus-selective-DL experiment. Test gold labels go only to evaluation. Earlier development inspection makes the reported experiment exploratory. |
| UTF-8 Decoding | Convert file bytes into readable Unicode text, rejecting invalid encoding rather than inventing text. CSV parsing supports quoted commas and multiline reviews. |
| Field Validation | Identify ID/review fields and check required headers, row structure, blank text and limits. Current upload limits are 10 MiB, 1,000 rows and 10,000 characters per review. File-level failures are rejected; row-level problems remain visible. |
| Duplicate Flagging | Mark repeated text or IDs while retaining the submitted rows. This differs from offline dataset preparation, which removed exact duplicate bodies. |
| Source Retention | Preserve original wording, row identity and character offsets so outputs can be traced to evidence. |
| Working Copies | Create appropriate processing views without destroying source evidence. Baseline matching normalizes selected forms; Hybrid retains casing/punctuation for sentiment rules and logs scoring-copy aliases. |

**Example:** A CSV contains `1,"The room was spacious, but breakfast was cold."`. The comma inside quotes stays inside one review cell. Both independent pipelines receive the same retained review, with its row ID.

**Viva answer:** “Preprocessing validates and preserves the input before analysis. It keeps every submitted row identifiable, flags duplicates and creates working views while retaining the original text and source offsets.”

### B. Lexical and Grammatical Analysis

**Input:** source-aligned review views. **Output:** baseline tokens/AST or independent Hybrid grammatical candidates, with diagnostics.

| SentiWordNet path block | Process and example |
|---|---|
| Token Scanning | Split text into tokens and preserve token kind, original text and offsets. `room` can be ASPECT, `spacious` OPINION and `not` NEGATION. |
| Phrase Matching | Match configured multiword entries using longest matching; recognize `air conditioning` as one aspect rather than unrelated words. Aliases and configured contractions are resolved with evidence. |
| Predictive Parsing | Apply our supported grammar and bounded recovery rules to link targets, opinions and modifiers. `The room was spacious` connects room and spacious; supported coordinated targets can share a predicate. The AST is a structured record of these relationships. Unsupported language retains diagnostics. |

| Independent Hybrid block | Process and example |
|---|---|
| Pattern Parsing | TextBlob PatternParser supplies POS tags and shallow grammatical annotations. `room` is a noun and `spacious` an adjective. This is not unrestricted semantic understanding or a dependency parser. |
| Phrase Chunking | Group tokens into shallow noun, verb, adjective and preposition phrases. For example, a noun phrase can include `the spacious room`. |
| Opinion Attachment | Our rules connect opinions to separately matched hotel targets, using position, chunks, supported opinion verbs and limited subject inheritance. In `spacious room`, the adjective attaches forward; in `the room was spacious`, it attaches backward. Contrast segmentation helps separate room praise from a breakfast complaint. |

**Viva answer:** “The baseline uses our token vocabulary and compiler parser. Hybrid independently uses TextBlob grammatical annotations and our attachment rules. Both seek aspect-opinion relationships, but they do not share a parser or opinion vocabulary.”

### C. Semantic Attachment and Scoring

**Input:** baseline AST clauses or Hybrid candidates. **Output:** categorized opinions and recorded sentiment evidence.

| SentiWordNet path block | Process and example |
|---|---|
| Category Mapping | Map the target to a configured hotel category and choose an issue. `room` maps to Room; `clean` can describe a Cleanliness issue within Room. Check aspect/opinion/modifier compatibility. These are project rules, not categories supplied by SentiWordNet. |
| Sense Lookup | Select the configured WordNet sense for the opinion. Hotel-specific configured senses take precedence; expanded entries otherwise use first lemma-ranked senses. This is not general contextual word-sense disambiguation. |
| P/N Scoring | Read native SentiWordNet positive P and negative N values. Compute lexical sentiment L=P-N and objectivity O=1-P-N. Retain the sense, scores and evidence. |

| Hybrid block | Process and example |
|---|---|
| Aspect Mapping | Map the independently extracted target using Hybrid's own aspect inventory, for example breakfast to Food and air conditioning to Facilities. |
| VADER + TextBlob | Score the extracted aspect context using VADER compound and TextBlob polarity; retain TextBlob subjectivity and assessment evidence. Separate whole-review scores are also computed. Subjectivity is not confidence. |
| Evidence Fusion | With evidence from both tools, average effective scores using equal weights; if only one tool has usable evidence, retain that score. With neither, preserve Unavailable rather than inventing Neutral. Explicit alias replacements affect scoring copies only and remain visible. |

**Fusion illustration, not a measured review result:** VADER +0.6 and TextBlob +0.4 with usable evidence give `(0.6+0.4)/2=+0.5`, before any applicable project context rule.

**Viva answer:** “Semantic analysis determines what each opinion refers to and obtains its sentiment evidence. Baseline uses selected SentiWordNet sense scores; Hybrid independently scores its contexts with VADER and TextBlob, then combines available evidence.”

### D. Adjustment and Final Records

**Input:** categorized opinions and raw/effective sentiment evidence. **Output:** final opinion records, review/category aggregates and processing diagnostics/status.

| SentiWordNet path block | Process and example |
|---|---|
| Domain Rules | Apply documented hotel-specific sense preferences or calibrated values where configured. All adjustments retain rule IDs/reasons. This prevents treating native dictionary scores and project adjustments as the same evidence. |
| Scoped Negation | Apply the negation attached to the parsed opinion, once. `not clean` reverses the adjusted opinion under the baseline's rule. Degree multipliers such as `very` are also applied. Negation is limited by parsed scope, not the entire review. |
| Aspect Records | Clip the score to [-1,1], assign polarity/strength and create structured records containing category, issue, opinion, source evidence and trace. IR means intermediate representation: structured analysis records, not machine code. |

| Hybrid block | Process and example |
|---|---|
| Context Rules | Use the tools' contextual sentiment and explicit hotel rules. The project equipment-not-functioning rule can score `air conditioning was not working` at -0.70. Do not apply the baseline's extra negation flip again after VADER/TextBlob have handled context. |
| Score Aggregation | Retain individual context scores and calculate permitted review/category summaries. Lexical review means average available aspect scores subject to the method's completeness policy. Dashboard category means average within each review, then across reviews. Opposing positive/negative evidence retains Mixed, even if the mean is near zero. |
| Status Assignment | Complete: no detected unresolved/scope issue and all required candidates scored. Partial: useful scored aspects coexist with unresolved/unsupported evidence. Unsupported: no scored aspect. Invalid input and component errors retain failure information. Complete is not a human-verified correctness label. |

**Five lexical bands:** Strong Negative `s <= -0.50`; Weak Negative `-0.50 < s < -0.05`; Neutral `-0.05 <= s <= +0.05`; Weak Positive `+0.05 < s < +0.50`; Strong Positive `s >= +0.50`.

**Viva answer:** “This stage applies traceable domain and contextual adjustments, produces final aspect records and aggregates, and assigns processing status. Only Partial/Unsupported Hybrid reviews are eligible for neural reanalysis; the SentiWordNet result is retained separately for comparison.”

### E. Independent Deep Learning Reanalysis

**Input:** every original sentence of an eligible Partial/Unsupported Hybrid review, a frozen trained model and frozen validation-selected thresholds. **Output:** independently accepted category-sentiment predictions or abstention, with sentence evidence.

| Block | Process and explanation |
|---|---|
| Original Sentences | Reread the original routed review and split it into sentences while retaining offsets. The model receives all original sentences, not just unmatched words and not Hybrid's scores. |
| Category Queries | Pair each sentence with each of eight category descriptions: Room, Cleanliness, Service, Food, Facilities, Excluded, Other and NotRelated. The last three are background groups. Staff is pooled into Service under DL training labels. |
| Fine-tuned MiniLM | A shared encoder represents each sentence/category pair; a shared classification head predicts Absent, Negative, Neutral/Mixed or Positive. Both encoder and head were fine-tuned, so this is DL classification rather than a fixed embedding plus a shallow classifier or a generative chatbot. |
| Threshold Checks | Accept an in-scope non-Absent prediction only if it meets that category's validation-selected probability threshold. Background groups are not emitted as hotel categories. Overlength pairs remain unavailable rather than being silently truncated; low-evidence cases can abstain. |
| Selected Result | Use the independent neural result as the selected analysis for the routed review, including abstention. Keep the original Hybrid output inspectable rather than appending new neural opinions to it. Aggregate accepted sentence evidence by category, then across categories for a review direction index when available. |

For accepted positive/negative predictions the direction index uses `(p_positive-p_negative)/(p_positive+p_negative)`. It expresses relative model belief, not calibrated sentiment intensity. Neutral/Mixed predictions leave the aggregate index unavailable under the current policy; the DL model was not trained on five strong/weak intensity classes.

**Viva answer:** “Only unresolved Hybrid reviews enter the fifth stage. MiniLM reads their original sentences paired with category queries and predicts sentiment or absence. Validation-selected thresholds filter the results, and the selected output remains separate from the original Hybrid evidence.”

### Offline DL Training

This happens before deployment, not every time a review is uploaded.

| Block | Process and explanation |
|---|---|
| Trip-MA Train | 2,038 usable human-labelled segments provide supervised training examples. Eight queries per segment produce 16,304 sentence-category pairs, not 16,304 independent reviews. |
| Category-pair Fine-tuning | Update the pretrained encoder and four-state classification head using labelled pairs and weighted cross-entropy. The reported run used three epochs on RTX 2050. |
| Trip-MA Validation | 602 separate segments support model/checkpoint and threshold selection. They do not supply gradient updates. |
| Checkpoint + Threshold Selection | Select the checkpoint and category thresholds using validation performance rather than choosing them from test performance. The reported run selected epoch 3. |
| Frozen Model + Thresholds | Save the learned parameters, tokenizer, category queries, thresholds and integrity metadata. These are reused during inference; frozen here means held fixed for deployment/evaluation, not that the encoder was never trained. |

**Viva answer:** “We fine-tune on human-labelled training pairs, choose the checkpoint and thresholds on validation data, then deploy the saved model. Test annotations never enter training or validation selection in this run.”

### Evaluation and diagram notation

| Block | Process and explanation |
|---|---|
| Pipeline Results | Collect method-labelled outputs. SentiWordNet remains a comparator; the selected Hybrid/DL pipeline retains Complete Hybrid outputs and replaces routed outputs with the independent model result. |
| SemEval Gold | Human annotations provide ground truth for the mapped SentiWordNet-versus-Hybrid experiment. |
| Trip-MA Test Gold | Human annotations provide ground truth for the separate Hybrid-versus-selective-DL experiment on 1,474 segments. |
| Matched-cohort Metric Calculation | Compare predictions with the appropriate gold for the same input segment and declared category mapping. Do not mix the two datasets into one ranking or treat unlabelled Booking coverage as accuracy. |
| Precision / Recall / F1 / Accuracy / Coverage | Precision measures correctness of predicted pairs; recall measures gold pairs recovered; F1 balances both. Polarity accuracy measures correct eligible sentiment labels. Coverage measures whether outputs were produced, not whether they are correct. |

Rectangles represent processing; parallelograms represent datasets/data outputs. Solid arrows represent data flow. Dashed arrows from the frozen model represent model/threshold configuration. Dashed outer rectangles group processing stages. Gray fills identify existing library components; white fills identify project processing/integration. Gray does not mean a stronger or more accurate result.

**One-minute architecture answer:** “We preserve and validate each review, then analyze it through two independent paths. The baseline uses our compiler grammar and SentiWordNet; Hybrid uses Pattern grammar and VADER/TextBlob. Both produce traceable category-sentiment records. Hybrid's processing status decides whether neural reanalysis is needed. Only Partial/Unsupported reviews are independently reread by fine-tuned MiniLM, using category queries and validation-selected thresholds. Training uses human Trip-MA labels offline, while separate human test annotations measure performance. Original evidence, abstentions and regressions remain visible.”



### Answer to faculty

> We validate and preserve review text, independently extract and score aspects through SentiWordNet and Hybrid, then route only unresolved Hybrid reviews to fine-tuned MiniLM. Training and validation occur offline; human gold annotations are used separately for evaluation. Every method retains its evidence and limitations.

## Q9. Explain the entire report and map the paper sections and algorithms to code files.

**Paper section:** Entire paper and implementation

### Key explanation

- The full guide covers the title, abstract, introduction, literature, five proposed stages, six equations, datasets, training, metrics, results and limitations.
- Open docs/paper-and-code-viva-guide.md for the detailed section explanations, function names and file-to-purpose table.
- For current DL training open dl_pair.py::train, not the earlier routed_training.py::train.
- To explain code, state its input, main decisions, output and limitations.

### Answer to faculty

> The report compares two independent lexical pipelines and selectively applies fine-tuned MiniLM to unresolved Hybrid reviews. Code separates input validation, extraction, scoring, routing, training and evaluation, so every reported claim can be traced to functions and saved outputs.

## Evidence used

- Implementation: `hotel_compiler/models.py`, `lexer.py`, `parser.py`, `expanded_parser.py`, `semantics.py`, `hybrid_nlp.py`, `hybrid_vocabulary.py`, `hybrid.py`, `dl_pair.py`.
- Dictionaries: `hotel_compiler/resources/domain_expanded.json`, `sentiwordnet_expanded.tsv`, `hybrid_domain.json`, `hybrid_vocabulary.json`.
- Results: `output/experiments/2026-10-21/expanded-sentiwordnet-release/semeval-development/metrics.csv`; `output/neural/2026-10-23-dl-pair-evaluation/metrics.csv` and `change_summary.json`.
