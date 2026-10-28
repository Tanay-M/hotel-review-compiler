# Team 17 eight page IEEE conference paper

Revised 27 October 2026. The matching Word and PDF are exactly eight pages including references, as rendered by Microsoft Word. Authors are Tanay Mohta and Aditya Rawat; affiliations/email details are omitted until supplied.

## Structure and compression

The paper retains Abstract, I Introduction, II Literature Survey (three subsections), III Proposed Systems, IV Results and Implementation, V Performance and Metrics, VI Conclusion, and IEEE numbered references. All five processing stages have descriptive headings and compact pseudocode. The user-approved architecture is Figure 1 on page 2 and spans both columns, occupying most of that page for readable labels. Dataset names and sizes appear inside connected data blocks, with distinct offline training and evaluation flows. The detailed status-decision, Retain Hybrid and Failure Record section is omitted as requested; the DL connector remains labelled Partial / Unsupported only. Preprocessing is the first processing stage. Core processing labels are approximately 7.7 points at the placed figure width.

The revision reduces repeated explanations and redundant figures. It preserves the original A4 two-column layout, 10-point Times New Roman body, title sizing and page margins; these are checked against the archived 12-page document. It retains 35 references including 32 research works, five algorithms, six native editable equations, five tables and three figures. The figures comprise one explanatory architecture and two measured comparison charts. Coverage, class-level behavior, training and category error analysis remain in tables/prose. No experiment result was changed to obtain eight pages.

## Results and figure provenance

SemEval and Trip-MA are separate experiments: SentiWordNet versus Hybrid on 148 mapped polarity cases, and Hybrid versus selective DL on 1,474 mapped test segments (including 1,113 unresolved segments). No cross-dataset DL-versus-SentiWordNet ranking is implied. Booking's 383 accepted DL category outputs out of 456 routed reviews measure coverage, not accuracy. Facilities regression, merged Neutral/Mixed labels, pooled Staff, development reuse and one-seed limitations remain explicit.

The graphs are Python visualizations of saved model-evaluation CSVs. scripts/paper_figures.py draws the lexical comparison; scripts/build_dl_paper_assets.py draws DL pair-F1. The evaluation programs are hotel_compiler/research_runner.py and hotel_compiler/routed_cli.py. scripts/verify_paper_graph_provenance.py independently checks saved predictions/counts, metric values and plotted SVG labels. graph_provenance.json records values and input/output hashes; docs/paper-graph-provenance.md provides the code/data index. The architecture is explanatory and is not a measured result chart.

## Reproduction and preserved version

- Prose: docs/conference_manuscript.md (matching compact copy: docs/conference_manuscript_8page.md).
- Word builder: scripts/build_conference_paper.py.
- Approved dataset-block architecture: scripts/build_approved_paper_architecture.py, using scripts/build_architecture_approval.py.
- PDF export: scripts/render_conference_paper.ps1.
- Canonical PNG rendering: scripts/render_conference_pages.py.
- Structural, numerical, format and eight-page checks: scripts/audit_conference_paper.py.
- Supplement: Team_17_Paper_Figures_and_Tables.zip includes all three figures as SVG/PDF/PNG, aggregate results, DL training metadata, references, cleaning metadata, graph provenance and audit evidence. Raw Trip-MA review data and model weights are not redistributed.
- Preserved 12-page paper and authoring sources: archive/pre-eight-page-revision-2026-10-26.zip.
- Preserved compact eight-page revision before restoring the full architecture: archive/pre-full-architecture-restoration-2026-10-26.zip.
- Preserved eight-page paper before inserting the approved dataset-block diagram: archive/pre-approved-dataset-diagram-2026-10-27.zip.

All final pages are visually checked after rendering. The numerical audit preserves measured scores and verifies the unchanged typography and margins. The prior 243-test implementation run remains separate evidence of software contracts; compression changes neither analysis nor training behavior.
