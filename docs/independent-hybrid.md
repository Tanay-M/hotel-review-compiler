# Independent grammar-assisted VADER–TextBlob hybrid (v2)

Implemented 15 October 2026. Compare the unchanged SentiWordNet compiler with the independent hybrid using the offline research commands. Since 18 October the [WebUI also exposes both methods](web-hybrid-demo.md), including single-review comparison and hybrid CSV traces. No SQL, LLM, API key, or newly trained hotel model is required.

## Code and linguistic capabilities

**18 October vocabulary update:** [Booking-guided expansion](hybrid-vocabulary-expansion.md)
adds 671 total aspect phrases and a 497-form guarded lexical catalog. Earlier
paper experiments remain frozen; new experiments record the vocabulary resource
hash and scoring-copy evidence.

| File | Responsibility |
|---|---|
| `hotel_compiler/hybrid_nlp.py` | Contraction/source mapping; TextBlob POS and phrase chunks; aspect matching; grammatical attachment; limited inheritance; contextual rules |
| `hotel_compiler/resources/hybrid_domain.json` | Independent six-category aspect phrases, price exclusions and contextual score rules |
| `hotel_compiler/hybrid_vocabulary.py` and `resources/hybrid_vocabulary.json` | Expanded aspect lookup, guarded normalization and its provenance |
| `hotel_compiler/hybrid.py` | VADER/PatternAnalyzer, evidence-aware fusion, aspect and whole-review results |
| `hotel_compiler/sentiment_policy.py` | Descriptive five-band labels; separate Mixed label |
| `hotel_compiler/research_runner.py` | Independent execution, complete row retention, separate opinion rows, grammar CSVs, metrics and metadata |
| `tests/test_independent_hybrid.py` | Authored contracts; not an independent accuracy dataset |

The hybrid does not call the baseline lexer, predictive parser, semantic analyzer, opinion vocabulary or SentiWordNet scorer. The optional legacy `compiled` argument validates only text/ID identity, never its analysis. The runner no longer supplies it.

TextBlob PatternParser supplies sentence-token groups, POS tags and NP/VP/adjective/preposition chunks. Noun phrases are assembled from NP chunks, avoiding the Brown-trained default extractor and corpus downloads. This is shallow parsing plus attachment rules, not dependency parsing. Optional relation/lemma modes are not used. Installed English tagging resources are hashed.

Patterns: adjective-before-aspect, aspect-predicate, lexical opinion verb-object, coordinated subjects, shared predicates, contrasts and immediate it/they references with a unique previous target. Ambiguous references remain unresolved. Unknown adjectives can be extracted without appearing in the old vocabulary, but may lack sentiment evidence.

VADER receives original casing, punctuation and informal sentiment cues. PatternAnalyzer receives a contraction-expanded copy preserving casing/punctuation. Whole-review scoring is separate. Ratings, source feedback headings and gold labels never enter model input.

Six categories remain Room, Staff, Service, Food, Cleanliness and Facilities. Aspect matching uses an independent dictionary; it is not learned category recognition. Price adjectives are excluded from aspect-quality predictions and diagnosed. Location/Price/Value remain outside scope.

## Scoring, synthesis and status

Both analyzers execute. If either fails, the score is unavailable. When both have evidence, lexical fusion L = 0.5*VADER compound + 0.5*TextBlob polarity. When only one has evidence, use its score. Neither with evidence means unavailable, not neutral. A zero TextBlob assessment can be neutral evidence. Subjectivity is recorded, not interpreted as confidence.

For an aspect context, an unambiguous configured category rule can replace L. Preserve raw V/T, L, final score, matched text and rule ID. Opposing rule signs prevent an override. Rules cover room quietness/noise/space/comfort, hygiene, bland food, prompt/slow service, functional failure/success and missing hot water. These values are project conventions, not library source values. Local domain negation applies once; the old compiler's modifiers are never applied to library scores. Whole-text scoring has no category override.

Five bands: <= -0.5 Strong Negative; (-0.5,-0.05) Weak Negative; [-0.05,+0.05] Neutral; (+0.05,+0.5) Weak Positive; >= +0.5 Strong Positive. Missing is Unavailable. Bands are descriptive, not confidence or human-validated intensity classes.

