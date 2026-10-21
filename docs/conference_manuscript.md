# An Auditable Grammar Assisted Hybrid for Aspect Sentiment Analysis of Hotel Reviews

Authors: Tanay Mohta and Aditya Rawat

## Abstract

Hotel reviews often contain different opinions about rooms, staff, food, and services, making a single polarity label insufficient for operational interpretation. This paper presents a compiler-inspired comparison of a controlled SentiWordNet pipeline and an independent grammar-assisted VADER-TextBlob hybrid. The hybrid preserves source text, attaches opinions to six hotel categories using shallow grammatical evidence, and combines lexical scores with explicit contextual rules. A reviewed vocabulary layer supplies guarded canonical scoring copies while retaining original library evidence. Experiments use 100 curated and 200 randomly sampled hotel reviews, a declared SemEval-2015 hotel adaptation, and 3,102 nonblank Booking Italy review bodies for vocabulary development. On 148 eligible sentence-category cases, the expanded hybrid correctly predicts 85 cases against 42 for the baseline: all-case accuracy increases from 28.38% to 57.43%, and macro-F1 from 0.2260 to 0.3999. Category-polarity tuple recall increases while precision decreases. On random reviews, 70/200 hybrid results satisfy heuristic completeness checks. Booking Italy bodies with any scored aspect increase from 84.24% to 87.07%, but only 7.87% are complete. These are development measurements, not unseen-test accuracy. Neutral sentiment and complex attachment remain limitations. The contribution is an auditable integration and evaluation framework rather than a new pretrained model.

Keywords: aspect-based sentiment analysis; hotel reviews; compiler pipeline; SentiWordNet; VADER; TextBlob; reproducible evaluation.

## I. Introduction

Hotel administrators need to understand which part of a guest experience prompted an opinion. Feature-oriented review summarization addresses this need by associating evaluations with product or service attributes [1]. Document sentiment classification provides a useful overall signal [2], but it can conceal conflicting experiences within a review. A guest may appreciate the room while criticizing staff behavior. Preserving both opinions is more useful than allowing their numerical average to erase the disagreement.

Our earlier implementation represents hotel-review analysis as a sequence of compiler stages: preprocessing, lexical analysis, syntax analysis, semantic interpretation, lexical scoring, adjustments, and result generation. Its SentiWordNet component uses synset-level sentiment evidence [3]. The controlled grammar makes intermediate decisions inspectable, but also restricts the language that reaches the scorer. Replacing only that scorer cannot recover an opinion that the front end already rejected.

This work therefore constructs a second, independent pipeline. VADER supplies valence-sensitive lexical sentiment rules [4], while TextBlob's Pattern-based language facilities provide grammatical evidence [5]. Both pipelines retain the same six project categories: Room, Staff, Service, Food, Cleanliness, and Facilities. They receive the same review text but may produce different aspect records. Evaluation uses a documented mapping of SemEval hotel annotations [6], without substituting whole-review sentiment for a missing aspect prediction.

The engineering contributions are an independent grammatical attachment stage, evidence-aware VADER-TextBlob integration, a reviewed vocabulary layer with retained original evidence, and a source-preserving experimental interface. The expanded hybrid recognizes 671 aspect phrases and 497 reviewed lexical forms without changing the native sentiment dictionaries or the baseline. The framework separates unavailable predictions from neutral sentiment, retains conflicting polarity as Mixed, and provides one tabular result per submitted review. This comparison evaluates complete pipelines; it does not establish that tool recency or averaging alone improves sentiment analysis. All benchmark results are development measurements rather than a claim of unseen generalization.

## II. Literature Survey

### A. Lexical Resources and Contextual Valence

Early work demonstrated that adjective orientation can be inferred using conjunction constraints. Hatzivassiloglou and McKeown [7] modeled relationships between coordinated adjectives, motivating attention to grammatical context rather than isolated word counts. Turney [8] estimated review orientation from adjective- and adverb-containing phrases using an unsupervised association method. These studies establish complementary roles for lexical orientation and phrase selection; the present implementation uses fixed dictionaries and shallow grammatical attachment rather than reproducing their learning procedures.

