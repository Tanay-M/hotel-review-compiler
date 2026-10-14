# Deterministic language expansion - 12 October 2026

**14 October update:** See [the current vocabulary and scoring expansion](vocabulary-expansion.md): 345 aspect phrases, 356 opinion terms, 32 aliases, 315 source synsets, and 136 passing tests. Complete coverage on the unchanged authored 100-review development sample improved from 54% to 88%; this is not sentiment accuracy. The six categories remain unchanged. Older dated measurements below describe their original milestones.

The expanded compiler is shared by CLI, the existing browser API, and CSV batching. No SQL, LLM, trained tagger, embeddings, or runtime network dependency is added. Restart a running demo server to load the new code/resources. The UI layout is unchanged.

## Supported additions

| Family | Example | Result |
|---|---|---|
| Equipment state | The air conditioning was not working. | Facilities / Air Conditioning / Negative, -0.25 |
| Functional verb | The WiFi does not work. | Facilities / WiFi / Negative, -0.25 |
| Auxiliary contraction | The heater didn't function. | Facilities / Heating / Negative, -0.25 |
| Functionality phrase | The elevator was out of order. | Facilities / Elevator / Negative, -0.25 |
| Opinion before aspect | Very rude staff. | Staff / Friendliness / Negative |
| Selected adverb | The AC doesn't work properly. | Negative; adverb retained |
| Negative emphasis | The fridge did not work at all. | Negative; no additional weight or negation |
| Inherited predicate | The WiFi works but doesn't work well. | Positive and Negative records; overall Mixed |
| Vocabulary | Comfortable beds; noisy room; spacious room. | Comfort / Positive; Noise / Negative; Space / Positive |

The six-category taxonomy remains. There are now 53 aspect phrases, 44 canonical opinions, seven explicit opinion/phrase aliases, and 42 genuine source synsets. New aspects include air conditioner, shower, television/TV, heater/heating, elevator/lift, fridge/refrigerator, lights/lighting, beds, mattresses, towels, and waiters.

## Logic and current grammar

- `resources/domain.json` defines senses, aliases, compatibility, auxiliary words, allowed adverbs, and explicit rule IDs/reasons.
- `lexer.py::tokenize` longest-matches known phrases, retains source spans, and normalizes aliases visibly. `work`/`works` become FUNCTION_VERB tokens with canonical `working` and base/finite form. `out of order` becomes one OPINION token with canonical `broken`. Auxiliary contractions split into AUXILIARY + NEGATION, including curly apostrophes.
- `parser.py::ReviewParser._clause` distinguishes subject-first, opinion-before-aspect, and inherited forms. A copula expects OPINION; an auxiliary expects a base FUNCTION_VERB. `does works`, `was work`, and `Works AC` are rejected. Only `really` may modify a functional verb; degree intensifiers apply to state/adjective opinions.
- `models.py::Clause` retains auxiliary/copula, adverb/emphasis, syntax form, and a separate opinion range. A full clause span includes its explicit aspect even when the adjective comes first; the opinion range excludes the noun.
- `semantics.py::analyze_semantics` checks compatibility before producing a record. `staff were working` is outside equipment scoring; `food was functioning` is rejected. Invalid semantic clauses clear inheritance. `at all` requires negation in that clause. `properly`/`well` are only supported after working/functioning or their verb forms.
- `sentiwordnet.py::evaluate` retains original P/N and gloss, with separate normalization and calibration IDs. Adverbs/emphasis use unit weight; negation is applied once.
- `vocabulary.py::validate_vocabulary` rejects inconsistent aliases, target references, and calibration definitions before normal batch/web processing.

The expanded clause shapes are:

```text
Clause               -> DETERMINER ArticleBody | ASPECT SubjectPredicate
                      | StatePredicate AspectOpt | FunctionalPredicate
                      | COPULA StatePredicate | AUXILIARY FunctionalPredicate
ArticleBody          -> ASPECT SubjectPredicate | StatePredicate ASPECT
SubjectPredicate     -> COPULA StatePredicate | AUXILIARY FunctionalPredicate
                      | StatePredicate | FunctionalPredicate
StatePredicate       -> NegationOpt IntensifierOpt OPINION AdverbOpt EmphasisOpt
FunctionalPredicate  -> NegationOpt IntensifierOpt FUNCTION_VERB AdverbOpt EmphasisOpt
AspectOpt            -> ASPECT | epsilon
```

