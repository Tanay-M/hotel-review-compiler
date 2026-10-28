# Auditable Aspect Sentiment Analysis of Hotel Reviews with Selective Deep Learning Reanalysis

Authors: Tanay Mohta and Aditya Rawat

## Abstract

Hotel reviews contain aspect-specific opinions that lexical rules can leave unresolved. We integrate a SentiWordNet compiler baseline, an independent VADER-TextBlob hybrid, and selective deep learning (DL) reanalysis. Only Partial or Unsupported hybrid reviews enter a category-conditioned MiniLM classifier; Complete results are retained. Both encoder and neural head are fine-tuned using human-labelled hotel sentences. On a declared SemEval-2015 hotel adaptation with 148 eligible sentence-category cases, SentiWordNet and Hybrid achieve 48.65% and 57.43% polarity accuracy and 0.5912 and 0.6450 pair-F1. In a separate mapped Trip-MA experiment, DL routing raises category-polarity micro-F1 from 0.4184 to 0.4993 across 1,474 test segments and from 0.3261 to 0.4813 on 1,113 unresolved segments. Four mapped categories improve, while Facilities declines. Of 456 routed reviews in a 500-review real Booking demonstration, 383 receive accepted categories; these unlabelled counts measure coverage. The applied contribution is independent, evidence-preserving reanalysis with measured recovery and explicit abstentions. Previously inspected benchmarks, approximate category mappings and merged Neutral/Mixed supervision limit generalization; results remain exploratory.

Keywords: aspect sentiment; hotel reviews; SentiWordNet; VADER; TextBlob; MiniLM; selective deep learning.

## I. Introduction

Aspect-based sentiment analysis links opinions to services or attributes [1]; document polarity [2] can conceal conflicting room and staff experiences. Operational systems must also identify language they cannot reliably interpret.

We compare SentiWordNet compiler processing [3] with an independent VADER-TextBlob hybrid [4], [5] across six hotel categories. Both retain source spans, scoring evidence and diagnostics. Different dictionaries, grammars and aspect mappings make this a pipeline comparison. Adapted SemEval annotations [6] supply category/polarity gold.

For unresolved reviews, a fine-tuned transformer independently reads the original text and replaces the selected Hybrid result. Complete results and original lexical evidence are retained. Our applied contribution is source-preserving integration with measured recovery and regression; sentence-pair classification and fallback routing are established techniques.

## II. Literature Survey

### A. Lexical Resources and Contextual Valence

Hatzivassiloglou and McKeown [7] used conjunction constraints for adjective orientation; Turney [8] used phrase-level semantic association. Wilson et al. [9] separated prior and contextual polarity. SO-CAL [10] models negation and intensification. SentiWordNet [11], [3] supplies synset sentiment but requires sense selection. VADER [4] adds valence rules; Pattern [5] supplies TextBlob's grammatical and sentiment facilities. NRC-Canada [12] uses lexical features in supervised classification. Intensity evaluation [13] and adjective ranking [14] motivate distinguishing descriptive score bands from validated strength classes.

### B. Aspect Extraction and Targeted Sentiment

Double propagation [15] and subjective-pattern bootstrapping [16] recover targets or opinions through linguistic relations. SemEval-2014/2015/2016 [17], [6], [18] formalize categories, targets and polarity. Target-dependent LSTMs [19], attention [20], recursive models [21], gated convolutions [22] and graph convolutions [23] provide learned alternatives. Auxiliary-sentence BERT [24] motivates our category-conditioned pairs; review post-training [25] supplies adaptation context. We use these ideas for selective local reanalysis, without reproducing their benchmark claims.

A supplied aspect need not occur in the text; our category query therefore includes Absent. Lexical attachments remain separately inspectable, while neural category predictions are not presented as grammar-derived target spans.

### C. Representation and Evaluation Considerations

