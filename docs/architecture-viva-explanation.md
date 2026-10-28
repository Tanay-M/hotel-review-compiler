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
