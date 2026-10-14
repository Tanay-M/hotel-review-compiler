"""Update native editable Word blocks while preserving their layout and colours."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile

from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'output/architecture/Team_17_Detailed_Block_Diagram.docx'
OUTPUT = ROOT / 'output/architecture/Team_17_Detailed_Block_Diagram_Updated.docx'
W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
NS = {'w': W}

# Keep the same bullet count and the existing title/body/code paragraph styles.
UPDATES = {
    '1  Preprocessing and validation': [
        'Read single-review text or decode CSV as UTF-8 with optional BOM.',
        'Map sr.no and review; parse quoted commas and multiline fields.',
        'Validate headers, cells, blank text, 10 MiB, 1,000 rows and 10,000 characters per review.',
        'Keep original text and row order; flag duplicate text and supplied IDs.',
        'Normalize case, curly apostrophes and selected hyphens for matching; preserve source offsets.',
        'Retain negations, modifiers, context and unknown words for analysis.',
    ],
    '2  Lexical analysis': [
        'Regex-scan words, numbers, punctuation and the configured A/C form.',
        'Longest-match 345 aspect phrases and 356 canonical opinion terms.',
        'Classify aspects, opinions, modifiers, introductions, context and grammar markers.',
        'Expand configured contractions into a verb plus not; retain source spans.',
        'Apply 32 explicit aliases, including leaking and stopped cooling; retain their rule IDs.',
        'Keep unknown WORD tokens; disambiguate safe as noun or adjective from local syntax.',
    ],
    '3  Syntax analysis': [
        'Predictively parse the controlled review grammar.',
        'Accept copulas, auxiliaries and equipment predicates.',
        'Share predicates across coordinated subjects; parse adjective lists before nouns.',
        'Parse possession and explicit targets: soft bed; pleased with service.',
        'Keep introductions, configured time/context and source spans in the AST.',
        'Diagnose unsupported clauses; recover at the next boundary.',
    ],
    '4  Semantic analysis': [
        'Attach opinions to explicit aspects and valid shared subjects.',
        'Keep six categories: Room, Staff, Service, Food, Cleanliness and Facilities.',
        'Choose the aspect/opinion issue or a contextual sense override.',
        'Target the contained noun in possession; inherit across valid connectors only.',
        'Check category/aspect, alias and modifier guards; at all needs negation.',
        'Keep expressions/spans; diagnose Location/Price and implicit complaints.',
    ],
    '5  SentiWordNet lookup': [
        'Look up the configured opinion sense supplied by our controlled vocabulary.',
        'Read original SentiWordNet positive P and negative N without changing either value.',
        'Calculate objective score = 1 - P - N.',
        'Calculate lexical sentiment L = P - N.',
        'Retain source sense ID, gloss, P/N and L in the scoring trace.',
        'Pink denotes the inherited lexical scoring method; our sense configuration is in the blue resource block.',
    ],
    '6  Domain and intensity adjustments': [
        'Use L unless a category preference applies.',
        'Apply 100 adjustments across 73 terms, including the five earlier calibrations.',
        'New rules orient |L|; zero uses 0.25. Firm bedding is neutral.',
        'Use the selected sense rule and degree weight: slightly 0.75, very 1.25, extremely 1.5.',
        'Keep original P/N, L, domain score, rule/reason and multiplier visible; score is not confidence.',
    ],
    'Shared controlled vocabulary and resource checks': [
        'Supply six categories, 345 aspect phrases, 356 opinions, 32 aliases, grammar, compatibility and modifier/context rules; configure default/category senses, including fresh.',
        'Package 315 genuine SentiWordNet rows; verify checksum and lemma/sense membership. Curated catalog uses first adjective rank or explicit overrides; export opinion_senses.csv audit.',
    ],
    'Diagnostics and compiler trace across stages': [
        'Retain input/syntax/semantic diagnostics by row/span; recover valid clauses while unknown language remains visible.',
        'Expose tokens, AST with retained context, semantic records, source/domain scoring evidence and IR; open each review independently.',
    ],
}


def paragraph_text(paragraph):
    return ''.join(paragraph.itertext())


def replace_text(paragraph, text):
    nodes = paragraph.findall('.//w:t', NS)
    if not nodes:
        raise ValueError('Expected existing editable text in paragraph.')
    nodes[0].text = text
    nodes[0].set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
    for node in nodes[1:]:
        node.text = ''


def update():
    original_hash = sha256(SOURCE.read_bytes()).hexdigest()
    with ZipFile(SOURCE) as source:
        root = etree.fromstring(source.read('word/document.xml'))
        found = {key: 0 for key in UPDATES}
        for box in root.findall('.//w:txbxContent', NS):
            paragraphs = box.findall('w:p', NS)
            title = paragraph_text(paragraphs[0])
            if title not in UPDATES:
                continue
            bullets = UPDATES[title]
            while len(paragraphs) < len(bullets) + 2:
                new_paragraph = deepcopy(paragraphs[-2])
                box.insert(box.index(paragraphs[-1]), new_paragraph)
                paragraphs = box.findall('w:p', NS)
            assert len(paragraphs) == len(bullets) + 2, (title, len(paragraphs))
            for paragraph, text in zip(paragraphs[1:-1], bullets):
                replace_text(paragraph, text)
            found[title] += 1
        # Word supplies both modern DrawingML and editable VML fallback text boxes.
        assert all(count == 2 for count in found.values()), found
        for paragraph in root.findall('./w:body/w:p', NS):
            text = paragraph_text(paragraph)
            if text.startswith('Team 17   Page '):
                nodes = paragraph.findall('.//w:t', NS)
                if nodes:
                    replace_text(paragraph, text + '   Updated 14 October 2026')
        xml = etree.tostring(root, encoding='UTF-8', xml_declaration=True, standalone=True)
        with ZipFile(OUTPUT, 'w') as output:
            for entry in source.infolist():
                output.writestr(entry, xml if entry.filename == 'word/document.xml' else source.read(entry.filename))
    assert sha256(SOURCE.read_bytes()).hexdigest() == original_hash
    with ZipFile(SOURCE) as source, ZipFile(OUTPUT) as output:
        assert source.namelist() == output.namelist()
        for name in source.namelist():
            if name != 'word/document.xml':
                assert source.read(name) == output.read(name), name
        assert not any(name.startswith('word/media/') for name in output.namelist())
    print(f'Updated {len(UPDATES)} blocks in both native editable representations. All other package parts unchanged.')
    print(OUTPUT)


if __name__ == '__main__':
    update()
