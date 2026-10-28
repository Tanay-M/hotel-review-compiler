"""Append introduction questions and maintain Markdown as the viva notebook."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'docs/research-paper-viva-qa.json'
OUTPUT=ROOT/'Research_Paper_Viva_QA.md'
NEW=[
 {'id':5,'topic':'Introduction','question':'What is a source span? Explain with an example.',
  'points':[
   'A source span records the start and end character positions of a piece of evidence in the original submitted review. It is not a sentiment score.',
   'For "The room was clean.", zero-based span [4, 8) identifies "room" and [13, 18) identifies "clean". The start is included; the end is excluded. The full sentence has span [0, 19).',
   'Offsets allow the interface and exported evidence to show which words supported a token, aspect, opinion, clause or diagnostic. Working copies must remain aligned to the original text.',
   'Lexical pipelines retain token/opinion/context spans. The DL stage supplies original sentence evidence, not independently verified exact target/opinion spans.'],
  'viva':'A source span is the location of supporting text in the original review, stored as start and end character positions. It lets us trace a prediction to its evidence and highlight the exact text. The DL component retains sentence evidence rather than claiming exact opinion extraction.'},
 {'id':6,'topic':'Introduction','question':'What different dictionaries, grammars and aspect mappings do the two pipelines use?',
  'points':[
   'Dictionary means a collection of recognized words/phrases and associated information. Grammar means rules for connecting words into aspect-opinion structures. Aspect mapping means assigning an identified target to a hotel category.',
   'SentiWordNet pipeline: resources/domain_expanded.json defines 772 aspect phrases, 21,181 opinion entries, 752 aliases and modifier/compatibility rules. resources/sentiwordnet_expanded.tsv supplies native synset positive/negative scores. Our project dictionary chooses a synset; SentiWordNet itself does not choose hotel categories.',
   'Hybrid pipeline: resources/hybrid_domain.json plus resources/hybrid_vocabulary.json supply a separate 671-phrase aspect inventory and 497-form lexical-alias catalog. VADER has its own valence lexicon and contextual rules; TextBlob Pattern sentiment has its own polarity/subjectivity lexicon. Scoring-copy aliases are explicit project additions, not new native lexicon entries.',
   'Baseline grammar uses our token classes, predictive parser and bounded recovery rules in lexer.py, parser.py and expanded_parser.py. It handles patterns such as "The room was spacious", "spacious room", coordinated targets, supported opinion verbs and explicit absence. It does not parse unrestricted English.',
   'Hybrid grammar uses TextBlob PatternParser for POS tags and shallow phrase chunks. Our hybrid_nlp.py segments clauses, matches aspect phrases and attaches preceding adjectives, following predicates and supported opinion verbs. VADER supplies sentiment rules, not this grammatical front end. The two pipelines do not share a parser.',
   'For "The room was spacious", the baseline matches configured ASPECT and OPINION entries and parses their relationship. Hybrid uses noun/adjective/POS/chunk evidence plus our attachment rules, then scores the extracted context using its sentiment tools. Recognition does not guarantee either tool has a usable score.',
   'Examples of configured aspect mappings include room -> Room, breakfast -> Food and air conditioning -> Facilities. These are project ontology choices rather than categories learned by SentiWordNet or automatically supplied by VADER.',
   'In "The room was clean", the baseline can return category Room with issue Cleanliness: category and issue are different fields. Hybrid also recognizes room as Room; a human benchmark may instead categorize room hygiene under Cleanliness. Shared category names therefore do not guarantee identical annotation conventions.',
   'The paper compares complete pipelines whose vocabularies, extraction rules and category conventions differ. Its performance difference cannot be attributed solely to one sentiment dictionary.'
  ],
  'viva':'The baseline uses our controlled hotel vocabulary, compiler parser and SentiWordNet synset scores. Hybrid uses a separate aspect dictionary, TextBlob grammatical parsing, our attachment rules and VADER/TextBlob sentiment resources. Both use hotel category mappings, but their extraction and mapping decisions can differ. We therefore compare full pipelines, not just scoring dictionaries.'},
 {'id':7,'topic':'Introduction','question':'What are measured recovery and regression?',
  'points':[
   'Recovery means a correct gold category-polarity pair appears after DL reanalysis when Hybrid previously missed it. Regression means a pair Hybrid previously predicted correctly is lost after replacement. These are measured by comparing both outputs with human annotations for the same segment.',
   'Illustrative recovery: human gold (Service, Negative), Hybrid missing, DL (Service, Negative). Illustrative regression: human gold (Room, Positive), Hybrid (Room, Positive), replacement loses or changes that prediction. These examples explain definitions; they are not additional measured test cases.',
   'The saved Trip-MA comparison reports 97 newly correct pairs and 44 previously correct pairs lost: net correct-pair gain = 97 - 44 = 53. Overall matched pairs rise from 314 to 367.',
   'The selected pipeline also introduces 114 false pairs and removes 198 previous false pairs. F1 accounts for both missed gold pairs and incorrect predictions; it is not determined by net correct-pair gain alone.',
   'Overall pair-F1 rises from 0.4184 to 0.4993, but Facilities F1 falls from 0.1854 to 0.1389. Higher overall F1 does not mean every category or routed review improves.',
   'These are category-polarity pair counts, not numbers of corrected whole reviews. A review or segment can contain multiple pairs. Complete status is not an independent correctness label.'],
  'viva':'We measure recovery as newly correct category-sentiment pairs after DL, and regression as previously correct pairs lost after replacement. On Trip-MA we gained 97 correct pairs and lost 44, a net gain of 53. We report both improvements and harms rather than assuming DL always helps.'}
]


def build():
    entries=json.loads(DATA.read_text(encoding='utf-8'))
    existing={x['id'] for x in entries}
    entries.extend(x for x in NEW if x['id'] not in existing)
    DATA.write_text(json.dumps(entries,indent=2,ensure_ascii=False),encoding='utf-8')
    lines=['# Research Paper Viva Questions and Answers','',
           'Team 17 | Tanay Mohta and Aditya Rawat | Updated 28 October 2026','',
           'This Markdown file is the continuing Q&A notebook. It includes the earlier abstract questions and the introduction questions. Future questions should be appended here; the Word notebook is no longer updated.','']
    for item in entries:
        lines.extend([f"## Q{item['id']}. {item['question']}",'',f"**Paper section:** {item['topic']}",'','### Key explanation',''])
        lines.extend('- '+p for p in item['points'])
        if item.get('detail_file'):
            lines.extend(['',(ROOT/item['detail_file']).read_text(encoding='utf-8'),''])
        lines.extend(['','### Answer to faculty','', '> '+item['viva'],''])
    lines.extend(['## Evidence used','',
      '- Implementation: `hotel_compiler/models.py`, `lexer.py`, `parser.py`, `expanded_parser.py`, `semantics.py`, `hybrid_nlp.py`, `hybrid_vocabulary.py`, `hybrid.py`, `dl_pair.py`.',
      '- Dictionaries: `hotel_compiler/resources/domain_expanded.json`, `sentiwordnet_expanded.tsv`, `hybrid_domain.json`, `hybrid_vocabulary.json`.',
      '- Results: `output/experiments/2026-10-21/expanded-sentiwordnet-release/semeval-development/metrics.csv`; `output/neural/2026-10-23-dl-pair-evaluation/metrics.csv` and `change_summary.json`.',''])
    OUTPUT.write_text('\n'.join(lines),encoding='utf-8')
    assert [e['id'] for e in entries]==list(range(1,len(entries)+1))
    print(f'Saved all {len(entries)} questions in {OUTPUT}; Word file unchanged.')


if __name__=='__main__':build()