Subjectivity extraction [26], recursive composition [27] and convolutional classification [28] illustrate contextual representation. Surveys [29], [30] distinguish extraction, category detection and polarity metrics. We fine-tune all-MiniLM-L6-v2 [31], rather than performing distillation. Trip-MA [32] supplies human hotel annotations, including implicit opinions, but merges Neutral/Mixed and differs in taxonomy. We therefore report polarity accuracy, category-polarity F1, coverage and abstention separately.

Our contribution integrates transparent lexical processing and learned reanalysis, rather than introducing a new sentiment representation. Comparisons execute local methods on matched inputs; published scores from different corpora or label spaces are not treated as a common ranking.

## III. Proposed Systems

Figure 1 presents five stages: preprocessing, lexical/grammatical analysis, semantic scoring, adjustment/reporting, and independent DL reanalysis. The SentiWordNet and Hybrid paths are independent after validation. Only the Hybrid status controls DL routing. Dataset labels enter offline training or evaluation; inference receives review text without gold labels.

{{WIDEFIG:architecture_approved|Fig. 1. Full architecture with dataset blocks. Review text feeds independent SentiWordNet and Hybrid paths; only Partial/Unsupported Hybrid reviews enter DL. Trip-MA training/validation labels support offline learning, while gold test annotations enter evaluation only.}}

### A. Preprocessing and Validation

Runtime input is text or UTF-8 CSV with serial ID and review. Validation checks headers, field structure, blank content and size limits, supporting quoted commas and multiline cells. Every row retains identity, original text and validation issues; duplicates are flagged rather than dropped. Working copies preserve offsets, spelling, punctuation and negation. Offline Booking cleaning removes missing markers, controls, excess whitespace and exact duplicate bodies without rewriting reviews or filtering for successful predictions.

The handoff is a retained row containing its ID, original review and validation findings. Later stages receive source-aligned working views rather than destructive replacements: case and punctuation remain available to VADER, and character spans still identify evidence in the submitted review. This separates dataset preparation from runtime analysis and distinguishes an invalid CSV row from valid language that an analyzer cannot interpret.

{{ALG:1}}

### B. Lexical and Grammatical Analysis

SentiWordNet longest-matches 772 aspect phrases, 21,181 opinion entries and 752 aliases. Its scanner preserves token classes/spans and expands configured contractions. Predictive parsing and bounded recovery handle attributive/predicate opinions, coordinated targets, possession, selected opinion verbs and unique-target references; ambiguity retains diagnostics. Explicit absence such as no hot water becomes negated availability.

Hybrid does not call that lexer, parser or opinion list. TextBlob PatternParser [33] provides POS and shallow noun/verb/adjective/preposition chunks, not dependency parsing. Original-token alignment preserves spans. Sentence/contrast segmentation and directional attachment produce independent opinion candidates, even when a sentiment tool cannot score them. Candidate extraction and score availability therefore remain distinct.

{{ALG:2}}

### C. Semantic Attachment and Sentiment Evidence

SentiWordNet maps targets to configured categories/issues. Its resource packages 14,311 unchanged native synsets supporting 21,181 entries. Explicit hotel senses take precedence; added lemmas use first lemma-ranked senses, not contextual disambiguation. The scorer retains positive P, negative N, objective 1-P-N and lexical polarity P-N. A recorded domain value D defaults to P-N; degree m and scoped negation n yield (1).

{{EQ:baseline}}

Hybrid longest-matches its own 671 aspect phrases and attaches attributive opinions forward, predicates backward and opinion verbs to objects, sharing valid coordinated subjects. Unique-target inheritance is bounded. Price/Value/Location remain outside scope. VADER supplies compound sentiment; TextBlob supplies polarity, subjectivity and assessed expressions. Subjectivity is not confidence. Both score extracted contexts and, separately, whole reviews. A guarded 497-form catalog aliases native-unknown expressions only in scoring copies; original text and native/effective outputs remain available.

For effective scores V and T, evidence flags eV and eT give (2). With fixed w=0.5, two supported tools are averaged; one supported tool retains its value. No evidence means Unavailable, not Neutral. Component errors remain errors. Domain rules and lexical aliases are project logic, not new native library scores.

