"""Apply the measured DL extension to the existing manuscript source once."""
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'docs/conference_manuscript.md'
s=p.read_text(encoding='utf-8')
if '### E. Independent Deep Learning Reanalysis' in s:
    raise SystemExit('DL revision already applied; edit the source directly.')
# Make room for two research sources first cited at the end of the survey.
s=re.sub(r'\[(31|32|33)\]',lambda m:f'[{int(m[1])+2}]',s)
s=s.replace('# An Auditable Grammar Assisted Hybrid for Aspect Sentiment Analysis of Hotel Reviews',
 '# Auditable Aspect Sentiment Analysis of Hotel Reviews with Selective Deep Learning Reanalysis',1)
abstract='''Hotel reviews contain aspect-specific opinions that fixed vocabularies and shallow grammatical rules can leave unresolved. We present an auditable pipeline combining a SentiWordNet compiler baseline, an independent VADER-TextBlob hybrid, and selective deep learning reanalysis. Only reviews marked Partial or Unsupported by the hybrid enter a category-conditioned MiniLM classifier; Complete outputs are retained. The transformer and neural head are fine-tuned together on human-labelled hotel sentences. The selected DL result is independent of hybrid opinion matches, while original evidence and abstentions remain visible. On a declared SemEval-2015 hotel adaptation with 148 eligible sentence-category cases, SentiWordNet and Hybrid achieve 48.65% and 57.43% polarity accuracy and 0.5912 and 0.6450 pair-F1. A separate mapped Trip-MA experiment contains 1,474 test segments: selective DL increases category-polarity micro-F1 from 0.4184 to 0.4993 overall and from 0.3261 to 0.4813 on 1,113 unresolved segments. Four mapped categories improve, while Facilities declines. On 500 real Booking reviews, 456 enter DL and 383 receive accepted categories; these unlabelled counts measure coverage, not correctness. The contribution is an evidence-preserving integration and measured unresolved-review recovery, rather than a new transformer algorithm. Previously inspected benchmarks, approximate category mappings and merged Neutral/Mixed supervision limit generalization; the reported results are exploratory.'''
s=re.sub(r'(?s)(## Abstract\n\n).*?(\n\nKeywords:)',lambda m:m[1]+abstract+m[2],s,count=1)
s=s.replace('Keywords: aspect-based sentiment analysis; hotel reviews; compiler pipeline; SentiWordNet; VADER; TextBlob; reproducible evaluation.',
 'Keywords: aspect-based sentiment analysis; hotel reviews; SentiWordNet; VADER; TextBlob; MiniLM; selective deep learning.')
