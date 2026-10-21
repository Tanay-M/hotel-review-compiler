"""Build editable IEEE-style Word manuscript from reviewed prose and saved metrics.

Run with the Codex bundled Python. No analysis scores are recomputed here.
"""
from pathlib import Path
from copy import deepcopy
import csv
import json
import re
from zipfile import ZipFile, ZIP_DEFLATED
from docx import Document
from docx.enum.section import WD_SECTION_START
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Mm, Pt, RGBColor

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output'/'paper'
RUN=ROOT/'output'/'experiments'/'2026-10-21'/'hybrid-vocabulary-paper'
VOCAB=ROOT/'output/experiments/2026-10-18/booking-vocabulary/report'
ASSETS=OUT/'assets'
NAME='Team_17_IEEE_Conference_Paper'


def read_csv(path):
    with path.open(encoding='utf-8-sig',newline='') as h:return list(csv.DictReader(h))


ACL_ORDER={2:'W02-1011',3:'L10-1531',6:'S15-2082',7:'P97-1023',8:'P02-1053',9:'H05-1044',
           10:'J11-2001',11:'L06-1225',12:'S13-2053',13:'S16-1004',14:'D17-1058',15:'J11-1002',
           16:'W03-1014',17:'S14-2004',18:'S16-1002',19:'C16-1311',20:'D16-1058',21:'D16-1059',
           22:'P18-1234',23:'D19-1464',24:'N19-1035',25:'N19-1242',26:'P04-1035',27:'D13-1170',28:'D14-1181'}
VENUES={'W02-1011':'Proc. EMNLP','L10-1531':'Proc. LREC','S15-2082':'Proc. SemEval',
        'P97-1023':'Proc. ACL-EACL','P02-1053':'Proc. ACL','H05-1044':'Proc. HLT-EMNLP',
        'L06-1225':'Proc. LREC','S13-2053':'Proc. *SEM, vol. 2: SemEval',
        'S16-1004':'Proc. SemEval','D17-1058':'Proc. EMNLP','W03-1014':'Proc. EMNLP',
        'S14-2004':'Proc. SemEval','S16-1002':'Proc. SemEval','C16-1311':'Proc. COLING',
        'D16-1058':'Proc. EMNLP','D16-1059':'Proc. EMNLP','P18-1234':'Proc. ACL',
        'D19-1464':'Proc. EMNLP-IJCNLP','N19-1035':'Proc. NAACL-HLT','N19-1242':'Proc. NAACL-HLT',
        'P04-1035':'Proc. ACL','D13-1170':'Proc. EMNLP','D14-1181':'Proc. EMNLP'}


def author_name(name):
    name=re.sub(r'\s*\([^)]*\)','',name)
    parts=name.split()
    return ' '.join(p[0]+'.' for p in parts[:-1])+' '+parts[-1]


