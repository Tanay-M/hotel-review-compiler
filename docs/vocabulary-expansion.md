# Expanded deterministic hotel language — 14 October 2026

The six categories remain **Room, Staff, Service, Food, Cleanliness, Facilities**, as requested. The expanded analyzer runs offline through the same compiler used by single reviews, CSV batches, and the dashboard. It adds no LLM, trained NLP model, database, or runtime dependency.

## Measured improvement

The existing `examples/hotel_reviews_100.csv` was analyzed before and after the change without changing its reviews or adding input columns.

| Measure | Before | After |
|---|---:|---:|
| Submitted/analyzed reviews | 100 | 100 |
| Complete | 54 | 88 |
| Partial | 28 | 6 |
| Unsupported | 18 | 6 |
| Extracted opinions | 127 | 167 |
| Invalid input / processing errors | 0 / 0 | 0 / 0 |
| Aspect phrases | 53 | 345 |
| Canonical opinion terms | 44 | 356 |
| Explicit opinion aliases | 7 | 32 |
| Genuine packaged SentiWordNet rows | 42 | 315 |

Complete coverage increased by **34 percentage points to 88% on this sample**. This is supported-language coverage on an authored development dataset, **not 88% sentiment accuracy or a guarantee for arbitrary uploads**. The remaining twelve rows are visible individually; no unsupported text is counted as Neutral. Precision, recall, and F1 still need independent human labels and a held-out set of naturally occurring reviews.

The unchanged input SHA-256 is `3172b6c07e8265c993fb743fd8b577df4d9f4899906ff9671224ab1e7c9a8e14`. Saved CSV evidence is in `output/evaluation/vocabulary-expansion-2026-10-14/`: `coverage_comparison.csv`, `review_comparison.csv`, `remaining_inspection.csv`, and current report tables. Each run records its input and analysis fingerprints. The input itself still has only `sr.no,review`.

## What was expanded

- Hundreds of hotel aspect phrases: room types, furniture, linen, bathrooms, reception/housekeeping staff, meals and drinks, check-in/out, connectivity, plumbing, lighting, locks, and equipment.
- Adjectives for quality, cleanliness, comfort, noise, staff/service behavior, food, and facilities. Examples include spotless, grimy, immaculate, moldy, musty, cramped, spacious, squeaky, courteous, dismissive, attentive, inefficient, bland, savory, stale, underdone, defective, unreliable, and leaky.
- Explicit aliases, including undercooked → underdone, mouthwatering → mouth-watering, leaking → leaky, and stopped cooling → malfunctioning. Equipment aliases have aspect guards; “stopped cooling” is restricted to air conditioning. Aliases never swallow negation.
- Degree modifiers, including slightly, somewhat, fairly, quite, exceptionally, a bit, and a little bit. These are documented arithmetic conventions, not learned probabilities.
- Common introductory phrases, selected time/social context phrases, sensory linking verbs, and constrained relational tails. Known context is retained in the syntax trace; unknown words and arbitrary trailing clauses still produce diagnostics.

## Grammar examples for a demonstration

| Supported form | Example | Association |
|---|---|---|
| Shared predicate across subjects | The room and bathroom were clean. | Clean applies to both explicit subjects. |
| Shared subjects and predicates | The room and bathroom were clean and spacious. | Four aspect/opinion records. |
| Adjectives before noun | Clean and quiet room. | Two opinions about Room. |
| Possession/contained aspect | The room had a comfortable bed. | Comfortable targets bed, not the containing room noun. |
| Introduction and time phrase | I found the room very clean when we arrived. | Clean targets Room; context is retained. |
| Experience with explicit target | I was pleased with the service. | Pleased targets Service. |
| Equipment failure | The air conditioning stopped cooling during the night. | Facilities / Air Conditioning, negative. |
| Noun/adjective overlap | The safe was broken. / The room was safe. | Equipment safe versus evaluative adjective safe. |

These are bounded grammar rules, not unrestricted English understanding. Pronoun resolution, sarcasm, implicit complaints, arbitrary relational clauses, and complicated negation remain outside scope. “We waited forty minutes before reception” does not have an explicitly scored adjective; “Water was leaking from the bathroom ceiling” is still an unsupported construction even though a simpler explicit plumbing/leaky predicate is recognized.

Standalone Location and Price/Value opinions remain outside the six categories. Reviews combining those with supported hotel opinions are partial. The compiler does not force them into Room or Facilities. A retained phrase such as “for the price” is context, not an extracted price opinion.

## SentiWordNet scoring: what comes from the resource

**P and N are the original SentiWordNet positive/negative values.** The packaged TSV preserves the original source rows; checksum, term membership, and source-row equality are verified. The original archive hash and subset hash are recorded in `resources/provenance.json`. Every canonical opinion has a real POS/offset sense, source terms, and gloss.

Sense selection is static and reproducible: existing configured senses are preserved; new terms use the first ranked adjective sense unless the catalog supplies an explicit domain-relevant sense override. Overrides address polysemy such as “great,” “raw,” “hard,” “stale,” “thoughtful,” “savory,” and “salty.” Selection does **not** choose whichever sense has the most positive or negative score. Selected senses and reasons are visible in Scoring, with an auditable CSV at `hotel_compiler/resources/opinion_senses.csv`.