{{EQ:fusion}}

{{ALG:3}}

### D. Adjustment and Final Records

SentiWordNet applies recorded domain, degree and negation adjustments. Hybrid uses its libraries' contextual rules without repeating the SentiWordNet multiplier; explicit hotel rules may override fusion for functional failure, missing hot water, hygiene or service responsiveness. Opposing rule signs prevent an override. Five lexical bands use boundaries -0.5, -0.05, +0.05 and +0.5: Strong Negative, Weak Negative, Neutral, Weak Positive and Strong Positive. Missing scores remain unavailable; opposing opinions retain Mixed.

Equation (3) averages retained aspect scores. SentiWordNet Partial means describe recognized opinions only; Hybrid exposes its aspect mean only when all extracted contexts are scored. Dashboard category means average within each review, then across reviews, giving reviews equal weight. Whole-text scores remain separate.

{{EQ:mean}}

Complete means no detected unresolved/scope issue and all required candidates scored; it is not human-verified correctness. Partial retains scored opinions with diagnostics; Unsupported has no scored aspect. Invalid rows and processing errors retain failures. Final records preserve category, context, available scores/bands and source spans.

{{ALG:4}}

### E. Independent Deep Learning Reanalysis

Only Partial/Unsupported Hybrid reviews enter DL; Complete reviews and validation/component failures do not. The model processes every original sentence of each routed review, without using hybrid matches or scores. For sentence u and category description q_c, one MiniLM encoder and shared four-state neural head produce (4). Eight queries cover Room, Cleanliness, Service, Food, Facilities and three background groups: Excluded, Other and NotRelated. Staff is pooled into Service under the training source; Location/Value are Excluded. States are Absent, Negative, Neutral/Mixed and Positive.

{{EQ:dl_prob}}

Both encoder and head minimize weighted cross-entropy (5). For minibatch B, y_j is the target state and w_y is proportional to square-root inverse state frequency, normalized to mean one. Categories not annotated under the source scheme become Absent. Only human source annotations supply supervision.

The eight queries share parameters, allowing multiple categories per sentence without eight independent transformers. Each admitted segment yields eight supervised pairs. Training contains 14,318 Absent, 1,244 Positive, 466 Negative and 276 Neutral/Mixed pairs; weighting reduces absence dominance. The loss divides by summed minibatch target weights. These are pair counts rather than independent reviews; no oversampled copies are reported as additional organic data.

{{EQ:dl_loss}}

The highest-probability non-Absent state is emitted when it meets its category threshold. Validation selects thresholds from {0.25, 0.35, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90}, with higher values winning ties. A sentence whose longest category pair exceeds 160 WordPiece tokens remains unavailable, without truncation. Background predictions are not reported as hotel categories.

The independent DL result becomes the selected analysis, including abstention; it is not unioned with hybrid opinions or silently replaced with Neutral. Original Hybrid evidence remains accessible. Accepted Positive/Negative probabilities give direction index (6), describing relative belief rather than calibrated intensity. Category indices average sentence indices, then receive equal weight in the review mean. Merged Neutral/Mixed predictions leave aggregate indices unavailable; opposing labels retain Mixed. The model supplies sentence evidence, not exact target/opinion spans or trained strong/weak labels.

{{EQ:dl_direction}}

{{ALG:5}}

## IV. Results and Implementation

### A. Dataset Description

Table I separates annotated evaluation/training sources from unlabelled coverage cohorts. Booking's 200-review sample comes from the published 515,738-record source [34] with documented random eligibility/deduplication, not grammar-success filtering. Crawlfeeds' Italy export [35] has 4,367 rows; removing 1,266 empty bodies and 12 exact duplicates leaves 3,089 unique reviews. Original positive/negative body fields are joined, preserving wording; titles/ratings are excluded. The seed-172026 demo sample of 500 is nested within that corpus and is not independent evidence. No review is invented or paraphrased.