Wilson, Wiebe, and Hoffmann [9] distinguished prior word polarity from polarity in context, including the distinction between neutral and polar expressions. Taboada et al. [10] described SO-CAL, which combines lexical orientation with intensification and negation. These findings motivate retaining modifiers and explicit uncertainty in our intermediate records. Esuli and Sebastiani [11] introduced SentiWordNet's positive, negative, and objective synset evidence; its later release [3] refined automatic annotation of WordNet senses. A synset resource nevertheless requires a sense-selection policy when incorporated into a domain application.

VADER [4] combines a human-rated sentiment lexicon with rules for text cues such as negation, emphasis, and degree modifiers. It is relevant to informal feedback, but it is not itself a hotel-aspect extractor. The NRC-Canada system [12] illustrates another use of lexical features within supervised tweet classification. Its architecture should not be conflated with our rule-based fusion. Pattern [5] offers a practical language-processing toolkit from which TextBlob exposes grammatical and sentiment components.

Polarity and intensity also require different evaluation targets. Kiritchenko et al. [13] studied phrase-level sentiment intensity across language and domain settings, while Sharma et al. [14] investigated adjective-intensity ranking using sentiment-bearing embeddings. Their work motivates reporting intensity separately from polarity. Our five score bands are descriptive intervals; without independently annotated strength labels, they cannot be reported as validated five-class accuracy.

### B. Aspect Extraction and Targeted Sentiment

Qiu et al. [15] used syntactic relationships to expand opinion words and extract targets through double propagation. Riloff and Wiebe [16] learned subjective extraction patterns through bootstrapping. These studies support the general importance of linguistic relationships, although our implementation neither trains their models nor performs iterative dependency-based lexicon expansion. Instead, it attaches open adjective and lexical opinion candidates to an explicit hotel-aspect dictionary using shallow phrase information.

The SemEval-2014 task [17], its 2015 continuation [6], and the multilingual 2016 task [18] formalized aspect-oriented evaluation with annotated targets, categories, and polarity. They also show why incompatible label spaces and subtasks should not be combined into one accuracy claim. Our six-category crosswalk is a declared adaptation; it is not an official reproduction of the benchmark's complete ontology or target-span task.

Learned approaches provide further context. Tang et al. [19] incorporated target information into LSTM representations. Wang et al. [20] used attention for aspect-level sentiment, and another Wang et al. study [21] jointly modeled aspect and opinion extraction with recursive neural conditional random fields. Xue and Li [22] explored gated convolutions, while Zhang et al. [23] incorporated dependency structure through aspect-specific graph convolution. These works demonstrate richer methods for target-context association than a fixed vocabulary gate. They are background studies, not models evaluated by this project.

Sun et al. [24] reformulated aspect sentiment through auxiliary sentences and BERT sentence-pair classification. Xu et al. [25] investigated review-oriented BERT post-training and related downstream tasks. Such methods address representational limitations beyond lexical matching, but introduce training, model resources, and experimental requirements outside the present implementation. We retain a local lexicon-based system whose intermediate decisions can be inspected during a compiler-design review.

### C. Representation and Evaluation Considerations

Pang and Lee [26] investigated subjectivity extraction before document classification, emphasizing that relevant text selection can influence the final classifier. Socher et al. [27] introduced phrase-level sentiment composition and fine-grained supervision, and Kim [28] studied convolutional sentence classification using pretrained word vectors. Their results concern different representations and datasets; the corresponding published accuracy values are therefore not baselines in our experiment.

The survey by Zhang et al. [29] distinguishes aspect terms, categories, opinion expressions, and their relations across ABSA tasks. Chebolu et al. [30] review dataset selection and annotation characteristics. Together, these studies motivate separate measures for extraction coverage, category-polarity recovery, and sentiment classification. Our comparison addresses an engineering gap: an inspectable hotel-review pipeline must expose abstentions and attachment failures as well as scores. It does not claim a new state-of-the-art algorithm or compare its adapted metrics directly with unrelated published rankings.

## III. Proposed Systems

