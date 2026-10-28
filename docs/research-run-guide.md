# Running the two-system paper experiments

**Expanded compiler update:** Use `--compiler-profile expanded` on `compare` or `evaluate-semeval` to compare the broader SentiWordNet compiler against the unchanged hybrid. Omitting it retains the original profile. Final expanded results are under `output/experiments/2026-10-21/expanded-sentiwordnet-release/`; [the comparison reference](expanded-sentiwordnet-and-demo.md) provides measured results, real-data cleaning, source maps, launchers and full-corpus commands. The IEEE paper now uses these current results and labels the two approaches simply SentiWordNet and Hybrid.

Implemented 15 October 2026; publication update 21 October. The two systems are the SentiWordNet compiler and the VADER–TextBlob hybrid. The offline research runner needs no WebUI, SQL or LLM API. The [current paper](../output/paper/PAPER_README.md) uses `output/experiments/2026-10-21/expanded-sentiwordnet-release/`. [Published CSVs](../output/datasets/README.md) and [source acquisition/licensing notes](../data/README.md) are included in Git; the raw SemEval XML and upstream archives require a separate download.

Current hybrid is v2 with independent TextBlob grammatical extraction. See [implementation, policy and module pseudocode](independent-hybrid.md). Earlier `paper/` runs preserve v1 results; `independent-hybrid-v2/` contains the new comparison. The WebUI now exposes both independent methods for live demonstrations; see [hybrid demo instructions](web-hybrid-demo.md). Saved paper experiments remain separate. The inspected SemEval benchmark is development evidence, not an untouched holdout.

## Installation

A local `.venv` with research dependencies is already installed. From the project directory:

```powershell
.\.venv\Scripts\python.exe -m hotel_compiler.research_cli --help
```

On a fresh machine with Python 3.10 or newer:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[research]"
```

Completed runs capture installed versions in environment_lock.txt and source_snapshot.zip containing analysis code, packaged resources and pyproject.toml. These exclude raw datasets and credentials. For reproduction on compatible Python/platform, install the lock file in a fresh environment and install the captured project without dependency upgrades. Record any change.

## Verify the data

```powershell
.\.venv\Scripts\python.exe -m hotel_compiler.research_cli verify-data --output-dir output/experiments/my-source-check
```

All 100 demo and 200 random reviews are checked against the actual downloaded archive, with per-row verification exported. Preparation trims surrounding field whitespace, removes exact missing-field placeholders, and joins the supplied feedback fields with newline when both exist. Original fields and parent IDs remain in provenance. No wording is generated or rewritten. This authenticates preparation against the dataset, not the human identity of each original reviewer. The vocabulary-scoped demo was selected after a pilot and is not an unbiased accuracy test.

## Compare CSV inputs

```powershell
.\.venv\Scripts\python.exe -m hotel_compiler.research_cli compare output/datasets/real_hotel_demo_100.csv --dataset-role curated_demo --output-dir output/experiments/my-demo-run --repeats 5
.\.venv\Scripts\python.exe -m hotel_compiler.research_cli compare output/datasets/real_hotel_random_200.csv --dataset-role random_real --output-dir output/experiments/my-random-run --repeats 5
```

The existing PowerShell launcher also supports `--research` followed by these arguments. Use a new output directory each time; existing evidence is protected. Failed builds do not publish partial runs as successful. CSV limits remain 1,000 rows, 10 MiB and 10,000 characters per review. Optional --vader-weight changes the declared weight for a separately versioned development experiment; default 0.5. Do not tune on reported test results while continuing to call them unseen evaluation.

## Independent gold evaluation

```powershell
.\.venv\Scripts\python.exe -m hotel_compiler.research_cli evaluate-semeval data/vendor/real-hotel-research/semeval2015_hotels.xml --output-dir output/experiments/my-semeval-run --bootstrap-repeats 1000
```

This is a coarse-category adaptation, not official SemEval performance. The crosswalk excludes prices/location and most HOTEL annotations, and collapses predicted Staff into benchmark Service. XML gold and exported scope/exclusions are retained. Metrics concern category/polarity sets, not exact issues or target spans. Cases have one gold polarity per coarse category; missing/conflicting predictions count as errors. Bootstrap sampling uses parent reviews. The smaller common-scored subset cannot replace all-eligible results.

## Evidence files

| File | Paper use |
|---|---|
| review_results.csv | One row per review, paired means, separate whole-text hybrid, five bands and diagnostics |
| opinion_results.csv | Separate system rows; original P/N, hybrid contexts, components, lexical fusion, grammar pattern and domain rule |
| hybrid_tokens.csv / hybrid_noun_phrases.csv / hybrid_segments.csv | Independent TextBlob grammatical traces with source spans |
| dataset_description.csv and module_results.csv | Dataset scope and four-module implementation counts |
| coverage.csv | Processing status, not correctness |
| strength_distribution.csv | Descriptive bands and unavailable scores |
| runtime_runs.csv and runtime_summary.csv | Every repetition, mean, median, standard deviation and throughput |
| metrics.csv and per_class_metrics.csv | Gold accuracy, three-class macro-F1, support and coverage |
| predictions.csv and confusion_counts.csv | Inspectable predictions, gold and abstentions |
| annotation_scope.csv and excluded_annotations.csv | Benchmark inclusion/exclusion evidence |
| paired_scored_subset.csv | Secondary identical-case scoring comparison, excluding extraction failures |
| fig_*.pdf / fig_*.svg / fig_*.png | Vector figures and 300-dpi raster alternatives |
| *_table.tex | Table snippets; CSV also supports Word tables |
| INFERENCES.md | Module/figure explanations for Results and Discussion |
| run_metadata.csv | Hashes, code fingerprints, libraries, policy, machine and timing scope |
| source_snapshot.zip and environment_lock.txt | Reproduction materials |

Unlabeled CSV comparisons produce no invented accuracy/F1. Ratings and feedback headings never enter model input. Five-band counts are descriptive unless independent intensity gold is obtained. Formula-leading CSV strings are escaped for spreadsheet display; hashes refer to original analyzed inputs.

Runtime alternates method order and measures warm independent core execution. Both systems include front-end work; the hybrid also scores complete original text. Initialization, I/O, plotting and UI work are excluded. This is a shared desktop, not isolated hardware; interpret small differences cautiously.

## Paper handoff

[Implemented module/step pseudocode](implemented-modules-and-pseudocode.md) supports Sections 3 and 4. [Editable architecture](hybrid-architecture.mmd) groups the original eight blocks into four manuscript modules and starts with preprocessing.

The complete manuscript and synthesized 30-work literature survey are in `output/paper/`, using an IEEE-style two-column Word layout and numbered references. Preserve adverse measured results and distinguish authored tests, curated demos, random samples and benchmark gold in captions.
