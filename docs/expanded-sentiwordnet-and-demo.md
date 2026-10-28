# Expanded SentiWordNet and real Booking demo

Implemented and evaluated October 21, 2026. This is a separate expanded compiler profile. The original resources, vocabulary, scoring policy and predictions remain available as the original profile; the independent VADER–TextBlob hybrid is unchanged.

## Open and use the website

Double-click **Start_Demo.bat** in the project root. It starts the local server, checks readiness and opens **http://127.0.0.1:8000/**. Running it again reuses the server. **Stop_Demo.bat** stops only the server identified by this project's launcher. `Start_Demo.bat -Port 8010` selects another port; use the same argument when stopping it. The launcher starts the server in the background, so closing its initial window does not stop the website. Logs/PID files stay in ignored `tmp/web-demo/`.

The default UI method is **SentiWordNet compiler (expanded)**. The menu also contains **VADER + TextBlob hybrid** and **SentiWordNet compiler (original)**. Single-review comparison uses the selected original/expanded compiler against the hybrid, retaining separate results and traces.

For real data choose **CSV & dashboard → Use real Booking 500**. This loads the cleaned CSV and analyzes all 500 original review records with the selected method. Every review has its own table row and result/trace button. To compare the other method, change the method and run the same real-data button again. The offline experiments retain both outputs together; the UI retains one batch at a time. The dashboard can include complete + partial reviews when explicitly selecting the recognized-opinions scope. Completeness counts remain visible and are not relabeled.

## Resource expansion

| Resource | Original compiler | Expanded compiler |
|---|---:|---:|
| Aspect phrases | 345 | 772 |
| Opinion entries | 356 | 21,181 |
| Opinion aliases | 32 | 752 |
| Genuine packaged synsets | 315 | 14,311 |
| Categories | 6 | 6 |

The expanded compiler adds 20,812 native adjective lemmas and 13 selected experience/action verb lemmas. The underlying corpus is the checksum-pinned genuine SentiWordNet 3.0 distribution. New native words use their first WordNet-ranked sense rather than the sense with the strongest positive/negative score. Existing configured senses, compatibility restrictions, contextual sense choices and domain adjustments are retained. Source P/N, objective evidence and lexical P-N are never invented or rewritten. Zero source polarity remains zero unless an already-existing explicit domain policy applies.

The shared reviewed hotel-aspect additions and lexical forms broaden coverage, but the compiler does not call the hybrid parser, VADER or TextBlob to identify or score opinions. It can run with Python site packages disabled. Original library/tool resources and hybrid fusion/contextual rules are unchanged.

This is a broad adjective lexicon, not all WordNet noun/verb/adverb senses or perfect word-sense disambiguation. A dictionary adjective does not necessarily express a subjective opinion in context. New senses can be objective or unsuitable for a particular hotel meaning. These limitations remain visible through native evidence and development evaluation.

## Grammar and robustness changes

- Retains the original controlled grammar, equipment predicates, adjective-before-noun forms, subject/predicate coordination, possession and explicit contexts.
- Adds bounded deterministic recovery of attributive and predicate opinions inside otherwise unsupported clauses. Unexplained language keeps diagnostics and Partial status.
- Supports native experience verbs with explicit objects: “I loved the breakfast” and “We enjoyed the pool.” Service-action verbs attach to their explicit subjects.
- Resolves comparative/superlative forms while keeping original source text. Native non-adjective forms are excluded from stemming so “offer” cannot become “off.”
- Resolves explicit `it/they/which/that/who` references only with a unique preceding target and bounded context; an immediately following sentence may inherit an explicit pronoun target. Ambiguous or intervening unresolved language blocks inference.
- Supports comma-separated predicate lists, safe coordinated subjects, `&`, colons, and contraction forms such as “it's” and “they're.”
- Treats explicit facility absence such as “no hot water” as a negated availability predicate, with the normalization rule and source spans retained.
- Preserves negation scope and source offsets; “not only clean but also comfortable” does not negate clean. Quantified or multiple negation can remain unsupported instead of inventing a blanket sign.
- Distinguishes grammatical “felt like” from the opinion verb like, and factual links such as kept/found from adjective opinions. Source-backed adjective entries remain subject to syntax rather than acting as unrestricted keyword matches.
- Uses cached profile-specific lexical tables and thread-local configuration so simultaneous original/expanded requests do not leak vocabulary or resources between each other.

