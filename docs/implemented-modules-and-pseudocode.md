# Implemented modules and pseudocode for the conference paper

Implementation date 15 October 2026. This describes executable code, not future features. The four manuscript modules below group the original eight architecture blocks. Each module has an overall algorithm and each processing step has its own pseudocode for adaptation to the IEEE two-column paper. Established resources and algorithms must be cited; using VADER and TextBlob does not make their algorithms our contribution.

## Systems and numerical policy

The two main systems are the original SentiWordNet compiler and the independent VADER–TextBlob hybrid v2. The baseline uses the original controlled front end; the hybrid uses TextBlob grammatical analysis and independent aspect attachment. See [the complete v2 specification and four module algorithms](independent-hybrid.md). Whole-text sentiment is a separately scoped output, never a substitute for missing aspects.

For a context x, lexical fusion L(x) = 0.5 V(x) + 0.5 T(x) when both tools have evidence. If only one has evidence, use its score. A component exception remains a processing error. Neither tool with evidence means unavailable unless an explicit aspect-domain rule supplies a score. Applicable independent contextual rules retain their IDs, raw component values and pre-rule L. The default equal weight is untuned; TextBlob subjectivity is not a confidence weight.

Final numeric scores are interpreted as Strong Negative at or below -0.5, Weak Negative above -0.5 and below -0.05, Neutral from -0.05 through +0.05 inclusive, Weak Positive above +0.05 and below +0.5, and Strong Positive at or above +0.5. Missing scores are Unavailable. These strength intervals are descriptive, not confidence or independently validated human intensity classes.

## Module 1 Input preparation and lexical analysis

Code: `hotel_compiler/csv_input.py`, `front_end.py`, `lexer.py`, `vocabulary.py`.

Input is a review string or a CSV with selected review and identifier columns. Output is validated row identities and a source-spanned token stream. CSV ingestion preserves one logical row per submitted review. Tokenization normalizes matching forms without replacing the original review used by the hybrid.

### Algorithm M1 Module orchestration

```text
Read a review or decode the CSV under configured limits
Retain each row's identity, original text and input issues
For each valid review:
    validate type, nonempty content and maximum length
    scan and classify tokens while preserving original character spans
Return original review rows, tokens and validation issues
```

### Algorithm 1A CSV ingestion and validation

```text
Check byte limit and decode UTF-8 with optional BOM
Parse quoted CSV fields and multiline cells
Validate unique nonempty headers and selected column names
For every data row:
    retain ordinal and source line boundaries
    check field count, blank review and character limit
    retain supplied ID and flag duplicate IDs/text
    keep invalid rows with issues rather than dropping them
Return ordered input records and source-file hash
```

### Algorithm 1B Lexical scanning

```text
Scan original characters for words, numbers and punctuation
Normalize only the token matching representation
Apply longest configured aspect/opinion phrase match
Recognize grammatical markers, contractions and configured aliases
Keep alias rule IDs, original spelling and character offsets
Keep unknown words as WORD tokens
Return the ordered token stream
```

## Module 2 Syntax and semantic aspect interpretation

Code: `hotel_compiler/parser.py`, `semantics.py`, `front_end.py`, `resources/domain.json`.

The baseline parser implements a controlled predictive grammar and semantic guards. The following baseline algorithms remain unchanged. The hybrid instead uses TextBlob POS and phrase chunks, open adjective candidates, independent aspect phrases, grammatical attachments, coordinated subjects and limited unique pronoun inheritance. Its detailed Module 2 pseudocode is in [the v2 specification](independent-hybrid.md). The systems can extract different numbers of opinions.

### Algorithm M2 Module orchestration

```text
Parse the token stream into clause nodes
Recover at supported boundaries when a clause is unsupported
Bind each accepted opinion to a compatible hotel aspect
Retain syntax and semantic diagnostics
Set aspect coverage from accepted opinions and diagnostics
Return AST, semantic records, diagnostics and coverage
```

### Algorithm 2A Predictive syntax analysis

```text
While tokens remain:
    recognize configured introduction/context phrases
    attempt a supported subject/predicate, possession or adjective-list form
    attach copula/auxiliary, negation and degree markers in grammar order
    build clause nodes with source spans and connectors
    if the construction fails:
        emit a syntax diagnostic
        advance to the next supported recovery boundary
Return all accepted clauses and syntax diagnostics
```

### Algorithm 2B Semantic binding and guards