def bibliography():
    refs={
      1:'M. Hu and B. Liu, “Mining and summarizing customer reviews,” in Proc. ACM SIGKDD, 2004, pp. 168–177, doi: 10.1145/1014052.1014073.',
      4:'C. J. Hutto and E. Gilbert, “VADER: A parsimonious rule-based model for sentiment analysis of social media text,” Proc. ICWSM, vol. 8, no. 1, pp. 216–225, 2014, doi: 10.1609/icwsm.v8i1.14550.',
      5:'T. De Smedt and W. Daelemans, “Pattern for Python,” J. Mach. Learn. Res., vol. 13, pp. 2063–2067, 2012.',
      29:'W. Zhang, X. Li, Y. Deng, L. Bing, and W. Lam, “A survey on aspect-based sentiment analysis: Tasks, methods, and challenges,” IEEE Trans. Knowl. Data Eng., vol. 35, no. 11, pp. 11019–11038, 2023, doi: 10.1109/TKDE.2022.3230975.',
      30:'S. U. S. Chebolu, F. Dernoncourt, N. Lipka, and T. Solorio, “Survey of aspect-based sentiment analysis datasets,” arXiv preprint arXiv:2204.05232, 2022. [Online]. Available: https://arxiv.org/abs/2204.05232',
      31:'TextBlob contributors, “TextBlob 0.19.0 documentation,” accessed Oct. 15, 2026. [Online]. Available: https://textblob.readthedocs.io/en/stable/',
      32:'J. Liu, “515K hotel reviews data in Europe,” Kaggle dataset, accessed Oct. 15, 2026. [Online]. Available: https://www.kaggle.com/datasets/jiashenliu/515k-hotel-reviews-data-in-europe',
      33:'Crawlfeeds, “Booking Italy hotel reviews,” user-supplied CSV export, received Oct. 18, 2026. Source file and SHA-256 retained in the project provenance archive.',
    }
    for number,identifier in ACL_ORDER.items():
        source=json.loads((OUT/'sources'/f'{identifier}.json').read_text(encoding='utf-8'));m=source['metadata']
        names=m['citation_author']
        if identifier=='D16-1058':names=['Yequan Wang','Minlie Huang','Li Zhao','Xiaoyan Zhu']  # PDF author order.
        if identifier=='P97-1023':names=['Vasileios Hatzivassiloglou','Kathleen R. McKeown']
        if identifier=='P02-1053':names=['Peter D. Turney']
        if identifier=='D13-1170':names=['Richard Socher','Alex Perelygin','Jean Y. Wu','Jason Chuang','Christopher D. Manning','Andrew Y. Ng','Christopher Potts']
        authors=[author_name(n) for n in names]
        people=(authors[0]+' et al.' if len(authors)>6 else ', '.join(authors[:-1])+', and '+authors[-1] if len(authors)>2 else ' and '.join(authors))
        title=m['citation_title'][0];year=m['citation_publication_date'][0].split('/')[0]
        if 'citation_journal_title' in m:
            venue=f'Comput. Linguist., vol. {m["citation_volume"][0]}, no. {m["citation_issue"][0]}, pp. {m["citation_firstpage"][0]}–{m["citation_lastpage"][0]}, {year}'
        else:
            venue=f'in {VENUES[identifier]}, {year}'
            if 'citation_firstpage' in m:venue+=f', pp. {m["citation_firstpage"][0]}–{m["citation_lastpage"][0]}'
        text=f'{people}, “{title},” {venue}'
        if 'citation_doi' in m:text+=', doi: '+m['citation_doi'][0]
        else:text+='. [Online]. Available: '+source['url']
        refs[number]=text.rstrip('.')+'.'
    assert set(refs)==set(range(1,34))
    return refs


