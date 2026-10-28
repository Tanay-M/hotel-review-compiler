# Defensible novelty: targeted prior-art assessment

Research date: 21 October 2026. This is a focused primary-source comparison, not an exhaustive systematic review or a patentability search. Absence of an identical implementation in these searches does not establish priority. No manuscript, code, experiment, or result was changed during this assessment.

## Conclusion

The project has a defensible **application and systems contribution**, with useful implementation choices and an honest empirical comparison. It does **not currently establish a fundamentally new sentiment algorithm, a novel idea of combining sentiment lexicons, the first grammatical aspect extractor, or the first explainable sentiment system**. Its strongest contribution is the particular auditable integration: two independent analysis paths, original-text and scoring-copy provenance, explicit lexical-evidence accounting, partial-analysis diagnostics, and reproducible whole-pipeline evaluation on hotel reviews.

That is credible for a compiler-design project and an exploratory applied research paper. A strong claim of general methodological superiority requires additional controlled evidence. The following are novelty judgments inferred from the overlaps below, rather than statements made by the cited authors.

## Closest verified prior art

| Primary source | Established overlap | Consequence for our claim |
|---|---|---|
| Taboada et al., **Lexicon-Based Methods for Sentiment Analysis**, Computational Linguistics, 2011, DOI 10.1162/COLI_a_00049. [Publisher-hosted ACL record and PDF](https://aclanthology.org/J11-2001/) | SO-CAL uses sentiment-bearing words and contextual valence shifters, including intensifiers and negation. | Lexicon scores adjusted by grammatical context are established; our domain and intensity rules are implementation work, not a new general principle. |
| Hutto and Gilbert, **VADER: A Parsimonious Rule-Based Model for Sentiment Analysis of Social Media Text**, ICWSM, 2014. [AAAI proceedings](https://ojs.aaai.org/index.php/ICWSM/article/view/14550) | A sentiment lexicon is combined with grammatical and syntactical intensity rules; SentiWordNet is among its comparators. | Using VADER, negation, capitalization, punctuation, modifiers, or comparing lexical systems is not our invention. |
| Poria et al., **A Rule-Based Approach to Aspect Extraction from Product Reviews**, SocialNLP, 2014, DOI 10.3115/v1/W14-5905. [ACL Anthology](https://aclanthology.org/W14-5905/) | Rules exploiting dependency structures and commonsense knowledge extract explicit and implicit review aspects. | Grammar-assisted aspect extraction predates this project. Our shallow-chunk implementation differs technically, but the broad task and strategy are established. |
| Consoli, Barbaglia, and Manzan, **Explaining Sentiment from Lexicon**, X-SENTIMENT 2021 workshop. [Proceedings full paper](https://ceur-ws.org/Vol-2918/paper7.pdf) | Linguistic rules identify text fragments semantically linked to a concept and explain the origin of its sentiment. | Neither target-linked linguistic explanations nor interpretable lexical sentiment are new in themselves. Our more specific scoring and transformation audit can be described as a system feature, without claiming first-ever explainability. |
| Alharbi et al., **TriLex: A fusion approach for unsupervised sentiment analysis of short texts**, PLOS ONE, 2025, DOI 10.1371/journal.pone.0317100. [Publisher full text](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0317100) | Combines TextBlob, VADER, and AFINN using normalized scores, weighted averaging, agreement, and thresholds. | Combining VADER and TextBlob, or using a weighted average of lexical tools, is not defensible as the core novelty. TriLex does not establish our specific hotel attachment, source mapping, or evidence-availability policy. |
| Nguyen, Nguyen, and Pham, **A Two-Stage Classifier for Sentiment Analysis**, IJCNLP, 2013. [ACL record and full paper](https://aclanthology.org/I13-1114/) | Uses a reject option for sentiment classification; rejected cases are handled by another classifier. | Abstention in sentiment analysis is established. Our deterministic lack-of-evidence states are different from probabilistic rejection, but cannot support an invention-of-abstention claim. |
| **Aspect based Sentiment Oriented Summarization of Hotel Reviews**, Procedia Computer Science 115, 2017, pp. 563–571, DOI 10.1016/j.procs.2017.09.115. [Publisher abstract](https://www.sciencedirect.com/science/article/pii/S1877050917319439) | Hotel reviews are assigned to predefined aspects, analyzed, and summarized using existing NLP resources. | Hotel-specific aspect sentiment and consolidated summaries are established applications. The abstract was accessible through publisher search results; direct full-page fetch returned HTTP 403, so no unverified fine-grained implementation claim is made here. |

Additional cross-check: Hill, Fresneda, and Anandarajan, **The wisdom of the lexicon crowds**, Journal of Big Data, 2025, DOI 10.1186/s40537-025-01186-7, combines thirteen lexicons and benchmarks them across thirteen datasets. This further rules out generic multi-lexicon integration as a novelty claim. [Publisher full text](https://link.springer.com/article/10.1186/s40537-025-01186-7)

Compiler-style stage names are also insufficient for priority: Ramzan et al., **An Intelligent Data Analysis for Hotel Recommendation Systems using Machine Learning** (2019 author preprint), explicitly combines lexical, syntax and semantic analysis for hotel-feature sentiment. Its recommendation and guest-type components differ from this project, but the stage sequence is already present in hotel prior art. [Author preprint](https://arxiv.org/abs/1910.06669). Our concrete source-linked IR, diagnostics and recovery implementation should be described precisely instead of claiming that compiler phases themselves are unprecedented in hotel analysis.

An extension beyond one chosen base paper is not necessarily new to the wider literature. We can claim additional implemented capabilities relative to that base only after checking its full methods; global novelty must also account for the independent prior work above.

## What belongs to the libraries, and what belongs to this project

TextBlob already exposes PatternAnalyzer, taggers, noun-phrase facilities, and PatternParser. POS tags and shallow grammatical annotations are therefore capabilities we integrate, not algorithms we invented. [Official TextBlob documentation](https://textblob.readthedocs.io/en/dev/advanced_usage.html)

VADER already supports ordinary negation, degree modifiers, punctuation emphasis, capitalized emphasis, slang, emoticons, and emoji processing. We should not present these inherited features as Team 17 contributions. [Official VADER implementation](https://github.com/cjhutto/vaderSentiment)

Our local implementation adds the hotel category dictionaries, explicit aspect attachment/inheritance rules, category-guarded lexical aliases, original-to-scoring-copy audit, configured domain score rules, evidence availability policy, compiler intermediate records, review-level processing states, source trace exports, and experimental adapters. It is legitimate to say we designed and implemented these pieces; it is not yet justified to say that each idea is unprecedented.

## Most defensible contribution hierarchy

1. **Strongest current contribution: auditable end-to-end hotel analysis.** The result is not just a polarity: it retains the aspect, original span, grammatical attachment, lexical component scores, any alias substitution, any domain override, final score, and processing diagnostics. The compiler framing gives a concrete intermediate representation and recovery mechanism. This is useful systems design. Related transparent lexical systems exist, so avoid claiming the first such architecture.
2. **Specific design contribution: evidence-aware, source-preserving lexical adaptation.** Native-known forms are protected from alias replacement; configured unknown forms receive a guarded scoring representation while the original text remains intact. Raw component scores, original/effective text, and final rule-based changes remain visible. This is more precise and defensible than saying “we combine VADER and TextBlob.” The current search did not establish identical prior use of this exact policy, but that does not prove it is new. Its measurable benefit is not yet isolated by ablation.
3. **Specific design contribution: distinguish sentiment from processing availability.** Neutral sentiment, unavailable lexical evidence, partial analysis, contradictory opinions, invalid input, and execution errors are represented separately. This prevents a failed extraction from quietly becoming neutral. These are valuable engineering semantics. They are not calibrated confidence and are not a newly invented rejection framework.
4. **Empirical contribution: documented whole-pipeline trade-offs.** We compare independent deterministic SentiWordNet and shallow-grammar hybrid implementations on identical texts, retain missing predictions in denominators, and expose precision/recall and coverage differences. Different extraction dictionaries/rules/category mappings mean it is not a scorer-only experiment.

CSV upload, a dashboard, a five-band threshold scheme, averaging review scores, larger dictionaries, using real Booking reviews, and writing IEEE-style pseudocode are useful project outputs. They do not independently establish research novelty. A cleaned subset of existing reviews is not a newly human-annotated benchmark.

## What the current evidence actually supports

Authoritative run: `output/experiments/2026-10-21/expanded-sentiwordnet-release/semeval-development/metrics.csv`.

| Metric on 148 eligible sentence/category cases | SentiWordNet | Hybrid |
|---|---:|---:|
| Correct cases | 72 | 85 |
| Accuracy | 48.65% | 57.43% |
| Classification coverage | 54.73% | 63.51% |
| Conditional accuracy on scored cases | 88.89% | 90.43% |
| Macro-F1 | 0.4037 | 0.3999 |
| Category/polarity tuple precision | 0.7232 | 0.6828 |
| Category/polarity tuple recall | 0.5000 | 0.6111 |
| Category/polarity tuple-F1 | 0.5912 | 0.6450 |

The hybrid recovers more cases and has an **8.78 percentage point** overall accuracy advantage on this development adaptation. SentiWordNet has higher tuple precision and slightly higher macro-F1. We cannot honestly claim that Hybrid is superior on every measure. Conditional accuracy excludes abstentions, so it must not replace end-to-end accuracy in the headline.

The 148 cases were inspected during development, come from a small 30-parent-review source, and use a custom six-category crosswalk. They are not an untouched holdout or an official SemEval leaderboard score. Four neutral gold cases make class-balanced conclusions unstable. Neither component ablation, override ablation, scorer-only controlled comparison, nor paired significance testing has established which mechanism caused improvement.

On all 3,089 cleaned Booking Italy reviews, at least one aspect is scored for 81.42% (SentiWordNet) and 87.41% (Hybrid), but Complete is only 1.65% and 7.96%. There is no independent aspect gold here: these are availability and processing-coverage observations, not sentiment accuracy or proof of real-world correctness. These facts limit robust-generalization claims even though the inputs are real reviews.

## Recommended wording for a viva or contribution paragraph

> We contribute an auditable hotel-review analysis framework that integrates deterministic compiler-based sentiment analysis and an independent grammar-assisted VADER–TextBlob hybrid. Our implementation preserves source-linked aspect evidence, records guarded lexical transformations and score overrides, and separates neutral sentiment from incomplete or unavailable analysis. A reproducible comparison reports both prediction quality and coverage, showing improved recovery by the hybrid with a precision and class-balance trade-off.

If asked “What new algorithm have you invented?”, the honest response is: **We have not invented VADER, TextBlob, SentiWordNet, or a fundamentally new learning algorithm. Our current contribution is the domain-specific architecture, explicit evidence and failure semantics, traceable adaptation policy, and measured comparative implementation.**

## Highest-value evidence needed to strengthen a methodology claim

- Freeze code/resources before annotating or evaluating fresh reviews; split by whole parent review and prevent duplicate leakage. Include an untouched, independently annotated hotel test set with documented guidelines and preferably two annotators plus agreement.
- Hold extraction fixed and compare VADER-only, TextBlob-only, and their fusion on exactly the same aspect contexts. This isolates fusion instead of changing the extractor at the same time.
- Add one-at-a-time removal tests for guarded aliases, domain overrides, attachment/inheritance rules, and source-evidence requirements. Report each feature's effect on held-out precision, recall, macro-F1, tuple-F1, and abstention/coverage. Do not select favorable examples as the primary evaluation.
- Evaluate diagnostics: annotate whether allegedly Complete rows actually miss sentiment-bearing content. Report whether Partial/Unsupported flags identify real omissions. Completeness is currently a heuristic, not a verified quality guarantee.
- Report full-pipeline paired uncertainty and error categories; compare to a suitable external ABSA baseline if making a stronger research claim. Existing-paper scores from different datasets/tasks are not directly comparable.

These are proposed additional experiments, not features implemented or results obtained by this research note.