The architecture contains four modules: preprocessing, lexical and grammatical analysis, semantic attachment and scoring, and adjustment and result generation. Figures 1-4 illustrate these stages using short block labels and dashed groups. Gray identifies established methods; white identifies project integration logic. Preprocessing is the first processing block. The two analysis paths remain independent after validation and retain their own outputs throughout comparison.

### A. Module 1 Preprocessing and Validation

The input interface accepts review text or a UTF-8 CSV containing a serial identifier and review. It validates headers, field structure, blank content, and configured size limits while retaining invalid rows and diagnostic reasons. Quoted commas and multiline cells remain valid CSV content. Duplicate flags provide evidence without silently deleting submitted observations. Original wording, punctuation, capitalization, and row identity are preserved for analysis and provenance.

{{FIG:module1_preprocessing|Fig. 1. Module 1 preprocessing. Original text is preserved before the independent analysis paths; review records enter from outside the processing block.}}

Each valid review is passed unchanged to both methods. The hybrid later creates a contraction-expanded working copy with a mapping back to original character spans. This separation matters because global lowercasing or punctuation removal would discard cues useful to VADER. Dataset preparation and runtime preprocessing are recorded separately: removing an explicit missing-feedback placeholder during sampling does not authorize rewriting spelling or sentiment in a review.

{{ALG:1}}

### B. Module 2 Lexical and Grammatical Analysis

{{FIG:module2_grammar|Fig. 2. Module 2 independent front ends. Both paths receive Module 1 text; the baseline AST is not an input to the hybrid grammar.}}

The baseline scans tokens, matches configured phrases, and applies a controlled predictive grammar to build clause records. Unknown language remains visible through recovery diagnostics. Its current configuration contains 345 aspect phrases and 356 canonical opinion terms, with 315 packaged source synsets. This configuration is frozen for the comparison.

The hybrid does not call the baseline lexer, parser, or opinion vocabulary. TextBlob's PatternParser supplies POS tags and shallow NP, VP, adjective, and preposition chunks [31]. Noun phrases are assembled from NP chunks. The implementation does not require the separate Brown-trained noun-phrase extractor and does not claim dependency parsing. Original spans are retained through contraction expansion and token alignment.

Clause segmentation separates sentence boundaries, contrasts, and coordinated predicates while preserving coordinated noun subjects. Candidate discovery admits adjectives and lexical opinion expressions without requiring membership in the old SentiWordNet opinion list. Thus, a grammatical candidate can be extracted even if neither sentiment dictionary later supplies a score. This avoids confusing extraction success with sentiment availability.

{{ALG:2}}

### C. Module 3 Semantic Attachment and Sentiment Evidence

{{FIG:module3_scoring|Fig. 3. Module 3 separate scoring paths. The hybrid retains native evidence before guarded alias normalization and retains effective component scores after any rescoring.}}

Baseline semantics associates accepted opinions with configured categories and issues. It selects a configured SentiWordNet sense and retains positive P, negative N, objective evidence 1-P-N, and lexical score L=P-N. The resource's source values are not rewritten. A separate domain value D may replace L under the baseline's existing hotel rules; degree multiplier m and negation multiplier n then give its clipped final score.

{{EQ:baseline}}

The independent hybrid longest-matches its own six-category aspect phrases, combining its initial 164 phrases with 507 reviewed additions. Attributive opinions attach forward to nouns, predicates attach backward to subjects, and opinion verbs can attach to following targets. Trailing opinions can be shared by coordinated subjects. Pronoun inheritance requires an immediately following reference with a unique previous target. Ambiguous references, unsupported topics, and unresolved segments produce diagnostics. Location, Price, and Value remain outside scope; price opinions are not relabeled as room quality.

VADER records compound sentiment and positive, neutral, and negative proportions. TextBlob PatternAnalyzer records polarity, subjectivity, and assessed expressions. Both execute on each extracted context and separately on the complete review. Subjectivity is not prediction confidence. The expanded vocabulary adds a project-curated catalog of 497 lexical forms, including inflections and spelling variants; these are not new native library lexicon entries. For a native-unknown form allowed by the context's category, a canonical expression is substituted only in a scoring copy. Known native entries take precedence. For example, the catalog maps eligible occurrences of polite to courteous and tasty to delicious. These are explicit project interpretations, not learned synonyms or unchanged raw library scores.