```text
For every clause in order:
    resolve explicit subject or permitted same-sentence inherited subject
    if no subject exists: record MISSING_ASPECT and continue
    find the configured category and target/opinion issue
    check aspect/category, alias, adverb and emphasis compatibility
    if a guard fails: retain a diagnostic and reset inheritance
    otherwise create a semantic opinion with local negation and degree
    retain the source opinion expression and original source positions
Return semantic opinions and semantic diagnostics
```

## Module 3 Sentiment evidence and five-band interpretation

Code: `hotel_compiler/sentiwordnet.py`, `hybrid.py`, `sentiment_policy.py`.

SentiWordNet retains its original numeric scoring policy. The hybrid scores its own grammatical aspect contexts, retaining punctuation/casing and expanding contractions in TextBlob's working copy. Whole-text hybrid scoring separately receives the original review. Ratings and source field headings never enter the model.

### Algorithm M3 Two-system scoring

```text
For each baseline semantic opinion: obtain its lexical/domain/modifier score
For each independently extracted hybrid context:
    obtain VADER and TextBlob scores
    fuse under the evidence-aware policy; retain any explicit contextual rule
Label each system's own results using the five-band policy
Separately fuse VADER/TextBlob on the complete original review
Return numeric evidence, component phrases, labels, errors and scope
```

### Algorithm 3A SentiWordNet lookup

```text
Verify packaged resource checksum and configured sense membership
Select the opinion's default or explicit category-specific synset
Read original positive P and negative N
Compute objective evidence O = 1 - P - N
Compute lexical score L = P - N
Retain synset ID and gloss; never rewrite source P or N
```

### Algorithm 3B Domain and intensity adjustment

```text
Use lexical score L unless a documented category/sense rule applies
If a rule applies: use its configured domain score D and reason
Select the degree multiplier m from semantic analysis, default 1
Compute intensity-adjusted score A = D * m
Retain source P/N, domain rule, D and m separately
```

### Algorithm 3C Negation and clipping

```text
Set n = -1 for an explicitly negated opinion, otherwise +1
Compute raw final score R = A * n
Clip R to [-1,+1] and round to six decimal places
Retain the local negation multiplier and unclipped score in the trace
Do not transfer negation to a separate later clause
```

### Algorithm 3D VADER and TextBlob hybrid

```text
Input original context x and fixed weight w (default 0.5)
Run VADER(x) and retain compound, positive/neutral/negative proportions
Run TextBlob PatternAnalyzer(x), retaining polarity, subjectivity and assessments
If either analyzer fails:
    mark processing_error, preserve available evidence, return unavailable score
If both analyzers return lexical evidence:
    H = round(w * VADER_compound + (1-w) * TextBlob_polarity, 6)
Else if one has evidence: H = its score
Else: H = unavailable
Retain lexical fusion separately
For an aspect context, apply an unambiguous configured contextual domain rule
Retain raw components, disagreement, original context and domain rule evidence
Return H and its labels
Do not apply compiler intensity or negation to H again
```

### Algorithm 3E Five-band score interpretation

```text
Require 0 <= neutral boundary a < strong boundary b <= 1
If score is missing: return Unavailable
Require a finite score in [-1,+1]
If score <= -b: return Strong Negative
Else if score < -a: return Weak Negative
Else if score <= a: return Neutral
Else if score < b: return Weak Positive
Else: return Strong Positive
```

## Module 4 Review synthesis and reproducible experiments

Code: `hotel_compiler/models.py`, `hybrid.py`, `research_data.py`, `research_metrics.py`, `research_runner.py`, `research_plots.py`, `research_cli.py`.

The offline runner produces review/opinion CSVs, dataset/module summaries, diagnostics, provenance, repeated timings, metric tables where gold labels exist, and scientific figures. Existing UI behavior is preserved; it is not needed to run these experiments.

### Algorithm M4 Module orchestration

```text
Load a declared dataset and record its role and hash
Retain one output row for every submitted review, including invalid rows
Run both systems independently with their own aspect interpretation and scoring
Synthesize aspect means, Mixed labels and explicit scope
If independent gold labels exist: run the declared comparable evaluation
Otherwise: report descriptive counts without accuracy claims
Repeat independent timed runs after warm-up
Export tables, figure files, inference notes and method metadata
Commit the completed run to a new directory; never overwrite earlier evidence
```

### Algorithm 4A Final sentiment and review mean