{{TABLE:datasets}}

SemEval contains 30 reviews, 266 sentences and 339 human opinions. The declared six-category crosswalk excludes 141 annotations, leaving 198 mapped annotations and 162 unique category-polarity pairs; 148 unambiguous sentence-category cases support classification. Staff predictions collapse to Service; price/location are excluded. This is a coarse mapping, not official target-span evaluation.

Trip-MA's release contains 258 training and 111 test reviews. We remove 36 training reviews sharing test hotels, derive validation by a fixed hotel hash, and exclude cross-split/conflicting text duplicates. Prepared train/validation/test contain 2,040/602/1,474 segments from 180/42/111 reviews and 157/39/103 hotels. Hotel/review/text identities are disjoint. Conversion detokenizes original source surface tokens, retaining serialization and hashes. Two long training segments are excluded: 2,038 usable segments yield 16,304 category pairs. Validation/test denominators retain all rows. SERVICE/CHECKIN pool into Service; BUILDING/BUSINESS map approximately to Facilities; x/ix remain Neutral/Mixed. Its labels differ from SemEval, requiring separate experiments.

In the SemEval crosswalk, ROOMS maps to Room, FACILITIES/ROOMS_AMENITIES to Facilities, FOOD_DRINKS to Food, SERVICE to Service and HOTEL cleanliness to Cleanliness. Conflicting coarse-category annotations remain in pair evaluation but outside single-polarity classification. For DL, original polarity codes retain explicit and implicit opinions. No synthetic review, star-rating proxy or system-generated prediction is treated as human aspect annotation.

### B. Preprocessing and Validation Implementation

All retained cohorts pass validation and source reconstruction. The 3,089-review corpus runs in upload-sized parts of 1,000/1,000/1,000/89 with order preserved. CSV exports retain every submitted row; separate files preserve opinions, diagnostics and hashes. Source correspondence verifies dataset bytes, not reviewer authenticity. The local implementation uses no external LLM service. Saved experiment settings and input/resource hashes support reproduction; 243 software tests check contracts, not accuracy.

### C. Lexical and Grammatical Implementation

On 200 random reviews, SentiWordNet emits 516 opinions and Hybrid 626 contexts; on the 500-review Italy subset, counts are 1,307 and 2,166. Candidate definitions differ, so larger counts alone do not show correct attachment. The latter run retains 26,236 SentiWordNet tokens, 1,559 clauses and 26,773 Pattern POS/chunk tokens for inspection. Hybrid uses VADER 3.3.2, TextBlob 0.19.0 and NLTK 3.10.3.

### D. Semantic Attachment and Scoring Implementation

The benchmark sentence "The rooms were quiet." receives positive Room sentiment from SentiWordNet's hotel preference and +0.45 from Hybrid's room_quiet rule. Native component scores and overrides remain distinct. The authored example "The air conditioning wasn't working." demonstrates Hybrid's Facilities equipment_not_functioning rule (-0.70), not an additional real-data accuracy case. Broad SentiWordNet coverage can still select neutral or inappropriate senses, while grammatical extraction can lack usable sentiment evidence.

### E. Adjustment and Reporting Implementation

Table II reports Complete (C), Partial (P) and Unsupported (U) counts on real cohorts. Any-aspect coverage reaches 81.42%/87.41% on the full Italy corpus, but only 1.65%/7.96% satisfy SentiWordNet/Hybrid completeness heuristics. These are processing outcomes without aspect gold. A near-zero mean does not erase opposing opinions, and whole-review sentiment never fills missing aspect predictions.

{{TABLE:compact_coverage}}

### F. Deep Learning Training and Execution