The tools first score the original context. When guarded substitutions occur, both score the canonical copy; the trace retains original and effective results, the scoring text, source-relative matches, and substitution reasons. A whole-review copy permits only aliases approved for all six categories. Original review wording and target spans remain unchanged, and apostrophe normalization in an altered scoring copy preserves contraction negation. Any component exception remains a processing error. Let V and T denote the effective compound and polarity scores after this step, and eV and eT indicate corresponding lexical evidence. When both components execute successfully and the denominator is positive, fusion is defined by (2).

{{EQ:fusion}}

With w=0.5, both supported components are averaged; if only one contains evidence, its score is retained without dilution by an unsupported zero. Neither component with evidence means unavailable, not automatically Neutral. A component exception remains a processing error even if the other component returns a number. The weight is an untuned policy choice, not an experimentally optimized parameter.

{{ALG:3}}

### D. Module 4 Adjustment and Final Records

The baseline retains its existing domain, degree, and negation rules. In the hybrid, an explicit category-context rule may replace lexical fusion for functional failures, missing hot water, room preferences, hygiene, or service responsiveness. Raw library scores, pre-rule fusion, rule identity, matched text, and final score remain inspectable. Rules with opposing signs in one context do not override fusion. These values are project conventions rather than new scores attributed to either library.

{{FIG:module4_synthesis|Fig. 4. Module 4 adjustment, synthesis, and evaluation. Scores remain separate by method; baseline negation is not applied again to hybrid library outputs.}}

The five descriptive bands are Strong Negative at or below -0.5, Weak Negative between -0.5 and -0.05, Neutral from -0.05 through +0.05, Weak Positive between +0.05 and +0.5, and Strong Positive at or above +0.5. Missing results remain Unavailable. Positive and negative opinions together retain a Mixed label even if their mean is near zero.

For review i, the hybrid aspect mean averages its mi extracted context scores only when all are available. It is unavailable if any required score is missing. This summarizes recognized aspects rather than proving complete understanding. A whole-review lexical score is exported separately because its scope differs. Dashboard category means average a category within each review and then across contributing reviews, giving reviews equal weight. The UI exposes both methods for demonstration; offline exports provide the paper's reproducible evidence.

{{EQ:mean}}

Final records contain method, category, aspect/context spans, polarity, strength, evidence, and processing status. Complete means all extracted candidates are scored and no unresolved or scope diagnostic is detected; it is a heuristic processing status. Partial retains scored results alongside diagnostics. Unsupported has no scored aspect, and processing_error records an analysis failure. CSV-invalid rows retain their validation outcome. Independent opinion sets are exported as separate method rows rather than paired by their position in a list.

{{ALG:4}}

## IV. Results and Implementation

### A. Dataset Description

Table I distinguishes four cohorts with different roles and annotation availability.

{{TABLE:datasets}}

The Booking source contains 515,738 published feedback records [32]. The project uses two smaller samples rather than treating the full corpus as evaluated. The curated 100 intentionally favor short aspect-predicate language and baseline vocabulary, following an inspected pilot. The random 200 are sampled from the broader eligible pool under documented basic filtering and deduplication, without the demo's grammar restriction. The two samples do not share parent source rows.
Sampling trims outer field whitespace, removes exact missing-feedback placeholders, and joins original positive/negative feedback fields when both are retained. It does not invent reviews, repair spelling, or rewrite internal wording. Source row maps, original field contents, archive hashes, and per-review checks reproduce the 300 inputs. Field headings and reviewer ratings are excluded from analyzed text. Neither Booking cohort supplies independently annotated aspect polarity, so its processing counts are not sentiment accuracy.

