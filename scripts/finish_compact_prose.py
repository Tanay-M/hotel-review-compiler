"""Retain core annotation, representation and error-analysis details compactly."""
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'docs/conference_manuscript.md'
s=p.read_text(encoding='utf-8')
if '{{TABLE:dl_categories}}' in s:raise SystemExit('Already applied.')
insertions={
'### C. Representation and Evaluation Considerations':'''These methods address different extraction assumptions. A target-conditioned classifier can estimate sentiment for a supplied aspect but does not by itself establish that the aspect occurs. Our four-state category query therefore includes Absent alongside sentiment states. Conversely, the lexical paths retain explicit opinion attachments and their errors. Preserving these outputs separately exposes which method produced a decision instead of presenting neural categories as grammar-derived target spans.''',
'## III. Proposed Systems':'''The study occupies an application-integration setting rather than proposing a new sentiment representation. Lexical transparency is retained for recognized language, while learned category conditioning addresses unresolved text. Related work motivates both components, but published scores use other corpora, label spaces or training protocols. Consequently, the comparisons below execute local methods on matched inputs within each experiment; external literature scores are not copied into an apparent accuracy ranking.''',
'{{ALG:1}}':'''The handoff is a retained row containing its ID, original review and validation findings. Later stages receive source-aligned working views rather than destructive replacements: case and punctuation remain available to VADER, and character spans still identify evidence in the submitted review. This separates dataset preparation from runtime analysis and distinguishes an invalid CSV row from valid language that an analyzer cannot interpret.''',
'{{EQ:dl_loss}}':'''The eight queries share parameters, allowing multiple categories per sentence without eight independent transformers. Each admitted segment yields eight supervised pairs. Training contains 14,318 Absent, 1,244 Positive, 466 Negative and 276 Neutral/Mixed pairs; weighting reduces absence dominance. The loss divides by summed minibatch target weights. These are pair counts rather than independent reviews; no oversampled copies are reported as additional organic data.''',
'### B. Preprocessing and Validation Implementation':'''In the SemEval crosswalk, ROOMS maps to Room, FACILITIES/ROOMS_AMENITIES to Facilities, FOOD_DRINKS to Food, SERVICE to Service and HOTEL cleanliness to Cleanliness. Conflicting coarse-category annotations remain in pair evaluation but outside single-polarity classification. For DL, original polarity codes retain explicit and implicit opinions. No synthetic review, star-rating proxy or system-generated prediction is treated as human aspect annotation.''',
'### D. Validity and Limitations':'''{{TABLE:dl_categories}}

Table V makes the aggregate tradeoff explicit. Room, Service and Food recover more matched category-polarity pairs under routing. Cleanliness reaches 28 matches among 35 predictions, whereas Facilities loses nine matches. The broad BUILDING/BUSINESS crosswalk and limited supervision are plausible contributors to Facilities difficulty, but this experiment does not isolate causal effects. Higher total F1 supports improved recovery in this setting, not guaranteed correction of each Partial review or superiority on every category.'''
}
for marker,prose in insertions.items():
    assert s.count(marker)==1,marker
    s=s.replace(marker,prose+'\n\n'+marker,1)
p.write_text(s,encoding='utf-8')
(p.parent/'conference_manuscript_8page.md').write_text(s,encoding='utf-8')
print('Compact manuscript retains detailed supervision and category error evidence.')