```text
lexical_score = original_P - original_N
domain_score  = lexical_score, unless an explicit category preference applies
final_score   = clip(domain_score * intensity * negation_sign, -1, +1)
```

Some source senses have lexical scores that conflict with a hotel preference or are zero. Separate deterministic category preferences cover 73 terms across 100 category adjustments, including the five earlier rules. The trace exposes the **unchanged original P/N**, lexical score, domain score, rule ID/reason, sense choice, intensity, and negation. These preferences are our rules, not SentiWordNet values. New preference rules keep the lexical magnitude and adjust direction; when lexical sentiment is zero, they use a stated 0.25 convention. Earlier documented calibrations retain their original values. A physical firm mattress is treated as neutral because firmness has no universal preference.

“Fresh” also has three explicit category-specific senses: food freshness, clean linen in Room, and pure air/hygiene in Facilities/Cleanliness. For food, original P=0.375 and N=0.625 give lexical −0.25; the documented food-freshness preference gives +0.25. The linen sense has its own source P/N and rule. Context-specific senses do not inherit a calibration belonging to a different source sense.

Negation applies once after domain scoring. Intensity then scales the magnitude; clipping keeps scores in [−1,+1]. The neutral threshold is 0.05. This numeric score is an interpretable index, not confidence or a calibrated probability. Categories/issues and compatibility rules remain explicit configuration; SentiWordNet does not infer the aspect or issue.

## Where the logic is written

| File | Responsibility |
|---|---|
| `resources/domain.json` | Runtime aspect/category mappings, opinion senses, aliases, compatibility, modifiers, context phrases, preferences. |
| `scripts/hotel_vocabulary_catalog.json` | Curated build catalog, sense overrides and hotel preference declarations. |
| `scripts/expand_hotel_vocabulary.py` | Deterministic vocabulary/resource build and sense audit CSV. |
| `scripts/prepare_sentiwordnet.py` | Verified archive/subset preparation and provenance/license. |
| `hotel_compiler/lexer.py::tokenize` | Longest phrase matching, normalization, source spans, safe noun/adjective classification, token types. |
| `hotel_compiler/parser.py::ReviewParser._predicate/_contexts/_clause` | Predicate syntax, bounded context, coordination, possession, experiential frames and recovery. |
| `hotel_compiler/semantics.py::analyze_semantics` | Aspect/opinion attachment, inheritance, category/issue selection and compatibility guards. |
| `hotel_compiler/sentiwordnet.py::load_synsets/evaluate` | Source verification, selected sense lookup, P/N, preferences, negation/intensity and score evidence. |
| `hotel_compiler/pipeline.py::analyze_review` | Integrates the compiler stages and final complete/partial/unsupported status. |
| `hotel_compiler/batch.py`, `csv_input.py` | CSV validation and one independent compiler result for every row. |
| `hotel_compiler/aggregation.py`, `reporting.py`, `paper_tables.py` | Scope-aware summaries, evidence-backed conclusions and CSV/text report exports. |
| `web_assets/index.html/styles.css/app.js` | Web presentation; Demo Notes removed, input full width, context and sense selection shown in traces. |

## Verification and running

The full suite passes **136 tests**, including all 356 opinion terms and their negated forms, source P/N preservation, aliases, grammar/recovery, batch equivalence, all 500 HTTP review results, and report exports. The 100 authored language contracts still match their expected outcomes; the contract for “Clean and quiet room” was explicitly updated to the newly supported complete two-opinion form. These are implementation regression checks, not independent accuracy evaluation. Python compilation and both browser JavaScript syntax checks pass.

From the project folder:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\serve.ps1
```

Open `http://127.0.0.1:8000/`. In **CSV & dashboard**, use **100 reviews** or upload `examples/hotel_reviews_100.csv` with text column `review` and ID column `sr.no`. The updated sample reports 88 complete, 6 partial, 6 unsupported and 167 opinions. Select any review row to see its individual results and traces. Restart the server after changing Python code/resources.

To rebuild vocabulary resources from the curated catalog (maintenance only):

```powershell
python scripts/expand_hotel_vocabulary.py
```

The builder verifies the pinned official corpus archive. If it is absent, first run `python scripts/prepare_sentiwordnet.py --download` to fetch the verified source, then rerun the builder. Normal analysis uses the packaged subset offline. No download or model call occurs during review analysis.

## Resource references

- [SentiWordNet authors' resource repository](https://github.com/aesuli/sentiwordnet)
- [Original SentiWordNet 3.0 paper, LREC 2010](https://aclanthology.org/L10-1531/)
- [Official NLTK SentiWordNet documentation](https://www.nltk.org/howto/sentiwordnet.html)

The resource remains CC BY-SA 3.0 with packaged attribution. Earlier project documentation and the Word architecture diagram are dated snapshots; use these updated counts and evidence for the later report.