The SemEval hotel XML contains 30 parent reviews, 266 sentences, and 339 original opinion annotations [6]. The declared mapping excludes 141 annotations outside the project scope, retaining 137 eligible sentences and 162 unique coarse category-polarity pairs. Classification uses 148 sentence-category cases having a single gold polarity for that coarse category. These are not 148 independent reviews. Gold annotations are used only by the evaluator after prediction.

The crosswalk maps ROOMS to Room, FACILITIES and ROOMS_AMENITIES to Facilities, FOOD_DRINKS to Food, SERVICE to Service, and HOTEL cleanliness to Cleanliness. Predicted Staff is collapsed into benchmark Service. Price, Location, and other HOTEL annotations are excluded. Ambiguous coarse-category polarities remain in tuple evaluation but not in the single-polarity classification denominator. This mapping measures neither exact target-span nor issue-label accuracy.

The user-supplied Crawlfeeds Booking Italy export [33] contains 4,367 source rows: 3,102 have nonblank review bodies and 1,265 lack both body fields after literal missing markers are removed. Original positive and negative body fields are joined with a newline. Titles, headings, ratings, identities, and metadata are excluded from analyzed text; duplicate and empty-body rows remain in the source sequence. The same source bytes and body preparation are used before and after vocabulary expansion. This inspected development corpus has no independent aspect-polarity gold labels and is separate from the earlier 300-review samples.

### B. Module 1 Implementation Results

All 300 Booking sample inputs pass the experiment's CSV validation and source-reconstruction checks. All rows are preserved in paired review tables, including unsupported outcomes. This confirms input integrity and traceability to the downloaded dataset, not the identity or authenticity of each original reviewer. The random cohort has a mean length of 194.915 characters; its varied clauses provide a broader processing challenge than the deliberately constrained demonstration.

The analysis implementation is Python-based, using VADER 3.3.2, TextBlob 0.19.0, and NLTK 3.10.3. Experiments export the installed environment, input hash, code snapshot, resource hashes, and numerical policy. The updated benchmark and sample experiments were rerun on October 21, 2026; the saved Booking Italy before/after audit was produced on October 18. These artifacts support reproduction without sending reviews to an external service. Both systems run independently in the research runner and demonstration UI. Empty Booking Italy bodies are retained as missing-input outcomes and excluded from the 3,102-body coverage denominator.

### C. Module 2 Implementation Results

The random cohort produces 14 baseline opinion records and 626 expanded-hybrid context records, compared with 579 contexts in the earlier hybrid run. This shows broader candidate extraction, not that all new attachments are correct. POS tags, noun phrases, contexts, original offsets, and diagnostics are exported to inspect decisions. The annotated experiment quantifies the precision-recall tradeoff; the unannotated sample cannot establish accuracy.

The curated cohort is completely processed for 97 baseline reviews and 100 hybrid reviews. Selection used baseline-compatible vocabulary and grammar, so these counts characterize a demonstration rather than unbiased generalization. On random reviews, the baseline yields 1 complete, 11 partial, and 188 unsupported outcomes. The expanded hybrid yields 70 complete, 101 partial, and 29 unsupported outcomes, with no processing errors in either method.

{{TABLE:vocabulary}}

Table II compares the same Booking Italy bodies before and after vocabulary development. Scored contexts rise from 11,041 to 12,584, while adjective occurrences without lexical lookup support decline from 2,025 to 1,217, a 39.90% reduction. The extraction set also grows, so these counts are not matched-case correctness measurements. Native-unknown adjectives may include factual descriptors or tagging errors. The 497 forms are a catalog size, not the number proven correct by annotation.

{{FIG:booking_vocabulary_coverage|Fig. 5. Vocabulary-development outcomes on the same 3,102 nonblank Booking Italy bodies. The 1,265 missing-body rows are outside these bars; processing status does not measure sentiment accuracy.}}

Bodies with any scored aspect increase from 2,613/3,102 (84.24%) to 2,701/3,102 (87.07%). Complete processing rises from 210 to 244 bodies, reaching only 7.87%; 2,457 remain partial and 401 unsupported. Figure 5 shows that long reviews still exceed the system's scope, often through narrative language or Location/Price topics. Coverage improvement must not be presented as 87.07% complete understanding.

### D. Module 3 Implementation Results