```text
For each system's aspect results:
    preserve every individual opinion score and strength
    if positive and negative opinions coexist: overall = Mixed
    otherwise derive Positive, Negative, Neutral or Unanalyzed
For the compiler: mean = sum(final opinion scores) / opinion count
For the hybrid: use the same mean only when every extracted opinion is scored
If no opinions exist or required hybrid scores are missing: mean is unavailable
Label the mean as a net score band without replacing overall Mixed
Keep partial analyses labeled recognized opinions only
Keep whole-text hybrid score separate from the aspect mean
```

### Algorithm 4B Source verification

```text
Read each prepared CSV and its separate source map
Reconstruct input text from stored original fields under documented preparation
Verify input hash, row identity and reconstruction equality
Stream the original downloaded archive
Compare every mapped original field against its actual source row
Check that all expected source rows exist and sample parent IDs do not overlap
Export per-row verification and archive hash
```

### Algorithm 4C Adapted human-gold evaluation

```text
Read local SemEval XML as data and retain parent review and sentence IDs
Map declared in-scope entity/attribute labels to coarse project categories
Record every excluded original annotation and the exclusion reason
For sentences with mapped opinions:
    build a set of coarse gold category/polarity pairs
    build the two systems' predicted pair sets
    accumulate matched, predicted and gold pairs for extraction metrics
    for each category with exactly one gold polarity:
        preserve the prediction, including Mixed or Unanalyzed
        count missing/conflicting predictions as errors in accuracy and recall
Calculate fixed three-class macro-F1 and per-class support
Bootstrap accuracy intervals by source review, not independent sentence
Export an optional common-scored subset with its smaller denominator
Do not call this adaptation official SemEval performance or span/issue accuracy
```

### Algorithm 4D Repeated timing and publication outputs

```text
Warm both methods and load lexical resources before timing
Choose prefix sizes from actual available reviews; never duplicate rows to reach a size
For each size and repetition:
    alternate method execution order
    time each full system independently, including its own front end
    exclude CSV I/O, package initialization and plotting
Save every run, mean, median, standard deviation and throughput
Plot directly from measured counts/metrics/timings
Export vector PDF/SVG plus 300-dpi PNG and CSV numeric tables
Write figure-specific inference notes, denominators and limitations
```

## Worked scoring example

The numeric example below was captured with the earlier shared-front-end hybrid v1; it is historical, not the current v2 result. Use the latest exported opinion_results.csv and the v2 specification for current scores.

Original review: The room was not comfortable, but the staff were very helpful.

| Opinion | Compiler final | Compiler strength | VADER | TextBlob | Hybrid final | Hybrid strength |
|---|---:|---|---:|---:|---:|---|
| not comfortable | -0.500000 | Strong Negative | -0.4023 | -0.2000 | -0.301150 | Weak Negative |
| very helpful | +0.312500 | Weak Positive | +0.4754 | +0.2000 | +0.337700 | Weak Positive |

The compiler's aspect mean is -0.093750 and the hybrid's aspect mean is +0.018275. Both preserve overall Mixed. The whole-text hybrid score is a separate +0.254350. These differences illustrate score interpretation and aggregation; they are not an accuracy measurement for this example.

## Paper assembly map

Use the official IEEE conference two-column template when the manuscript is written. The requested content maps as follows:

- Abstract: research question, two systems, dataset/evaluation scope, measured findings and limitation.
- 1 Introduction: motivation for aspect interpretation and inspectable evidence.
- 2 Literature Survey: lexicon/valence rules; aspect extraction; evaluation/intensity. The existing 30-paper candidate list is a preparation aid, not a completed survey.
- 3 Proposed System: editable architecture and Modules 1–4 above, with actual implementation pseudocode. These are project algorithms; cite established lexical tools accurately.
- 4 Results and Implementation: dataset-description table and module_results.csv, scoring examples, coverage, paired outputs and figure-specific inference.
- 5 Performance and Metrics: explicitly adapted human-gold results, per-class metrics, confusion matrices, repeated timings and error analysis. Separate curated demonstrations, random unlabeled samples and benchmark gold.
- 6 Conclusion: findings supported by the runs, remaining grammar limitations, and future extensions.
- References: numbered IEEE references, not APA author-year formatting, unless faculty later supplies a custom requirement.

The new hybrid is a declared combination of established tools, not a proven better model. Report measured results even if the new method is weaker on a particular task. Strength distributions alone do not establish five-class accuracy.