The sequence classifier initializes from all-MiniLM-L6-v2 revision 1110a243fdf4706b3f48f1d95db1a4f5529b4d41. Both encoder and head train for three epochs; validation F1 progresses 0.4052/0.4764/0.5037 and selects epoch 3. AdamW uses encoder/head learning rates 2e-5/2e-4, decay 0.01, 10% warmup, linear decay, clipping 1.0 and seed 172026. Batch 8 with accumulation 2 gives effective batch 16 over 3,057 updates. Training/validation take 248.0 seconds on RTX 2050, with 510.1 MiB peak allocated tensor memory, excluding driver/process totals. Encoder hashes verify updates. This is one run with no AI-labelled supervision.

For 500 real Booking reviews, 44 Complete outputs retain Hybrid and 456 unresolved reviews enter DL. Of these, 383 obtain accepted categories and 73 abstain, with no model errors. These counts are coverage, not confirmed corrections. The authored complaint "We waited two hours before anyone checked us in." changes from Hybrid Unsupported to DL Service/Negative (direction index approximately -0.7427); it illustrates behavior rather than adding test gold.

## V. Performance and Metrics

### A. Evaluation Protocol

SemEval all-case accuracy is C/N for N=148 eligible cases; coverage is S/N for S single-polarity predictions. Missing/Mixed predictions count as errors; strong/weak bands collapse to polarity sign. Conditional accuracy C/S uses unequal selected subsets. Per-class precision TP/(TP+FP), recall TP/(TP+FN) and F1=2PR/(P+R) assign zero when denominators vanish; macro-F1 equally averages Positive, Negative and Neutral. Accuracy intervals resample the 30 parent reviews 1,000 times.

Joint pair precision/recall divide exact category-polarity matches by predicted/gold pairs; micro-F1 pools counts. Exact segment match requires identical sets, including empty sets, and is sensitive to background-heavy data. DL checkpoint and thresholds are frozen using validation before this run's test scoring. Each benchmark retains its own mapping and denominators; Booking coverage cannot supply accuracy.

### B. SentiWordNet and Hybrid Comparison

{{TABLE:compact_lexical}}

Hybrid correctly classifies 85/148 versus 72/148 cases, an 8.78-point accuracy gain, and matches 99/145 predicted pairs versus SentiWordNet's 81/112 against 162 gold pairs. Its recovery improves while SentiWordNet retains higher pair precision and slightly higher macro-F1 (Table III, Fig. 2). Review-cluster accuracy intervals are 48.99%-65.73% and 39.31%-60.00%; overlap alone does not establish statistical superiority.

{{FIG:performance_comparison|Fig. 2. Python-rendered SemEval development metrics from saved experiment CSVs. Accuracy, macro-F1 and coarse category-polarity pair-F1 are distinct measures.}}

Gold cases are positive-heavy: 103 Positive, 41 Negative and 4 Neutral. Positive/Negative F1 is 0.8152/0.3846 for Hybrid and 0.7558/0.2553 for SentiWordNet. SentiWordNet recovers one Neutral case (F1 0.2000); Hybrid recovers none. The equally weighted Neutral term explains the small macro-F1 reversal, but four cases cannot support a stable neutral-performance claim.

### C. Selective Deep Learning Evaluation

On 1,474 Trip-MA test segments containing 724 in-scope gold pairs, Hybrid matches 314/777 predictions; Hybrid-DL matches 367/746. Pair-F1 rises 0.4184 to 0.4993 (+8.09 points). The 1,113 Partial/Unsupported segments contain 414 gold pairs: Hybrid matches 127/365 versus DL 180/334, raising F1 from 0.3261 to 0.4813 (+15.52 points). The remaining 361 segment outputs are unchanged. These are annotated segments, not 1,474 whole reviews; Booking separately verifies review-level routing.

{{TABLE:dl_metrics}}

{{FIG:dl_joint_pair_f1|Fig. 3. Python-rendered joint pair-F1 from the frozen Trip-MA evaluation. DL processes only the unresolved subset; other Hybrid outputs are retained.}}

