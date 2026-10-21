# Team 17 complete project review reference

**15 October extension:** The vocabulary and grammar below remain the SentiWordNet baseline reference. The new two-system comparison, five-band policy, offline metrics/figures and all implemented pseudocode are documented in [the research guide](research-run-guide.md) and [module algorithms](implemented-modules-and-pseudocode.md). Broad POS-based extraction is not implemented. Current research execution passes 162 automated tests with research dependencies installed.

Checked against the current implementation on **14 October 2026**. This is the single file to open during the faculty review: it contains the complete configured vocabulary, supported grammar and guards, phase responsibilities, original lexical scores and separate scoring rules, result labels, dashboard calculations, diagnostics, and code locations.

Use the headings or **Ctrl+F** to find an aspect, adjective, alias, diagnostic, or file. The lists below come from the actual packaged `domain.json` and SentiWordNet TSV, rather than a proposed feature list. Recognition is bounded by grammar and semantic guards; being listed does not mean a word works in every possible sentence.

## Contents

1. [Short explanation and scope](#1-short-explanation-and-scope)
2. [Complete partial unsupported and error labels](#2-complete-partial-unsupported-and-error-labels)
3. [Dashboard mean index and denominators](#3-dashboard-mean-index-and-denominators)
4. [Preprocessing and input validation](#4-preprocessing-and-input-validation)
5. [Lexical analysis and all grammar vocabulary](#5-lexical-analysis-and-all-grammar-vocabulary)
6. [Syntax rules and boundaries](#6-syntax-rules-and-boundaries)
7. [Semantic rules and every aspect phrase](#7-semantic-rules-and-every-aspect-phrase)
8. [SentiWordNet and every canonical opinion](#8-sentiwordnet-and-every-canonical-opinion)
9. [Every opinion alias and compatibility guard](#9-every-opinion-alias-and-compatibility-guard)
10. [Every domain calibration and contextual sense](#10-every-domain-calibration-and-contextual-sense)
11. [IR traces and diagnostics](#11-ir-traces-and-diagnostics)
12. [Verified examples and limitations](#12-verified-examples-and-limitations)
13. [Code locations and running the project](#13-code-locations-and-running-the-project)

## 1 Short explanation and scope

> We analyze hotel reviews through a compiler-style pipeline. The lexer recognizes configured phrases while preserving the original text. The parser applies a restricted grammar. Semantic analysis binds opinions to hotel aspects and checks compatibility. SentiWordNet supplies original positive and negative values; transparent domain rules, intensity and negation produce an opinion score. The final IR keeps each aspect opinion separately. CSV processing preserves one output row per review, and the dashboard summarizes the eligible results.

The project runs offline, without an LLM, trained tagger, embeddings, model training, or SQL. SentiWordNet is an existing lexical resource, not our aspect extractor. Categories, issues, senses, aliases, grammar and preference rules are explicit configuration/code.

| Current item | Count / value |
| --- | --- |
| Categories | Room, Staff, Service, Food, Cleanliness, Facilities |
| Aspect phrases | 345 |
| Canonical opinion terms | 356 |
| Opinion aliases | 32 |
| Packaged original SentiWordNet rows | 315 |
| Neutral opinion threshold | 0.05 |
| Historical regression suite | 136 passing tests at the expansion milestone |

The existing authored 100-review development sample produced 88 complete, 6 partial and 6 unsupported outcomes. This measures **supported-language coverage**, not 88% sentiment accuracy. Location and Value/Price are outside the six categories. A retained phrase such as “for the price” is context, not a price opinion.

## 2 Complete partial unsupported and error labels

There are **two layers**. The batch execution layer labels a row `analyzed`, `invalid_input`, or `processing_error`. A successfully analyzed row then has the compiler status `complete`, `partial`, or `unsupported`. The WebUI shows the compiler status if available, otherwise the execution status. Thus `analyzed` does not mean the English was fully supported.

| Displayed status | Exact basis | Meaning / example |
| --- | --- | --- |
| complete | At least one final opinion record AND no syntax/semantic diagnostics. | The room was clean. |
| partial | At least one final opinion record AND at least one diagnostic. | The room was clean but the location was convenient. Room is retained; the location clause is diagnosed. |
| unsupported | No final opinion records. | The location was convenient. No supported aspect/opinion result; overall Unanalyzed. |
| invalid_input | The CSV row has validation issues; it is not sent through the compiler. | Missing/blank review, wrong number of CSV cells, or review longer than 10,000 characters. |
| processing_error | An unexpected Exception escapes analysis for that otherwise valid CSV row; the batch catches it and retains an error result. | A runtime implementation failure. Ordinary unknown language does not produce this label. |

The actual decision in `pipeline.py::analyze_review` is:

```python
if records and not diagnostics:
    status = "complete"
elif records:
    status = "partial"
else:
    status = "unsupported"
```

“Complete” describes successful processing under our supported language. It is **not** confidence, an independent accuracy judgment, or proof that arbitrary English was interpreted correctly. A complete result can be positive, negative, mixed or neutral.

An unrecognized trailing word can prevent an entire clause from being accepted; the parser does not silently keep its adjective and ignore the rest. Other valid clauses can survive recovery. A diagnostic after a valid clause can make the review partial even if that clause yielded a record. Semantic failures, such as “staff were working,” can also yield unsupported if no valid records remain.

**Special cases:** blank single-review text returns unsupported with `EMPTY_INPUT`; blank text in a CSV is instead invalid_input before compilation. Invalid direct API argument types/IDs and oversized single text raise exceptions, rather than becoming a normal review status. A broken shared SentiWordNet resource raises `ResourceError` and aborts the batch; it is not turned into hundreds of per-row processing errors. Malformed/unreadable CSV files or bad headers reject the upload before any batch results are accepted. Duplicate text or IDs are flags, not invalid-input statuses.

### Overall sentiment is a different label

- Both positive and negative records present → Mixed, even if their numeric average is zero.
- Positive present without Negative → Positive; neutral records do not erase it.
- Negative present without Positive → Negative.
- Records exist but all are Neutral → Neutral.
- No records → Unanalyzed, never automatically Neutral.

### Need inspection and coverage

`Need inspection = submitted reviews - complete reviews`. It includes partial, unsupported, invalid_input and processing_error rows; it is a dashboard grouping, not another compiler status.

The completely analyzed card shows two denominators: complete/submitted and complete/analyzed. “Analyzed” includes complete + partial + unsupported and excludes invalid_input/processing_error. Complete coverage can be 100% of analyzed rows while some submitted rows were invalid. A zero denominator yields an unavailable percentage, not zero. Every submitted CSV record still has its own result row.

## 3 Dashboard mean index and denominators

The **Mean index** is an equal-review mean of the final signed opinion scores for a category. It lies in **[-1,+1]** and includes neutral scores in the average. It is not a star rating, accuracy, confidence, or the percentage of positive reviews.

For category C:

```text
review_mean(r, C) = sum(final opinion scores for C in review r)
                    / number of opinions for C in review r

category_mean(C)  = sum(review_mean(r, C) for eligible reviews mentioning C)
                    / number of eligible reviews mentioning C
```

The engine uses `math.fsum`, rounds the category result to six decimal places, and the UI displays four decimals. It does not pool all category opinions into one unweighted opinion average: a long review with many room adjectives must not outweigh a short review simply because it has more opinions. Only opinions belonging to that category are used, not the whole review's score.

### Worked example using actual compiler scores

| Review | Room opinion scores | Mean for this review |
| --- | --- | --- |
| The room was clean and spacious. | clean: +0.1250, spacious: +0.2500 | +0.187500 |
| The room was dirty. | dirty: -0.7500 | -0.750000 |

Room Mean index = (+0.1875 + (-0.7500)) / 2 = **-0.281250**, displayed as **-0.2813** by the JavaScript UI. The two reviews each have 50% weight, even though the first has two Room opinions.

### Final score for an individual review

Each review also exposes `review_score` and `review_score_scope` as computed properties on AnalysisResult. Review score = sum of all final opinion scores in that review divided by the number of opinion results, rounded to six decimals. Its range is [-1,+1]. It averages opinions, not sentences, clauses or category means. The individual aspect scores remain available.

For “The room was not clean, but the staff were very helpful,” the score is (-0.125 + 0.3125) / 2 = +0.09375. The label remains Mixed. Opposite scores can average to zero without changing Mixed into Neutral. Complete results use scope “complete review”; partial results use “recognized opinions only.” No results means a null/unavailable score, represented by an empty numeric CSV cell. Invalid/failed CSV rows have no AnalysisResult and likewise display an unavailable score.

The score appears in the single-review summary and scoring trace, individual batch table/drill-down, CLI, single/batch CSV exports and report ZIP reviews.csv. It is not a confidence or rating. The category mean formula above remains separate and unchanged.

### Which reviews enter the calculation

- **Complete reviews primary scope:** only rows with execution status analyzed and compiler status complete.
- **Complete plus partial secondary scope:** those rows plus partial reviews, using only their recognized opinions. Unrecognized portions remain excluded.
- Unsupported, invalid_input and processing_error rows never enter category sentiment means or sentiment counts.
- A review not mentioning a category contributes nothing to that category's denominator; it is not inserted with score zero.
- No eligible category mentions → unavailable mean, displayed as a dash. Fewer than five mentioning reviews → low support. These thresholds are reporting conventions, not statistical significance.
- Repeated CSV rows retain distinct internal IDs and count separately; duplicate external IDs do not merge them.
- Search/table filters do not recalculate the selected dashboard scope's totals. Switching the scope does recalculate its eligible population.

Category polarity counts use the presence of Positive/Negative records within that review/category, independently of its numeric mean. A mixed review can have a positive, negative or zero mean and still count as Mixed. For example, one Positive and one Negative category opinion remain Mixed even when they cancel. “Any negative” counts each mentioning review with a negative opinion once, including Mixed. Complaint ranking orders distinct negative-mention review counts, with ties sharing rank; it measures frequency, not severity.

The same two-stage mean is used for a specific category/issue group, with only that issue's opinions. Overall sentiment percentages divide by eligible reviews; category percentages divide by eligible reviews mentioning that category, not all uploaded rows.

## 4 Preprocessing and input validation

The first logical phase reads and validates the input. Some matching normalization lives at the beginning of the lexer rather than a separate executable module.

- Single review: require a string, a nonblank supplied ID if present, and at most 10,000 characters. Preserve the original review.
- CSV: decode UTF-8, allowing a BOM; use a real CSV parser for quoted commas, quotes and multiline reviews. Trim header names; text/ID columns must differ. Header names are case-sensitive.
- Our demo input is exactly `sr.no,review`, one review per record. WebUI defaults to those names. CLI/Python CSV defaults are `review_text` and optional `review_id`; select alternate names explicitly.
- Default file limit: 10 MiB; default batch limit: 1,000 data rows. These file/row limits can be configured explicitly by the batch interface. Review-length limit remains 10,000 characters.
- Reject whole file: missing/duplicate/blank headers, missing selected text column, missing explicit nondefault ID column, malformed CSV, bad encoding, no data rows, or exceeded file/row limit.
- Keep per-row invalid results: column-count mismatch, blank/missing text, text-length excess. A blank supplied ID becomes absent. Unselected columns are recorded as ignored and do not determine sentiment.
- Preserve source text, row order, ordinal and physical CSV line span. Assign an internal batch/row identity; supplied IDs may repeat.
- Flag all rows sharing exactly the same nonblank text or supplied ID. No fuzzy duplicate detection, automatic deduplication or opinion inference.
- Normalize matching values to lowercase; translate curly apostrophe and selected hyphens without destroying original spans. Retain negation and unknown words; there is no generic stopword deletion, stemming, lemmatizer or spell correction.

## 5 Lexical analysis and all grammar vocabulary

`lexer.py::tokenize` regex-scans words, numbers and punctuation, then selects the longest configured phrase. Known multiword phrases may cross whitespace but not punctuation. Every token retains `kind`, normalized `value`, original `text`, zero-based character `start/end`, alias rule and functional-verb form where applicable. Source slices use `text[start:end]`; offsets are characters, not bytes.

The scanner recognizes decimal/integer numbers and the explicit A/C spelling; recognizing a NUMBER does not make arbitrary numerical complaints part of the syntax grammar. Apostrophes/hyphens within words are supported according to the scanner. Unknown words become WORD and unclassified punctuation becomes PUNCTUATION.

Token classes are ASPECT, OPINION, FUNCTION_VERB, DETERMINER, COPULA, AUXILIARY, NEGATION, INTENSIFIER, ADVERB, EMPHASIS, INTRODUCTION, CONTEXT, POSSESSION, POST_MODIFIER, RELATION, RELATION_TARGET, CONNECTOR, COMMA, END, NUMBER, WORD and PUNCTUATION. EOF is the parser reaching the end of its token stream, not an emitted token.

The noun/adjective overlap “safe” is handled by local syntax: before a copula/auxiliary it is an aspect; after an opinion without another following aspect it can be a noun (“broken safe”); otherwise it can be an opinion (“room was safe”). This is an explicit rule, not a trained POS tagger.

### Complete small-word and phrase inventory

**Determiners (8):** `the`, `a`, `an`, `my`, `our`, `their`, `this`, `that`.

**Copulas and linking verbs (26):** `is`, `are`, `was`, `were`, `seems`, `seemed`, `looks`, `looked`, `feels`, `felt`, `tastes`, `tasted`, `seem`, `look`, `feel`, `taste`, `smell`, `smells`, `smelled`, `appear`, `appears`, `appeared`, `became`, `become`, `remained`, `remains`.

**Auxiliaries (3):** `do`, `does`, `did`.

**Negations (2):** `not`, `never`.

**Connectors (3):** `and`, `but`, `however`.

**Predicate adverbs (2):** `properly`, `well`.

**Emphasis phrases (1):** `at all`.

**Introduction phrases (22):** `i found`, `we found`, `i thought`, `we thought`, `i felt`, `we felt`, `i think`, `we think`, `i must say`, `we must say`, `overall`, `honestly`, `unfortunately`, `fortunately`, `there was`, `there were`, `there is`, `there are`, `i was`, `we were`, `i am`, `we are`.

**Retained context phrases (33):** `when we arrived`, `when i arrived`, `on arrival`, `upon arrival`, `during our stay`, `during my stay`, `throughout our stay`, `throughout my stay`, `during the night`, `at night`, `in the morning`, `in the evening`, `at breakfast`, `at dinner`, `for us`, `to us`, `to me`, `to everyone`, `for my family`, `for our family`, `at the hotel`, `in our room`, `in my room`, `in the room`, `for the price`, `for the money`, `for a hotel`, `for a short stay`, `for our stay`, `for my stay`, `on our first night`, `on the first night`, `throughout the night`.

**Possession forms (4):** `has`, `have`, `had`, `with`.

**Post modifiers (2):** `enough`, `indeed`.

**Context relations (6):** `to`, `for`, `with`, `from`, `near`, `by`.

**Relation targets (20):** `airport`, `the airport`, `station`, `train station`, `railway station`, `bus station`, `beach`, `the beach`, `city center`, `city centre`, `town center`, `town centre`, `shops`, `shopping`, `restaurants`, `town`, `downtown`, `everything`, `the city`, `the station`.

**Experiential opinions allowed in I was frames (10):** `happy`, `unhappy`, `satisfied`, `dissatisfied`, `pleased`, `displeased`, `disappointed`, `impressed`, `disgusted`, `delighted`.

`with` is finally classified as RELATION because relation vocabulary takes precedence over possession vocabulary; the parser explicitly recognizes that RELATION as possession before a predicate. Experiential opinions are a subset of the canonical opinions listed later, not a separate set of invented scores.

**Separators:** comma is COMMA; `.`, `!`, `?`, `;` are END. Other punctuation is retained but does not automatically become a supported boundary.

### All configured intensity multipliers

| Phrase | Multiplier |
| --- | --- |
| `a bit` | 0.75 |
| `a little` | 0.75 |
| `a little bit` | 0.75 |
| `a lot` | 1.25 |
| `absolutely` | 1.5 |
| `exceptionally` | 1.5 |
| `extremely` | 1.5 |
| `fairly` | 0.9 |
| `highly` | 1.25 |
| `incredibly` | 1.5 |
| `particularly` | 1.25 |
| `quite` | 1.1 |
| `rather` | 1.1 |
| `really` | 1.25 |
| `slightly` | 0.75 |
| `so` | 1.25 |
| `somewhat` | 0.75 |
| `too` | 1.25 |
| `very` | 1.25 |
| `very much` | 1.25 |
| No intensifier | 1.0 |

Each predicate allows at most one NEGATION then one INTENSIFIER. A multiword intensity phrase is one token. `too` uses the configured multiplier; this version does not infer the pragmatic complaint implied by every “too” sentence. Adverbs, emphasis and post modifiers retain their text but add no extra numeric weight.

### All expanded contractions

| Contraction | Emitted tokens |
| --- | --- |
| isn't | COPULA is + NEGATION not |
| aren't | COPULA are + NEGATION not |
| wasn't | COPULA was + NEGATION not |
| weren't | COPULA were + NEGATION not |
| don't | AUXILIARY do + NEGATION not |
| doesn't | AUXILIARY does + NEGATION not |
| didn't | AUXILIARY did + NEGATION not |

Curly apostrophe variants also match after normalization. Other contractions are not automatically expanded. Original contraction pieces keep their source spans; the semantic expression displays “not” for the original “n't” component.

## 6 Syntax rules and boundaries

The implementation is a hand-written predictive recursive-descent parser with lookahead and bounded clause recovery. It builds a ReviewAST; it does not run a statistical parser or understand all English grammar. These are the actual supported rule families and guards.

| Rule | Family | Process / guard | Example |
| --- | --- | --- | --- |
| G01 | Subject then predicate | Optional determiner + explicit ASPECT; optional copula or auxiliary; opinion predicate. Copula and auxiliary cannot both be supplied. | The room was clean. |
| G02 | Predicate modifiers | Optional NEGATION, then optional INTENSIFIER, then opinion; optional ADVERB, EMPHASIS and POST_MODIFIER in that order. | The room was not very clean. |
| G03 | Copula state | A copula requires OPINION, not FUNCTION_VERB. | The AC was working. |
| G04 | Auxiliary function | Auxiliary requires base FUNCTION_VERB work/function; finite works/functions is rejected after it. | The WiFi does not work. |
| G05 | Bare function | FUNCTION_VERB without auxiliary/copula is accepted; only really may intensify that verb. Agreement is not generally checked. | The WiFi works well. |
| G06 | Inherited predicate | Predicate without subject needs a previous explicit valid subject across and/but/however in the same sentence. No negation is inherited. | The room was clean and quiet. |
| G07 | Opinion before noun | Adjective/state predicate followed by explicit ASPECT; no copula/auxiliary or FUNCTION_VERB in this form. | A comfortable bed. |
| G08 | Prenominal lists | Adjacent opinion terms or lists separated by comma/and must end in an explicit ASPECT. Modifiers can follow a list separator. | A clean, quiet room. |
| G09 | Shared noun subjects | Explicit aspects joined by and/comma/Oxford comma share the predicate; but/however do not join nouns here. | The room and bathroom were clean. |
| G10 | Shared noun predicates | A subject group shares following and/but predicates; stop when the next clause begins a new explicit aspect. | The room and bathroom were clean and spacious. |
| G11 | Possession | Explicit containing subject + has/have/had/with + optional determiner + opinion(s) + contained ASPECT. Opinions target the contained noun. | The room had a comfortable bed. |
| G12 | Introduction | At most one configured INTRODUCTION and optional comma before the normal clause. | I found the room clean. |
| G13 | Experiential target | I was/we were/I am/we are + configured experiential opinion + with/by + optional determiner + explicit ASPECT. | I was pleased with the service. |
| G14 | Known context | Zero or more configured CONTEXT tokens after the predicate or final aspect; preserve them in the AST. | The room was clean when we arrived. |
| G15 | Bounded relation tail | After known context, at most one RELATION + optional determiner + configured RELATION_TARGET. This is context, not a new category. | Targets must be from the exact relation-target list; arbitrary trailing nouns are rejected. |
| G16 | Post modifier | One configured enough/indeed after the predicate; retained in the opinion expression with unit weight. | The room was clean enough. |
| G17 | Boundaries | Connectors with optional comma, comma with optional connector, and sentence END tokens separate clauses. Sentence ends reset inheritance. | The room was clean, but the staff were rude. |
| G18 | Recovery | Unsupported clause -> diagnostic and skip to next boundary; clear inherited context and try subsequent clauses. Do not silently discard unknown tails. | The room was glorp but the staff were helpful. |
| G19 | Separator diagnostics | Leading/consecutive separators can give EMPTY_CLAUSE; a trailing non-sentence connector/comma can give MISSING_CLAUSE. | The room was clean and |

### Compact grammar notation

This is a readable summary; the G01–G19 guards above and parser lookahead are part of the language contract. `[]` means optional; `{}` means repetition.

```text
StatePredicate = [NEGATION] [INTENSIFIER] OPINION
                 [ADVERB] [EMPHASIS] [POST_MODIFIER]
FunctionPredicate = [NEGATION] [INTENSIFIER] FUNCTION_VERB
                    [ADVERB] [EMPHASIS] [POST_MODIFIER]
Subjects = [DETERMINER] ASPECT {noun_separator [DETERMINER] ASPECT}
ContextTail = {CONTEXT} [RELATION [DETERMINER] RELATION_TARGET]
Clause forms = [INTRODUCTION [COMMA]] Subjects [COPULA|AUXILIARY] Predicate ContextTail
             | [INTRODUCTION [COMMA]] [DETERMINER] StatePredicate {adjective_list_item} ASPECT ContextTail
             | [INTRODUCTION [COMMA]] Subjects POSSESSION [DETERMINER] StatePredicate {adjective_list_item} ASPECT ContextTail
             | experiential_intro StatePredicate (with|by) [DETERMINER] ASPECT ContextTail
             | [COPULA|AUXILIARY] Predicate ContextTail  (requires semantic subject inheritance)
```

This notation does not allow arbitrary choices everywhere: copulas require state opinions, auxiliaries require base function verbs, noun/adjective lists and shared predicates use the guarded lookahead above. A multiword alias such as “stopped cooling” behaves as one state OPINION. A leading time phrase is not automatically supported just because that phrase is recognized as context after a predicate.

## 7 Semantic rules and every aspect phrase

1. An explicit aspect selects its configured category. Longest-match “room service” selects Service rather than Room. Categories are not predicted by SentiWordNet.
2. Opinion attachment follows the AST, not distance alone. Possession targets the contained noun. Shared subjects/predicates create one semantic record for each supported pair.
3. A subject may be inherited only across and/but/however. Sentence ends, standalone commas, recovery and semantic failures clear inheritance. Pronouns and implicit targets are not resolved.
4. Enforce allowed aspect/category sets on the canonical opinion and, where present, its alias. No configured guard means there is no explicit compatibility restriction; it does not establish linguistic validity for all combinations.
5. Validate allowed adverbs: properly/well are configured only for working/functioning. “At all” requires explicit negation. Neither adds a second negation or numeric boost.
6. Issue selection normally takes the aspect's configured issue, otherwise a category-specific opinion issue, otherwise the default opinion issue. For Room, the opinion/contextual issue overrides a broad subaspect issue except the fixed View issue. Thus dirty bed becomes Room / Cleanliness, not automatically Comfort.
7. Attach this clause's negation, intensity, alias rule, expression and spans. These attributes are separate from P/N source scores. Negation scope is local; “not clean and quiet” does not automatically negate quiet.
8. Semantic failure creates a diagnostic and omits that record; other valid records may remain.

### Every configured aspect phrase

The tables show the raw configured aspect issue. “Opinion dependent” means no fixed issue in the aspect entry. The Room override and contextual-sense precedence above still apply.

### Room aspects (77)

| Recognized aspect phrase | Configured issue |
| --- | --- |
| `accommodation` | Opinion dependent |
| `accommodations` | Opinion dependent |
| `balconies` | Opinion dependent |
| `balcony` | Opinion dependent |
| `bath towel` | Cleanliness |
| `bath towels` | Cleanliness |
| `bathroom` | Opinion dependent |
| `bed` | Comfort |
| `bed linen` | Cleanliness |
| `bed linens` | Cleanliness |
| `bed sheet` | Cleanliness |
| `bed sheets` | Cleanliness |
| `bedding` | Comfort |
| `bedroom` | Opinion dependent |
| `bedrooms` | Opinion dependent |
| `beds` | Comfort |
| `bedsheet` | Cleanliness |
| `bedsheets` | Cleanliness |
| `blanket` | Comfort |
| `blankets` | Comfort |
| `carpet` | Cleanliness |
| `carpets` | Cleanliness |
| `ceiling` | Condition |
| `ceilings` | Condition |
| `chair` | Comfort |
| `chairs` | Comfort |
| `couch` | Comfort |
| `couches` | Comfort |
| `curtain` | Cleanliness |
| `curtains` | Cleanliness |
| `cushion` | Comfort |
| `cushions` | Comfort |
| `decor` | Condition |
| `decoration` | Condition |
| `double room` | Opinion dependent |
| `duvet` | Comfort |
| `duvets` | Comfort |
| `family room` | Opinion dependent |
| `floor` | Cleanliness |
| `floors` | Cleanliness |
| `furnishings` | Comfort |
| `furniture` | Comfort |
| `guest room` | Opinion dependent |
| `guest rooms` | Opinion dependent |
| `hotel room` | Opinion dependent |
| `hotel rooms` | Opinion dependent |
| `interior` | Condition |
| `interiors` | Condition |
| `linen` | Cleanliness |
| `linens` | Cleanliness |
| `living room` | Opinion dependent |
| `lodging` | Opinion dependent |
| `mattress` | Comfort |
| `mattresses` | Comfort |
| `ocean view` | View |
| `pillow` | Comfort |
| `pillows` | Comfort |
| `room` | Opinion dependent |
| `room view` | View |
| `rooms` | Opinion dependent |
| `sea view` | View |
| `seating` | Comfort |
| `sheet` | Cleanliness |
| `sheets` | Cleanliness |
| `single room` | Opinion dependent |
| `sofa` | Comfort |
| `sofa bed` | Comfort |
| `sofas` | Comfort |
| `suite` | Opinion dependent |
| `suites` | Opinion dependent |
| `towel` | Cleanliness |
| `towels` | Cleanliness |
| `view` | View |
| `views` | View |
| `wall` | Condition |
| `walls` | Condition |
| `window view` | View |

### Staff aspects (38)

| Recognized aspect phrase | Configured issue |
| --- | --- |
| `bellboy` | Opinion dependent |
| `bellboys` | Opinion dependent |
| `concierge` | Opinion dependent |
| `concierges` | Opinion dependent |
| `crew` | Opinion dependent |
| `doorman` | Opinion dependent |
| `doormen` | Opinion dependent |
| `employee` | Opinion dependent |
| `employees` | Opinion dependent |
| `front desk` | Opinion dependent |
| `front desk staff` | Opinion dependent |
| `front desk team` | Opinion dependent |
| `front-desk` | Opinion dependent |
| `front-desk staff` | Opinion dependent |
| `hotel employees` | Opinion dependent |
| `hotel staff` | Opinion dependent |
| `housekeeper` | Opinion dependent |
| `housekeepers` | Opinion dependent |
| `management` | Opinion dependent |
| `manager` | Opinion dependent |
| `managers` | Opinion dependent |
| `personnel` | Opinion dependent |
| `porter` | Opinion dependent |
| `porters` | Opinion dependent |
| `reception` | Opinion dependent |
| `reception personnel` | Opinion dependent |
| `reception staff` | Opinion dependent |
| `reception team` | Opinion dependent |
| `receptionist` | Opinion dependent |
| `receptionists` | Opinion dependent |
| `security guard` | Opinion dependent |
| `security guards` | Opinion dependent |
| `security staff` | Opinion dependent |
| `staff` | Opinion dependent |
| `staff members` | Opinion dependent |
| `team` | Opinion dependent |
| `waiter` | Opinion dependent |
| `waiters` | Opinion dependent |

### Service aspects (34)

| Recognized aspect phrase | Configured issue |
| --- | --- |
| `assistance` | Opinion dependent |
| `booking` | Reservation |
| `booking process` | Reservation |
| `bookings` | Reservation |
| `breakfast service` | Response Time |
| `check in` | Check-in |
| `check ins` | Check-in |
| `check out` | Check-out |
| `check-in` | Check-in |
| `check-ins` | Check-in |
| `check-out` | Check-out |
| `check-outs` | Check-out |
| `checkin` | Check-in |
| `checkout` | Check-out |
| `checkouts` | Check-out |
| `customer service` | Response Time |
| `deliveries` | Response Time |
| `delivery` | Response Time |
| `guest service` | Response Time |
| `guest services` | Response Time |
| `hospitality` | Opinion dependent |
| `housekeeping` | Response Time |
| `housekeeping service` | Response Time |
| `laundry service` | Response Time |
| `reception service` | Response Time |
| `reservation` | Reservation |
| `reservations` | Reservation |
| `response` | Response Time |
| `responses` | Response Time |
| `restaurant service` | Response Time |
| `room service` | Opinion dependent |
| `service` | Opinion dependent |
| `services` | Opinion dependent |
| `support` | Opinion dependent |

### Food aspects (51)

| Recognized aspect phrase | Configured issue |
| --- | --- |
| `beverage` | Taste |
| `beverages` | Taste |
| `bread` | Taste |
| `breakfast` | Opinion dependent |
| `breakfast buffet` | Opinion dependent |
| `buffet` | Opinion dependent |
| `cafe` | Opinion dependent |
| `cafeteria` | Opinion dependent |
| `cake` | Taste |
| `cakes` | Taste |
| `chicken` | Taste |
| `cocktail` | Taste |
| `cocktails` | Taste |
| `coffee` | Taste |
| `cuisine` | Opinion dependent |
| `dessert` | Taste |
| `desserts` | Taste |
| `dining` | Opinion dependent |
| `dinner` | Opinion dependent |
| `dinner buffet` | Opinion dependent |
| `dish` | Opinion dependent |
| `dishes` | Opinion dependent |
| `drink` | Taste |
| `drinks` | Taste |
| `egg` | Taste |
| `eggs` | Taste |
| `fish` | Taste |
| `food` | Opinion dependent |
| `fruit` | Taste |
| `fruits` | Taste |
| `juice` | Taste |
| `juices` | Taste |
| `lunch` | Opinion dependent |
| `meal` | Opinion dependent |
| `meals` | Opinion dependent |
| `meat` | Taste |
| `menu` | Opinion dependent |
| `pasta` | Taste |
| `restaurant` | Opinion dependent |
| `rice` | Taste |
| `salad` | Taste |
| `salads` | Taste |
| `snack` | Opinion dependent |
| `snacks` | Opinion dependent |
| `soup` | Taste |
| `soups` | Taste |
| `steak` | Taste |
| `supper` | Opinion dependent |
| `tea` | Taste |
| `toast` | Taste |
| `vegetables` | Taste |

### Cleanliness aspects (12)

| Recognized aspect phrase | Configured issue |
| --- | --- |
| `bathroom cleaning` | Hygiene |
| `bathroom cleanliness` | Hygiene |
| `cleaning` | Hygiene |
| `cleaning standards` | Hygiene |
| `cleanliness` | Hygiene |
| `hotel cleanliness` | Hygiene |
| `hygiene` | Hygiene |
| `hygiene standards` | Hygiene |
| `room cleaning` | Hygiene |
| `room cleanliness` | Hygiene |
| `sanitary conditions` | Hygiene |
| `sanitation` | Hygiene |

### Facilities aspects (133)

| Recognized aspect phrase | Configured issue |
| --- | --- |
| `a/c` | Air Conditioning |
| `ac` | Air Conditioning |
| `ac unit` | Air Conditioning |
| `air con` | Air Conditioning |
| `air conditioner` | Air Conditioning |
| `air conditioner unit` | Air Conditioning |
| `air conditioning` | Air Conditioning |
| `air conditioning unit` | Air Conditioning |
| `air-conditioner` | Air Conditioning |
| `air-conditioner unit` | Air Conditioning |
| `air-conditioning` | Air Conditioning |
| `aircon` | Air Conditioning |
| `amenities` | Amenities |
| `bathroom ceiling` | Plumbing |
| `bedside lamp` | Lighting |
| `bedside lamps` | Lighting |
| `car park` | Parking |
| `car parking` | Parking |
| `ceiling fan` | Ventilation |
| `central heating` | Heating |
| `door` | Safety |
| `door lock` | Safety |
| `door locks` | Safety |
| `doors` | Safety |
| `drain` | Plumbing |
| `drains` | Plumbing |
| `drinking water` | Water |
| `electric kettle` | Amenities |
| `elevator` | Elevator |
| `elevators` | Elevator |
| `exhaust fan` | Ventilation |
| `facilities` | Opinion dependent |
| `facility` | Amenities |
| `fan` | Ventilation |
| `fans` | Ventilation |
| `faucet` | Plumbing |
| `faucets` | Plumbing |
| `fire alarm` | Safety |
| `fire alarms` | Safety |
| `fitness center` | Gym |
| `fitness centre` | Gym |
| `fitness room` | Gym |
| `fridge` | Refrigerator |
| `fridges` | Refrigerator |
| `garden` | Amenities |
| `gym` | Gym |
| `gym equipment` | Gym |
| `gyms` | Gym |
| `hair dryer` | Amenities |
| `hairdryer` | Amenities |
| `heater` | Heating |
| `heaters` | Heating |
| `heating` | Heating |
| `hot water` | Water |
| `hotel facilities` | Amenities |
| `hotel safe` | Safety |
| `internet` | WiFi |
| `internet access` | WiFi |
| `internet connection` | WiFi |
| `iron` | Amenities |
| `kettle` | Amenities |
| `lamp` | Lighting |
| `lamps` | Lighting |
| `lift` | Elevator |
| `lifts` | Elevator |
| `light` | Lighting |
| `lighting` | Lighting |
| `lights` | Lighting |
| `lobby` | Amenities |
| `lock` | Safety |
| `locks` | Safety |
| `lounge` | Amenities |
| `mini bar` | Refrigerator |
| `mini fridge` | Refrigerator |
| `mini-fridge` | Refrigerator |
| `minibar` | Refrigerator |
| `minifridge` | Refrigerator |
| `parking` | Parking |
| `parking area` | Parking |
| `parking lot` | Parking |
| `plumbing` | Plumbing |
| `pool` | Pool |
| `pools` | Pool |
| `power outlet` | Amenities |
| `power outlets` | Amenities |
| `refrigerator` | Refrigerator |
| `refrigerators` | Refrigerator |
| `remote control` | Television |
| `room door` | Safety |
| `room safe` | Safety |
| `safe` | Safety |
| `safes` | Safety |
| `safety box` | Safety |
| `sauna` | Amenities |
| `security` | Safety |
| `shower` | Shower |
| `shower head` | Shower |
| `shower heads` | Shower |
| `showerhead` | Shower |
| `showers` | Shower |
| `shuttle` | Amenities |
| `shuttle service` | Amenities |
| `sink` | Plumbing |
| `sinks` | Plumbing |
| `socket` | Amenities |
| `sockets` | Amenities |
| `spa` | Amenities |
| `swimming pool` | Pool |
| `swimming pools` | Pool |
| `tap` | Plumbing |
| `taps` | Plumbing |
| `television` | Television |
| `television set` | Television |
| `television sets` | Television |
| `televisions` | Television |
| `terrace` | Amenities |
| `toilet` | Plumbing |
| `toilets` | Plumbing |
| `tv` | Television |
| `tv remote` | Television |
| `ventilation` | Ventilation |
| `water` | Water |
| `water pressure` | Water |
| `water supply` | Water |
| `wi fi` | WiFi |
| `wi-fi` | WiFi |
| `wi-fi connection` | WiFi |
| `wi-fi network` | WiFi |
| `wi-fi signal` | WiFi |
| `wifi` | WiFi |
| `wifi connection` | WiFi |
| `wifi signal` | WiFi |
| `wireless internet` | WiFi |

## 8 SentiWordNet and every canonical opinion

Each canonical opinion has a genuine SentiWordNet POS/offset ID, terms and gloss. **P and N below are original source values.** SentiWordNet supplies lexical evidence only; our semantic phase supplies category/aspect/issue association.

New terms are built from first-ranked WordNet adjective senses unless the curated catalog has an explicit hotel-context override. Earlier configured senses are retained. Selection does not optimize for the most positive/negative score. The term/sense membership and subset checksum are checked before normal evaluation; exact source-row preservation is covered by the validation suite.

```text
objective = 1 - P - N
lexical_score L = P - N
domain_score D = L, unless a configured rule for the selected category/sense applies
negation_sign = -1 if negated, otherwise +1
raw_score = D * intensity_multiplier * negation_sign
final_score = round(clip(raw_score, -1, +1), 6)
Positive if final_score > 0.05
Negative if final_score < -0.05
Neutral otherwise, including exactly +/-0.05
```

The stored calibration values are separate project rules; they do not rewrite P/N, the source gloss or the TSV. Final polarity uses D after modifiers, so a lexically zero or opposite-signed source score can yield a different domain interpretation. The source values and rule remain visible together. An unknown term never receives an invented Neutral score.

### Every canonical opinion and its default source score

These are default senses; category-specific overrides are listed in section 10. All six in the category column means no explicit category restriction. Aspect guard IDs refer to the exact sets in section 9. Default issue labels can be overridden by target issues or category-specific senses.

| Opinion | Default issue | Allowed categories | Aspect guard | Default sense | P | N | L = P - N |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `abrupt` | Professionalism | Staff, Service, Facilities | No explicit aspect guard | a:00640520 | 0.5 | 0.25 | 0.25 |
| `abusive` | Professionalism | Staff, Service, Facilities | No explicit aspect guard | a:01628531 | 0.0 | 0.875 | -0.875 |
| `abysmal` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:01499155 | 0.25 | 0.25 | 0.0 |
| `acceptable` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:00017782 | 0.625 | 0.0 | 0.625 |
| `accessible` | Condition | Room, Facilities | No explicit aspect guard | a:00019131 | 0.625 | 0.0 | 0.625 |
| `accommodating` | Professionalism | Staff, Service, Facilities | No explicit aspect guard | a:00020787 | 0.5 | 0.0 | 0.5 |
| `adequate` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:02336109 | 0.125 | 0.0 | 0.125 |
| `airy` | Comfort | Room, Facilities | No explicit aspect guard | a:02508917 | 0.0 | 0.125 | -0.125 |
| `amazing` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:02359789 | 0.5 | 0.25 | 0.25 |
| `appalling` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:00193367 | 0.0 | 0.5 | -0.5 |
| `appetizing` | Taste | Food | No explicit aspect guard | a:00133417 | 0.5 | 0.25 | 0.25 |
| `arrogant` | Professionalism | Staff, Service, Facilities | No explicit aspect guard | a:01889819 | 0.5 | 0.375 | 0.125 |
| `astonishing` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:02359789 | 0.5 | 0.25 | 0.25 |
| `atrocious` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:01126291 | 0.0 | 0.875 | -0.875 |
| `attentive` | Helpfulness | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:00163592 | 0.25 | 0.0 | 0.25 |
| `attractive` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:00166146 | 0.875 | 0.0 | 0.875 |
| `available` | Condition | Room, Facilities | No explicit aspect guard | a:00183053 | 0.375 | 0.0 | 0.375 |
| `average` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:01594146 | 0.0 | 0.0 | 0.0 |
| `awesome` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:01282510 | 0.875 | 0.125 | 0.75 |
| `awful` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:01126291 | 0.0 | 0.875 | -0.875 |
| `bad` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:01125429 | 0.0 | 0.625 | -0.625 |
| `basic` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:01855764 | 0.0 | 0.0 | 0.0 |
| `beautiful` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:00217728 | 0.75 | 0.0 | 0.75 |
| `big` | Space | Room, Facilities | No explicit aspect guard | a:01382086 | 0.25 | 0.125 | 0.125 |
| `bitter` | Taste | Food | No explicit aspect guard | a:02396098 | 0.0 | 0.375 | -0.375 |
| `bland` | Taste | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:02399595 | 0.0 | 0.375 | -0.375 |
| `blocked` | Condition | Room, Facilities | No explicit aspect guard | a:01621080 | 0.125 | 0.0 | 0.125 |
| `boisterous` | Noise | Room, Facilities | No explicit aspect guard | a:01666489 | 0.0 | 0.375 | -0.375 |
| `bright` | Lighting | Room, Facilities | No explicit aspect guard | a:00278551 | 0.125 | 0.0 | 0.125 |
| `brilliant` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:02342608 | 0.875 | 0.0 | 0.875 |
| `broken` | Functionality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:00680156 | 0.0 | 0.25 | -0.25 |
| `burned` | Taste | Food | No explicit aspect guard | a:00617137 | 0.0 | 0.5 | -0.5 |
| `burnt` | Taste | Food | No explicit aspect guard | a:00617137 | 0.0 | 0.5 | -0.5 |
| `calm` | Noise | Room, Facilities | No explicit aspect guard | a:00529657 | 0.125 | 0.5 | -0.375 |
| `caring` | Professionalism | Staff, Service, Facilities | No explicit aspect guard | a:00506601 | 0.5 | 0.25 | 0.25 |
| `cheerful` | Professionalism | Staff, Service, Facilities | No explicit aspect guard | a:00362467 | 0.75 | 0.0 | 0.75 |
| `chewy` | Taste | Food | No explicit aspect guard | a:02445978 | 0.125 | 0.375 | -0.25 |
| `chilly` | Temperature | Room, Facilities | No explicit aspect guard | a:01252566 | 0.0 | 0.125 | -0.125 |
| `clean` | Cleanliness | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:00417413 | 0.5 | 0.375 | 0.125 |
| `clogged` | Condition | Room, Facilities | No explicit aspect guard | a:01621268 | 0.0 | 0.0 | 0.0 |
| `cluttered` | Cleanliness | Room, Food, Cleanliness, Facilities | No explicit aspect guard | a:02424949 | 0.0 | 0.5 | -0.5 |
| `cold` | Temperature | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:01251128 | 0.0 | 0.75 | -0.75 |
| `comfortable` | Comfort | Room | No explicit aspect guard | a:00476819 | 0.0 | 0.75 | -0.75 |
| `compact` | Space | Room, Facilities | No explicit aspect guard | a:00502180 | 0.0 | 0.0 | 0.0 |
| `competent` | Professionalism | Staff, Service, Facilities | No explicit aspect guard | a:00510050 | 0.75 | 0.0 | 0.75 |
| `congested` | Space | Room, Facilities | No explicit aspect guard | a:01084486 | 0.0 | 0.25 | -0.25 |
| `connected` | Condition | Room, Facilities | No explicit aspect guard | a:01651346 | 0.0 | 0.0 | 0.0 |
| `considerate` | Professionalism | Staff, Service, Facilities | No explicit aspect guard | a:00638981 | 0.5 | 0.25 | 0.25 |
| `contaminated` | Cleanliness | Room, Food, Cleanliness, Facilities | No explicit aspect guard | a:01908889 | 0.0 | 0.375 | -0.375 |
| `convenient` | Condition | Room, Facilities | No explicit aspect guard | a:00604617 | 0.625 | 0.25 | 0.375 |
| `cooked` | Taste | Food | No explicit aspect guard | a:00615757 | 0.0 | 0.0 | 0.0 |
| `cooperative` | Professionalism | Staff, Service, Facilities | No explicit aspect guard | a:00513388 | 0.0 | 0.0 | 0.0 |
| `cosy` | Comfort | Room, Facilities | No explicit aspect guard | a:00477284 | 0.125 | 0.0 | 0.125 |
| `courteous` | Courtesy | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:00641460 | 0.75 | 0.0 | 0.75 |
| `cozy` | Comfort | Room, Facilities | No explicit aspect guard | a:00477284 | 0.125 | 0.0 | 0.125 |
| `cramped` | Space | Room, Facilities | No explicit aspect guard | a:00476663 | 0.0 | 0.0 | 0.0 |
| `crisp` | Taste | Food | No explicit aspect guard | a:00780352 | 0.25 | 0.0 | 0.25 |
| `crispy` | Taste | Food | No explicit aspect guard | a:02446931 | 0.0 | 0.0 | 0.0 |
| `crowded` | Space | Room, Facilities | No explicit aspect guard | a:00559690 | 0.125 | 0.0 | 0.125 |
| `cushioned` | Comfort | Room, Facilities | No explicit aspect guard | a:01153703 | 0.0 | 0.0 | 0.0 |
| `damaged` | Condition | Room, Facilities | No explicit aspect guard | a:00679147 | 0.0 | 0.75 | -0.75 |
| `damp` | Cleanliness | Room, Food, Cleanliness, Facilities | No explicit aspect guard | a:02548820 | 0.0 | 0.0 | 0.0 |
| `dangerous` | Safety | Room, Facilities | No explicit aspect guard | a:02058794 | 0.0 | 0.75 | -0.75 |
| `dark` | Lighting | Room, Facilities | No explicit aspect guard | a:00273082 | 0.125 | 0.125 | 0.0 |
| `deafening` | Noise | Room, Facilities | No explicit aspect guard | a:01453467 | 0.125 | 0.0 | 0.125 |
| `decent` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:02336109 | 0.125 | 0.0 | 0.125 |
| `defective` | Condition | Room, Facilities | No explicit aspect guard | a:01752953 | 0.5 | 0.0 | 0.5 |
| `delayed` | Response Time | Staff, Service, Facilities | No explicit aspect guard | a:01841295 | 0.0 | 0.75 | -0.75 |
| `delicious` | Taste | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:02396720 | 0.75 | 0.25 | 0.5 |
| `delighted` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:01805730 | 0.5 | 0.25 | 0.25 |
| `delightful` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:01807964 | 0.75 | 0.0 | 0.75 |
| `dilapidated` | Condition | Room, Facilities | No explicit aspect guard | a:00679717 | 0.0 | 0.375 | -0.375 |
| `diluted` | Taste | Food | No explicit aspect guard | a:00756091 | 0.0 | 0.625 | -0.625 |
| `dim` | Lighting | Room, Facilities | No explicit aspect guard | a:00275290 | 0.125 | 0.75 | -0.625 |
| `dingy` | Cleanliness | Room, Food, Cleanliness, Facilities | No explicit aspect guard | a:00420650 | 0.0 | 0.625 | -0.625 |
| `dirty` | Cleanliness | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:00419289 | 0.0 | 0.75 | -0.75 |
| `disappointed` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:02333976 | 0.0 | 0.5 | -0.5 |
| `disappointing` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:02082611 | 0.0 | 0.75 | -0.75 |
| `disconnected` | Condition | Room, Facilities | No explicit aspect guard | a:01651609 | 0.0 | 0.625 | -0.625 |
| `discourteous` | Professionalism | Staff, Service, Facilities | No explicit aspect guard | a:00640283 | 0.625 | 0.25 | 0.375 |
| `disgusted` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:01806677 | 0.375 | 0.125 | 0.25 |
| `disgusting` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:01625893 | 0.25 | 0.75 | -0.5 |
| `disheveled` | Cleanliness | Room, Food, Cleanliness, Facilities | No explicit aspect guard | a:02425220 | 0.125 | 0.75 | -0.625 |
| `dishevelled` | Cleanliness | Room, Food, Cleanliness, Facilities | No explicit aspect guard | a:02425220 | 0.125 | 0.75 | -0.625 |
| `dishonest` | Professionalism | Staff, Service, Facilities | No explicit aspect guard | a:01222884 | 0.0 | 0.875 | -0.875 |
| `dismissive` | Professionalism | Staff, Service, Facilities | No explicit aspect guard | a:01343411 | 0.5 | 0.25 | 0.25 |
| `displeased` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:01805889 | 0.125 | 0.75 | -0.625 |
| `disrespectful` | Professionalism | Staff, Service, Facilities | No explicit aspect guard | a:01994602 | 0.5 | 0.375 | 0.125 |
| `disruptive` | Noise | Room, Facilities | No explicit aspect guard | a:01923720 | 0.0 | 0.75 | -0.75 |
| `dissatisfied` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:00590163 | 0.0 | 0.5 | -0.5 |
| `disturbing` | Noise | Room, Facilities | No explicit aspect guard | a:01189386 | 0.0 | 0.875 | -0.875 |
| `drafty` | Comfort | Room, Facilities | No explicit aspect guard | a:01397674 | 0.0 | 0.5 | -0.5 |
| `draughty` | Comfort | Room, Facilities | No explicit aspect guard | a:01397674 | 0.0 | 0.5 | -0.5 |
| `dreadful` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:00193799 | 0.0 | 0.625 | -0.625 |
| `dry` | Cleanliness | Room, Food, Cleanliness, Facilities | No explicit aspect guard | a:02551380 | 0.0 | 0.25 | -0.25 |
| `durable` | Condition | Room, Facilities | No explicit aspect guard | a:01439496 | 0.0 | 0.0 | 0.0 |
| `dusty` | Cleanliness | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:01696346 | 0.0 | 0.375 | -0.375 |
| `edible` | Taste | Food | No explicit aspect guard | a:00828779 | 0.25 | 0.0 | 0.25 |
| `effective` | Professionalism | Staff, Service, Facilities | No explicit aspect guard | a:00834198 | 0.25 | 0.125 | 0.125 |
| `efficient` | Professionalism | Staff, Service, Facilities | No explicit aspect guard | a:00839619 | 0.375 | 0.375 | 0.0 |
| `elegant` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:00849357 | 0.5 | 0.0 | 0.5 |
| `enjoyable` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:01801029 | 0.5 | 0.25 | 0.25 |
| `excellent` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:02343110 | 1.0 | 0.0 | 1.0 |
| `exceptional` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:00488187 | 0.25 | 0.0 | 0.25 |
| `fabulous` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:01808227 | 0.875 | 0.125 | 0.75 |
| `fantastic` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:01676517 | 0.75 | 0.0 | 0.75 |
| `fast` | Response Time | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:00976508 | 0.0 | 0.0 | 0.0 |
| `faulty` | Condition | Room, Facilities | No explicit aspect guard | a:01752953 | 0.5 | 0.0 | 0.5 |
| `fetid` | Cleanliness | Room, Food, Cleanliness, Facilities | No explicit aspect guard | a:01053634 | 0.0 | 0.75 | -0.75 |
| `filthy` | Cleanliness | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:00421590 | 0.0 | 0.875 | -0.875 |
| `fine` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:02081114 | 0.375 | 0.0 | 0.375 |
| `firm` | Comfort | Room, Facilities | No explicit aspect guard | a:01151740 | 0.0 | 0.75 | -0.75 |
| `flavorful` | Taste | Food | No explicit aspect guard | a:02396911 | 0.0 | 0.5 | -0.5 |
| `flavorsome` | Taste | Food | No explicit aspect guard | a:02396911 | 0.0 | 0.5 | -0.5 |
| `flavourful` | Taste | Food | No explicit aspect guard | a:02396911 | 0.0 | 0.5 | -0.5 |
| `flickering` | Condition | Room, Facilities | No explicit aspect guard | a:02304119 | 0.25 | 0.0 | 0.25 |
| `foul` | Cleanliness | Room, Food, Cleanliness, Facilities | No explicit aspect guard | a:01625893 | 0.25 | 0.75 | -0.5 |
| `fresh` | Freshness | Food, Room, Cleanliness, Facilities | No explicit aspect guard | a:01067694 | 0.375 | 0.625 | -0.25 |
| `friendly` | Friendliness | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:01074650 | 0.25 | 0.125 | 0.125 |
| `functional` | Condition | Room, Facilities | A3 | a:01091728 | 0.25 | 0.0 | 0.25 |
| `functioning` | Functionality | Room, Staff, Service, Food, Cleanliness, Facilities | A2 | a:01091556 | 0.0 | 0.0 | 0.0 |
| `generous` | Professionalism | Staff, Service, Facilities | No explicit aspect guard | a:01111016 | 0.0 | 0.0 | 0.0 |
| `good` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:01123148 | 0.75 | 0.0 | 0.75 |
| `gorgeous` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:00219705 | 0.75 | 0.0 | 0.75 |
| `greasy` | Cleanliness | Room, Food, Cleanliness, Facilities | No explicit aspect guard | a:00992432 | 0.0 | 0.25 | -0.25 |
| `great` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:01123879 | 0.875 | 0.0 | 0.875 |
| `grimy` | Cleanliness | Room, Food, Cleanliness, Facilities | No explicit aspect guard | a:00420650 | 0.0 | 0.625 | -0.625 |
| `grubby` | Cleanliness | Room, Food, Cleanliness, Facilities | No explicit aspect guard | a:00420650 | 0.0 | 0.625 | -0.625 |
| `happy` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:01148283 | 0.875 | 0.0 | 0.875 |
| `hard` | Comfort | Room, Facilities | No explicit aspect guard | a:01150915 | 0.0 | 0.0 | 0.0 |
| `hazardous` | Safety | Room, Facilities | No explicit aspect guard | a:02059811 | 0.25 | 0.125 | 0.125 |
| `helpful` | Helpfulness | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:01195536 | 0.25 | 0.0 | 0.25 |
| `honest` | Professionalism | Staff, Service, Facilities | No explicit aspect guard | a:01222360 | 0.375 | 0.0 | 0.375 |
| `horrendous` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:00193799 | 0.0 | 0.625 | -0.625 |
| `horrible` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:00193480 | 0.0 | 0.625 | -0.625 |
| `hospitable` | Professionalism | Staff, Service, Facilities | No explicit aspect guard | a:01243825 | 0.5 | 0.375 | 0.125 |
| `hostile` | Professionalism | Staff, Service, Facilities | No explicit aspect guard | a:01244410 | 0.0 | 0.625 | -0.625 |
| `hot` | Temperature | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:01247240 | 0.0 | 0.0 | 0.0 |
| `huge` | Space | Room, Facilities | No explicit aspect guard | a:01387319 | 0.0 | 0.125 | -0.125 |
| `hygienic` | Hygiene | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:02113191 | 0.75 | 0.0 | 0.75 |
| `immaculate` | Cleanliness | Room, Food, Cleanliness, Facilities | No explicit aspect guard | a:00418364 | 0.5 | 0.0 | 0.5 |
| `impatient` | Professionalism | Staff, Service, Facilities | No explicit aspect guard | a:01737241 | 0.0 | 0.375 | -0.375 |
| `imperfect` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:01752167 | 0.125 | 0.75 | -0.625 |
| `impolite` | Professionalism | Staff, Service, Facilities | No explicit aspect guard | a:00641640 | 0.5 | 0.125 | 0.375 |
| `impressed` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:00071142 | 0.5 | 0.5 | 0.0 |
| `impressive` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:01282014 | 0.125 | 0.0 | 0.125 |
| `inaccessible` | Condition | Room, Facilities | No explicit aspect guard | a:00019874 | 0.5 | 0.125 | 0.375 |
| `inadequate` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:00051696 | 0.0 | 0.5 | -0.5 |
| `inattentive` | Helpfulness | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:00755876 | 0.0 | 0.625 | -0.625 |
| `incompetent` | Professionalism | Staff, Service, Facilities | No explicit aspect guard | a:02229324 | 0.0 | 0.75 | -0.75 |
| `inconsiderate` | Professionalism | Staff, Service, Facilities | No explicit aspect guard | a:00639356 | 0.0 | 0.375 | -0.375 |
| `inconvenient` | Condition | Room, Facilities | No explicit aspect guard | a:00605128 | 0.125 | 0.75 | -0.625 |
| `indifferent` | Professionalism | Staff, Service, Facilities | No explicit aspect guard | a:01342949 | 0.25 | 0.25 | 0.0 |
| `inedible` | Taste | Food | No explicit aspect guard | a:00829496 | 0.25 | 0.75 | -0.5 |
| `ineffective` | Professionalism | Staff, Service, Facilities | No explicit aspect guard | a:00835609 | 0.0 | 0.625 | -0.625 |
| `inefficient` | Professionalism | Staff, Service, Facilities | No explicit aspect guard | a:00840902 | 0.0 | 0.5 | -0.5 |
| `inferior` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:02345272 | 0.0 | 0.875 | -0.875 |
| `inoperative` | Condition | Room, Facilities | No explicit aspect guard | a:00833575 | 0.0 | 0.125 | -0.125 |
| `insecure` | Safety | Room, Facilities | No explicit aspect guard | a:02095786 | 0.125 | 0.375 | -0.25 |
| `intermittent` | Condition | Room, Facilities | No explicit aspect guard | a:00593836 | 0.0 | 0.0 | 0.0 |
| `inviting` | Comfort | Room, Facilities | No explicit aspect guard | a:01358363 | 0.75 | 0.0 | 0.75 |
| `juicy` | Taste | Food | No explicit aspect guard | a:01368793 | 0.0 | 0.375 | -0.375 |
| `kind` | Professionalism | Staff, Service, Facilities | No explicit aspect guard | a:01372049 | 0.625 | 0.0 | 0.625 |
| `knowledgeable` | Professionalism | Staff, Service, Facilities | No explicit aspect guard | a:00830051 | 0.25 | 0.0 | 0.25 |
| `large` | Space | Room, Facilities | No explicit aspect guard | a:01382086 | 0.25 | 0.125 | 0.125 |
| `late` | Response Time | Staff, Service, Facilities | No explicit aspect guard | a:01901186 | 0.125 | 0.25 | -0.125 |
| `lazy` | Professionalism | Staff, Service, Facilities | No explicit aspect guard | a:00294579 | 0.0 | 0.0 | 0.0 |
| `leaky` | Condition | Room, Facilities | No explicit aspect guard | a:01397385 | 0.0 | 0.0 | 0.0 |
| `littered` | Cleanliness | Room, Food, Cleanliness, Facilities | No explicit aspect guard | a:02424949 | 0.0 | 0.5 | -0.5 |
| `loud` | Noise | Room, Facilities | No explicit aspect guard | a:01452593 | 0.375 | 0.125 | 0.25 |
| `lousy` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:01127782 | 0.0 | 0.75 | -0.75 |
| `lovely` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:00219809 | 0.625 | 0.0 | 0.625 |
| `lukewarm` | Taste | Food | No explicit aspect guard | a:02529581 | 0.375 | 0.375 | 0.0 |
| `lumpy` | Comfort | Room, Facilities | No explicit aspect guard | a:00912490 | 0.0 | 0.625 | -0.625 |
| `luxurious` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:01298239 | 0.625 | 0.0 | 0.625 |
| `magnificent` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:01285376 | 0.5 | 0.25 | 0.25 |
| `maintained` | Condition | Room, Facilities | No explicit aspect guard | a:00737515 | 0.75 | 0.0 | 0.75 |
| `malfunctioning` | Condition | Room, Facilities | No explicit aspect guard | a:01092142 | 0.0 | 0.75 | -0.75 |
| `malodorous` | Condition | Room, Facilities | No explicit aspect guard | a:01053144 | 0.0 | 0.875 | -0.875 |
| `marvellous` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:01676517 | 0.75 | 0.0 | 0.75 |
| `marvelous` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:01676517 | 0.75 | 0.0 | 0.75 |
| `mediocre` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:02347564 | 0.222 | 0.778 | -0.556 |
| `messy` | Cleanliness | Room, Food, Cleanliness, Facilities | No explicit aspect guard | a:02426042 | 0.0 | 0.875 | -0.875 |
| `miserable` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:01150205 | 0.0 | 0.875 | -0.875 |
| `modern` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:00972902 | 0.0 | 0.0 | 0.0 |
| `moldy` | Cleanliness | Room, Food, Cleanliness, Facilities | No explicit aspect guard | a:01070088 | 0.0 | 0.375 | -0.375 |
| `mouldy` | Cleanliness | Room, Food, Cleanliness, Facilities | No explicit aspect guard | a:01070088 | 0.0 | 0.375 | -0.375 |
| `mouth-watering` | Taste | Food | No explicit aspect guard | a:00133669 | 0.625 | 0.25 | 0.375 |
| `musty` | Cleanliness | Room, Food, Cleanliness, Facilities | No explicit aspect guard | a:01070088 | 0.0 | 0.375 | -0.375 |
| `narrow` | Space | Room, Facilities | No explicit aspect guard | a:02561888 | 0.25 | 0.25 | 0.0 |
| `neat` | Cleanliness | Room, Food, Cleanliness, Facilities | No explicit aspect guard | a:02423284 | 0.5 | 0.375 | 0.125 |
| `negligent` | Professionalism | Staff, Service, Facilities | No explicit aspect guard | a:00754873 | 0.25 | 0.5 | -0.25 |
| `new` | Condition | Room, Facilities | No explicit aspect guard | a:01640850 | 0.375 | 0.0 | 0.375 |
| `nice` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:01586342 | 0.875 | 0.0 | 0.875 |
| `noisy` | Noise | Room, Facilities | No explicit aspect guard | a:01919931 | 0.375 | 0.375 | 0.0 |
| `nutritious` | Taste | Food | No explicit aspect guard | a:02557719 | 0.25 | 0.0 | 0.25 |
| `obliging` | Professionalism | Staff, Service, Facilities | No explicit aspect guard | a:00021110 | 0.75 | 0.0 | 0.75 |
| `obnoxious` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:01626874 | 0.0 | 0.625 | -0.625 |
| `obstructed` | Condition | Room, Facilities | No explicit aspect guard | a:01620509 | 0.0 | 0.0 | 0.0 |
| `odorless` | Cleanliness | Room, Food, Cleanliness, Facilities | No explicit aspect guard | a:01057775 | 0.0 | 0.25 | -0.25 |
| `odorous` | Cleanliness | Room, Food, Cleanliness, Facilities | No explicit aspect guard | a:01055073 | 0.0 | 0.0 | 0.0 |
| `odourless` | Cleanliness | Room, Food, Cleanliness, Facilities | No explicit aspect guard | a:01057775 | 0.0 | 0.25 | -0.25 |
| `oily` | Taste | Food | No explicit aspect guard | a:00992432 | 0.0 | 0.25 | -0.25 |
| `operational` | Functionality | Room, Staff, Service, Food, Cleanliness, Facilities | A2 | a:02124253 | 0.25 | 0.0 | 0.25 |
| `ordinary` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:01672607 | 0.375 | 0.5 | -0.125 |
| `outdated` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:00669138 | 0.0 | 0.75 | -0.75 |
| `outstanding` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:02343762 | 0.75 | 0.0 | 0.75 |
| `overdone` | Taste | Food | No explicit aspect guard | a:01533806 | 0.125 | 0.0 | 0.125 |
| `overheated` | Temperature | Room, Facilities | No explicit aspect guard | a:01249621 | 0.25 | 0.25 | 0.0 |
| `painful` | Comfort | Room, Facilities | No explicit aspect guard | a:01711071 | 0.125 | 0.75 | -0.625 |
| `palatable` | Taste | Food | No explicit aspect guard | a:01716227 | 0.375 | 0.125 | 0.25 |
| `passable` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:01724551 | 0.0 | 0.0 | 0.0 |
| `patient` | Professionalism | Staff, Service, Facilities | No explicit aspect guard | a:01735736 | 0.5 | 0.25 | 0.25 |
| `peaceful` | Noise | Room, Facilities | No explicit aspect guard | a:01740892 | 0.25 | 0.0 | 0.25 |
| `perfect` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:01749320 | 0.625 | 0.125 | 0.5 |
| `personable` | Professionalism | Staff, Service, Facilities | No explicit aspect guard | a:00168694 | 0.625 | 0.0 | 0.625 |
| `pleasant` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:01800349 | 0.625 | 0.125 | 0.5 |
| `pleased` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:01805157 | 0.625 | 0.0 | 0.625 |
| `plush` | Comfort | Room, Facilities | No explicit aspect guard | a:02025274 | 0.375 | 0.5 | -0.125 |
| `polite` | Courtesy | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:00641158 | 0.5 | 0.0 | 0.5 |
| `polluted` | Cleanliness | Room, Food, Cleanliness, Facilities | No explicit aspect guard | a:01908889 | 0.0 | 0.375 | -0.375 |
| `poor` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:01128719 | 0.0 | 0.875 | -0.875 |
| `premium` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:02343931 | 0.75 | 0.0 | 0.75 |
| `pristine` | Cleanliness | Room, Food, Cleanliness, Facilities | No explicit aspect guard | a:01907293 | 0.375 | 0.25 | 0.125 |
| `professional` | Professionalism | Staff, Service, Facilities | No explicit aspect guard | a:01870100 | 0.0 | 0.0 | 0.0 |
| `prompt` | Response Time | Staff, Service, Facilities | No explicit aspect guard | a:01900630 | 0.0 | 0.0 | 0.0 |
| `punctual` | Response Time | Staff, Service, Facilities | No explicit aspect guard | a:01900349 | 0.0 | 0.0 | 0.0 |
| `quick` | Response Time | Staff, Service, Facilities | No explicit aspect guard | a:00979366 | 0.0 | 0.0 | 0.0 |
| `quiet` | Noise | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:01918984 | 0.25 | 0.0 | 0.25 |
| `rancid` | Taste | Food | No explicit aspect guard | a:01070321 | 0.0 | 0.625 | -0.625 |
| `rapid` | Response Time | Staff, Service, Facilities | No explicit aspect guard | a:00979697 | 0.0 | 0.0 | 0.0 |
| `raw` | Taste | Food | No explicit aspect guard | a:00619433 | 0.0 | 0.75 | -0.75 |
| `reasonable` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:01943406 | 0.5 | 0.0 | 0.5 |
| `relaxing` | Comfort | Room, Facilities | No explicit aspect guard | a:01922227 | 0.375 | 0.0 | 0.375 |
| `reliable` | Reliability | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:00724081 | 0.375 | 0.0 | 0.375 |
| `remarkable` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:01678417 | 0.25 | 0.25 | 0.0 |
| `respectful` | Professionalism | Staff, Service, Facilities | No explicit aspect guard | a:01993940 | 0.625 | 0.0 | 0.625 |
| `responsive` | Professionalism | Staff, Service, Facilities | No explicit aspect guard | a:01999306 | 0.25 | 0.0 | 0.25 |
| `restful` | Comfort | Room, Facilities | No explicit aspect guard | a:01922227 | 0.375 | 0.0 | 0.375 |
| `roomy` | Space | Room, Facilities | No explicit aspect guard | a:00476249 | 0.0 | 0.0 | 0.0 |
| `rotten` | Taste | Food | No explicit aspect guard | a:01127782 | 0.0 | 0.75 | -0.75 |
| `rowdy` | Noise | Room, Facilities | No explicit aspect guard | a:01667110 | 0.125 | 0.0 | 0.125 |
| `rude` | Friendliness | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:00641944 | 0.0 | 0.625 | -0.625 |
| `rushed` | Professionalism | Staff, Service, Facilities | No explicit aspect guard | a:01271604 | 0.0 | 0.0 | 0.0 |
| `safe` | Safety | Room, Facilities | No explicit aspect guard | a:02057829 | 0.375 | 0.375 | 0.0 |
| `sagging` | Comfort | Room, Facilities | No explicit aspect guard | a:02403944 | 0.0 | 0.5 | -0.5 |
| `salty` | Taste | Food | No explicit aspect guard | a:02398773 | 0.0 | 0.125 | -0.125 |
| `sanitary` | Cleanliness | Room, Food, Cleanliness, Facilities | No explicit aspect guard | a:02112976 | 0.625 | 0.25 | 0.375 |
| `sanitized` | Cleanliness | Room, Food, Cleanliness, Facilities | No explicit aspect guard | a:03153554 | 0.375 | 0.0 | 0.375 |
| `satisfactory` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:02080577 | 0.5 | 0.125 | 0.375 |
| `satisfied` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:00589344 | 0.375 | 0.0 | 0.375 |
| `satisfying` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:02081563 | 0.25 | 0.0 | 0.25 |
| `savory` | Taste | Food | No explicit aspect guard | a:00133669 | 0.625 | 0.25 | 0.375 |
| `savoury` | Taste | Food | No explicit aspect guard | a:00133669 | 0.625 | 0.25 | 0.375 |
| `scrumptious` | Taste | Food | No explicit aspect guard | a:02396720 | 0.75 | 0.25 | 0.5 |
| `secure` | Safety | Room, Facilities | No explicit aspect guard | a:02093888 | 0.5 | 0.25 | 0.25 |
| `serene` | Noise | Room, Facilities | No explicit aspect guard | a:00529657 | 0.125 | 0.5 | -0.375 |
| `serviceable` | Condition | Room, Facilities | No explicit aspect guard | a:02123812 | 0.0 | 0.0 | 0.0 |
| `shabby` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:02583043 | 0.375 | 0.25 | 0.125 |
| `silent` | Noise | Room, Facilities | No explicit aspect guard | a:01919428 | 0.125 | 0.375 | -0.25 |
| `sleepless` | Comfort | Room, Facilities | No explicit aspect guard | a:00187176 | 0.0 | 0.625 | -0.625 |
| `slippery` | Safety | Room, Facilities | No explicit aspect guard | a:02234781 | 0.0 | 0.0 | 0.0 |
| `slow` | Response Time | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:00980527 | 0.0 | 0.0 | 0.0 |
| `sluggish` | Response Time | Staff, Service, Facilities | No explicit aspect guard | a:00981703 | 0.0 | 0.0 | 0.0 |
| `small` | Space | Room, Facilities | No explicit aspect guard | a:01391351 | 0.0 | 0.375 | -0.375 |
| `smelly` | Cleanliness | Room, Food, Cleanliness, Facilities | No explicit aspect guard | a:01053634 | 0.0 | 0.75 | -0.75 |
| `sociable` | Professionalism | Staff, Service, Facilities | No explicit aspect guard | a:02257141 | 0.625 | 0.125 | 0.5 |
| `soft` | Comfort | Room, Facilities | No explicit aspect guard | a:01152746 | 0.0 | 0.25 | -0.25 |
| `soggy` | Taste | Food | No explicit aspect guard | a:01185417 | 0.0 | 0.625 | -0.625 |
| `soiled` | Cleanliness | Room, Food, Cleanliness, Facilities | No explicit aspect guard | a:00419289 | 0.0 | 0.75 | -0.75 |
| `soundproof` | Noise | Room, Facilities | No explicit aspect guard | a:01775420 | 0.0 | 0.75 | -0.75 |
| `sour` | Taste | Food | No explicit aspect guard | a:01054922 | 0.0 | 0.375 | -0.375 |
| `spacious` | Space | Room | No explicit aspect guard | a:00476249 | 0.0 | 0.0 | 0.0 |
| `speedy` | Response Time | Staff, Service, Facilities | No explicit aspect guard | a:00979862 | 0.5 | 0.0 | 0.5 |
| `spicy` | Taste | Food | No explicit aspect guard | a:02398378 | 0.375 | 0.5 | -0.125 |
| `splendid` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:00219389 | 0.625 | 0.125 | 0.5 |
| `spotless` | Cleanliness | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:00418364 | 0.5 | 0.0 | 0.5 |
| `spotty` | Reliability | Room, Facilities | No explicit aspect guard | a:00578662 | 0.625 | 0.25 | 0.375 |
| `stable` | Condition | Room, Facilities | No explicit aspect guard | a:02290998 | 0.0 | 0.0 | 0.0 |
| `stained` | Cleanliness | Room, Food, Cleanliness, Facilities | No explicit aspect guard | a:00402004 | 0.0 | 0.375 | -0.375 |
| `stale` | Freshness | Food, Room | No explicit aspect guard | a:01068726 | 0.5 | 0.25 | 0.25 |
| `sterile` | Cleanliness | Room, Food, Cleanliness, Facilities | No explicit aspect guard | a:02115759 | 0.625 | 0.0 | 0.625 |
| `sticky` | Cleanliness | Room, Food, Cleanliness, Facilities | No explicit aspect guard | a:00053691 | 0.0 | 0.0 | 0.0 |
| `stiff` | Comfort | Room, Facilities | No explicit aspect guard | a:01023706 | 0.0 | 0.75 | -0.75 |
| `stinky` | Cleanliness | Room, Food, Cleanliness, Facilities | No explicit aspect guard | a:01053144 | 0.0 | 0.875 | -0.875 |
| `strong` | Condition | Room, Facilities | No explicit aspect guard | a:02321009 | 0.5 | 0.0 | 0.5 |
| `stuffy` | Comfort | Room, Facilities | No explicit aspect guard | a:02509484 | 0.125 | 0.25 | -0.125 |
| `stunning` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:01282921 | 0.0 | 0.0 | 0.0 |
| `sturdy` | Condition | Room, Facilities | No explicit aspect guard | a:02038994 | 0.5 | 0.25 | 0.25 |
| `stylish` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:00975171 | 0.5 | 0.125 | 0.375 |
| `substandard` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:02297409 | 0.0 | 0.25 | -0.25 |
| `succulent` | Taste | Food | No explicit aspect guard | a:01369078 | 0.0 | 0.375 | -0.375 |
| `superb` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:02342608 | 0.875 | 0.0 | 0.875 |
| `superior` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:02341266 | 0.625 | 0.0 | 0.625 |
| `supportive` | Comfort | Room, Facilities | No explicit aspect guard | a:02354537 | 0.125 | 0.0 | 0.125 |
| `sweet` | Taste | Food | No explicit aspect guard | a:02368336 | 0.0 | 0.0 | 0.0 |
| `sympathetic` | Professionalism | Staff, Service, Facilities | No explicit aspect guard | a:03008013 | 0.0 | 0.0 | 0.0 |
| `tainted` | Cleanliness | Room, Food, Cleanliness, Facilities | No explicit aspect guard | a:01070716 | 0.0 | 0.5 | -0.5 |
| `tardy` | Response Time | Staff, Service, Facilities | No explicit aspect guard | a:01901186 | 0.125 | 0.25 | -0.125 |
| `tasteless` | Taste | Food | No explicit aspect guard | a:02399399 | 0.125 | 0.25 | -0.125 |
| `tasty` | Taste | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:02395115 | 0.625 | 0.25 | 0.375 |
| `tender` | Taste | Food | No explicit aspect guard | a:02446651 | 0.0 | 0.25 | -0.25 |
| `terrible` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:01126291 | 0.0 | 0.875 | -0.875 |
| `terrific` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:01676517 | 0.75 | 0.0 | 0.75 |
| `thoughtful` | Professionalism | Staff, Service, Facilities | No explicit aspect guard | a:00639230 | 0.25 | 0.0 | 0.25 |
| `thoughtless` | Professionalism | Staff, Service, Facilities | No explicit aspect guard | a:02420530 | 0.625 | 0.0 | 0.625 |
| `tidy` | Cleanliness | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:02422685 | 0.625 | 0.0 | 0.625 |
| `timely` | Response Time | Staff, Service, Facilities | No explicit aspect guard | a:01900771 | 0.0 | 0.0 | 0.0 |
| `tiny` | Space | Room, Facilities | No explicit aspect guard | a:01392249 | 0.0 | 0.0 | 0.0 |
| `tranquil` | Noise | Room, Facilities | No explicit aspect guard | a:00529657 | 0.125 | 0.5 | -0.375 |
| `trustworthy` | Professionalism | Staff, Service, Facilities | No explicit aspect guard | a:02464693 | 0.5 | 0.0 | 0.5 |
| `ugly` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:00220956 | 0.0 | 0.375 | -0.375 |
| `unacceptable` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:02083053 | 0.0 | 0.75 | -0.75 |
| `unappetizing` | Taste | Food | No explicit aspect guard | a:00133851 | 0.0 | 0.75 | -0.75 |
| `unavailable` | Condition | Room, Facilities | No explicit aspect guard | a:00185921 | 0.375 | 0.5 | -0.125 |
| `unbearable` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:02435671 | 0.0 | 0.625 | -0.625 |
| `unclean` | Cleanliness | Room, Food, Cleanliness, Facilities | No explicit aspect guard | a:00419289 | 0.0 | 0.75 | -0.75 |
| `uncomfortable` | Comfort | Room | No explicit aspect guard | a:00478015 | 0.0 | 0.625 | -0.625 |
| `uncooperative` | Professionalism | Staff, Service, Facilities | No explicit aspect guard | a:00620585 | 0.0 | 0.625 | -0.625 |
| `uncrowded` | Space | Room, Facilities | No explicit aspect guard | a:00560453 | 0.0 | 0.25 | -0.25 |
| `underdone` | Taste | Food | No explicit aspect guard | a:00619601 | 0.125 | 0.0 | 0.125 |
| `unfriendly` | Friendliness | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:01076793 | 0.0 | 0.75 | -0.75 |
| `unhappy` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:01149494 | 0.0 | 0.75 | -0.75 |
| `unhelpful` | Helpfulness | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:01198019 | 0.125 | 0.25 | -0.125 |
| `unhygienic` | Hygiene | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:02113672 | 0.25 | 0.5 | -0.25 |
| `unimpressive` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:01286539 | 0.125 | 0.5 | -0.375 |
| `uninviting` | Comfort | Room, Facilities | No explicit aspect guard | a:01359035 | 0.75 | 0.0 | 0.75 |
| `unkempt` | Cleanliness | Room, Food, Cleanliness, Facilities | No explicit aspect guard | a:02426890 | 0.0 | 0.75 | -0.75 |
| `unkind` | Professionalism | Staff, Service, Facilities | No explicit aspect guard | a:01373728 | 0.5 | 0.375 | 0.125 |
| `unpalatable` | Taste | Food | No explicit aspect guard | a:01716491 | 0.125 | 0.75 | -0.625 |
| `unpleasant` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:01801600 | 0.125 | 0.625 | -0.5 |
| `unprofessional` | Professionalism | Staff, Service, Facilities | No explicit aspect guard | a:01870321 | 0.0 | 0.625 | -0.625 |
| `unreliable` | Reliability | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:00724861 | 0.0 | 0.75 | -0.75 |
| `unresponsive` | Professionalism | Staff, Service, Facilities | No explicit aspect guard | a:01999766 | 0.0 | 0.75 | -0.75 |
| `unsafe` | Safety | Room, Facilities | No explicit aspect guard | a:02094755 | 0.25 | 0.375 | -0.125 |
| `unsanitary` | Cleanliness | Room, Food, Cleanliness, Facilities | No explicit aspect guard | a:02113449 | 0.5 | 0.125 | 0.375 |
| `unsatisfactory` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:02082218 | 0.0 | 0.5 | -0.5 |
| `unserviceable` | Condition | Room, Facilities | No explicit aspect guard | a:02124654 | 0.0 | 0.625 | -0.625 |
| `unsound` | Safety | Room, Facilities | No explicit aspect guard | a:02275629 | 0.0 | 0.875 | -0.875 |
| `unstable` | Condition | Room, Facilities | No explicit aspect guard | a:02291843 | 0.25 | 0.375 | -0.125 |
| `unsympathetic` | Professionalism | Staff, Service, Facilities | No explicit aspect guard | a:02375828 | 0.0 | 0.875 | -0.875 |
| `unusable` | Condition | Room, Facilities | No explicit aspect guard | a:02497830 | 0.0 | 0.625 | -0.625 |
| `unventilated` | Comfort | Room, Facilities | No explicit aspect guard | a:02509292 | 0.0 | 0.25 | -0.25 |
| `unwashed` | Cleanliness | Room, Food, Cleanliness, Facilities | No explicit aspect guard | a:00423874 | 0.0 | 0.75 | -0.75 |
| `usable` | Condition | Room, Facilities | No explicit aspect guard | a:02496674 | 0.0 | 0.0 | 0.0 |
| `ventilated` | Comfort | Room, Facilities | No explicit aspect guard | a:02508766 | 0.0 | 0.0 | 0.0 |
| `warm` | Temperature | Room, Facilities | No explicit aspect guard | a:02529264 | 0.5 | 0.125 | 0.375 |
| `weak` | Condition | Room, Facilities | No explicit aspect guard | a:02324397 | 0.125 | 0.5 | -0.375 |
| `welcoming` | Professionalism | Staff, Service, Facilities | No explicit aspect guard | a:01244106 | 0.0 | 0.125 | -0.125 |
| `well-lighted` | Lighting | Room, Facilities | No explicit aspect guard | a:00271580 | 0.0 | 0.0 | 0.0 |
| `wet` | Cleanliness | Room, Food, Cleanliness, Facilities | No explicit aspect guard | a:02547317 | 0.0 | 0.0 | 0.0 |
| `wonderful` | Quality | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard | a:01676517 | 0.75 | 0.0 | 0.75 |
| `working` | Functionality | Room, Staff, Service, Food, Cleanliness, Facilities | A2 | a:01091728 | 0.25 | 0.0 | 0.25 |
| `worn` | Condition | Room, Facilities | No explicit aspect guard | a:02580449 | 0.0 | 0.5 | -0.5 |
| `worn-out` | Condition | Room, Facilities | No explicit aspect guard | a:02582873 | 0.0 | 0.25 | -0.25 |
| `yummy` | Taste | Food | No explicit aspect guard | a:02396720 | 0.75 | 0.25 | 0.5 |

### Source sense selection and gloss for every canonical opinion

| Opinion | Selection basis | Default source gloss |
| --- | --- | --- |
| `abrupt` | Explicit hotel-context gloss selection. | surprisingly and unceremoniously brusque in manner; "an abrupt reply" |
| `abusive` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | expressing offensive reproach |
| `abysmal` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | very great; limitless; "abysmal misery"; "abysmal stupidity" |
| `acceptable` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | worthy of acceptance or satisfactory; "acceptable levels of radiation"; "performances varied from acceptable to excellent" |
| `accessible` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | capable of being reached; "a town accessible by rail" |
| `accommodating` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | helpful in bringing about a harmonious adaptation; "the warden was always accommodating in allowing visitors in"; "made a special effort to be accommodating" |
| `adequate` | Explicit hotel-context gloss selection. | sufficient for the purpose; "an adequate income"; "the food was adequate"; "a decent wage"; "enough food"; "food enough" |
| `airy` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | open to or abounding in fresh air; "airy rooms" |
| `amazing` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | surprising greatly; "she does an amazing amount of work"; "the dog was capable of astonishing tricks" |
| `appalling` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | causing consternation; "appalling conditions" |
| `appetizing` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | appealing to or stimulating the appetite especially in appearance or aroma |
| `arrogant` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | having or showing feelings of unwarranted importance out of overbearing pride; "an arrogant official"; "arrogant claims"; "chesty as a peacock" |
| `astonishing` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | surprising greatly; "she does an amazing amount of work"; "the dog was capable of astonishing tricks" |
| `atrocious` | Explicit hotel-context gloss selection. | exceptionally bad or displeasing; "atrocious taste"; "abominable workmanship"; "an awful voice"; "dreadful manners"; "a painful performance"; "terrible handwriting"; "an unspeakable odor came sweeping into the room" |
| `attentive` | Previously configured controlled sense | (often followed by `to') giving care or attention; "attentive to details"; "the nurse was attentive to her patient"; "an attentive suitor" |
| `attractive` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | pleasing to the eye or mind especially through beauty or charm; "a remarkably attractive young man"; "an attractive personality"; "attractive clothes"; "a book with attractive illustrations" |
| `available` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | obtainable or accessible and ready for use or service; "kept a fire extinguisher available"; "much information is available through computers"; "available in many colors"; "the list of available candidates is unusually long" |
| `average` | Previously configured controlled sense | approximating the statistical norm or average or expected value; "the average income in New England is below that of the nation"; "of average height for his age"; "the mean annual rainfall" |
| `awesome` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | inspiring awe or admiration or wonder; "New York is an amazing city"; "the Grand Canyon is an awe-inspiring sight"; "the awesome complexity of the universe"; "this sea, whose gently awful stirrings seem to speak of some hidden soul beneath"- Melville; "Westminster Hall's awing majesty, so vast, so high, so silent" |
| `awful` | Previously configured controlled sense | exceptionally bad or displeasing; "atrocious taste"; "abominable workmanship"; "an awful voice"; "dreadful manners"; "a painful performance"; "terrible handwriting"; "an unspeakable odor came sweeping into the room" |
| `bad` | Previously configured controlled sense | having undesirable or negative qualities; "a bad report card"; "his sloppy appearance made a bad impression"; "a bad little boy"; "clothes in bad shape"; "a bad cut"; "bad luck"; "the news was very bad"; "the reviews were bad"; "the pay is bad"; "it was a bad light for reading"; "the movie was a bad choice" |
| `basic` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | pertaining to or constituting a base or basis; "a basic fact"; "the basic ingredients"; "basic changes in public opinion occur because of changes in priorities" |
| `beautiful` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | delighting the senses or exciting intellectual or emotional admiration; "a beautiful child"; "beautiful country"; "a beautiful painting"; "a beautiful theory"; "a beautiful party" |
| `big` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | above average in size or number or quantity or magnitude or extent; "a large city"; "set out for the big city"; "a large sum"; "a big (or large) barn"; "a large family"; "big businesses"; "a big expenditure"; "a large number of newspapers"; "a big group of scientists"; "large areas of the world" |
| `bitter` | Explicit hotel-context gloss selection. | causing a sharp and acrid taste experience;"quinine is bitter" |
| `bland` | Previously configured controlled sense | lacking taste or flavor or tang; "a bland diet"; "insipid hospital food"; "flavorless supermarket tomatoes"; "vapid beer"; "vapid tea" |
| `blocked` | Explicit hotel-context gloss selection. | completely obstructed or closed off; "the storm was responsible for many blocked roads and bridges"; "the drain was plugged" |
| `boisterous` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | noisy and lacking in restraint or discipline; "a boisterous crowd"; "a social gathering that became rambunctious and out of hand"; "a robustious group of teenagers"; "beneath the rumbustious surface of his paintings is sympathy for the vulnerability of ordinary human beings"; "an unruly class" |
| `bright` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | emitting or reflecting light readily or in large amounts; "the sun was bright and hot"; "a bright sunlit room" |
| `brilliant` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | of surpassing excellence; "a brilliant performance"; "a superb actor" |
| `broken` | Previously configured controlled sense | out of working order (`busted' is an informal substitute for `broken'); "a broken washing machine"; "the coke machine is broken"; "the coke machine is busted" |
| `burned` | Explicit hotel-context gloss selection. | ruined by overcooking; "she served us underdone bacon and burnt biscuits" |
| `burnt` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | ruined by overcooking; "she served us underdone bacon and burnt biscuits" |
| `calm` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | not agitated; without losing self-possession; "spoke in a calm voice"; "remained calm throughout the uproar"; "he remained serene in the midst of turbulence"; "a serene expression on her face"; "she became more tranquil"; "tranquil life in the country" |
| `caring` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | feeling and exhibiting concern and empathy for others; "caring friends" |
| `cheerful` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | being full of or promoting cheer; having or showing good spirits; "her cheerful nature"; "a cheerful greeting"; "a cheerful room"; "as cheerful as anyone confined to a hospital bed could be" |
| `chewy` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | requiring much chewing |
| `chilly` | Explicit hotel-context gloss selection. | appreciably or disagreeably cold |
| `clean` | Previously configured controlled sense | free from dirt or impurities; or having clean habits; "children with clean shining faces"; "clean white shirts"; "clean dishes"; "a spotlessly clean house"; "cats are clean animals" |
| `clogged` | Explicit hotel-context gloss selection. | stopped up; clogged up; "clogged pipes"; "clogged up freeways"; "streets choked with traffic" |
| `cluttered` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | filled or scattered with a disorderly accumulation of objects or rubbish; "the storm left the drivewaylittered with sticks nd debris"; "his library was a cluttered room with piles of books on every chair" |
| `cold` | Previously configured controlled sense | having a low or inadequate temperature or feeling a sensation of coldness or having been made cold by e.g. ice or refrigeration; "a cold climate"; "a cold room"; "dinner has gotten cold"; "cold fingers"; "if you are cold, turn up the heat"; "a cold beer" |
| `comfortable` | Previously configured controlled sense | providing or experiencing physical well-being or relief (`comfy' is informal); "comfortable clothes"; "comfortable suburban houses"; "made himself comfortable in an armchair"; "the antihistamine made her feel more comfortable"; "are you comfortable?"; "feeling comfy now?" |
| `compact` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | closely and firmly united or packed together; "compact soil"; "compact clusters of flowers" |
| `competent` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | properly or sufficiently qualified or capable or efficient; "a competent typist" |
| `congested` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | overfull as with blood |
| `connected` | Explicit hotel-context gloss selection. | plugged in; "first check to see whether the appliance is connected" |
| `considerate` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | showing concern for the rights and feelings of others; "friends considerate enough to leave us alone" |
| `contaminated` | Explicit hotel-context gloss selection. | rendered unwholesome by contaminants and pollution; "had to boil the contaminated water"; "polluted lakes and streams" |
| `convenient` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | suited to your comfort or purpose or needs; "a convenient excuse for not going" |
| `cooked` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | having been prepared for eating by the application of heat |
| `cooperative` | Explicit hotel-context gloss selection. | willing to adjust to differences in order to obtain agreement |
| `cosy` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | enjoying or affording comforting warmth and shelter especially in a small space; "a cozy nook near the fire"; "snug in bed"; "a snug little apartment" |
| `courteous` | Previously configured controlled sense | exhibiting courtesy and politeness; "a nice gesture" |
| `cozy` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | enjoying or affording comforting warmth and shelter especially in a small space; "a cozy nook near the fire"; "snug in bed"; "a snug little apartment" |
| `cramped` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | constricted in size; "cramped quarters"; "trying to bring children up in cramped high-rise apartments" |
| `crisp` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | (of something seen or heard) clearly defined; "a sharp photographic image"; "the sharp crack of a twig"; "the crisp snap of dry leaves underfoot" |
| `crispy` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | tender and brittle; "crisp potato chips" |
| `crowded` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | overfilled or compacted or concentrated; "a crowded theater"; "a crowded program"; "crowded trains"; "a young mother's crowded days" |
| `cushioned` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | softened by the addition of cushions or padding |
| `damaged` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | harmed or injured or spoiled; "I won't buy damaged goods"; "the storm left a wake of badly damaged buildings" |
| `damp` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | slightly wet; "clothes damp with perspiration"; "a moist breeze"; "eyes moist with tears" |
| `dangerous` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | involving or causing danger or risk; liable to hurt or harm; "a dangerous criminal"; "a dangerous bridge"; "unemployment reached dangerous proportions" |
| `dark` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | devoid of or deficient in light or brightness; shadowed or black; "sitting in a dark corner"; "a dark day"; "dark shadows"; "dark as the inside of a black cat" |
| `deafening` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | loud enough to cause (temporary) hearing loss |
| `decent` | Explicit hotel-context gloss selection. | sufficient for the purpose; "an adequate income"; "the food was adequate"; "a decent wage"; "enough food"; "food enough" |
| `defective` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | having a defect; "I returned the appliance because it was defective" |
| `delayed` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | not as far along as normal in development |
| `delicious` | Previously configured controlled sense | extremely pleasing to the sense of taste |
| `delighted` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | greatly pleased |
| `delightful` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | greatly pleasing or entertaining; "a delightful surprise"; "the comedy was delightful"; "a delicious joke" |
| `dilapidated` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | in deplorable condition; "a street of bedraggled tenements"; "a broken-down fence"; "a ramshackle old pier"; "a tumble-down shack" |
| `diluted` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | reduced in strength or concentration or quality or purity; "diluted alcohol"; "a dilute solution"; "dilute acetic acid" |
| `dim` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | lacking in light; not bright or harsh; "a dim light beside the bed"; "subdued lights and soft music" |
| `dingy` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | thickly covered with ingrained dirt or soot; "a miner's begrimed face"; "dingy linen"; "grimy hands"; "grubby little fingers"; "a grungy kitchen" |
| `dirty` | Previously configured controlled sense | soiled or likely to soil with dirt or grime; "dirty unswept sidewalks"; "a child in dirty overalls"; "dirty slums"; "piles of dirty dishes"; "put his dirty feet on the clean sheet"; "wore an unclean shirt"; "mining is a dirty job"; "Cinderella did the dirty work while her sisters preened themselves" |
| `disappointed` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | disappointingly unsuccessful; "disappointed expectations and thwarted ambitions"; "their foiled attempt to capture Calais"; "many frustrated poets end as pipe-smoking teachers"; "his best efforts were thwarted" |
| `disappointing` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | not up to expectations; "a disappointing performance from one who had seemed so promising" |
| `disconnected` | Explicit hotel-context gloss selection. | not plugged in or connected to a power source; "the iron is disconnected" |
| `discourteous` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | showing no courtesy; rude; "a distant and at times discourteous young" |
| `disgusted` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | having a strong distaste from surfeit; "grew more and more disgusted"; "fed up with their complaints"; "sick of it all"; "sick to death of flattery"; "gossip that makes one sick"; "tired of the noise and smoke" |
| `disgusting` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | highly offensive; arousing aversion or disgust; "a disgusting smell"; "distasteful language"; "a loathsome disease"; "the idea of eating meat is repellent to me"; "revolting food"; "a wicked stench" |
| `disheveled` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | in disarray; extremely disorderly; "her clothing was disheveled"; "powder-smeared and frowzled"; "a rumpled unmade bed"; "a bed with tousled sheets"; "his brown hair was tousled, thick, and curly"- Al Spiers |
| `dishevelled` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | in disarray; extremely disorderly; "her clothing was disheveled"; "powder-smeared and frowzled"; "a rumpled unmade bed"; "a bed with tousled sheets"; "his brown hair was tousled, thick, and curly"- Al Spiers |
| `dishonest` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | deceptive or fraudulent; disposed to cheat or defraud or deceive |
| `dismissive` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | showing indifference or disregard; "a dismissive shrug"; "the firm is dismissive of the competitor's product"; "'chronic fatigue syndrome' was known by the dismissive term 'housewife syndrome'" |
| `displeased` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | not pleased; experiencing or manifesting displeasure |
| `disrespectful` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | exhibiting lack of respect; rude and discourteous; "remarks disrespectful of the law"; "disrespectful in the presence of his parents"; "disrespectful toward his teacher" |
| `disruptive` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | characterized by unrest or disorder or insubordination; "effects of the struggle will be violent and disruptive"; "riotous times"; "these troubled areas"; "the tumultuous years of his administration"; "a turbulent and unruly childhood" |
| `dissatisfied` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | in a state of sulky dissatisfaction |
| `disturbing` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | causing distress or worry or anxiety; "distressing (or disturbing) news"; "lived in heroic if something distressful isolation"; "a disturbing amount of crime"; "a revelation that was most perturbing"; "a new and troubling thought"; "in a particularly worrisome predicament"; "a worrying situation"; "a worrying time" |
| `drafty` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | not airtight |
| `draughty` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | not airtight |
| `dreadful` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | causing fear or dread or terror; "the awful war"; "an awful risk"; "dire news"; "a career or vengeance so direful that London was shocked"; "the dread presence of the headmaster"; "polio is no longer the dreaded disease it once was"; "a dreadful storm"; "a fearful howling"; "horrendous explosions shook the city"; "a terrible curse" |
| `dry` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | free from liquid or moisture; lacking natural or normal moisture or depleted of water; or no longer wet; "dry land"; "dry clothes"; "a dry climate"; "dry splintery boards"; "a dry river bed"; "the paint is dry" |
| `durable` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | existing for a long time; "hopes for a durable peace"; "a long-lasting friendship" |
| `dusty` | Previously configured controlled sense | covered with a layer of dust; "a dusty pile of books" |
| `edible` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | suitable for use as food |
| `effective` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | producing or capable of producing an intended result or having a striking effect; "an air-cooled motor was more effective than a witch's broomstick for rapid long-distance transportation"-LewisMumford; "effective teaching methods"; "effective steps toward peace"; "made an effective entrance"; "his complaint proved to be effectual in bringing action"; "an efficacious law" |
| `efficient` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | being effective without wasting time or effort or expense; "an efficient production manager"; "efficient engines save gas" |
| `elegant` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | refined and tasteful in appearance or behavior or style; "elegant handwriting"; "an elegant dark suit"; "she was elegant to her fingertips"; "small churches with elegant white spires"; "an elegant mathematical solution--simple and precise and lucid" |
| `enjoyable` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | affording satisfaction or pleasure; "the company was enjoyable"; "found her praise gratifying"; "full of happiness and pleasurable excitement"; "good printing makes a book more pleasurable to read" |
| `excellent` | Previously configured controlled sense | very good;of the highest quality; "made an excellent speech"; "the school has excellent teachers"; "a first-class mind" |
| `exceptional` | Explicit hotel-context gloss selection. | surpassing what is common or usual or expected; "he paid especial attention to her"; "exceptional kindness"; "a matter of particular and unusual importance"; "a special occasion"; "a special reason to confide in her"; "what's so special about the year 2000?" |
| `fabulous` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | extremely pleasing; "a fabulous vacation" |
| `fantastic` | Previously configured controlled sense | extraordinarily good or great ; used especially as intensifiers; "a fantastic trip to the Orient"; "the film was fantastic!"; "a howling success"; "a marvelous collection of rare books"; "had a rattling conversation about politics"; "a tremendous achievement" |
| `fast` | Previously configured controlled sense | acting or moving or capable of acting or moving quickly; "fast film"; "on the fast track in school"; "set a fast pace"; "a fast car" |
| `faulty` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | having a defect; "I returned the appliance because it was defective" |
| `fetid` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | offensively malodorous; "a foul odor"; "the kitchen smelled really funky" |
| `filthy` | Previously configured controlled sense | disgustingly dirty; filled or smeared with offensive matter; "as filthy as a pigsty"; "a foul pond"; "a nasty pigsty of a room" |
| `fine` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | being satisfactory or in satisfactory condition; "an all-right movie"; "the passengers were shaken up but are all right"; "is everything all right?"; "everything's fine"; "things are okay"; "dinner and the movies had been fine"; "another minute I'd have been fine" |
| `firm` | Explicit hotel-context gloss selection. | not soft or yielding to pressure; "a firm mattress"; "the snow was firm underfoot"; "solid ground" |
| `flavorful` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | full of flavor |
| `flavorsome` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | full of flavor |
| `flavourful` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | full of flavor |
| `flickering` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | shining unsteadily |
| `foul` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | highly offensive; arousing aversion or disgust; "a disgusting smell"; "distasteful language"; "a loathsome disease"; "the idea of eating meat is repellent to me"; "revolting food"; "a wicked stench" |
| `fresh` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | recently made, produced, or harvested; "fresh bread"; "a fresh scent"; "fresh lettuce" |
| `friendly` | Previously configured controlled sense | characteristic of or befitting a friend; "friendly advice"; "a friendly neighborhood"; "the only friendly person here"; "a friendly host and hostess" |
| `functional` | Explicit hotel-context gloss selection. | (of e.g. a machine) performing or capable of performing; "in running (or working) order"; "a functional set of brakes" |
| `functioning` | Previously configured controlled sense | performing or able to perform its regular function; "a functioning flashlight" |
| `generous` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | willing to give and share unstintingly; "a generous donation" |
| `good` | Previously configured controlled sense | having desirable or positive qualities especially those suitable for a thing specified; "good news from the hospital"; "a good report card"; "when she was good she was very very good"; "a good knife is one good for cutting"; "this stump will make a good picnic table"; "a good check"; "a good joke"; "a good exterior paint"; "a good secretary"; "a good dress for the office" |
| `gorgeous` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | dazzlingly beautiful; "a gorgeous Victorian gown" |
| `greasy` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | containing an unusual amount of grease or oil; "greasy hamburgers"; "oily fried potatoes"; "oleaginous seeds" |
| `great` | Explicit hotel-context gloss selection. | very good; "he did a bully job"; "a neat sports car"; "had a great time at the party"; "you look simply smashing" |
| `grimy` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | thickly covered with ingrained dirt or soot; "a miner's begrimed face"; "dingy linen"; "grimy hands"; "grubby little fingers"; "a grungy kitchen" |
| `grubby` | Explicit hotel-context gloss selection. | thickly covered with ingrained dirt or soot; "a miner's begrimed face"; "dingy linen"; "grimy hands"; "grubby little fingers"; "a grungy kitchen" |
| `happy` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | enjoying or showing or marked by joy or pleasure; "a happy smile"; "spent many happy days on the beach"; "a happy marriage" |
| `hard` | Explicit hotel-context gloss selection. | resisting weight or pressure |
| `hazardous` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | involving risk or danger; "skydiving is a hazardous sport"; "extremely risky going out in the tide and fog"; "a wild financial scheme" |
| `helpful` | Previously configured controlled sense | providing assistance or serving a useful function |
| `honest` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | not disposed to cheat or defraud; not deceptive or fraudulent; "honest lawyers"; "honest reporting" |
| `horrendous` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | causing fear or dread or terror; "the awful war"; "an awful risk"; "dire news"; "a career or vengeance so direful that London was shocked"; "the dread presence of the headmaster"; "polio is no longer the dreaded disease it once was"; "a dreadful storm"; "a fearful howling"; "horrendous explosions shook the city"; "a terrible curse" |
| `horrible` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | provoking horror; "an atrocious automobile accident"; "a frightful crime of decapitation"; "an alarming, even horrifying, picture"; "war is beyond all words horrible"- Winston Churchill; "an ugly wound" |
| `hospitable` | Explicit hotel-context gloss selection. | disposed to treat guests and strangers with cordiality and generosity; "a good-natured and hospitable man"; "a hospitable act"; "hospitable invitations" |
| `hostile` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | characterized by enmity or ill will; "a hostile nation"; "a hostile remark"; "hostile actions" |
| `hot` | Previously configured controlled sense | used of physical heat; having a high or higher than desirable temperature or giving off heat or feeling or causing a sensation of heat or burning; "hot stove"; "hot water"; "a hot August day"; "a hot stuffy room"; "she's hot and tired"; "a hot forehead" |
| `huge` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | unusually great in size or amount or degree or especially extent or scope; "huge government spending"; "huge country estates"; "huge popular demand for higher education"; "a huge wave"; "the Los Angeles aqueduct winds like an immense snake along the base of the mountains"; "immense numbers of birds"; "at vast (or immense) expense"; "the vast reaches of outer space"; "the vast accumulation of knowledge...which we call civilization"- W.R.Inge |
| `hygienic` | Previously configured controlled sense | tending to promote or preserve health; "hygienic habits like using disposable tissues"; "hygienic surroundings with plenty of fresh air" |
| `immaculate` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | completely neat and clean; "the apartment was immaculate"; "in her immaculate white uniform"; "a spick-and-span kitchen"; "their spic red-visored caps" |
| `impatient` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | restless or short-tempered under delay or opposition; "impatient with the slower students"; "impatient of criticism" |
| `imperfect` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | not perfect; defective or inadequate; "had only an imperfect understanding of his responsibilities"; "imperfect mortals"; "drainage here is imperfect" |
| `impolite` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | not polite |
| `impressed` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | deeply or markedly affected or influenced |
| `impressive` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | making a strong or vivid impression; "an impressive ceremony" |
| `inaccessible` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | capable of being reached only with great difficulty or not at all |
| `inadequate` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | lacking the requisite qualities or resources to meet a task; "inadequate training"; "the staff was inadequate"; "she was unequal to the task" |
| `inattentive` | Previously configured controlled sense | not showing due care or attention; "inattentive students"; "an inattentive babysitter"; "neglectful parents" |
| `incompetent` | Explicit hotel-context gloss selection. | showing lack of skill or aptitude; "a bungling workman"; "did a clumsy job"; "his fumbling attempt to put up a shelf" |
| `inconsiderate` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | lacking regard for the rights or feelings of others; "shockingly inconsiderate behavior" |
| `inconvenient` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | not suited to your comfort, purpose or needs; "it is inconvenient not to have a telephone in the kitchen"; "the back hall is an inconvenient place for the telephone" |
| `indifferent` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | marked by a lack of interest; "an apathetic audience"; "the universe is neither hostile nor friendly; it is simply indifferent" |
| `inedible` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | not suitable for food |
| `ineffective` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | not producing an intended effect; "an ineffective teacher"; "ineffective legislation" |
| `inefficient` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | not producing desired results; wasteful; "an inefficient campaign against drugs"; "outdated and inefficient design and methods" |
| `inferior` | Explicit hotel-context gloss selection. | of low or inferior quality |
| `inoperative` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | not working or taking effect; "an inoperative law" |
| `insecure` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | not firm or firmly fixed; likely to fail or give way; "the hinge is insecure" |
| `intermittent` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | stopping and starting at irregular intervals; "intermittent rain showers" |
| `inviting` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | attractive and tempting; "an inviting offer" |
| `juicy` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | full of juice |
| `kind` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | having or showing a tender and considerate and helpful nature; used especially of persons and their behavior; "kind to sick patients"; "a kind master"; "kind words showing understanding and sympathy"; "thanked her for her kind letter" |
| `knowledgeable` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | highly educated; having extensive information or understanding; "knowing instructors"; "a knowledgeable critic"; "a knowledgeable audience" |
| `large` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | above average in size or number or quantity or magnitude or extent; "a large city"; "set out for the big city"; "a large sum"; "a big (or large) barn"; "a large family"; "big businesses"; "a big expenditure"; "a large number of newspapers"; "a big group of scientists"; "large areas of the world" |
| `late` | Explicit hotel-context gloss selection. | after the expected or usual time; delayed; "a belated birthday card"; "I'm late for the plane"; "the train is late"; "tardy children are sent to the principal"; "always tardy in making dental appointments" |
| `lazy` | Explicit hotel-context gloss selection. | disinclined to work or exertion; "faineant kings under whose rule the country languished"; "an indolent hanger-on"; "too lazy to wash the dishes"; "shiftless idle youth"; "slothful employees"; "the unemployed are not necessarily work-shy" |
| `leaky` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | permitting the unwanted passage of fluids or gases ; "a leaky roof"; "a leaky defense system" |
| `littered` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | filled or scattered with a disorderly accumulation of objects or rubbish; "the storm left the drivewaylittered with sticks nd debris"; "his library was a cluttered room with piles of books on every chair" |
| `loud` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | characterized by or producing sound of great volume or intensity; "a group of loud children"; "loud thunder"; "her voice was too loud"; "loud trombones" |
| `lousy` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | very bad; "a lousy play"; "it's a stinking world" |
| `lovely` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | appealing to the emotions as well as the eye |
| `lukewarm` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | moderately warm; "he hates lukewarm coffee"; "tepid bath water" |
| `lumpy` | Explicit hotel-context gloss selection. | having lumps; not smooth and even in texture; "lumpy gravy" |
| `luxurious` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | displaying luxury and furnishing gratification to the senses; "an epicurean banquet"; "enjoyed a luxurious suite with a crystal chandelier and thick oriental rugs"; "Lucullus spent the remainder of his days in voluptuous magnificence"; "a chinchilla robe of sybaritic lavishness" |
| `magnificent` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | characterized by grandeur; "the brilliant court life at Versailles"; "a glorious work of art"; "magnificent cathedrals"; "the splendid coronation ceremony" |
| `maintained` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | kept in good condition |
| `malfunctioning` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | not performing or able to perform its regular function; "a malfunctioning valve" |
| `malodorous` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | having an unpleasant smell |
| `marvellous` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | extraordinarily good or great ; used especially as intensifiers; "a fantastic trip to the Orient"; "the film was fantastic!"; "a howling success"; "a marvelous collection of rare books"; "had a rattling conversation about politics"; "a tremendous achievement" |
| `marvelous` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | extraordinarily good or great ; used especially as intensifiers; "a fantastic trip to the Orient"; "the film was fantastic!"; "a howling success"; "a marvelous collection of rare books"; "had a rattling conversation about politics"; "a tremendous achievement" |
| `mediocre` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | moderate to inferior in quality; "they improved the quality from mediocre to above average" |
| `messy` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | dirty and disorderly; "a mussy fussy bedroom"; "a child's messy eating habits" |
| `miserable` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | very unhappy; full of misery; "he felt depressed and miserable"; "a message of hope for suffering humanity"; "wretched prisoners huddled in stinking cages" |
| `modern` | Explicit hotel-context gloss selection. | relating to a recently developed fashion or style; "their offices are in a modern skyscraper"; "tables in modernistic designs"; |
| `moldy` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | covered with or smelling of mold; "moldy bread"; "a moldy (or musty) odor" |
| `mouldy` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | covered with or smelling of mold; "moldy bread"; "a moldy (or musty) odor" |
| `mouth-watering` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | pleasing to the sense of taste |
| `musty` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | covered with or smelling of mold; "moldy bread"; "a moldy (or musty) odor" |
| `narrow` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | not wide; "a narrow bridge"; "a narrow line across the page" |
| `neat` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | clean or organized; "her neat dress"; "a neat room" |
| `negligent` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | characterized by neglect and undue lack of concern; "negligent parents"; "negligent of detail"; "negligent in his correspondence" |
| `new` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | not of long duration; having just (or relatively recently) come into being or been made or acquired or discovered; "a new law"; "new cars"; "a new comet"; "a new friend"; "a new year"; "the New World" |
| `nice` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | pleasant or pleasing or agreeable in nature or appearance; "what a nice fellow you are and we all thought you so nasty"- George Meredith; "nice manners"; "a nice dress"; "a nice face"; "a nice day"; "had a nice time at the party"; "the corn and tomatoes are nice today" |
| `noisy` | Previously configured controlled sense | full of or characterized by loud and nonmusical sounds; "a noisy cafeteria"; "a small noisy dog" |
| `nutritious` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | of or providing nourishment; "good nourishing stew" |
| `obliging` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | showing a cheerful willingness to do favors for others; "to close one's eyes like a complaisant husband whose wife has taken a lover"; "the obliging waiter was in no hurry for us to leave" |
| `obnoxious` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | causing disapproval or protest; "a vulgar and objectionable person" |
| `obstructed` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | shut off to passage or view or hindered from action; "a partially obstructed passageway"; "an obstructed view"; "justice obstructed is not justice" |
| `odorless` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | having no odor; "odorless gas"; "odorless flowers" |
| `odorous` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | having odor or a characteristic odor; "odorous jasmine flowers"; "odorous garbage"; "fresh odorous bread" |
| `odourless` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | having no odor; "odorless gas"; "odorless flowers" |
| `oily` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | containing an unusual amount of grease or oil; "greasy hamburgers"; "oily fried potatoes"; "oleaginous seeds" |
| `operational` | Previously configured controlled sense | fit or ready for use or service; "the toaster was still functional even after being dropped"; "the lawnmower is a bit rusty but still usable"; "an operational aircraft"; "the dishwasher is now in working order" |
| `ordinary` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | not exceptional in any way especially in quality or ability or size or degree; "ordinary everyday objects"; "ordinary decency"; "an ordinary day"; "an ordinary wine" |
| `outdated` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | old; no longer valid or fashionable; "obsolete words"; "an obsolete locomotive"; "outdated equipment"; "superannuated laws"; "out-of-date ideas" |
| `outstanding` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | distinguished from others in excellence; "did outstanding work in human relations"; "an outstanding war record" |
| `overdone` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | represented as greater than is true or reasonable; "an exaggerated opinion of oneself" |
| `overheated` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | heated beyond a safe or desirable point; "the child became overheated"; "overheated metal" |
| `painful` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | causing physical or psychological pain; "worked with painful slowness" |
| `palatable` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | acceptable to the taste or mind; "palatable food"; "a palatable solution to the problem" |
| `passable` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | able to be passed or traversed or crossed; "the road is passable" |
| `patient` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | enduring trying circumstances with even temper or characterized by such endurance; "a patient smile"; "was patient with the children"; "an exact and patient scientist"; "please be patient" |
| `peaceful` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | not disturbed by strife or turmoil or war; "a peaceful nation"; "peaceful times"; "a far from peaceful Christmas"; "peaceful sleep" |
| `perfect` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | being complete of its kind and without defect or blemish; "a perfect circle"; "a perfect reproduction"; "perfect happiness"; "perfect manners"; "a perfect specimen"; "a perfect day" |
| `personable` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | (of persons) pleasant in appearance and personality |
| `pleasant` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | affording pleasure; being in harmony with your taste or likings; "we had a pleasant evening together"; "a pleasant scene"; "pleasant sensations" |
| `pleased` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | experiencing or manifesting pleasure |
| `plush` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | characterized by extravagance and profusion; "a lavish buffet"; "a lucullan feast" |
| `polite` | Previously configured controlled sense | showing regard for others in manners, speech, behavior, etc. |
| `polluted` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | rendered unwholesome by contaminants and pollution; "had to boil the contaminated water"; "polluted lakes and streams" |
| `poor` | Previously configured controlled sense | unsatisfactory; "a poor light for reading"; "poor morale"; "expectations were poor" |
| `premium` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | having or reflecting superior quality or value; "premium gasoline at a premium price" |
| `pristine` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | completely free from dirt or contamination; "pristine mountain snow" |
| `professional` | Explicit hotel-context gloss selection. | characteristic of or befitting a profession or one engaged in a profession; "professional conduct"; "professional ethics"; "a thoroughly professional performance" |
| `prompt` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | according to schedule or without delay; on time; "the train is prompt" |
| `punctual` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | acting or arriving or performed exactly at the time appointed; "she expected guests to be punctual at meals"; "he is not a particularly punctual person"; "punctual payment" |
| `quick` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | accomplished rapidly and without delay; "was quick to make friends"; "his quick reaction prevented an accident"; "hoped for a speedy resolution of the problem"; "a speedy recovery"; "he has a right to a speedy trial" |
| `quiet` | Previously configured controlled sense | free of noise or uproar; or making little if any sound; "a quiet audience at the concert"; "the room was dark and quiet" |
| `rancid` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | (used of decomposing oils or fats) having a rank smell or taste usually due to a chemical change or decomposition; "rancid butter"; "rancid bacon" |
| `rapid` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | done or occurring in a brief period of time; "a rapid rise through the ranks" |
| `raw` | Explicit hotel-context gloss selection. | not treated with heat to prepare it for eating |
| `reasonable` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | showing reason or sound judgment; "a sensible choice"; "a sensible person" |
| `relaxing` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | affording physical or mental rest; "she spent a restful night at home" |
| `reliable` | Previously configured controlled sense | worthy of reliance or trust; "a reliable source of information"; "a dependable worker" |
| `remarkable` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | unusual or striking; "a remarkable sight"; "such poise is singular in one so young" |
| `respectful` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | full of or exhibiting respect; "respectful behavior"; "a respectful glance" |
| `responsive` | Explicit hotel-context gloss selection. | readily reacting or replying to people or events or stimuli; showing emotion; "children are often the quickest and most responsive members of the audience" |
| `restful` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | affording physical or mental rest; "she spent a restful night at home" |
| `roomy` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | (of buildings and rooms) having ample space; "a roomy but sparsely furnished apartment"; "a spacious ballroom" |
| `rotten` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | very bad; "a lousy play"; "it's a stinking world" |
| `rowdy` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | disturbing the public peace; loud and rough; "a raucous party"; "rowdy teenagers" |
| `rude` | Previously configured controlled sense | socially incorrect in behavior; "resentment flared at such an unmannered intrusion" |
| `rushed` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | done under pressure; "a rush job" |
| `safe` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | free from danger or the risk of harm; "a safe trip"; "you will be safe here"; "a safe place"; "a safe bet" |
| `sagging` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | hanging down (as from exhaustion or weakness) |
| `salty` | Explicit hotel-context gloss selection. | one of the four basic taste sensations; like the taste of sea water |
| `sanitary` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | free from filth and pathogens; "sanitary conditions for preparing food"; "a sanitary washroom" |
| `sanitized` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | made sanitary |
| `satisfactory` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | giving satisfaction; "satisfactory living conditions"; "his grades were satisfactory" |
| `satisfied` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | filled with satisfaction; "a satisfied customer" |
| `satisfying` | Explicit hotel-context gloss selection. | providing freedom from worry |
| `savory` | Explicit hotel-context gloss selection. | pleasing to the sense of taste |
| `savoury` | Explicit hotel-context gloss selection. | pleasing to the sense of taste |
| `scrumptious` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | extremely pleasing to the sense of taste |
| `secure` | Explicit hotel-context gloss selection. | free from danger or risk; "secure from harm"; "his fortune was secure"; "made a secure place for himself in his field" |
| `serene` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | not agitated; without losing self-possession; "spoke in a calm voice"; "remained calm throughout the uproar"; "he remained serene in the midst of turbulence"; "a serene expression on her face"; "she became more tranquil"; "tranquil life in the country" |
| `serviceable` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | ready for service or able to give long service; "serviceable equipment"; "heavy serviceable fabrics" |
| `shabby` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | showing signs of wear and tear; "a ratty old overcoat"; "shabby furniture"; "an old house with dirty windows and tatty curtains" |
| `silent` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | marked by absence of sound; "a silent house"; "soundless footsteps on the grass"; "the night was still" |
| `sleepless` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | experiencing or accompanied by sleeplessness; "insomniac old people"; "insomniac nights"; "lay sleepless all night"; "twenty watchful, weary, tedious nights"- Shakespeare |
| `slippery` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | causing or tending to cause things to slip or slide; "slippery sidewalks"; "a slippery bar of soap"; "the streets are still slippy from the rain" |
| `slow` | Previously configured controlled sense | not moving quickly; taking a comparatively long time; "a slow walker"; "the slow lane of traffic"; "her steps were slow"; "he was slow in reacting to the news"; "slow but steady growth" |
| `sluggish` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | moving slowly; "a sluggish stream" |
| `small` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | limited or below average in number or quantity or magnitude or extent; "a little dining room"; "a little house"; "a small car"; "a little (or small) group" |
| `smelly` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | offensively malodorous; "a foul odor"; "the kitchen smelled really funky" |
| `sociable` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | inclined to or conducive to companionship with others; "a sociable occasion"; "enjoyed a sociable chat"; "a sociable conversation"; "Americans are sociable and gregarious" |
| `soft` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | yielding readily to pressure or weight |
| `soggy` | Explicit hotel-context gloss selection. | having the consistency of dough because of insufficient leavening or improper cooking; "the cake fell; it's a doughy mess" |
| `soiled` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | soiled or likely to soil with dirt or grime; "dirty unswept sidewalks"; "a child in dirty overalls"; "dirty slums"; "piles of dirty dishes"; "put his dirty feet on the clean sheet"; "wore an unclean shirt"; "mining is a dirty job"; "Cinderella did the dirty work while her sisters preened themselves" |
| `soundproof` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | impervious to, or not penetrable by, sound; "a soundproof room" |
| `sour` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | smelling of fermentation or staleness |
| `spacious` | Previously configured controlled sense | (of buildings and rooms) having ample space; "a roomy but sparsely furnished apartment"; "a spacious ballroom" |
| `speedy` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | characterized by speed; moving with or capable of moving with high speed; "a rapid movement"; "a speedy car"; "a speedy errand boy" |
| `spicy` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | having an agreeably pungent taste |
| `splendid` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | having great beauty and splendor; "a glorious spring morning"; "a glorious sunset"; "splendid costumes"; "a kind of splendiferous native simplicity" |
| `spotless` | Previously configured controlled sense | completely neat and clean; "the apartment was immaculate"; "in her immaculate white uniform"; "a spick-and-span kitchen"; "their spic red-visored caps" |
| `spotty` | Explicit hotel-context gloss selection. | lacking consistency; "the golfer hit the ball well but his putting was spotty" |
| `stable` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | resistant to change of position or condition; "a stable ladder"; "a stable peace"; "a stable relationship"; "stable prices" |
| `stained` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | marked or dyed or discolored with foreign matter; "a badly stained tablecloth"; "tear-stained cheeks" |
| `stale` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | lacking freshness, palatability, or showing deterioration from age; "stale bread"; "the beer was stale" |
| `sterile` | Explicit hotel-context gloss selection. | free of or using methods to keep free of pathological microorganisms; "a sterile operating area"; "aseptic surgical instruments"; "aseptic surgical techniques" |
| `sticky` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | having the sticky properties of an adhesive |
| `stiff` | Explicit hotel-context gloss selection. | incapable of or resistant to bending; "a rigid strip of metal"; "a table made of rigid plastic"; "a palace guardsman stiff as a poker"; "stiff hair"; "a stiff neck" |
| `stinky` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | having an unpleasant smell |
| `strong` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | having strength or power greater than average or expected; "a strong radio signal"; "strong medicine"; "a strong man" |
| `stuffy` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | lacking fresh air; "a dusty airless attic"; "the dreadfully close atmosphere"; "hot and stuffy and the air was blue with smoke" |
| `stunning` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | commanding attention; "an arresting drawing of people turning into animals"; "a sensational concert--one never to be forgotten"; "a stunning performance" |
| `sturdy` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | having rugged physical strength; inured to fatigue or hardships; "hardy explorers of northern Canada"; "proud of her tall stalwart son"; "stout seamen"; "sturdy young athletes" |
| `stylish` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | having elegance or taste or refinement in manners or dress; "a little less posh but every bit as stylish as Lord Peter Wimsey"; "the stylish resort of Gstadd" |
| `substandard` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | falling short of some prescribed norm; "substandard housing" |
| `succulent` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | full of juice; "lush fruits"; "succulent roast beef"; "succulent plants with thick fleshy leaves" |
| `superb` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | of surpassing excellence; "a brilliant performance"; "a superb actor" |
| `superior` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | of high or superior quality or performance; "superior wisdom derived from experience"; "superior math students" |
| `supportive` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | furnishing support or assistance; "a supportive family network"; "his family was supportive of his attempts to be a writer" |
| `sweet` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | having or denoting the characteristic taste of sugar |
| `sympathetic` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | of or relating to the sympathetic nervous system; "sympathetic neurons"; "sympathetic stimulation" |
| `tainted` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | touched by rot or decay; "tainted bacon"; "`corrupt' is archaic" |
| `tardy` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | after the expected or usual time; delayed; "a belated birthday card"; "I'm late for the plane"; "the train is late"; "tardy children are sent to the principal"; "always tardy in making dental appointments" |
| `tasteless` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | lacking flavor |
| `tasty` | Previously configured controlled sense | pleasing to the sense of taste; "a tasty morsel" |
| `tender` | Explicit hotel-context gloss selection. | easy to cut or chew; "tender beef" |
| `terrible` | Previously configured controlled sense | exceptionally bad or displeasing; "atrocious taste"; "abominable workmanship"; "an awful voice"; "dreadful manners"; "a painful performance"; "terrible handwriting"; "an unspeakable odor came sweeping into the room" |
| `terrific` | Explicit hotel-context gloss selection. | extraordinarily good or great ; used especially as intensifiers; "a fantastic trip to the Orient"; "the film was fantastic!"; "a howling success"; "a marvelous collection of rare books"; "had a rattling conversation about politics"; "a tremendous achievement" |
| `thoughtful` | Explicit hotel-context gloss selection. | considerate of the feelings or well-being of others |
| `thoughtless` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | showing lack of careful thought; "the debate turned into thoughtless bickering" |
| `tidy` | Previously configured controlled sense | marked by order and cleanliness in appearance or habits; "a tidy person"; "a tidy house"; "a tidy mind" |
| `timely` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | before a time limit expires; "the timely filing of his income tax return" |
| `tiny` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | very small; "diminutive in stature"; "a lilliputian chest of drawers"; "her petite figure"; "tiny feet"; "the flyspeck nation of Bahrain moved toward democracy" |
| `tranquil` | Explicit hotel-context gloss selection. | not agitated; without losing self-possession; "spoke in a calm voice"; "remained calm throughout the uproar"; "he remained serene in the midst of turbulence"; "a serene expression on her face"; "she became more tranquil"; "tranquil life in the country" |
| `trustworthy` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | worthy of trust or belief; "a trustworthy report"; "an experienced and trustworthy traveling companion" |
| `ugly` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | displeasing to the senses; "an ugly face"; "ugly furniture" |
| `unacceptable` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | not adequate to give satisfaction; "the coach told his players that defeat was unacceptable" |
| `unappetizing` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | not appetizing in appearance, aroma, or taste |
| `unavailable` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | not available or accessible or at hand; "fresh milk was unavailable during the emergency"; "his secretary said he was unavailable for comment" |
| `unbearable` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | incapable of being put up with; "an intolerable degree of sentimentality" |
| `unclean` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | soiled or likely to soil with dirt or grime; "dirty unswept sidewalks"; "a child in dirty overalls"; "dirty slums"; "piles of dirty dishes"; "put his dirty feet on the clean sheet"; "wore an unclean shirt"; "mining is a dirty job"; "Cinderella did the dirty work while her sisters preened themselves" |
| `uncomfortable` | Previously configured controlled sense | providing or experiencing physical discomfort; "an uncomfortable chair"; "an uncomfortable day in the hot sun" |
| `uncooperative` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | unwilling to cooperate; "an uncooperative witness" |
| `uncrowded` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | having or allowing sufficient room; "an uncrowded train"; "an uncrowded view" |
| `underdone` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | insufficiently cooked |
| `unfriendly` | Previously configured controlled sense | not disposed to friendship or friendliness; "an unfriendly coldness of manner"; "an unfriendly action to take" |
| `unhappy` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | experiencing or marked by or causing sadness or sorrow or discontent; "unhappy over her departure"; "unhappy with her raise"; "after the argument they lapsed into an unhappy silence"; "had an unhappy time at school"; "the unhappy (or sad) news"; "he looks so sad" |
| `unhelpful` | Previously configured controlled sense | providing no assistance |
| `unhygienic` | Previously configured controlled sense | unclean and constituting a likely cause of disease; "pathetic dogs kept in small unhygienic cages" |
| `unimpressive` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | not capable of impressing |
| `uninviting` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | neither attractive nor tempting |
| `unkempt` | Explicit hotel-context gloss selection. | not properly maintained or cared for; "an unkempt garden"; "native vistas and unkempt rambling paths"; "an ukempt appearance" |
| `unkind` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | lacking kindness; "a thoughtless and unkind remark"; "the unkindest cut of all" |
| `unpalatable` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | not pleasant or acceptable to the taste or mind; "an unpalatable meal"; "unpalatable truths"; "unpalatable behavior" |
| `unpleasant` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | disagreeable to the senses, to the mind, or feelings ; "an unpleasant personality"; "unpleasant repercussions"; "unpleasant odors" |
| `unprofessional` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | not characteristic of or befitting a profession or one engaged in a profession; "described in unprofessional language so that high school students could understand it"; "was censured for unprofessional conduct"; "unprofessional repairs" |
| `unreliable` | Previously configured controlled sense | not worthy of reliance or trust; "in the early 1950s computers were large and expensive and unreliable"; "an undependable assistant" |
| `unresponsive` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | not responding to some influence or stimulus |
| `unsafe` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | lacking in security or safety; "his fortune was increasingly insecure"; "an insecure future" |
| `unsanitary` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | not sanitary or healthful; "unsanitary open sewers"; "grim and unsanitary conditions" |
| `unsatisfactory` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | not giving satisfaction; "shops should take back unsatisfactory goods"; "her performance proved to be unsatisfactory"; "life is becoming increasingly unsatifactory"; "our discussion was very unsatisfactory" |
| `unserviceable` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | not ready for service; "unserviceable equipment may be replaced" |
| `unsound` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | not in good condition; damaged or decayed; "an unsound foundation" |
| `unstable` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | lacking stability or fixity or firmness; "unstable political conditions"; "the tower proved to be unstable in the high wind"; "an unstable world economy" |
| `unsympathetic` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | not sympathetic or disposed toward; "unsympathetic officialdom"; "people unsympathetic to the revolution"; "his dignity made him seem aloof and unsympathetic" |
| `unusable` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | not capable of being used |
| `unventilated` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | not ventilated; "stuffy unventilated rooms" |
| `unwashed` | Explicit hotel-context gloss selection. | not cleaned with or as if with soap and water; "a sink full of unwashed dishes" |
| `usable` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | capable of being put to use; "usable byproducts" |
| `ventilated` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | exposed to air; "a well ventilated room" |
| `warm` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | having or producing a comfortable and agreeable degree of heat or imparting or maintaining heat; "a warm body"; "a warm room"; "a warm climate"; "a warm coat" |
| `weak` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | wanting in physical strength; "a weak pillar" |
| `welcoming` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | very cordial; "a welcoming smile" |
| `well-lighted` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | provided with artificial light; "illuminated advertising"; "looked up at the lighted windows"; "a brightly lit room"; "a well-lighted stairwell" |
| `wet` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | covered or soaked with a liquid such as water; "a wet bathing suit"; "wet sidewalks"; "wet weather" |
| `wonderful` | Previously configured controlled sense | extraordinarily good or great ; used especially as intensifiers; "a fantastic trip to the Orient"; "the film was fantastic!"; "a howling success"; "a marvelous collection of rare books"; "had a rattling conversation about politics"; "a tremendous achievement" |
| `working` | Previously configured controlled sense | (of e.g. a machine) performing or capable of performing; "in running (or working) order"; "a functional set of brakes" |
| `worn` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | affected by wear; damaged by long use; "worn threads on the screw"; "a worn suit"; "the worn pockets on the jacket" |
| `worn-out` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | used until no longer useful; "battered trumpets and raddled radios"; "worn-out shoes with flapping soles" |
| `yummy` | First-ranked WordNet adjective sense; original SentiWordNet score retained. | extremely pleasing to the sense of taste |

## 9 Every opinion alias and compatibility guard

Aliases are explicit phrase normalization, not unconstrained morphology. Their source text and normalization rule are kept. FUNCTION_VERB aliases additionally carry base/finite form. A listed alias still needs a compatible target and valid grammar. Negation is not absorbed into aliases.

| Recognized alias | Canonical opinion | Token class | Verb form | Alias categories | Alias aspect guard |
| --- | --- | --- | --- | --- | --- |
| `brand new` | `new` | OPINION | Not applicable | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard |
| `busted` | `broken` | OPINION | Not applicable | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard |
| `comfy` | `comfortable` | OPINION | Not applicable | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard |
| `crunchy` | `crisp` | OPINION | Not applicable | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard |
| `freezing` | `chilly` | OPINION | Not applicable | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard |
| `function` | `functioning` | FUNCTION_VERB | base | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard |
| `functions` | `functioning` | FUNCTION_VERB | finite | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard |
| `leaking` | `leaky` | OPINION | Not applicable | Room, Staff, Service, Food, Cleanliness, Facilities | A4 |
| `mouthwatering` | `mouth-watering` | OPINION | Not applicable | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard |
| `out of order` | `broken` | OPINION | Not applicable | Facilities | No explicit aspect guard |
| `overcooked` | `overdone` | OPINION | Not applicable | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard |
| `overcrowded` | `crowded` | OPINION | Not applicable | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard |
| `poorly maintained` | `dilapidated` | OPINION | Not applicable | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard |
| `poorly-maintained` | `dilapidated` | OPINION | Not applicable | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard |
| `saggy` | `sagging` | OPINION | Not applicable | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard |
| `spotlessly clean` | `spotless` | OPINION | Not applicable | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard |
| `squeaky clean` | `spotless` | OPINION | Not applicable | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard |
| `stopped cooling` | `malfunctioning` | OPINION | Not applicable | Room, Staff, Service, Food, Cleanliness, Facilities | A1 |
| `stopped working` | `malfunctioning` | OPINION | Not applicable | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard |
| `stops cooling` | `malfunctioning` | OPINION | Not applicable | Room, Staff, Service, Food, Cleanliness, Facilities | A1 |
| `stops working` | `malfunctioning` | OPINION | Not applicable | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard |
| `undercooked` | `underdone` | OPINION | Not applicable | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard |
| `watered down` | `diluted` | OPINION | Not applicable | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard |
| `watered-down` | `diluted` | OPINION | Not applicable | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard |
| `well kept` | `maintained` | OPINION | Not applicable | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard |
| `well lit` | `well-lighted` | OPINION | Not applicable | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard |
| `well maintained` | `maintained` | OPINION | Not applicable | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard |
| `well-kept` | `maintained` | OPINION | Not applicable | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard |
| `well-lit` | `well-lighted` | OPINION | Not applicable | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard |
| `well-maintained` | `maintained` | OPINION | Not applicable | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard |
| `work` | `working` | FUNCTION_VERB | base | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard |
| `works` | `working` | FUNCTION_VERB | finite | Room, Staff, Service, Food, Cleanliness, Facilities | No explicit aspect guard |

### All exact allowed aspect sets

**A1 (12 phrases):** `a/c`, `ac`, `ac unit`, `air con`, `air conditioner`, `air conditioner unit`, `air conditioning`, `air conditioning unit`, `air-conditioner`, `air-conditioner unit`, `air-conditioning`, `aircon`.

**A2 (83 phrases):** `a/c`, `ac`, `ac unit`, `air con`, `air conditioner`, `air conditioner unit`, `air conditioning`, `air conditioning unit`, `air-conditioner`, `air-conditioner unit`, `air-conditioning`, `aircon`, `bathroom ceiling`, `bedside lamp`, `bedside lamps`, `ceiling fan`, `central heating`, `drain`, `drains`, `drinking water`, `elevator`, `elevators`, `exhaust fan`, `fan`, `fans`, `faucet`, `faucets`, `fridge`, `fridges`, `heater`, `heaters`, `heating`, `hot water`, `internet`, `internet access`, `internet connection`, `lamp`, `lamps`, `lift`, `lifts`, `light`, `lighting`, `lights`, `mini bar`, `mini fridge`, `mini-fridge`, `minibar`, `minifridge`, `plumbing`, `pool`, `refrigerator`, `refrigerators`, `remote control`, `shower`, `shower head`, `shower heads`, `showerhead`, `showers`, `sink`, `sinks`, `tap`, `taps`, `television`, `television set`, `television sets`, `televisions`, `toilet`, `toilets`, `tv`, `tv remote`, `ventilation`, `water`, `water pressure`, `water supply`, `wi fi`, `wi-fi`, `wi-fi connection`, `wi-fi network`, `wi-fi signal`, `wifi`, `wifi connection`, `wifi signal`, `wireless internet`.

**A3 (82 phrases):** `a/c`, `ac`, `ac unit`, `air con`, `air conditioner`, `air conditioner unit`, `air conditioning`, `air conditioning unit`, `air-conditioner`, `air-conditioner unit`, `air-conditioning`, `aircon`, `bathroom ceiling`, `bedside lamp`, `bedside lamps`, `ceiling fan`, `central heating`, `drain`, `drains`, `drinking water`, `elevator`, `elevators`, `exhaust fan`, `fan`, `fans`, `faucet`, `faucets`, `fridge`, `fridges`, `heater`, `heaters`, `heating`, `hot water`, `internet`, `internet access`, `internet connection`, `lamp`, `lamps`, `lift`, `lifts`, `light`, `lighting`, `lights`, `mini bar`, `mini fridge`, `mini-fridge`, `minibar`, `minifridge`, `plumbing`, `refrigerator`, `refrigerators`, `remote control`, `shower`, `shower head`, `shower heads`, `showerhead`, `showers`, `sink`, `sinks`, `tap`, `taps`, `television`, `television set`, `television sets`, `televisions`, `toilet`, `toilets`, `tv`, `tv remote`, `ventilation`, `water`, `water pressure`, `water supply`, `wi fi`, `wi-fi`, `wi-fi connection`, `wi-fi network`, `wi-fi signal`, `wifi`, `wifi connection`, `wifi signal`, `wireless internet`.

**A4 (31 phrases):** `bathroom ceiling`, `drain`, `drains`, `drinking water`, `faucet`, `faucets`, `fridge`, `fridges`, `hot water`, `mini bar`, `mini fridge`, `mini-fridge`, `minibar`, `minifridge`, `plumbing`, `refrigerator`, `refrigerators`, `shower`, `shower head`, `shower heads`, `showerhead`, `showers`, `sink`, `sinks`, `tap`, `taps`, `toilet`, `toilets`, `water`, `water pressure`, `water supply`.

### Per-opinion allowed adverbs

| Canonical opinion | Allowed adverbs |
| --- | --- |
| functioning | `properly`, `well` |
| working | `properly`, `well` |

## 10 Every domain calibration and contextual sense

Stored default-sense category adjustments are listed individually below. They apply only to compatible semantic records. New hotel-attribute preference rules orient the magnitude of P-N to a documented preference; if that lexical score is zero, the convention uses magnitude 0.25. Earlier specific calibrations retain their existing scores. Firm bedding is explicitly neutral because firmness alone has no universal hotel preference.

Category-specific senses are selected before evaluation. If the selected contextual sense has no calibration, its own P-N is used and a default-sense calibration is not inherited. A contextual calibration takes precedence over the default category calibration. The exact reasons are included for the professor to inspect; the source scores remain unchanged.

**Default-sense category adjustments: 100 across 73 terms.** Contextual rules below are additional overrides and can supersede entries in this table.

| Opinion | Category | Domain score D | Rule ID | Reason |
| --- | --- | --- | --- | --- |
| abrupt | Service | -0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| abrupt | Staff | -0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| airy | Room | 0.125 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| arrogant | Service | -0.125 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| arrogant | Staff | -0.125 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| blocked | Facilities | -0.125 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| calm | Room | 0.375 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| clogged | Facilities | -0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| comfortable | Room | 0.5 | physical_room_comfort | The selected physical-comfort sense has a negative source score despite its physical-well-being gloss. The hotel-domain convention treats explicit room/bed comfort as positive; original P/N are retained. |
| connected | Facilities | 0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| cooperative | Service | 0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| cooperative | Staff | 0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| cramped | Room | -0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| crispy | Food | 0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| crowded | Facilities | -0.125 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| crowded | Room | -0.125 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| damp | Room | -0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| dark | Room | -0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| deafening | Room | -0.125 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| defective | Facilities | -0.5 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| discourteous | Service | -0.375 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| discourteous | Staff | -0.375 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| disrespectful | Service | -0.125 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| disrespectful | Staff | -0.125 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| efficient | Facilities | 0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| efficient | Service | 0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| efficient | Staff | 0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| fast | Facilities | 0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| fast | Service | 0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| faulty | Facilities | -0.5 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| firm | Room | 0.0 | firmness_description | Firmness alone is a bedding property, not a universal positive/negative preference. Source P/N are retained. |
| flavorful | Food | 0.5 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| flavorsome | Food | 0.5 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| flavourful | Food | 0.5 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| flickering | Facilities | -0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| fresh | Cleanliness | 0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| fresh | Food | 0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| fresh | Room | 0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| functioning | Facilities | 0.25 | functioning_equipment | The functional-equipment sense has zero lexical sentiment. Explicitly functioning hotel equipment is a positive functionality state; negate this state once for nonfunctioning equipment. |
| hard | Room | -0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| hot | Room | -0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| impolite | Service | -0.375 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| impolite | Staff | -0.375 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| inaccessible | Facilities | -0.375 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| indifferent | Service | -0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| indifferent | Staff | -0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| intermittent | Facilities | -0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| juicy | Food | 0.375 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| lazy | Service | -0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| lazy | Staff | -0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| leaky | Facilities | -0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| leaky | Room | -0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| loud | Room | -0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| narrow | Room | -0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| noisy | Facilities | -0.5 | hotel_noise_complaint | The loud-sound sense has equal P and N. Explicitly noisy rooms/facilities are treated as hotel-domain complaints. |
| noisy | Room | -0.5 | hotel_noise_complaint | The loud-sound sense has equal P and N. Explicitly noisy rooms/facilities are treated as hotel-domain complaints. |
| obstructed | Facilities | -0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| overdone | Food | -0.125 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| overheated | Room | -0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| professional | Service | 0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| professional | Staff | 0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| prompt | Service | 0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| prompt | Staff | 0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| punctual | Service | 0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| punctual | Staff | 0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| quick | Facilities | 0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| quick | Service | 0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| quick | Staff | 0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| roomy | Room | 0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| rowdy | Room | -0.125 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| rushed | Service | -0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| safe | Facilities | 0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| safe | Room | 0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| serene | Room | 0.375 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| shabby | Room | -0.125 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| silent | Room | 0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| slippery | Facilities | -0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| slow | Facilities | -0.5 | slow_service_facilities | The physical-speed sense has zero lexical sentiment. Slow service or facilities are an explicit hotel-domain complaint rule. |
| slow | Service | -0.5 | slow_service_facilities | The physical-speed sense has zero lexical sentiment. Slow service or facilities are an explicit hotel-domain complaint rule. |
| sluggish | Service | -0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| soft | Room | 0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| soundproof | Facilities | 0.75 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| soundproof | Room | 0.75 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| spacious | Room | 0.25 | room_space_preference | The room/building-space sense has zero lexical sentiment. Explicit room spaciousness is a positive hotel-domain preference. |
| spotty | Facilities | -0.375 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| stable | Facilities | 0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| stale | Food | -0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| stale | Room | -0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| succulent | Food | 0.375 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| tender | Food | 0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| timely | Service | 0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| tiny | Room | -0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| tranquil | Room | 0.375 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| underdone | Food | -0.125 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| unkind | Service | -0.125 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| unkind | Staff | -0.125 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| unsanitary | Cleanliness | -0.375 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| usable | Facilities | 0.25 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| welcoming | Service | 0.125 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |
| welcoming | Staff | 0.125 | hotel_attribute_preference | Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. This is a domain rule, not a changed SentiWordNet score or learned confidence. |

### All category-specific sense overrides

| Opinion | Category | Sense | Context issue | P | N | L | Domain D | Rule / reason | Source gloss |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fresh | Cleanliness | a:01906320 | Hygiene | 0.5 | 0.25 | 0.25 | Use this sense's L | No contextual calibration;  | free from impurities; "clean water"; "fresh air" |
| fresh | Facilities | a:01906320 | Ventilation | 0.5 | 0.25 | 0.25 | Use this sense's L | No contextual calibration;  | free from impurities; "clean water"; "fresh air" |
| fresh | Room | a:00418198 | Cleanliness | 0.0 | 0.75 | -0.75 | 0.75 | fresh_linen_preference; Unused/unsoiled linen is a positive hotel preference; the selected source score is negative. P/N are retained. | not yet used or soiled; "a fresh shirt"; "a fresh sheet of paper"; "an unused envelope" |

For example, Food / fresh has source P=0.375, N=0.625 and L=-0.25, with a separate positive freshness preference. Room / fresh selects the unused/unsoiled linen sense and its own rule. Facilities/Cleanliness fresh selects a purity sense with its own lexical score. These are static category conventions, not general word-sense disambiguation or proof that every occurrence of “fresh room” means fresh linen.

## 11 IR traces and diagnostics

An opinion becomes an AspectResult with scoring evidence. `to_ir()` removes the evidence field from the compact IR but the full trace keeps it separately. A review with several opinions has several aspect-level records; CSV review output still joins them into one row for that submitted review.

**Lexical token fields:** `kind`, `value`, `text`, `start`, `end`, `normalization_rule`, `verb_form`.

**Syntax clause fields:** `subject`, `opinion`, `negation`, `intensifier`, `connector`, `start`, `end`, `copula`, `auxiliary`, `adverb`, `emphasis`, `opinion_start`, `opinion_end`, `form`, `context`.

**Semantic record fields:** `category`, `issue`, `aspect_term`, `opinion_term`, `opinion_expression`, `negated`, `intensifier`, `intensity_multiplier`, `aspect_inherited`, `clause_index`, `start`, `end`, `normalization_rule`, `adverb`, `emphasis`, `opinion_start`, `opinion_end`, `syntax_form`.

**Scoring evidence fields:** `synset`, `gloss`, `positive_score`, `negative_score`, `objective_score`, `lexical_score`, `domain_score`, `calibration_reason`, `intensity_multiplier`, `negation_multiplier`, `unclipped_score`, `final_score`, `normalization_rule`, `domain_rule_id`, `sense_selection`.

**Aspect result fields:** `review_id`, `category`, `issue`, `aspect_term`, `opinion_term`, `opinion_expression`, `polarity`, `score`, `start`, `end`, `evidence`.

**Diagnostic fields:** `code`, `message`, `start`, `end`, `stage`.

**Review result fields:** `review_id`, `review_text`, `status`, `overall`, `records`, `diagnostics`, `tokens`, `ast`, `semantics`.

The five UI trace tabs display tokens, syntax AST, semantic records, scoring evidence and IR. Context belongs to the syntax clause; an opinion's expression/span excludes the aspect noun and retained time context where appropriate. Every diagnostic keeps a code, message, stage and affected source span.

### All current review and row diagnostic codes

| Code | Stage | Trigger |
| --- | --- | --- |
| EMPTY_INPUT | Single-review input | Whitespace-only/empty single text; unsupported/Unanalyzed. |
| COLUMN_COUNT | CSV row validation | Row width differs from the header width. |
| EMPTY_REVIEW | CSV row validation | Missing or blank review cell. |
| REVIEW_TOO_LONG | CSV row validation | More than 10,000 characters. |
| EMPTY_CLAUSE | Syntax | A separator occurs where a clause was expected. |
| UNSUPPORTED_CLAUSE | Syntax | Required token/form was absent, incompatible verb form, repeated modifiers, unknown tail, etc.; message gives the exact reason. |
| MISSING_CLAUSE | Syntax | A final comma/connector requires another clause. |
| MISSING_ASPECT | Semantic | An opinion lacks an explicit or valid inherited aspect. |
| INCOMPATIBLE_OPINION | Semantic | Canonical/alias category or aspect guard fails. |
| UNSUPPORTED_ADVERB | Semantic | Adverb is not allowed for this opinion. |
| INVALID_EMPHASIS | Semantic | At all without explicit negation. |

`processing_error` retains an unexpected exception's type/message, rather than using an unsupported-language diagnostic code. Whole-file CSVInputError and shared ResourceError are separate failures, not extra categories or sentiment labels.

### Batch outputs and UI lifecycle

- Analyze every valid CSV row with the same public single-review compiler. Unsupported and partial results are ordinary retained outcomes; valid neighbors continue after a per-row unexpected exception.
- Keep one successful batch in memory. A later successful upload replaces it; clearing/restarting discards it. A failed upload preserves the previous batch. Concurrent uploads receive a busy response; there is no queue or database.
- Show one results-table row per input; drill down to individual opinion records and traces. Search, pagination and evidence filters do not discard stored outcomes.
- The dashboard calculates complete-only and complete-plus-partial scopes independently. It shows category distributions, overall labels, coverage, issue complaints, mean indices, denominators and evidence IDs.
- Findings use deterministic report templates over counts. Below 80% complete/submitted, primary coverage is flagged as limited; fewer than five group mentions is low support. These are explicit reporting conventions.
- User-triggered downloads provide one review row per input, separate aspect rows, summary tables and CSV/text report evidence. Formula-leading CSV cells are escaped for spreadsheet safety. Uploads require no category/score/result columns.
- Source/rule hashes and run metadata support reproducibility, but uploads without independently annotated labels cannot yield accuracy, precision, recall or F1.

## 12 Verified examples and limitations

The following outputs were generated through the real pipeline when this reference was built. They are demonstrations of the contract, not independent gold-label accuracy evidence.

| Review | Status / overall | Recognized results | Diagnostic codes |
| --- | --- | --- | --- |
| The room was clean and spacious. | complete / Positive | Room / Cleanliness: clean → Positive (+0.1250); Room / Space: spacious → Positive (+0.2500) | None |
| The room was dirty. | complete / Negative | Room / Cleanliness: dirty → Negative (-0.7500) | None |
| The room was clean but the location was convenient. | partial / Positive | Room / Cleanliness: clean → Positive (+0.1250) | UNSUPPORTED_CLAUSE |
| The location was convenient. | unsupported / Unanalyzed | None | UNSUPPORTED_CLAUSE |
| The staff were working. | unsupported / Unanalyzed | None | INCOMPATIBLE_OPINION |
| The room was not not clean. | unsupported / Unanalyzed | None | UNSUPPORTED_CLAUSE |
| The room and bathroom were clean and spacious. | complete / Positive | Room / Cleanliness: clean → Positive (+0.1250); Room / Space: spacious → Positive (+0.2500); Room / Cleanliness: clean → Positive (+0.1250); Room / Space: spacious → Positive (+0.2500) | None |
| Clean and quiet room. | complete / Positive | Room / Cleanliness: Clean → Positive (+0.1250); Room / Noise: quiet → Positive (+0.2500) | None |
| I found the room very clean when we arrived. | complete / Positive | Room / Cleanliness: very clean → Positive (+0.1562) | None |
| I was pleased with the service. | complete / Positive | Service / Quality: pleased → Positive (+0.6250) | None |
| The room had a comfortable bed. | complete / Positive | Room / Comfort: comfortable → Positive (+0.5000) | None |
| The WiFi does not work. | complete / Negative | Facilities / WiFi: not work → Negative (-0.2500) | None |
| The air conditioning stopped cooling during the night. | complete / Negative | Facilities / Air Conditioning: stopped cooling → Negative (-0.7500) | None |
| The room was not clean and quiet. | complete / Mixed | Room / Cleanliness: not clean → Negative (-0.1250); Room / Noise: quiet → Positive (+0.2500) | None |
| The room was clean enough. | complete / Positive | Room / Cleanliness: clean enough → Positive (+0.1250) | None |
| The room was clean and | partial / Positive | Room / Cleanliness: clean → Positive (+0.1250) | MISSING_CLAUSE |
| The staff arranged a taxi for us before sunrise. | unsupported / Unanalyzed | None | UNSUPPORTED_CLAUSE |
| There was water leaking from the bathroom ceiling. | unsupported / Unanalyzed | None | UNSUPPORTED_CLAUSE |

### Current limits to explain honestly

Recognized vocabulary is extensive but the grammar remains controlled. No unrestricted English, implicit complaints/aspects, general pronoun resolution, sarcasm, arbitrary verbs/modals, open-ended adjective inflection, multilingual analysis, or complex negation inference is implemented. Unsupported clauses remain visible. Factual “staff arranged a taxi” is not automatically positive; “waited forty minutes” is not automatically negative. The registered word leaking does not make every leaking construction supported. Agreement and plausible world knowledge are not fully validated. Negation and intensity use explicit arithmetic conventions, including “not bad”; they are not pragmatic inference.

## 13 Code locations and running the project

| Code location | Function / class | Logic |
| --- | --- | --- |
| [hotel_compiler/pipeline.py:15](../hotel_compiler/pipeline.py#L15) | analyze_review | Single-review orchestration, limits, status and overall sentiment. |
| [hotel_compiler/models.py:126](../hotel_compiler/models.py#L126) | review_score | Mean of final opinion scores within one review; computed property. |
| [hotel_compiler/models.py:133](../hotel_compiler/models.py#L133) | review_score_scope | Complete, recognized-only or unavailable score scope. |
| [hotel_compiler/csv_input.py:96](../hotel_compiler/csv_input.py#L96) | parse_review_csv | UTF-8 CSV/file/row validation and duplicate flags. |
| [hotel_compiler/lexer.py:18](../hotel_compiler/lexer.py#L18) | tokenize | Regex scanning, matching, normalization, tokenization and safe overlap. |
| [hotel_compiler/parser.py:15](../hotel_compiler/parser.py#L15) | ReviewParser | Grammar, AST forms, lookahead, context and recovery. |
| [hotel_compiler/semantics.py:7](../hotel_compiler/semantics.py#L7) | analyze_semantics | Attachment, category/issues, inheritance and guards. |
| [hotel_compiler/sentiwordnet.py:55](../hotel_compiler/sentiwordnet.py#L55) | evaluate | Sense, original P/N, calibration, intensity, negation and final score. |
| [hotel_compiler/sentiwordnet.py:26](../hotel_compiler/sentiwordnet.py#L26) | load_synsets | Checksum and term/sense consistency checks. |
| [hotel_compiler/vocabulary.py:48](../hotel_compiler/vocabulary.py#L48) | load_vocabulary | Load and validate the runtime vocabulary. |
| [hotel_compiler/batch.py:32](../hotel_compiler/batch.py#L32) | analyze_batch | Independent row execution, invalid input, unexpected error isolation. |
| [hotel_compiler/batch_models.py:35](../hotel_compiler/batch_models.py#L35) | BatchResult | Counts, coverage denominators and retained row identity. |
| [hotel_compiler/aggregation.py:31](../hotel_compiler/aggregation.py#L31) | _group | Mean of review means and category/issue counts. |
| [hotel_compiler/aggregation.py:94](../hotel_compiler/aggregation.py#L94) | aggregate_batch | Primary and secondary scope selection. |
| [hotel_compiler/reporting.py:64](../hotel_compiler/reporting.py#L64) | build_report | Deterministic findings, support/coverage notes and evidence. |
| [hotel_compiler/paper_tables.py:21](../hotel_compiler/paper_tables.py#L21) | paper_tables | CSV/text report evidence and metadata. |

### Configuration and presentation files

| Resource / UI file | Purpose |
| --- | --- |
| [domain.json](../hotel_compiler/resources/domain.json) | All exact vocabulary/rules listed in this file. |
| [opinion_senses.csv](../hotel_compiler/resources/opinion_senses.csv) | Source/domain sense audit, including contextual senses. |
| [hotel_vocabulary_catalog.json](../scripts/hotel_vocabulary_catalog.json) | Curated build-time word families, overrides and preferences. |
| [expand_hotel_vocabulary.py](../scripts/expand_hotel_vocabulary.py) | Build the expanded runtime resources from the pinned corpus. |
| [prepare_sentiwordnet.py](../scripts/prepare_sentiwordnet.py) | Prepare exact source rows, checksum/provenance and license. |
| [models.py](../hotel_compiler/models.py) | Phase/result/trace record definitions. |
| [web.py](../hotel_compiler/web.py) | Local HTTP adapter and resource/input checks. |
| [web_batch.py](../hotel_compiler/web_batch.py) | One in-memory batch and synchronous upload guard. |
| [app.js](../hotel_compiler/web_assets/app.js) | Single-review results and trace rendering; four-decimal display. |
| [dashboard.js](../hotel_compiler/web_assets/dashboard.js) | Coverage cards, category Mean index, charts and per-review table. |
| [tests](../tests/) | Regression checks, including simulated processing errors and equal-review means. |

### Run from the project directory

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\serve.ps1
```

Open **http://127.0.0.1:8000/**. Keep the terminal open; Ctrl+C stops the server. Single review shows opinion rows and five trace tabs. CSV & dashboard accepts `examples/hotel_reviews_100.csv`; select `review` as text column and `sr.no` as ID column. Click any review row for its result/diagnostics/traces. Refresh clears the displayed browser view; restarting clears the retained server batch. No external document or category labels need uploading.

With installed Python 3.10 or newer, `python -m hotel_compiler.web` also starts the server. The compiler has no third-party runtime dependencies. Diagram-authoring helpers are separate development tools and may need their own packages.

```powershell
python -m hotel_compiler "The room was not clean, but the staff were very helpful." --trace
python -m unittest discover -s tests -v
```

To update this reference after changing vocabulary/grammar, regenerate the inventory and recheck the explanatory rules against the source code. This file is a dated snapshot; it is not an automatic runtime grammar generator.

### Resource provenance

| Item | Value |
| --- | --- |
| Resource | SentiWordNet 3.0.0 |
| Selected source rows | 315 |
| Source archive SHA-256 | b66876a17aaeb4c7c7c8d2f5bb2cf91fde16e1b76e2421e5480fedd17ad248c1 |
| Packaged subset SHA-256 | 7ac9c17ddc46ffaa68bfbc7a8743072519b881daad0ac6fd54e468fb674e7109 |
| Current domain.json SHA-256 | dc30dc84fbc518827d02727280bef76e06fd20ddf96e578fd23296d439fca14e |
| License | CC BY-SA 3.0 |
| Reference | Baccianella, Esuli, Sebastiani (2010). SentiWordNet 3.0: An Enhanced Lexical Resource for Sentiment Analysis. LREC. |

Original P/N and source rows are preserved. Attribution is in [SENTIWORDNET_LICENSE.txt](../hotel_compiler/resources/SENTIWORDNET_LICENSE.txt). Source data details are in [provenance.json](../hotel_compiler/resources/provenance.json).