ALGORITHMS={
1:('Source preserving preprocessing',[
 'Input: review text or CSV records; size limits',
 'Output: retained rows, original text, validation issues',
 'Decode UTF-8; map serial ID and review fields.',
 'For each record r:',
 '    Retain row identity and exact original review.',
 '    Check headers, field count, blank text and length.',
 '    Record duplicate flags without dropping r.',
 '    If invalid: preserve r with its validation issues.',
 '    Else: send the original review to both methods.',
 'Return every submitted row and its evidence.'
]),
2:('Independent grammatical aspect attachment',[
 'Input: original review x; merged aspect dictionary A',
 'Output: aspect contexts C and linguistic diagnostics',
 'Expand contractions in a source-mapped working copy.',
 'Run PatternParser; retain POS and phrase chunks.',
 'Longest-match A; split contrasts and predicates.',
 'For each segment s:',
 '    Find adjectives and lexical opinion candidates.',
 '    Exclude Price/Location topics; retain diagnostics.',
 '    Attach attributive opinions forward to nouns.',
 '    Attach predicates backward; verb opinions to objects.',
 '    Share coordinated targets only under valid patterns.',
 '    Inherit only safe shared or unique pronoun targets.',
 '    Retain unresolved predicates without inventing scores.',
 '    Emit original contexts, target spans and rule names.',
 'Return C and all unresolved/scope diagnostics.'
]),
3:('Evidence aware hybrid sentiment',[
 'Input: aspect context x, category c, weight w = 0.5',
 'Output: native/effective evidence, fusion L and final H',
 'Run native VADER(x) and PatternAnalyzer(x); retain both.',
 'If either fails: return unavailable with component error.',
 'Set x* = x; find reviewed lexical aliases allowed for c.',
 'Replace native-unknown matches in scoring copy x* only.',
 'If x* differs: rescore both; preserve source-span matches.',
 'If rescoring fails: return unavailable with component error.',
 'Determine lexical-evidence flags eV and eT.',
 'If both flags: L = w*V.compound + (1-w)*T.polarity.',
 'Else if one flag: L = that supported component score.',
 'Else: L = unavailable.',
 'H = L; find applicable category-context rules.',
 'If rule signs agree: H = first configured rule score.',
 'Retain x, x*, native/effective V, T, L, H and rule.',
 'Retain assessments and subjectivity; do not infer confidence.',
 'Assign descriptive polarity and strength; return evidence.'
]),
4:('Review synthesis and comparable evaluation',[
 'Input: each method’s opinions and optional human labels',
 'Output: review rows, traces, metrics and paper artifacts',
 'For each method and review independently:',
 '    Preserve opinions, missing scores and diagnostics.',
 '    Set Mixed when positive and negative coexist.',
 '    Compute mean only under the method’s score policy.',
 '    Keep whole-text sentiment separate from aspect mean.',
 'Export one review row and separate method opinion rows.',
 'If gold labels exist: apply the declared category mapping.',
 '    Count missing/Mixed classification cases as errors.',
 '    Compute accuracy, class F1 and coarse tuple metrics.',
 'Else: export coverage without accuracy claims.',
 'Save source/code hashes, environment, tables and figures.'
])}


def font(run,size=None,bold=None,italic=None):
    run.font.name='Times New Roman';run.font.color.rgb=RGBColor(0,0,0)
    run._element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),'Times New Roman')
    if size:run.font.size=Pt(size)
    if bold is not None:run.bold=bold
    if italic is not None:run.italic=italic


def setup(doc):
    section=doc.sections[0]
    section.page_width=Mm(210);section.page_height=Mm(297)
    section.top_margin=Mm(19);section.bottom_margin=Mm(43)
    section.left_margin=Mm(13);section.right_margin=Mm(13)
    section.header_distance=Mm(8);section.footer_distance=Mm(8)
    style=doc.styles['Normal'];style.font.name='Times New Roman';style.font.size=Pt(10);style.font.color.rgb=RGBColor(0,0,0)
    fmt=style.paragraph_format;fmt.first_line_indent=Inches(.14);fmt.space_after=Pt(0);fmt.space_before=Pt(0);fmt.line_spacing=1
    fmt.widow_control=True
    for name in ['Title','Subtitle','Heading 1','Heading 2','Caption']:
        s=doc.styles[name];s.font.name='Times New Roman';s.font.color.rgb=RGBColor(0,0,0)
        s.paragraph_format.first_line_indent=Pt(0)
    for name in ['Normal','Title','Subtitle','Heading 1','Heading 2','Caption']:
        fonts=doc.styles[name].element.get_or_add_rPr().get_or_add_rFonts()
        for attribute in list(fonts.attrib):
            if 'theme' in attribute.lower():del fonts.attrib[attribute]
        for attribute in ['ascii','hAnsi','eastAsia','cs']:fonts.set(qn('w:'+attribute),'Times New Roman')
    s=doc.styles['Title'];s.font.size=Pt(24);s.font.bold=False;s.paragraph_format.alignment=WD_ALIGN_PARAGRAPH.CENTER;s.paragraph_format.space_after=Pt(9);s.paragraph_format.line_spacing=1
    s=doc.styles['Heading 1'];s.font.size=Pt(10);s.font.bold=False;s.font.small_caps=True;s.paragraph_format.alignment=WD_ALIGN_PARAGRAPH.CENTER;s.paragraph_format.space_before=Pt(8);s.paragraph_format.space_after=Pt(4)
    s=doc.styles['Heading 2'];s.font.size=Pt(10);s.font.bold=False;s.font.italic=True;s.paragraph_format.space_before=Pt(6);s.paragraph_format.space_after=Pt(3)
    for name in ['Heading 1','Heading 2']:doc.styles[name].paragraph_format.keep_with_next=True
    s=doc.styles['Caption'];s.font.size=Pt(8);s.font.bold=False;s.font.italic=False;s.paragraph_format.space_before=Pt(3);s.paragraph_format.space_after=Pt(6);s.paragraph_format.line_spacing=1
    # Do not inherit theme title borders, decorative rules, headers or footers.
    for name in ['Title','Subtitle','Heading 1','Heading 2']:
        ppr=doc.styles[name].element.find(qn('w:pPr'))
        if ppr is not None:
            for el in list(ppr):
                if el.tag==qn('w:pBdr'):ppr.remove(el)
    doc.core_properties.title='An Auditable Grammar Assisted Hybrid for Aspect Sentiment Analysis of Hotel Reviews'
    doc.core_properties.author='Tanay Mohta and Aditya Rawat'
    doc.core_properties.subject='Compiler design project and development evaluation'
    doc.core_properties.keywords='hotel reviews, aspect sentiment, SentiWordNet, VADER, TextBlob'
    settings=doc.settings.element
    compat=OxmlElement('w:doNotHyphenateCaps');settings.append(compat)