DL adds 97 correct pairs and loses 44, a net gain of 53; it introduces 114 false pairs and removes 198. A 1,000-resample paired bootstrap over 111 reviews gives a descriptive DL-minus-Hybrid F1 interval of +4.94 to +11.67 points. Four mapped categories improve, while Facilities declines from 0.1854 to 0.1389. Cleanliness gains partly reflect taxonomy alignment: Hybrid often assigns room hygiene to Room. Post-hoc merging Room/Cleanliness in both gold and predictions still raises F1 from 0.4420 to 0.5147 without refitting; this is a sensitivity analysis, not independent evidence. Different SemEval/Trip-MA tasks do not establish a direct DL-versus-SentiWordNet ranking.

{{TABLE:dl_categories}}

Table V makes the aggregate tradeoff explicit. Room, Service and Food recover more matched category-polarity pairs under routing. Cleanliness reaches 28 matches among 35 predictions, whereas Facilities loses nine matches. The broad BUILDING/BUSINESS crosswalk and limited supervision are plausible contributors to Facilities difficulty, but this experiment does not isolate causal effects. Higher total F1 supports improved recovery in this setting, not guaranteed correction of each Partial review or superiority on every category.

### D. Validity and Limitations

SemEval, prior errors and the Trip-MA benchmark were inspected in earlier development; Booking informed vocabulary work. Results are exploratory, despite validation-only selection within the DL run. One seed, approximate ontology mappings and no component ablation limit attribution/generalization. First-ranked SentiWordNet senses, shallow Hybrid parsing and DL can mishandle implicit language, reference or sarcasm. The status gate can retain an incorrect Complete output or replace a correct Partial prediction with an error.

Trip-MA does not separately supervise Staff or strong/weak intensity and merges Neutral/Mixed. DL direction indices are uncalibrated relative beliefs, not validated intensity. Source redistribution terms are not explicit, so downloaded/prepared Trip-MA copies remain local. No independent intensity labels validate the lexical five bands. Fresh human-held-out annotation, repeated seeds and controlled ablations are needed before broader claims. Figures are deterministic Python visualizations of saved results; architecture boxes are explanatory, not measurements.

## VI. Conclusion

The project integrates a source-traceable SentiWordNet compiler, independent VADER-TextBlob analysis and selective DL reanalysis. Hybrid improves mapped SemEval accuracy and pair recovery, while SentiWordNet retains slightly higher macro-F1 and pair precision. On a separate Trip-MA experiment, DL raises overall pair-F1 from 0.4184 to 0.4993 and unresolved-subset F1 from 0.3261 to 0.4813, with a Facilities regression. The Booking demonstration obtains accepted categories for 383 of 456 routed reviews without treating coverage as correctness. The applied contribution is independent unresolved-review reanalysis with preserved evidence and abstentions. Previously inspected data, merged labels and one training run require cautious interpretation and fresh human evaluation.

## References

[1] M. Hu and B. Liu, “Mining and summarizing customer reviews,” in Proc. ACM SIGKDD, 2004, pp. 168–177, doi: 10.1145/1014052.1014073.

[2] B. Pang, L. Lee, and S. Vaithyanathan, “Thumbs up? Sentiment Classification using Machine Learning Techniques,” in Proc. EMNLP, 2002, pp. 79–86, doi: 10.3115/1118693.1118704.

[3] S. Baccianella, A. Esuli, and F. Sebastiani, “SentiWordNet 3.0: An Enhanced Lexical Resource for Sentiment Analysis and Opinion Mining,” in Proc. LREC, 2010. [Online]. Available: https://aclanthology.org/L10-1531/.

[4] C. J. Hutto and E. Gilbert, “VADER: A parsimonious rule-based model for sentiment analysis of social media text,” Proc. ICWSM, vol. 8, no. 1, pp. 216–225, 2014, doi: 10.1609/icwsm.v8i1.14550.

[5] T. De Smedt and W. Daelemans, “Pattern for Python,” J. Mach. Learn. Res., vol. 13, pp. 2063–2067, 2012.

