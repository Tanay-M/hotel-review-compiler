Results tables for an IEEE-format course report

reviews.csv has exactly one row per submitted CSV record, including invalid and unsupported inputs.
aspects.csv holds separate extracted opinions; join on row_id, never a duplicated supplied ID.
Category/issue polarity counts are distinct reviews, not opinions; Mixed is preserved.
Any-negative counts include Mixed once. Scores average within each review before averaging reviews.
Both aggregate scopes are explicit. Complete-only is primary; partial-inclusive means recognized opinions only.
Blank averages/percentages mean no evidence. Low support, duplicates, and coverage must accompany interpretations.
CSV formula-leading strings are apostrophe-escaped for spreadsheet safety. Unicode/BOM are supported.
These are descriptive results, not measured prediction accuracy or a star rating.
For empirical accuracy, independently annotate representative reviews and evaluate held-out labels.
The authored 100-case regression corpus is a separate contract evaluation, not a blind real-world dataset.
Record dataset provenance, annotation protocol, model/rule version, limits, hardware, repeated timing methods, and limitations.
The ZIP contains no JSON and does not draft or submit a paper.