def paragraph(doc,text='',**options):
    p=doc.add_paragraph();p.add_run(text)
    for run in p.runs:font(run)
    for k,v in options.items():setattr(p.paragraph_format,k,v)
    return p


def algorithm(doc,number):
    title,lines=ALGORITHMS[number]
    p=paragraph(doc,f'Algorithm {number}  {title}',first_line_indent=Pt(0),space_before=Pt(6),space_after=Pt(3),keep_with_next=True)
    for r in p.runs:font(r,8.5,True)
    for i,line in enumerate(lines,1):
        p=paragraph(doc,f'{i:02d}  '+line,first_line_indent=Pt(0),space_after=Pt(0),keep_with_next=i<len(lines),keep_together=True)
        p.paragraph_format.line_spacing=Pt(9.3)
        for r in p.runs:font(r,8.3)
    p.paragraph_format.space_after=Pt(6)


def image(doc,name,caption):
    p=doc.add_paragraph();p.paragraph_format.first_line_indent=Pt(0);p.paragraph_format.space_before=Pt(6);p.paragraph_format.space_after=Pt(0);p.paragraph_format.keep_with_next=True;p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    run=p.add_run();run.add_picture(str(ASSETS/f'{name}.png'),width=Inches(3.45))
    run._r.xpath('.//wp:docPr')[0].set('descr',caption)
    p=doc.add_paragraph(caption,'Caption');p.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY;p.paragraph_format.keep_together=True