[6] M. Pontiki, D. Galanis, H. Papageorgiou, S. Manandhar, and I. Androutsopoulos, “SemEval-2015 Task 12: Aspect Based Sentiment Analysis,” in Proc. SemEval, 2015, pp. 486–495, doi: 10.18653/v1/S15-2082.

[7] V. Hatzivassiloglou and K. R. McKeown, “Predicting the Semantic Orientation of Adjectives,” in Proc. ACL-EACL, 1997, pp. 174–181, doi: 10.3115/976909.979640.

[8] P. D. Turney, “Thumbs Up or Thumbs Down? Semantic Orientation Applied to Unsupervised Classification of Reviews,” in Proc. ACL, 2002, pp. 417–424, doi: 10.3115/1073083.1073153.

[9] T. Wilson, J. Wiebe, and P. Hoffmann, “Recognizing Contextual Polarity in Phrase-Level Sentiment Analysis,” in Proc. HLT-EMNLP, 2005, pp. 347–354. [Online]. Available: https://aclanthology.org/H05-1044/.

[10] M. Taboada, J. Brooke, M. Tofiloski, K. Voll, and M. Stede, “Lexicon-Based Methods for Sentiment Analysis,” Comput. Linguist., vol. 37, no. 2, pp. 267–307, 2011, doi: 10.1162/COLI_a_00049.

[11] A. Esuli and F. Sebastiani, “SENTIWORDNET: A Publicly Available Lexical Resource for Opinion Mining,” in Proc. LREC, 2006. [Online]. Available: https://aclanthology.org/L06-1225/.

[12] S. Mohammad, S. Kiritchenko, and X. Zhu, “NRC-Canada: Building the State-of-the-Art in Sentiment Analysis of Tweets,” in Proc. *SEM, vol. 2: SemEval, 2013, pp. 321–327. [Online]. Available: https://aclanthology.org/S13-2053/.

[13] S. Kiritchenko, S. Mohammad, and M. Salameh, “SemEval-2016 Task 7: Determining Sentiment Intensity of English and Arabic Phrases,” in Proc. SemEval, 2016, pp. 42–51, doi: 10.18653/v1/S16-1004.

[14] R. Sharma, A. Somani, L. Kumar, and P. Bhattacharyya, “Sentiment Intensity Ranking among Adjectives Using Sentiment Bearing Word Embeddings,” in Proc. EMNLP, 2017, pp. 547–552, doi: 10.18653/v1/D17-1058.

[15] G. Qiu, B. Liu, J. Bu, and C. Chen, “Opinion Word Expansion and Target Extraction through Double Propagation,” Comput. Linguist., vol. 37, no. 1, pp. 9–27, 2011, doi: 10.1162/coli_a_00034.

[16] E. Riloff and J. Wiebe, “Learning Extraction Patterns for Subjective Expressions,” in Proc. EMNLP, 2003, pp. 105–112. [Online]. Available: https://aclanthology.org/W03-1014/.

[17] M. Pontiki, D. Galanis, J. Pavlopoulos, H. Papageorgiou, I. Androutsopoulos, and S. Manandhar, “SemEval-2014 Task 4: Aspect Based Sentiment Analysis,” in Proc. SemEval, 2014, pp. 27–35, doi: 10.3115/v1/S14-2004.

[18] M. Pontiki et al., “SemEval-2016 Task 5: Aspect Based Sentiment Analysis,” in Proc. SemEval, 2016, pp. 19–30, doi: 10.18653/v1/S16-1002.

[19] D. Tang, B. Qin, X. Feng, and T. Liu, “Effective LSTMs for Target-Dependent Sentiment Classification,” in Proc. COLING, 2016, pp. 3298–3307. [Online]. Available: https://aclanthology.org/C16-1311/.

[20] Y. Wang, M. Huang, L. Zhao, and X. Zhu, “Attention-based LSTM for Aspect-level Sentiment Classification,” in Proc. EMNLP, 2016, pp. 606–615, doi: 10.18653/v1/D16-1058.