Optional modifiers have terminal-or-epsilon productions. Parser guards enforce base verbs and modifier applicability; semantic guards enforce aspect compatibility, negative emphasis, and inheritance. Review boundaries/recovery retain the original design. Sentence ends, standalone commas, and recovery reset context; pronouns are not resolved.

## Source scores and domain rules

| Opinion | Sense | P | N | Domain base |
|---|---|---:|---:|---|
| working | a:01091728 | 0.25 | 0 | +0.25 directly from equipment sense |
| functioning | a:01091556 | 0 | 0 | +0.25; `functioning_equipment` |
| operational | a:02124253 | 0.25 | 0 | +0.25 directly from ready-for-use sense |
| comfortable | a:00476819 | 0 | 0.75 | +0.5 in Room; `physical_room_comfort` |
| uncomfortable | a:00478015 | 0 | 0.625 | -0.625 directly from physical discomfort |
| noisy | a:01919931 | 0.375 | 0.375 | -0.5 in Room/Facilities; `hotel_noise_complaint` |
| spacious | a:00476249 | 0 | 0 | +0.25 in Room; `room_space_preference` |

The physical `comfortable` source row is negative despite its well-being gloss. We preserve it and document a separate Room preference rule, rather than selecting a financially comfortable sense or inventing P/N. The original `slow_service_facilities` rule remains -0.5. Thus five opinion entries have domain rules: slow and four new entries. All 42 TSV rows are unchanged official rows, checked against the pinned source archive.

Configured aliases are `out of order` -> `broken`, `comfy` -> `comfortable`, `busted` -> `broken`, `work`/`works` -> `working`, and `function`/`functions` -> `functioning`. These are explicit interpretations, not automatic synonym discovery or trained lemmatization. Original expressions are retained; normalization IDs appear in token/semantic/scoring traces. Out-of-order normalization is restricted to Facilities.

## Validation and evaluation

`examples/robustness_cases.json` contains 100 authored labeled contracts: 70 development and 30 reserved. Labels were recorded before implementation changes. Reserved cases check recombinations of the same language families; they are not an independent blind real-world dataset.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\evaluate.ps1 .\examples\robustness_cases.json
```

Portable equivalent, with optional new report:

```powershell
python -m hotel_compiler.evaluation examples/robustness_cases.json --output output/batches/my-evaluation.json
```

Existing reports are protected. `evaluation.py` compares multisets of category/issue/polarity triples per review, retaining repeated opinions. It reports split/family metrics, mismatches, unknown words, diagnostic counts, corpus hash, and analysis fingerprint. Polarity agreement uses matched category/issue counts; source-span accuracy is checked separately in tests.

On these same 100 contracts, exact outcomes improved from 29/100 to 100/100 and tuple recall from 13.48% to 100%. Sixty-nine cases should be complete; 31 deliberately exercise partial/rejection behavior. This is contract validation, not 100% real-world accuracy. An independently annotated real-review corpus is still needed. Snapshots are saved as `output/batches/robustness-baseline.json` and `robustness-current.json`.

Original 24 examples retain their expected outputs. Expanded patterns also retain identical single-review results and traces in 100/500-row JSON exports. Source spans, alias evidence, compatibility, negation boundaries, resource integrity, and evaluation counts have dedicated checks.

## Remaining scope

Still diagnose pronouns, implicit aspects, arbitrary verbs/modals such as `cannot work`, complex/repeated negation, `not only ... but also ...`, `working poorly`, and `works not properly`. `clean and quiet room` is only partial because the first adjective is not attached backward to a later noun. Older opinion entries are not a full semantic type system; `food was slow` retains its documented lexical-neutral result.

Review/category/issue reporting and the CSV dashboard were subsequently implemented on 13 October; see `aggregation.md` and `web-dashboard.md`. The API is minimal/synchronous under the user's latest preference. Next evidence work: independently annotated held-out reviews and repeated timing for the course report. SQL and learned NLP/LLM enhancements remain deferred.