s=s.replace('We compare two complete, independently executed systems.','We compare two independently executed lexical systems and extend the hybrid with a selective DL stage.',1)
old='The contributions are source-preserving analysis, inspectable deterministic and shallow grammatical attachment, evidence-aware VADER-TextBlob integration, and reproducible comparison with abstentions retained. Scores, five descriptive bands, Mixed outcomes, diagnostics, and one tabular result per review support demonstration and reporting. Tool recency is not evidence of superiority: the study reports measures favoring either system and makes no claim of an untouched test set or a new pretrained model.'
new='''The fifth processing stage addresses the hybrid's unresolved outputs. A fine-tuned category-conditioned transformer processes the entire original text of each Partial or Unsupported review, without requiring an accepted hybrid aspect or opinion. Complete reviews retain their hybrid analysis. The selected DL output replaces that review's selected analysis rather than appending predictions to the lexical opinions; original hybrid evidence remains available. A separate human-annotated hotel experiment measures the change in category-polarity recovery.

The applied contributions are source-preserving compiler and hybrid analysis, selective independent DL reanalysis, and reproducible evaluation that records recovered predictions, regressions and abstentions. Five descriptive lexical bands, Mixed outcomes and tabular review results support reporting. We do not claim invention of sentence-pair ABSA, generic fallback routing or a pretrained transformer. The experiments compare complete systems under declared mappings and do not establish state-of-the-art performance or an untouched final test.'''
assert old in s;s=s.replace(old,new)
old='Such methods address representational limitations beyond lexical matching, but introduce training, model resources, and experimental requirements outside the present implementation. We retain a local lexicon-based system whose intermediate decisions can be inspected during a compiler-design review.'
new='These methods motivate our category-conditioned sentence-pair formulation. We fine-tune a compact transformer on hotel supervision and invoke it only for unresolved hybrid reviews. This adapts an established learning formulation within a source-traceable application; it is not a reproduction of either paper\'s model or published benchmark score.'
assert old in s;s=s.replace(old,new)
needle='## III. Architectural Diagram'
survey='''MiniLM [31] compresses pretrained transformer representations through self-attention distillation, motivating a small local encoder. We initialize from the all-MiniLM-L6-v2 checkpoint and fine-tune it for category-conditioned classification; we do not perform distillation ourselves. Jiménez Zafra et al. [32] introduced multilingual aspect-oriented hotel annotations. Their English Trip-MA release supplies our human category/polarity supervision, including implicit opinions. Its Neutral/Mixed class and category scheme require an explicit crosswalk rather than being treated as identical to our lexical outputs.

'''
s=s.replace(needle,survey+needle,1)
old='{{WIDEFIG:architecture_single|Fig. 1. SentiWordNet compiler architecture: (a) preprocessing and validation, (b) lexical and syntax analysis, (c) semantic analysis and lexical lookup, and (d) adjustment and final records. The independent VADER-TextBlob hybrid is described in Section IV.}}'
new='{{WIDEFIG:architecture_single|Fig. 1. Unified architecture with independent SentiWordNet and VADER-TextBlob paths. Only Partial or Unsupported hybrid reviews enter the fifth stage, which reads original sentences with category queries and selects an independent DL result. Complete reviews retain Hybrid. Shading identifies existing library components; outlined blocks show project processing and integration.}}'
assert old in s;s=s.replace(old,new)
old='The architecture comprises preprocessing and validation, lexical and grammatical analysis, semantic attachment and scoring, and adjustment and result generation. The independent analysis paths retain their own outputs throughout comparison. Figure 1 depicts the SentiWordNet compiler path; the VADER-TextBlob path uses independent shallow grammatical extraction and lexical fusion as described below.'
new='The architecture contains five processing stages: preprocessing and validation, lexical and grammatical analysis, semantic attachment and scoring, adjustment and result generation, and independent DL reanalysis. Figure 1 retains separate SentiWordNet and Hybrid paths. The fifth stage is gated by the Hybrid status alone; it does not use a learned diagnostic selector or require opinions recognized by either lexical front end. All stages preserve original review identity and evidence.'
assert old in s;s=s.replace(old,new)
methods='''### E. Independent Deep Learning Reanalysis

For hybrid result H and original review x, the stage runs only when H.status is Partial or Unsupported. Complete reviews retain H; invalid input and component failures retain their error status. The model receives every original sentence of the selected review, not only the unmatched clause or extracted aspects. Hybrid opinion lists, scores and grammar matches are not model inputs. This allows category inference for an implicit complaint such as a long wait at reception.

Let u denote an original sentence and q_c a natural-language category description. The same MiniLM encoder and shared four-class neural head process the pair (u, q_c), yielding the probability vector in (4). Eight queries cover Room, Cleanliness, Service, Food, Facilities, Excluded, Other and NotRelated. The first five are reported categories; Location/Value remain Excluded. There are eight queries to one network, not eight separately trained transformers. Staff is pooled under Service because the source has no separately labelled Staff class. States are Absent, Negative, Neutral/Mixed and Positive; the merged third class is retained explicitly.

{{EQ:dl_prob}}

Both encoder and classification head are fine-tuned using weighted cross-entropy (5), where B is a minibatch, y_j is its target state and w_y is a class weight. Weights are proportional to the square root of inverse state frequency and normalized to mean one. The weighted reduction divides by the sum of target weights within the minibatch. Absent targets use categories not annotated for a segment under the source scheme. No AI-generated labels or review ratings supply supervision.

{{EQ:dl_loss}}

At inference, the highest-probability state is accepted only if it is not Absent and exceeds category threshold tau_c. Thresholds are selected on validation category-polarity F1 from {0.25, 0.35, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90}; higher thresholds win ties. Only in-scope accepted categories are emitted. Pairs exceeding 160 WordPiece tokens remain unavailable with a warning; no silent truncation or successful-completion claim is made.

The DL output becomes the selected result for each routed review, even when it abstains. It is not unioned with hybrid opinions, and an abstention does not quietly fall back to Hybrid or Neutral. Original hybrid evidence remains separately accessible. Sentence spans support inspection but are not learned exact target/opinion spans. Opposing accepted polarities retain Mixed; source Neutral/Mixed is displayed as Mixed/uncertain.

For accepted Positive/Negative predictions, (6) reports a model direction index using their probabilities. It describes relative positive/negative belief, not lexical intensity, a calibrated probability or a star rating. Category indices average accepted sentence indices, followed by an equal-category review mean. A merged Neutral/Mixed prediction leaves the corresponding aggregate index unavailable. The lexical five-band policy is not imposed on these unvalidated neural probabilities.

{{EQ:dl_direction}}

{{ALG:5}}

'''
s=s.replace('## V. Results and Implementation',methods+'## V. Results and Implementation',1)
s=s.replace('Table I distinguishes the annotated evaluation, a real-review sample, and the cleaned Italy corpus with its nested demo subset.',
 'Table I distinguishes annotated evaluation and training sources, a real-review sample, and the cleaned Italy corpus with its nested demo subset.',1)
