"""Structural and measured-value audit, supplementary to visual page review."""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from hashlib import sha256
import csv
import json
import re
from docx import Document
from docx.oxml.ns import qn
import pdfplumber

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/paper'
RUN=ROOT/'output/experiments/2026-10-21/hybrid-vocabulary-paper'
VOCAB=ROOT/'output/experiments/2026-10-18/booking-vocabulary/report'


def load(path):
    with path.open(encoding='utf-8-sig',newline='') as h:return list(csv.DictReader(h))


def main():
    path=OUT/'Team_17_IEEE_Conference_Paper.docx';doc=Document(path)
    paragraphs=[p.text for p in doc.paragraphs];text='\n'.join(paragraphs)
    reference_lines=[p for p in paragraphs if re.match(r'^\[\d+\]  ',p)]
    assert len(reference_lines)==33
    assert [int(re.match(r'\[(\d+)\]',p).group(1)) for p in reference_lines]==list(range(1,34))
    body=text.split('REFERENCES')[0]
    first=[]
    for value in re.findall(r'\[(\d+)\]',body):
        if int(value) not in first:first.append(int(value))
    assert first==list(range(1,34)),first
    assert len(doc.inline_shapes)==8
    assert len(doc.tables)==4
    assert sum(p.startswith('Algorithm ') for p in paragraphs)==4
    assert sum(p.startswith('Fig. ') for p in paragraphs)==8
    assert len(doc.element.xpath('.//m:oMath'))==4
    assert doc.styles['Normal'].font.size.pt==10
    assert doc.styles['Title'].font.size.pt==24
    assert doc.styles['Normal'].font.name=='Times New Roman'
    assert any(s._sectPr.find(qn('w:cols')).get(qn('w:num'))=='2' for s in doc.sections)
    assert 'Tanay Mohta and Aditya Rawat' in text
    assert not any(token in text for token in ['{{','TBD','YOUR NAME','uploaded'])
    metrics=load(RUN/'semeval-development/metrics.csv')
    table_text='\n'.join(c.text for t in doc.tables for r in t.rows for c in r.cells)
    for row in metrics:
        assert f'{100*float(row["accuracy"]):.2f}%' in table_text
        for key in ['macro_f1','tuple_precision','tuple_recall','tuple_f1']:assert f'{float(row[key]):.4f}' in table_text
    assert '85/148' in table_text.replace(' ','')
    vocab=load(VOCAB/'coverage_comparison.csv')
    for measure in ['Aspect phrases','Reviewed lexical forms','Reviews with at least one scored aspect','Complete processing','Partial processing','Unsupported processing','Scored contexts','Adjective occurrences without lexical lookup support']:
        row=next(r for r in vocab if r['measure']==measure)
        for key in ['before','after']:assert f'{int(row[key]):,}' in table_text
    with pdfplumber.open(OUT/'Team_17_IEEE_Conference_Paper.pdf') as pdf:
        pages=len(pdf.pages);assert 8<=pages<=12,pages
        fonts=sorted({c['fontname'] for p in pdf.pages for c in p.chars})
        assert all('TimesNewRoman' in f or 'CambriaMath' in f for f in fonts),fonts
        assert all(not any(c['x0']<32 or c['x1']>565 or c['top']<45 or c['bottom']>725 for c in p.chars) for p in pdf.pages)
    page_dir=ROOT/'tmp/paper-qa-2026-10-21'
    assert len(list(page_dir.glob('page-*.png')))==pages
    audit={'updated':'2026-10-21','pages':pages,'research_works':30,'total_references':33,'pseudocode_algorithms':4,
           'architecture_diagrams':4,'measured_charts':4,'tables':4,'native_math_equations':4,
           'reference_order':'all 33 cited in first-appearance order',
           'metric_table':'matches saved development metric CSV',
           'author_details':'two supplied names; affiliations/emails intentionally omitted until supplied',
           'evaluation_scope':'development/exploratory; not untouched holdout',
           'rendering':'Microsoft Word 16 native export plus canonical DOCX skill rasterizer',
           'visual_review':f'all {pages} final rendered pages inspected; final reference page balanced',
           'experiment_root':str(RUN.relative_to(ROOT)),
           'booking_vocabulary_evidence':str(VOCAB.relative_to(ROOT)),
           'results':{r['system']:{key:r[key] for key in ['cases','correct','accuracy','macro_f1','tuple_f1']} for r in metrics},
           'prior_version':'archive/pre-vocabulary-update-2026-10-21.zip',
           'fonts':fonts,
           'sha256':{p.name:sha256(p.read_bytes()).hexdigest() for p in [path,OUT/'Team_17_IEEE_Conference_Paper.pdf']}}
    (OUT/'paper_audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    with ZipFile(OUT/'Team_17_Paper_Figures_and_Tables.zip','w',compression=ZIP_DEFLATED) as archive:
        for asset in sorted((OUT/'assets').iterdir()):
            if asset.suffix in {'.svg','.pdf','.png'}:archive.write(asset,'figures/'+asset.name)
        for directory,names in {
            'semeval-development':['metrics.csv','per_class_metrics.csv','dataset_description.csv','annotation_scope.csv','excluded_annotations.csv'],
            'demo100':['coverage.csv','dataset_description.csv'],
            'random200':['coverage.csv','dataset_description.csv','runtime_summary.csv','runtime_runs.csv'],
        }.items():
            for name in names:archive.write(RUN/directory/name,f'tables/{directory}/{name}')
        archive.write(OUT/'references.json','references.json')
        archive.write(OUT/'PAPER_README.md','README.md')
        archive.write(OUT/'paper_audit.json','paper_audit.json')
        for name in ['coverage_comparison.csv','lexical_catalog.csv','added_aspect_phrases.csv']:
            archive.write(VOCAB/name,'tables/booking-vocabulary/'+name)
        archive.write(ROOT/'output/experiments/2026-10-15/independent-hybrid-v2/semeval-development/metrics.csv','tables/prior-hybrid/metrics.csv')
    print(json.dumps({k:v for k,v in audit.items() if k not in {'fonts','sha256'}},indent=2))


if __name__=='__main__':main()