def table(doc,key):
    metrics=read_csv(RUN/'semeval-development'/'metrics.csv')
    classes=read_csv(RUN/'semeval-development'/'per_class_metrics.csv')
    if key=='datasets':
        caption='TABLE I\nEXPERIMENTAL COHORTS AND AVAILABLE LABELS'
        headers=['Cohort','Size','Label and role']
        rows=[['Booking curated','100 reviews','No aspect gold; supported-language demo'],
              ['Booking random','200 reviews','No aspect gold; coverage and runtime'],
              ['SemEval Hotels','30 reviews\n266 sentences','Human opinions; 148 mapped classification cases'],
              ['Booking Italy','4,367 rows\n3,102 bodies','No aspect gold; vocabulary development']]
        widths=[1.02,.73,1.70]
    elif key=='vocabulary':
        caption='TABLE II\nVOCABULARY DEVELOPMENT ON BOOKING ITALY'
        headers=['Measure','Before','Expanded'];rows=[]
        data={r['measure']:r for r in read_csv(VOCAB/'coverage_comparison.csv')}
        for key_,label in [('Aspect phrases','Aspect phrases'),('Reviewed lexical forms','Reviewed lexical forms'),('Reviews with at least one scored aspect','Bodies with scored aspects'),('Complete processing','Complete bodies'),('Partial processing','Partial bodies'),('Unsupported processing','Unsupported bodies'),('Scored contexts','Scored contexts'),('Adjective occurrences without lexical lookup support','Unsupported adjective occurrences')]:
            row=data[key_];rows.append([label,f'{int(row["before"]):,}',f'{int(row["after"]):,}'])
        widths=[1.65,.90,.90]
    elif key=='metrics':
        caption='TABLE III\nEND TO END DEVELOPMENT COMPARISON'
        headers=['Measure','SentiWordNet','Hybrid']
        s,h=metrics
        pct=lambda v:f'{100*float(v):.2f}%'
        rows=[['Correct / eligible',f'{s["correct"]} / {s["cases"]}',f'{h["correct"]} / {h["cases"]}'],
              ['All-case accuracy',pct(s['accuracy']),pct(h['accuracy'])],
              ['95% cluster interval',f'{100*float(s["accuracy_ci95_low"]):.2f}–{100*float(s["accuracy_ci95_high"]):.2f}%',f'{100*float(h["accuracy_ci95_low"]):.2f}–{100*float(h["accuracy_ci95_high"]):.2f}%'],
              ['Classification coverage',f'{s["scored"]}/148\n{pct(s["coverage"])}',f'{h["scored"]}/148\n{pct(h["coverage"])}'],
              ['Conditional accuracy',pct(s['conditional_accuracy']),pct(h['conditional_accuracy'])],
              ['Macro-F1',f'{float(s["macro_f1"]):.4f}',f'{float(h["macro_f1"]):.4f}']]
        for label,k in [('Tuple precision','tuple_precision'),('Tuple recall','tuple_recall'),('Tuple-F1','tuple_f1')]:rows.append([label,f'{float(s[k]):.4f}',f'{float(h[k]):.4f}'])
        widths=[1.45,1,1]
    elif key=='classes':
        caption='TABLE IV\nCLASS SUPPORT AND F1 ON THE MAPPED SCOPE'
        headers=['Class','Support','SWN F1','Hybrid F1'];rows=[]
        for label in ['Negative','Neutral','Positive']:
            s,h=[r for r in classes if r['label']==label]
            rows.append([label,s['support'],f'{float(s["f1"]):.4f}',f'{float(h["f1"]):.4f}'])
        widths=[.88,.56,1.0,1.01]
    else:raise ValueError(key)
    p=paragraph(doc,caption,first_line_indent=Pt(0),space_before=Pt(6),space_after=Pt(3),keep_with_next=True)
    p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    for r in p.runs:font(r,8)
    t=doc.add_table(rows=1,cols=len(headers));t.alignment=WD_TABLE_ALIGNMENT.CENTER;t.autofit=False
    for col,w in zip(t.columns,widths):col.width=Inches(w)
    for i,label in enumerate(headers):t.cell(0,i).text=label
    for data in rows:
        cells=t.add_row().cells
        for cell,value in zip(cells,data):cell.text=value
    pr=t._tbl.tblPr;borders=OxmlElement('w:tblBorders')
    for side in ['top','left','bottom','right','insideH','insideV']:
        edge=OxmlElement('w:'+side);edge.set(qn('w:val'),'single');edge.set(qn('w:sz'),'4');edge.set(qn('w:color'),'D9D9D9');borders.append(edge)
    pr.append(borders)
    for ri,row in enumerate(t.rows):
        row._tr.get_or_add_trPr().append(OxmlElement('w:cantSplit'))
        if ri==0:row._tr.get_or_add_trPr().append(OxmlElement('w:tblHeader'))
        for ci,cell in enumerate(row.cells):
            cell.width=Inches(widths[ci]);cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            tcpr=cell._tc.get_or_add_tcPr();margins=OxmlElement('w:tcMar')
            for side,n in [('top',35),('bottom',35),('left',45),('right',45)]:
                node=OxmlElement('w:'+side);node.set(qn('w:w'),str(n));node.set(qn('w:type'),'dxa');margins.append(node)
            tcpr.append(margins)
            if ri==0:
                shade=OxmlElement('w:shd');shade.set(qn('w:fill'),'F2F2F2');tcpr.append(shade)
            for p in cell.paragraphs:
                p.paragraph_format.first_line_indent=Pt(0);p.paragraph_format.space_after=Pt(0);p.paragraph_format.line_spacing=1
                p.paragraph_format.keep_with_next=ri<len(t.rows)-1
                p.alignment=WD_ALIGN_PARAGRAPH.LEFT if ci==0 or key=='datasets' else WD_ALIGN_PARAGRAPH.CENTER
                for r in p.runs:font(r,8,bold=ri==0)
    spacer=doc.add_paragraph();spacer.paragraph_format.space_after=Pt(3);spacer.paragraph_format.line_spacing=Pt(2)