[21] W. Wang, S. J. Pan, D. Dahlmeier, and X. Xiao, “Recursive Neural Conditional Random Fields for Aspect-based Sentiment Analysis,” in Proc. EMNLP, 2016, pp. 616–626, doi: 10.18653/v1/D16-1059.

[22] W. Xue and T. Li, “Aspect Based Sentiment Analysis with Gated Convolutional Networks,” in Proc. ACL, 2018, pp. 2514–2523, doi: 10.18653/v1/P18-1234.

[23] C. Zhang, Q. Li, and D. Song, “Aspect-based Sentiment Classification with Aspect-specific Graph Convolutional Networks,” in Proc. EMNLP-IJCNLP, 2019, pp. 4568–4578, doi: 10.18653/v1/D19-1464.

[24] C. Sun, L. Huang, and X. Qiu, “Utilizing BERT for Aspect-Based Sentiment Analysis via Constructing Auxiliary Sentence,” in Proc. NAACL-HLT, 2019, pp. 380–385, doi: 10.18653/v1/N19-1035.

[25] H. Xu, B. Liu, L. Shu, and P. S. Yu, “BERT Post-Training for Review Reading Comprehension and Aspect-based Sentiment Analysis,” in Proc. NAACL-HLT, 2019, pp. 2324–2335, doi: 10.18653/v1/N19-1242.

[26] B. Pang and L. Lee, “A Sentimental Education: Sentiment Analysis Using Subjectivity Summarization Based on Minimum Cuts,” in Proc. ACL, 2004, pp. 271–278, doi: 10.3115/1218955.1218990.

[27] R. Socher et al., “Recursive Deep Models for Semantic Compositionality Over a Sentiment Treebank,” in Proc. EMNLP, 2013, pp. 1631–1642. [Online]. Available: https://aclanthology.org/D13-1170/.

[28] Y. Kim, “Convolutional Neural Networks for Sentence Classification,” in Proc. EMNLP, 2014, pp. 1746–1751, doi: 10.3115/v1/D14-1181.

[29] W. Zhang, X. Li, Y. Deng, L. Bing, and W. Lam, “A survey on aspect-based sentiment analysis: Tasks, methods, and challenges,” IEEE Trans. Knowl. Data Eng., vol. 35, no. 11, pp. 11019–11038, 2023, doi: 10.1109/TKDE.2022.3230975.

[30] S. U. S. Chebolu, F. Dernoncourt, N. Lipka, and T. Solorio, “Survey of aspect-based sentiment analysis datasets,” arXiv preprint arXiv:2204.05232, 2022. [Online]. Available: https://arxiv.org/abs/2204.05232

[31] W. Wang, F. Wei, L. Dong, H. Bao, N. Yang, and M. Zhou, “MiniLM: Deep self-attention distillation for task-agnostic compression of pre-trained transformers,” arXiv preprint arXiv:2002.10957, 2020. [Online]. Available: https://arxiv.org/abs/2002.10957

[32] S. M. Jiménez Zafra, G. Berardi, A. Esuli, D. Marcheggiani, M. T. Martín-Valdivia, and A. Moreo Fernández, “A multi-lingual annotated dataset for aspect-oriented opinion mining,” in Proc. EMNLP, 2015, pp. 2533–2538, doi: 10.18653/v1/D15-1302.

[33] TextBlob contributors, “TextBlob 0.19.0 documentation,” accessed Oct. 15, 2026. [Online]. Available: https://textblob.readthedocs.io/en/stable/

[34] J. Liu, “515K hotel reviews data in Europe,” Kaggle dataset, accessed Oct. 15, 2026. [Online]. Available: https://www.kaggle.com/datasets/jiashenliu/515k-hotel-reviews-data-in-europe

[35] Crawlfeeds, “Booking Hotel Reviews Dataset: Booking Italy hotel reviews,” Hugging Face dataset, CC BY-NC 4.0, accessed Oct. 21, 2026. [Online]. Available: https://huggingface.co/datasets/crawlfeeds/Booking-Hotel-Reviews-Dataset