The grammar remains deterministic and shallow. It does not fully interpret sarcasm, implicit complaints, tense/modal meaning or all narrative constructions. Adding vocabulary is not evidence that every attachment is correct.

## Cleaned real dataset

Source: the supplied Crawlfeeds Booking Italy export, byte-matched to the publisher release. The original two-column source remains unchanged. The cleaned derivative removes exact missing-marker lines and nonprinting C0 controls, normalizes whitespace, removes blank bodies and exact cleaned-text duplicates, and retains ordinary wording such as “Nothing.” It does not repair spelling/punctuation, paraphrase, extract only favorable sentences or select by model outputs.

| Preparation | Records |
|---|---:|
| Original source rows | 4,367 |
| Blank/missing bodies removed, including an N/A-only body | 1,266 |
| Exact cleaned-text duplicate rows removed | 12 |
| Unique nonblank cleaned reviews | 3,089 |
| Fixed uniform random demo sample, seed 172026 | 500 |

Inputs contain only `sr.no,review`. [Dataset instructions](../output/datasets/booking_cleaned/README.md) link the 500-review demo, full corpus, four UI-ready parts, source maps and cleaning audit. The 500 is a subset of the 3,089, not additional independent observations. Source maps identify every original ordinal and original/cleaned text hash. License and attribution: [CC BY-NC 4.0, Crawl Feeds](../output/datasets/ATTRIBUTION.md).

## Final development comparison

Authoritative results: `output/experiments/2026-10-21/expanded-sentiwordnet-release/`. Earlier pilot/intermediate directories remain separate and are not the final reported result. Grammar/function-word guards were developed using authored cases and inspected real reviews; the benchmark is already an inspected development benchmark. No claim of unseen generalization or statistical superiority is made.

Both expanded systems receive identical text, six category labels, the same 148-case SemEval mapping, abstention policy and three-class evaluation. The original compiler is retained for historical comparison. This is a comparison of complete pipelines, not a controlled experiment changing only their scoring lexicons. Aspect dictionaries, attachment rules and some aspect-category mappings still differ; conflicts retaining the original compiler mapping are enumerated in `provenance_expanded.json`. No fusion weights, hybrid overrides or score thresholds were tuned in this task. Five-band strengths remain descriptive; Strong/Weak signs collapse to the three annotated polarity classes for evaluation.

| Measure | Original SWN (historical) | Expanded SWN | Unchanged hybrid |
|---|---:|---:|---:|
| Correct / eligible | 42 / 148 | 72 / 148 | 85 / 148 |
| All-case accuracy | 28.38% | 48.65% | 57.43% |
| Macro-F1 | 0.2260 | 0.4037 | 0.3999 |
| Coarse tuple precision | 0.9200 | 0.7232 | 0.6828 |
| Coarse tuple recall | 0.2840 | 0.5000 | 0.6111 |
| Coarse tuple-F1 | 0.4340 | 0.5912 | 0.6450 |

The expansion improves the compiler substantially over the narrow original. The hybrid still has higher all-case accuracy, recall and tuple-F1. Expanded SWN has slightly higher macro-F1, partly because it correctly labels one of only four Neutral cases while the hybrid labels none. The tiny neutral support and development reuse limit that inference. The final guards suppress some false matches and lower the headline count versus an earlier pilot; the final 72-case result is retained rather than selecting the best intermediate score.

### Real Booking coverage, not accuracy