dataset='''Trip-MA's English author release [32] contains 258 source training reviews and 111 test reviews. We remove 36 training reviews sharing a hotel with test, derive validation from the remaining training hotels using a fixed hash, and exclude cross-split text duplicates or conflicting duplicate labels. Prepared train/validation/test partitions contain 2,040/602/1,474 segments from 180/42/111 reviews and 157/39/103 hotels. Hotel IDs, review IDs and normalized text hashes are disjoint. Source token/POS/lemma serialization is detokenized from original surface tokens; it is not an untouched raw-text export or generated replacement text. Original serialization, mapped labels and hashes are retained locally.

The DL crosswalk maps ROOMS to Room, CLEANLINESS to Cleanliness, SERVICE/CHECKIN to Service, FOOD to Food, and BUILDING/BUSINESS to Facilities; LOCATION/VALUE are Excluded. OTHER and NOTRELATED are separate background queries. Source explicit/implicit positive codes map to Positive, negative codes to Negative, and x/ix to Neutral/Mixed. Two overlength training segments are excluded, leaving 2,038 usable segments and 16,304 sentence/category pairs. All 602 validation and 1,474 test rows remain in evaluation denominators. The source category scheme differs from SemEval and the six-category lexical systems, so these experiments are reported separately.

'''
s=s.replace('### B. Preprocessing and Validation Implementation',dataset+'### B. Preprocessing and Validation Implementation',1)
s=s.replace('Python implementations run locally without LLM calls.','Python implementations run locally without external LLM calls. DL training and inference use a local compact transformer.',1)
s=s.replace('The latest software regression suite passes 210 authored tests;','The latest software regression suite passes 243 authored tests;',1)
# The training figure follows the three previously existing figures.
s=s.replace('Fig. 4.', 'Fig. 5.').replace('Fig. 5. Per-class','Fig. 6. Per-class')
# Previous replacement intentionally touches only the figure caption prefix.
s=s.replace('Table III and Fig. 4','Table IV and Fig. 5').replace('{{TABLE:metrics}}','{{TABLE:metrics}}')
implementation='''### F. Deep Learning Training and Execution

We initialize the sequence classifier from sentence-transformers/all-MiniLM-L6-v2 at pinned revision 1110a243fdf4706b3f48f1d95db1a4f5529b4d41. The encoder and neural head receive gradient updates; this is supervised DL rather than a frozen embedding plus classical classifier. A separate earlier frozen-encoder ML pilot is not the selected DL system reported here. Training settings appear in Table III. The highest validation pair micro-F1 selects epoch 3 before this run's test scoring. Saved encoder parameter hashes differ before and after training, verifying actual updates. Training uses no AI-labelled examples.

{{TABLE:dl_training}}

Three epochs require 248.0 seconds including validation on an RTX 2050. Peak allocated PyTorch tensor memory is 510.1 MiB, excluding total process and GPU-driver memory. Validation F1 rises from 0.4052 to 0.4764 and 0.5037 (Fig. 4). These are one-run measurements, not multi-seed averages or a controlled runtime comparison with lexical systems. The installed dashboard uses the saved local checkpoint and serializes inference; it uses CUDA when available and otherwise CPU.

{{FIG:dl_validation_f1|Fig. 4. Validation category-polarity pair F1 over the three training epochs. Epoch 3 is selected without using this run's test scores.}}

For the 500-review real Booking subset, the unchanged hybrid emits 44 Complete, 399 Partial and 57 Unsupported outputs. Exactly 456 unresolved reviews enter DL; 383 receive accepted category predictions and 73 abstain. Forty-four Complete results retain Hybrid, and no model errors occur. These are routing/coverage counts without human Booking gold, not 383 confirmed corrections or Complete reviews. An authored demonstration, "We waited two hours before anyone checked us in.", is Unsupported in Hybrid and receives Service/Negative from DL, with direction index approximately -0.7427. It is illustrative rather than an additional annotated accuracy case.

'''
s=s.replace('## VI. Performance and Metrics',implementation+'## VI. Performance and Metrics',1)
s=s.replace('### D. Validity and Limitations','### E. Validity and Limitations',1)
results='''### D. Selective Deep Learning Evaluation

Trip-MA evaluation uses the frozen checkpoint and thresholds on all 1,474 prepared test segments, with 724 in-scope gold category-polarity pairs. Hybrid predicts 777 pairs and matches 314; the selected Hybrid-DL pipeline predicts 746 and matches 367. Table VI reports joint micro-precision, recall and F1. A match requires both category and polarity. Exact segment match requires identical predicted and gold sets, including empty sets; many background segments make it an imperfect summary of opinion recovery. Missing predictions remain recall errors.

{{TABLE:dl_metrics}}

The full pipeline's pair-F1 increases from 0.4184 to 0.4993, an 8.09 percentage-point gain. The 1,113 segments originally marked Partial or Unsupported contain 414 gold pairs: Hybrid matches 127 of 365 predictions, while DL matches 180 of 334. Their F1 increases from 0.3261 to 0.4813, a 15.52-point gain (Fig. 7). The other 361 segment outputs remain unchanged. These test inputs are annotated segments rather than 1,474 full reviews; the Booking demonstration separately verifies review-level routing.

{{FIG:dl_joint_pair_f1|Fig. 7. Joint category-polarity micro-F1 on all Trip-MA test segments and the subset routed from Hybrid. Values are separate from SemEval polarity accuracy.}}

The extension adds 97 correct pairs and loses 44 previous correct pairs, a net gain of 53; it introduces 114 false pairs and removes 198. A paired bootstrap with 1,000 resamples of the 111 parent reviews gives a descriptive 95% interval of +4.94 to +11.67 F1 percentage points for DL minus Hybrid. The interval does not remove development reuse or establish general superiority. Four mapped categories improve, while Facilities F1 decreases from 0.1854 to 0.1389 (Fig. 8).

{{FIG:dl_category_f1|Fig. 8. Per-category joint pair F1 on the same mapped Trip-MA test. Facilities declines despite the aggregate improvement.}}

Cleanliness gains partly reflect taxonomy alignment: the hybrid often labels room hygiene as Room while Trip-MA uses Cleanliness. A post-hoc sensitivity analysis merging Room and Cleanliness in both gold and predictions still increases all-test F1 from 0.4420 to 0.5147, without refitting. This is a sensitivity analysis of the same predictions, not another independent test. No direct ranking of DL against SentiWordNet is inferred from the different SemEval experiment, and no five-class strength accuracy is claimed.

'''
s=s.replace('### E. Validity and Limitations',results+'### E. Validity and Limitations',1)
s=s.replace('No preregistration, paired significance test, or component ablation isolates the contribution of vocabulary, grammar, fusion, or overrides.',
 'No preregistration or component ablation isolates the contributions of vocabulary, grammar, fusion or overrides. The separate DL experiment includes a descriptive paired cluster bootstrap.',1)