Average extracted context scores only when all are available; otherwise aspect mean is unavailable. Positive and negative coexistence yields Mixed independently of the mean. Whole-review lexical score has a different scope.

- Complete: candidates exist, all are scored, no detected unresolved/scope diagnostic. This is heuristic processing coverage, not proof of complete understanding.
- Partial: scored candidate plus diagnostics/missing score.
- Unsupported: no scored candidate and no processing failure.
- Processing error: parser or attached scorer failed; preserve diagnostics and available whole-text evidence.
- Invalid input: CSV validation failed; preserve the row.

Sarcasm, complex negation, long pronoun chains, implicit aspects, temporal changes and unlisted aspect synonyms remain limitations. Not-only constructions receive inspection diagnostics. Neither library knows every adjective. Spell correction, translation and TextBlob's movie-review classifier are not used.

## Module 1 pseudocode: preprocessing and linguistic evidence

```text
Validate review type, ID and length; preserve original text
Expand contractions in working copy; map characters to original spans
Run TextBlob PatternParser with bundled English resources
Align tokens to original spans; retain POS and phrase/preposition chunks
Assemble noun phrases from NP chunks
Return linguistic evidence and source mapping
```

## Module 2 pseudocode: independent grammatical attachment

```text
Longest-match independent six-category aspect phrases
Split sentences, contrasts and coordinated predicates
Retain coordinated noun subjects together
For each segment:
    discover adjectives and lexical opinion candidates
    exclude price opinions and record scope diagnostics
    inherit only safe shared subjects / unique immediate pronoun targets
    attach attributive opinions forward and predicate opinions backward
    attach opinion verbs to following targets
    share trailing predicates across coordinated subjects
    retain functional and unknown predicates without a sentiment-word gate
    emit original local context, target spans and grammar rule
    diagnose unresolved text
```

## Module 3 pseudocode: hybrid fusion and contextual evidence

```text
V = VADER(original context)
T = PatternAnalyzer(contraction-expanded context)
If either failed: return unavailable with component error
If both have lexical evidence: L = w*V.compound + (1-w)*T.polarity
Else if one has evidence: L = that component's score
Else: L = unavailable
H = L
For aspect contexts, apply an unambiguous configured domain rule to H
Retain V, T, L, H, assessments, subjectivity, rule and matched context
Round to six decimals; assign polarity and descriptive strength
```

## Module 4 pseudocode: synthesis and independent experiments

```text
For every original row, including invalid rows:
    run unchanged SentiWordNet compiler independently
    run grammatical hybrid independently
    retain separate statuses and opinion sets
    export one paired review row; never zip opinions by position
    export linguistic trace, diagnostics and per-method score evidence
If human annotations exist:
    apply identical category crosswalk and denominators
    count missing/conflicting predictions as classification errors
    calculate accuracy, fixed three-class macro-F1 and tuple metrics
Else: export coverage without accuracy claims
Save figures, code snapshot, resource hashes and environment
Label previously inspected benchmarks as development evidence
```

## Running and evidence

```powershell
.\.venv\Scripts\python.exe -m hotel_compiler.research_cli compare output/datasets/real_hotel_random_200.csv --dataset-role random_real --output-dir output/experiments/my-hybrid-v2 --repeats 3
.\.venv\Scripts\python.exe -m hotel_compiler.research_cli evaluate-semeval data/vendor/real-hotel-research/semeval2015_hotels.xml --output-dir output/experiments/my-semeval-development
```

Use new output directories. `review_results.csv` has one row per review. `opinion_results.csv` contains separate system rows; method-specific blanks are expected. `hybrid_tokens.csv`, `hybrid_noun_phrases.csv`, `hybrid_segments.csv` and `diagnostics.csv` expose processing. Metadata, source snapshots and inference notes accompany figures.

The curated 100 is a demo, not an accuracy test. Random 200 has no aspect gold labels. SemEval was inspected before v2 development: current metrics are development/exploratory. A future independent evaluation must split by parent review or use fresh annotations and freeze configuration before testing.