def mr(text):
    r=OxmlElement('m:r');pr=OxmlElement('m:rPr');sty=OxmlElement('m:sty');sty.set(qn('m:val'),'p');pr.append(sty);r.append(pr)
    rp=OxmlElement('w:rPr');fonts=OxmlElement('w:rFonts');fonts.set(qn('w:ascii'),'Cambria Math');fonts.set(qn('w:hAnsi'),'Cambria Math');rp.append(fonts);sz=OxmlElement('w:sz');sz.set(qn('w:val'),'19');rp.append(sz);r.append(rp)
    t=OxmlElement('m:t');t.text=text;r.append(t);return r


def sub(base,index):
    el=OxmlElement('m:sSub');e=OxmlElement('m:e');e.append(mr(base));s=OxmlElement('m:sub');s.append(mr(index));el.extend([e,s]);return el


def frac(numerator,denominator):
    el=OxmlElement('m:f');n=OxmlElement('m:num');d=OxmlElement('m:den')
    for item in numerator:n.append(item)
    for item in denominator:d.append(item)
    el.extend([n,d]);return el


def equation(doc,key):
    p=doc.add_paragraph();p.paragraph_format.first_line_indent=Pt(0);p.paragraph_format.space_before=Pt(5);p.paragraph_format.space_after=Pt(5);p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    math=OxmlElement('m:oMath')
    if key=='baseline':items=[sub('s','SWN'),mr(' = clip(D · m · n, −1, 1)')];number=1
    elif key=='fusion':
        items=[sub('L','h'),mr('(x) = '),frac([mr('w '),sub('e','V'),mr(' V + (1 − w) '),sub('e','T'),mr(' T')],[mr('w '),sub('e','V'),mr(' + (1 − w) '),sub('e','T')])];number=2
    elif key=='mean':
        n=OxmlElement('m:nary');pr=OxmlElement('m:naryPr');ch=OxmlElement('m:chr');ch.set(qn('m:val'),'∑');pr.append(ch);n.append(pr)
        for tag,content in [('sub',mr('j = 1')),('sup',sub('m','i')),('e',sub('H','ij'))]:node=OxmlElement('m:'+tag);node.append(content);n.append(node)
        items=[sub('R','i'),mr(' = '),frac([mr('1')],[sub('m','i')]),n];number=3
    else:
        items=[mr('Accuracy = '),frac([mr('C')],[mr('N')]),mr('   Coverage = '),frac([mr('S')],[mr('N')])];number=4
    for item in items:math.append(item)
    p._p.append(math);run=p.add_run(f'    ({number})');font(run,9)