The benchmark sentence "The rooms were quiet." illustrates category-dependent interpretation. The baseline's hotel preference produces positive Room sentiment. The hybrid's explicit room_quiet rule likewise assigns +0.45, retaining its original component outputs and pre-rule fusion. The rule is visible in the trace; it is not presented as a value supplied by SentiWordNet, VADER, or TextBlob.

An authored development example, "The air conditioning wasn't working.", demonstrates functional language. Its grammatical context maps to Facilities, and the equipment_not_functioning rule gives -0.70. This example documents implemented behavior and is not an additional real-dataset accuracy observation. An unrecognized predicate can still remain unscored. Domain rules therefore supplement lexical evidence without converting every extracted phrase into a fabricated sentiment decision.

### E. Module 4 Implementation Results

Figure 6 separates processing outcomes on random reviews. The expanded hybrid supplies at least one scored aspect for 171/200 reviews (85.5%), compared with 12/200 for the baseline. Only 70/200 hybrid reviews (35%) satisfy heuristic completeness checks. The earlier hybrid obtained 167/200 with any score and 66 complete outcomes on the same sample. These increases describe processing coverage, not an increase in annotated accuracy. A review can contain useful extracted aspects and still require inspection.

{{FIG:random_coverage|Fig. 6. Updated processing outcomes on 200 random real reviews. Counts describe heuristic coverage, not correctness; neither method has processing errors in this run.}}

Each review receives one comparison row; separate opinion tables preserve differing extraction counts. Exports retain five bands, component disagreement, rule IDs, grammar patterns, diagnostics, and lexical-normalization evidence. A near-zero mean does not erase Mixed, and missing aspect scores are not replaced by whole-text sentiment. The implementation's latest software regression run passes 195 authored tests. All 300 rerun baseline review scores, statuses, and extraction counts match the earlier saved run, and the baseline fingerprint matches the pre-expansion snapshot. These checks establish implementation contracts rather than sentiment accuracy.

## V. Performance and Metrics

### A. Evaluation Protocol

Let N=148 be the eligible classification cases, C the correctly predicted cases, and S the cases receiving a Positive, Negative, or Neutral prediction. All-case accuracy is C/N and classification coverage is S/N. Missing or Mixed predictions count as errors for this single-polarity task. Conditional accuracy C/S is secondary and uses each method's selected scored subset. Strong and weak bands collapse to their polarity sign for this three-class evaluation. For each class, precision is TP/(TP+FP), recall is TP/(TP+FN), and F1 is their harmonic mean, 2PR/(P+R), with zero for undefined zero-support predictions. Macro-F1 averages all three class F1 values, including a missed class's zero.

{{EQ:metrics}}

Tuple precision uses matched category-polarity pairs divided by predicted pairs, and recall divides matched pairs by gold pairs. Tuple-F1 is their harmonic mean. Accuracy intervals are percentile bootstrap intervals from 1,000 resamples of the 30 parent reviews; sentences within a review are not independent bootstrap units. Table III and Fig. 7 use identical mapping and denominators for both methods. Parameters remain w=0.5, neutral boundary 0.05, and strong boundary 0.5. Fusion weights and contextual-rule values were not retuned for this update.

### B. Comparative Accuracy and Recovery

{{TABLE:metrics}}

The expanded hybrid increases all-case accuracy by 29.05 percentage points relative to the baseline, from 42 to 85 correct cases. Classification coverage rises from 44/148 to 94/148, and macro-F1 from 0.2260 to 0.3999. Its 95% review-cluster bootstrap accuracy interval is 48.99%-65.73%, compared with 19.11%-38.60% for the baseline. The 57.43% accuracy still leaves substantial scope for improvement under this strict denominator.

{{FIG:performance_comparison|Fig. 7. Updated development metrics on the declared SemEval mapping. Macro-F1 includes all three polarity classes; tuple-F1 measures coarse category-polarity sets, not spans.}}

