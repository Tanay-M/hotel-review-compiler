# Team 17 conference manuscript — October 21, 2026 update

Authors: Tanay Mohta and Aditya Rawat. Affiliations and emails remain omitted until supplied.

The editable Word manuscript and native Word-exported PDF preserve the IEEE-style A4 conference layout: full-width title, two-column body, Times New Roman 10-point text and numbered IEEE references. The previous paper, assets, source and scripts are preserved in `archive/pre-vocabulary-update-2026-10-21.zip`.

## Updated content

- Expanded hybrid aspect matching (164 to 671 phrases) and 497 reviewed lexical forms; guarded scoring copies retain original review text and native/effective tool evidence.
- Four modules, four architecture diagrams, four pseudocode algorithms, four native Word equations, four tables and four measured graphs.
- Thirty research works and 33 references, including software documentation and two separately identified dataset sources.
- Rerun annotated benchmark, curated 100, random 200 and runtime measurements. Booking Italy coverage uses the saved before/after audit on identical source rows.
- Fusion weights and contextual-rule values remain fixed; fusion/override ablations remain deferred.

## Evidence and interpretation

Fresh experiments: `output/experiments/2026-10-21/hybrid-vocabulary-paper/`.

On the declared SemEval mapping, SentiWordNet obtains 42/148 correct (28.38%, macro-F1 0.2260); the expanded hybrid obtains 85/148 (57.43%, macro-F1 0.3999). Its earlier version obtained 83/148 (56.08%, macro-F1 0.3956). Updated hybrid tuple-F1 is 0.6450, lower than the earlier 0.6645; this adverse result is retained. Neither system correctly predicts the four neutral cases. These are development measurements on an inspected, adapted benchmark, not official task rankings or untouched holdout accuracy. Five strength bands lack independent intensity labels.

The random cohort has 70 complete, 101 partial and 29 unsupported expanded-hybrid outcomes. Some aspect score is available for 171/200 (85.5%), whereas heuristic completeness is 70/200 (35%); neither is accuracy. The curated 100 is intentionally model-informed. All 300 rerun baseline review scores, statuses and extraction counts match the earlier run.

Booking Italy evidence: `output/experiments/2026-10-18/booking-vocabulary/report/`.

Of 4,367 source rows, 3,102 have body text and 1,265 have no body. Coverage denominators use nonblank bodies. Some scored aspect is available for 2,613 bodies before expansion and 2,701 after (84.24% to 87.07%). Complete outcomes rise from 210 to 244 (7.87% after). Scored contexts increase by 1,543. No independent aspect-polarity annotations exist, so no accuracy or F1 is inferred for this inspected vocabulary-development corpus. Duplicates and empty rows remain. Original positive/negative body fields are joined with a newline; ratings, titles and metadata do not enter scoring. Source SHA-256: `137cec35ddbd678b2bdb1bc93eccb2e844926c8503d3d7f898e274e387933dbd`.

Lexical normalization affects only an internal scoring copy. It is a project synonym policy, not a modification of native VADER/TextBlob dictionaries or of submitted wording. Aliases may alter intensity and introduce errors. The SentiWordNet baseline remains frozen. Runtime values are descriptive within-run desktop measurements under uncontrolled background load.

## Reproduction and materials

Prose: `docs/conference_manuscript.md`. Figures: `scripts/paper_figures.py`. Builder: `scripts/build_conference_paper.py`. Native PDF export: `scripts/render_conference_paper.ps1`. Page renderer: `scripts/render_conference_pages.py`. Audit and evidence ZIP: `scripts/audit_conference_paper.py`. Document tasks use the bundled document Python runtime; experiments use `.venv/Scripts/python.exe`.

The Word body, tables and equations are editable. Embedded figures are high-resolution images; the ZIP includes editable SVGs, vector PDFs, PNGs, numeric CSVs, references and audit metadata. Source reviews and raw archives are excluded from the ZIP. Diagram style preserves serif text, dashed groups, short block labels and grayscale method/integration shading. White indicates project integration, not that every block is a novel algorithm.

All final pages are rendered and visually checked. `paper_audit.json` records structure, citations, metric checks, fonts, evidence paths and document hashes. Internal QA images are not deliverables. No institutional or conference acceptance details are invented.