| Cohort / measure | Expanded SWN | Hybrid |
|---|---:|---:|
| Demo: some scored aspect | 403 / 500 (80.60%) | 443 / 500 (88.60%) |
| Demo: Complete | 10 | 44 |
| Demo: Partial | 393 | 399 |
| Demo: Unsupported | 97 | 57 |
| Full cleaned corpus: some scored aspect | 2,515 / 3,089 (81.42%) | 2,700 / 3,089 (87.41%) |
| Full cleaned corpus: Complete | 51 | 246 |
| Full cleaned corpus: Partial | 2,464 | 2,454 |
| Full cleaned corpus: Unsupported | 574 | 389 |

Neither run has invalid inputs or processing errors. Both preserve every cleaned review's result, including unsupported outcomes. Long narratives and out-of-scope Location/Price topics still make whole-review completeness low; recognized-aspect coverage must not be called complete analysis or accuracy. Booking has no independent aspect-polarity gold labels. The full corpus's `booking-all/all_reviews.csv` contains 3,089 paired rows linked to original source ordinals, while the 500-demo run has its own paired review/opinion tables. Vector PDF/SVG graphs and numerical CSV metrics are generated for the annotated and sample comparisons.

The IEEE Word/PDF has now been revised to use this final comparison throughout the abstract, methodology, diagrams, tables, graphs and conclusion. The paper presents only SentiWordNet versus Hybrid; the current broad compiler is its sole SentiWordNet approach. See [paper and evidence notes](../output/paper/PAPER_README.md). The prior paper is archived.

## Code locations and reproduction

| Responsibility | File |
|---|---|
| Profile isolation | `hotel_compiler/compiler_profiles.py` |
| Native corpus/resource builder | `scripts/build_expanded_sentiwordnet.py` |
| Expanded vocabulary, unchanged-source synsets and provenance | `hotel_compiler/resources/domain_expanded.json`, `sentiwordnet_expanded.tsv`, `provenance_expanded.json` |
| Longest matching, morphology and lexical guards | `hotel_compiler/lexer.py` |
| Bounded additional grammar and recovery | `hotel_compiler/expanded_parser.py` |
| Aspect binding and native scoring | `hotel_compiler/semantics.py`, `sentiwordnet.py` |
| Browser adapters and real-data button | `web_analysis.py`, `web_batch.py`, `web.py`, `web_assets/dashboard.js` |
| Cleaning and CSV creation | `scripts/prepare_clean_booking_demo.py`, `build_clean_booking_demo.mjs` |
| Full real-corpus comparison | `scripts/compare_clean_booking_corpus.py` |
| Authored regression contracts | `tests/test_expanded_sentiwordnet.py`, `tests/test_web_hybrid.py` |

```powershell
# Single expanded compiler review (original remains the default CLI profile)
.venv\Scripts\python.exe -m hotel_compiler --compiler-profile expanded "I loved the breakfast."

# Paired real-data comparison; choose a new output directory
.venv\Scripts\python.exe -m hotel_compiler.research_cli compare output/datasets/booking_cleaned/booking_italy_cleaned_demo_500.csv --compiler-profile expanded --dataset-role random_real --output-dir output/experiments/my-expanded-demo --repeats 0

# Full cleaned corpus, with explicit inspected-development role
.venv\Scripts\python.exe scripts/compare_clean_booking_corpus.py --output-dir output/experiments/my-expanded-booking-all

# Annotated comparison; original XML remains a separately downloaded local source
.venv\Scripts\python.exe -m hotel_compiler.research_cli evaluate-semeval data/vendor/real-hotel-research/semeval2015_hotels.xml --compiler-profile expanded --output-dir output/experiments/my-expanded-gold --bootstrap-repeats 1000

.venv\Scripts\python.exe -m unittest discover -s tests
```

Use `--compiler-profile original` to rerun the original compiler. Existing result directories are protected against accidental overwrite. The final software regression suite passes **210 tests**; these tests verify contracts rather than establish sentiment accuracy. The expanded compiler also runs with `python -S`, demonstrating that its analysis does not require VADER/TextBlob/NLTK site packages.