Tuple recall rises from 0.2840 to 0.6111, whereas precision falls from 0.9200 to 0.6828. The expanded hybrid matches 99 of 145 predicted pairs against 162 gold pairs; the baseline matches 46 of 50. Broader extraction recovers more opinions while introducing incorrect associations. Conditional accuracy decreases from 95.45% to 90.43% on different selected subsets and does not replace the all-case comparison.

Compared with the earlier hybrid on the same annotated cases, correct classifications rise only from 83 to 85 (56.08% to 57.43%), and macro-F1 from 0.3956 to 0.3999. Tuple-F1 instead falls from 0.6645 to 0.6450 as additional predictions introduce errors. Vocabulary expansion therefore improves some measures and worsens another; the data do not support a blanket superiority claim. This is a descriptive version comparison, not a component ablation or significance test.

### C. Class Behavior and Runtime

{{TABLE:classes}}

Table IV shows that expanded-hybrid positive recall is 0.7282 and negative recall 0.2439; neither method correctly predicts the four neutral cases. Zero neutral F1 remains in macro-F1 despite its small support. Positive F1 rises from the earlier hybrid's 0.8022 to 0.8152, while negative F1 remains 0.3846. Neutral interpretation and negative attachment require further work beyond adding positive candidates.

Figure 8 reports warm core runtime for actual random-sample prefixes. Each point uses three repetitions with alternating method order; error bars are sample standard deviations, not confidence intervals. Initialization, CSV I/O, plotting, and UI rendering are excluded. The hybrid includes grammar, aspect and whole-review scoring, and additional tool passes when aliases change a scoring copy. Shared desktop load was not controlled, so timings are descriptive rather than a hardware-normalized benchmark. Cross-date timing changes cannot be attributed solely to vocabulary size.

{{FIG:runtime_comparison|Fig. 8. Updated warm runtime on original review prefixes. Error bars are standard deviations of three repetitions; background desktop load was not controlled.}}

For 200 reviews, the baseline mean is 0.110 s with a 0.015 s standard deviation; the expanded hybrid mean is 1.395 s with a 0.083 s standard deviation. The hybrid takes approximately 12.70 times as long within this run. Broader analysis has a measurable cost even though both systems execute locally without an LLM call.

### D. Validity and Limitations

The annotated benchmark and its earlier errors were examined before hybrid development. Booking Italy was inspected to develop the vocabulary. Neither is an untouched evaluation holdout. Changes were not preregistered, and no paired significance test or ablation isolates component effects. Fusion and contextual-rule ablations are outside this evaluation; the policy remains fixed. Future evaluation should freeze configuration before fresh annotation or a parent-review split. Published neural scores reviewed in Section II are not directly comparable with this adapted task.

Further limitations include the small positive-heavy benchmark, excluded categories, shallow attachment, limited pronoun resolution, sarcasm, implicit complaints, negation, and temporal changes. Canonical aliases are manual semantic approximations and may alter intensity; their strengths are not independently calibrated. The baseline retains its original smaller grammar and lexicon, so this comparison does not establish superiority over every expanded SentiWordNet implementation. Different completeness heuristics are not ground truth. Source verification establishes correspondence to retained dataset bytes rather than reviewer authenticity. Five bands require separate human strength labels before five-class accuracy can be claimed. These constraints qualify the gains and preserve the adverse findings.

## VI. Conclusion

This paper compared a controlled SentiWordNet compiler with an independent grammar-assisted VADER-TextBlob hybrid, expanded through reviewed aspect phrases and guarded lexical normalization. Original review text and native/effective evidence remain inspectable. On the development mapping, the expanded hybrid reaches 57.43% accuracy and 0.3999 macro-F1 against 28.38% and 0.2260 for the frozen baseline. Compared with the earlier hybrid, it adds two correct classification cases but lowers tuple-F1 from 0.6645 to 0.6450. Random-review completeness reaches 35%; Booking Italy yields scored aspects for 87.07% of nonblank bodies but complete processing for only 7.87%. These findings show vocabulary coverage gains alongside unresolved attachment and calibration problems. Fresh annotations, frozen policies, component ablations, and independently labeled intensity data are needed before stronger generalization or strength-classification claims.

## References

{{REFERENCES}}