s=s.replace('Published neural results in Section II concern different tasks and are not comparable accuracy baselines here.',
 'Published neural scores in Section II concern different tasks and are not comparable accuracy baselines here.',1)
limitations='''The Trip-MA test was already inspected during earlier project experiments. Although this DL run freezes checkpoint and thresholds using validation before scoring test, it is a follow-up exploratory comparison rather than a new untouched final evaluation. One seed and approximate Facilities/Service mappings limit robustness claims. The source does not supervise separate Staff or strong/weak intensity labels; Neutral and Mixed remain merged. DL predicts sentence-level category/polarity rather than exact targets, and its probabilities are not calibrated strength scores. A status gate can miss wrong hybrid outputs labelled Complete or route a correct Partial result to a worse prediction. Source licensing for redistributing Trip-MA is not explicit; downloaded and prepared copies remain local rather than being bundled in the public codebase. Fresh independent human annotation and repeated-seed experiments remain necessary.

'''
s=s.replace('## VII. Conclusion',limitations+'## VII. Conclusion',1)
start=s.index('## VII. Conclusion\n\n');end=s.index('\n\n## References',start)
conclusion='''## VII. Conclusion

The project combines an auditable SentiWordNet compiler baseline, independent VADER-TextBlob hybrid analysis, and selective DL reanalysis of unresolved hybrid reviews. The lexical comparison yields 48.65% versus 57.43% polarity accuracy and 0.5912 versus 0.6450 pair-F1 under the declared SemEval mapping; SentiWordNet retains slightly higher macro-F1 and pair precision. On a separate mapped Trip-MA evaluation, the Hybrid-DL pipeline increases pair-F1 from 0.4184 to 0.4993 overall and from 0.3261 to 0.4813 on unresolved segments, with a Facilities regression. The real Booking demonstration routes 456 of 500 reviews and obtains accepted categories for 383 without treating coverage as correctness. The applied contribution is independent, source-traceable DL reanalysis with retained original outputs and explicit abstentions. Previously inspected data, ontology differences, merged labels and a single training run limit the evidence. Fresh human-held-out evaluation, separate Staff/intensity supervision and repeated-seed experiments are needed before stronger generalization claims.'''
s=s[:start]+conclusion+s[end:]
assert not re.search(r'\bmodules?\b',s,re.I)
p.write_text(s,encoding='utf-8')
print('Updated manuscript prose with fifth-stage DL methodology and saved results.')