def build():
    OUT.mkdir(parents=True,exist_ok=True);doc=Document();setup(doc)
    raw=(ROOT/'docs'/'conference_manuscript.md').read_text(encoding='utf-8')
    blocks=[b.strip() for b in raw.split('\n\n') if b.strip()]
    title=blocks.pop(0)[2:];authors=blocks.pop(0).replace('Authors: ','')
    doc.add_paragraph(title,'Title')
    p=paragraph(doc,authors,first_line_indent=Pt(0),space_after=Pt(9));p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    for r in p.runs:font(r,11)
    section=doc.add_section(WD_SECTION_START.CONTINUOUS)
    cols=section._sectPr.find(qn('w:cols'));cols.set(qn('w:num'),'2');cols.set(qn('w:space'),'360')
    cols.set(qn('w:equalWidth'),'1')
    abstract=False;refs=bibliography()
    for block in blocks:
        if block=='## Abstract':abstract=True;continue
        if block.startswith('## '):doc.add_paragraph(block[3:].upper(),'Heading 1');continue
        if block.startswith('### '):doc.add_paragraph(block[4:],'Heading 2');continue
        if block.startswith('{{FIG:'):
            name,caption=block[6:-2].split('|',1);image(doc,name,caption);continue
        if block.startswith('{{ALG:'):algorithm(doc,int(block[6:-2]));continue
        if block.startswith('{{TABLE:'):table(doc,block[8:-2]);continue
        if block.startswith('{{EQ:'):equation(doc,block[5:-2]);continue
        if block=='{{REFERENCES}}':
            for number,text in refs.items():
                p=paragraph(doc,f'[{number}]  {text}',first_line_indent=Inches(-.19),left_indent=Inches(.19),space_after=Pt(2),keep_together=True)
                p.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
                for r in p.runs:font(r,8)
            continue
        if abstract:
            p=paragraph(doc,'Abstract—'+block,first_line_indent=Pt(0),space_after=Pt(5))
            for r in p.runs:font(r,9,True)
            abstract=False;continue
        if block.startswith('Keywords:'):
            p=paragraph(doc,block.replace('Keywords:','Index Terms—'),first_line_indent=Pt(0),space_after=Pt(5))
            for r in p.runs:font(r,9,True,True)
            continue
        paragraph(doc,block.replace('\n',' '))
    # References must be numbered in citation order, not dict insertion order.
    # Rearrange the generated trailing bibliography deterministically.
    ref_paragraphs=[p for p in doc.paragraphs if re.match(r'^\[\d+\]  ',p.text)]
    sorted_elements=[deepcopy(p._p) for p in sorted(ref_paragraphs,key=lambda p:int(re.match(r'^\[(\d+)\]',p.text).group(1)))]
    if ref_paragraphs:
        parent=ref_paragraphs[0]._p.getparent();idx=parent.index(ref_paragraphs[0]._p)
        for p in ref_paragraphs:parent.remove(p._p)
        for offset,element in enumerate(sorted_elements):parent.insert(idx+offset,element)
    # Closing the body with a continuous section lets Word balance the final
    # reference page instead of filling one column and leaving the other empty.
    ending=doc.add_section(WD_SECTION_START.CONTINUOUS)
    ending._sectPr.find(qn('w:cols')).set(qn('w:num'),'1')
    path=OUT/f'{NAME}.docx';doc.save(path)
    (OUT/'references.json').write_text(json.dumps({n:refs[n] for n in sorted(refs)},ensure_ascii=False,indent=2),encoding='utf-8')
    (OUT/'manuscript_source.md').write_text(raw.replace('{{REFERENCES}}','\n\n'.join(f'[{n}] {refs[n]}' for n in sorted(refs))),encoding='utf-8')
    print(f'Word manuscript: {path}')
    print(f'33 references, 4 algorithms, 8 figures, 4 tables; {len(raw.split())} prose/source words before references and algorithms.')


if __name__=='__main__':build()
