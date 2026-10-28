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
RUN=ROOT/'output'/'experiments'/'2026-10-21'/'expanded-sentiwordnet-release'
VOCAB=ROOT/'output/experiments/2026-10-18/booking-vocabulary/report'
ASSETS=OUT/'assets'
NAME='Team_17_IEEE_Conference_Paper'
DL=ROOT/'output/neural/2026-10-23-dl-pair-evaluation'
DL_RUN=ROOT/'output/neural/2026-10-23-dl-pair-human-v1'


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
      31:'W. Wang, F. Wei, L. Dong, H. Bao, N. Yang, and M. Zhou, “MiniLM: Deep self-attention distillation for task-agnostic compression of pre-trained transformers,” arXiv preprint arXiv:2002.10957, 2020. [Online]. Available: https://arxiv.org/abs/2002.10957',
      32:'S. M. Jiménez Zafra, G. Berardi, A. Esuli, D. Marcheggiani, M. T. Martín-Valdivia, and A. Moreo Fernández, “A multi-lingual annotated dataset for aspect-oriented opinion mining,” in Proc. EMNLP, 2015, pp. 2533–2538, doi: 10.18653/v1/D15-1302.',
      33:'TextBlob contributors, “TextBlob 0.19.0 documentation,” accessed Oct. 15, 2026. [Online]. Available: https://textblob.readthedocs.io/en/stable/',
      34:'J. Liu, “515K hotel reviews data in Europe,” Kaggle dataset, accessed Oct. 15, 2026. [Online]. Available: https://www.kaggle.com/datasets/jiashenliu/515k-hotel-reviews-data-in-europe',
      35:'Crawlfeeds, “Booking Hotel Reviews Dataset: Booking Italy hotel reviews,” Hugging Face dataset, CC BY-NC 4.0, accessed Oct. 21, 2026. [Online]. Available: https://huggingface.co/datasets/crawlfeeds/Booking-Hotel-Reviews-Dataset',
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
    assert set(refs)==set(range(1,36))
    return refs


ALGORITHMS={
1:('Preprocessing and Validation',[
 'Input: data X; limits Λ',
 'Output: records R',
 'R ← ∅',
 'for each r ∈ Decode(X) do',
 '    (id, x) ← Extract(r)',
 '    d ← Validate(r, Λ)',
 '    b ← IsDuplicate(x, R)',
 '    R ← R ∪ {(id, x, d, b)}',
 'end for',
 'return R'
]),
2:('Aspect–Opinion Extraction',[
 'Input: review x',
 'Output: candidates Cₛ, Cₕ',
 'T ← TokenizeAndMatch(x)',
 'A ← ParseAndRecover(T)',
 'Cₛ ← ResolveTargets(A)',
 'P ← PatternParser(x)',
 'Q ← SegmentAndMatch(P)',
 'Cₕ ← AttachOpinions(Q)',
 'return Cₛ, Cₕ'
]),
3:('Sentiment Scoring',[
 'Input: candidates Cₛ, Cₕ',
 'Output: scored opinions Oₛ, Oₕ',
 'Oₛ ← ∅; Oₕ ← ∅',
 'for each c ∈ Cₛ do',
 '    (P, N) ← SenseScores(c)',
 '    D ← DomainRule(c, P − N)',
 '    s ← clip(D × Degree(c) × Negation(c))',
 '    Oₛ[c] ← (s, Band(s))',
 'end for',
 'for each c ∈ Cₕ do',
 '    x* ← AliasCopy(c)',
 '    (V, T, eV, eT) ← ScoreBoth(x*)',
 '    f ← Fuse(V, T, eV, eT)',
 '    s ← ContextRule(c, f)',
 '    Oₕ[c] ← (s, Band(s))',
 'end for',
 'return Oₛ, Oₕ'
]),
4:('Aggregation and Evaluation',[
 'Input: opinions O; diagnostics Δ; optional gold G',
 'Output: results R; metrics M',
 'R ← ∅',
 'for each method m and review i do',
 '    S ← AvailableScores(O[m,i])',
 '    μ ← ReviewMean(O[m,i], m)',
 '    y ← Mixed if BothSigns(S) else Band(μ)',
 '    q ← Status(O[m,i], Δ[m,i])',
 '    R[m,i] ← (μ, y, q)',
 'end for',
 'M ← Evaluate(O, G) if G exists else Coverage(R)',
 'Export(R, O, M)',
 'return R, M'
]),
5:('Independent Deep Learning Reanalysis',[
 'Input: review x; hybrid H; model θ; thresholds τ',
 'Output: selected result Y',
 'if H.status ∉ {Partial, Unsupported}: return H',
 'Y ← ∅',
 'for each u ∈ Sentences(x) do',
 '    if MaxPairLength(u) > 160: continue',
 '    for each c ∈ Categories do',
 '        p ← Softmax(f_θ(u, q_c))',
 '        y ← ArgMax(p)',
 '        if InScope(c) ∧ y ≠ Absent ∧ p[y] ≥ τ[c]:',
 '            Y ← Y ∪ {(c, y, Span(u), p)}',
 '    end for',
 'end for',
 'return Aggregate(Y) if Y ≠ ∅ else Abstain'
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
    doc.core_properties.title='Auditable Aspect Sentiment Analysis of Hotel Reviews with Selective Deep Learning Reanalysis'
    doc.core_properties.author='Tanay Mohta and Aditya Rawat'
    doc.core_properties.subject='Compiler design project and development evaluation'
    doc.core_properties.keywords='hotel reviews, aspect sentiment, SentiWordNet, VADER, TextBlob, MiniLM, deep learning'
    settings=doc.settings.element
    compat=OxmlElement('w:doNotHyphenateCaps');settings.append(compat)


def paragraph(doc,text='',**options):
    p=doc.add_paragraph();append_notation(p,text)
    for run in p.runs:font(run)
    for k,v in options.items():setattr(p.paragraph_format,k,v)
    return p


def append_notation(p,text):
    """Typeset the small set of inline DL indices with editable Word runs."""
    symbols={'q_c':('q','c'),'tau_c':('τ','c'),'y_j':('y','j'),'w_y':('w','y'),'f_θ':('f','θ')}
    for part in re.split(r'(q_c|tau_c|y_j|w_y|f_θ)',text):
        if part in symbols:
            base,index=symbols[part];font(p.add_run(base));r=p.add_run(index);font(r);r.font.subscript=True
        elif part:p.add_run(part)


def algorithm(doc,number):
    title,lines=ALGORITHMS[number]
    p=paragraph(doc,f'Algorithm {number}  {title}',first_line_indent=Pt(0),space_before=Pt(4),space_after=Pt(2),keep_with_next=True)
    for r in p.runs:font(r,8.5,True)
    def rule(p,side):
        borders=p._p.get_or_add_pPr().find(qn('w:pBdr'))
        if borders is None:
            borders=OxmlElement('w:pBdr');p._p.get_or_add_pPr().append(borders)
        edge=OxmlElement('w:'+side)
        for key,value in [('val','single'),('sz','4'),('space','1'),('color','000000')]:
            edge.set(qn('w:'+key),value)
        borders.append(edge)
    rule(p,'top');rule(p,'bottom')
    step=0
    for i,line in enumerate(lines):
        label=line.startswith(('Input:','Output:'))
        if not label:step+=1
        p=paragraph(doc,first_line_indent=Pt(0),space_after=Pt(0),keep_with_next=i<len(lines)-1,keep_together=True)
        p.paragraph_format.line_spacing=Pt(9.5)
        if label:
            key,value=line.split(':',1)
            font(p.add_run(key+':'),8.5,True)
            font(p.add_run(value),8.5)
        else:
            p.paragraph_format.tab_stops.add_tab_stop(Pt(15))
            font(p.add_run(f'{step}:\t'),8.5)
            content=line.lstrip();indent=(len(line)-len(content))//4
            font(p.add_run('    '*indent),8.5)
            match=re.match(r'^(for each|end for|return)\b',content)
            if match:
                font(p.add_run(match.group()),8.5,True)
                font(p.add_run(content[match.end():]),8.5)
            else:
                append_notation(p,content)
                for r in p.runs:font(r,8.5)
    rule(p,'bottom')
    p.paragraph_format.space_after=Pt(4)


def image(doc,name,caption):
    p=doc.add_paragraph();p.paragraph_format.first_line_indent=Pt(0);p.paragraph_format.space_before=Pt(6);p.paragraph_format.space_after=Pt(0);p.paragraph_format.keep_with_next=True;p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    run=p.add_run();run.add_picture(str(ASSETS/f'{name}.png'),width=Inches(3.45))
    run._r.xpath('.//wp:docPr')[0].set('descr',caption)
    p=doc.add_paragraph(caption,'Caption');p.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY;p.paragraph_format.keep_together=True



def wide_architecture(doc,name,caption):
    # Full detailed diagram spans both columns within Proposed Systems.
    section=doc.add_section(WD_SECTION_START.CONTINUOUS)
    section._sectPr.find(qn('w:cols')).set(qn('w:num'),'1')
    p=doc.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent=Pt(0);p.paragraph_format.space_after=Pt(0)
    p.paragraph_format.keep_with_next=True
    run=p.add_run();run.add_picture(str(ASSETS/f'{name}.png'),width=Inches(7.1))
    run._r.xpath('.//wp:docPr')[0].set('descr',caption)
    p=doc.add_paragraph(caption,'Caption');p.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
    section=doc.add_section(WD_SECTION_START.CONTINUOUS)
    cols=section._sectPr.find(qn('w:cols'));cols.set(qn('w:num'),'2');cols.set(qn('w:space'),'360')


def table(doc,key):
    metrics=read_csv(RUN/'semeval-development'/'metrics.csv')
    classes=read_csv(RUN/'semeval-development'/'per_class_metrics.csv')
    if key=='datasets':
        caption='TABLE I\nEXPERIMENTAL COHORTS AND AVAILABLE LABELS'
        headers=['Cohort','Size','Label and role']
        rows=[['SemEval Hotels','30 reviews\n266 sentences','Human opinions; 148 mapped classification cases'],
              ['Booking random','200 reviews','No aspect gold; processing coverage'],
              ['Booking Italy','3,089 reviews','Cleaned from 4,367 rows; no aspect gold'],
              ['Italy demo subset','500 reviews','Random subset of the 3,089; no aspect gold'],
              ['Trip-MA train','2,040 segments','Human categories/polarity; 180 reviews; 2,038 usable'],
              ['Trip-MA validation','602 segments','42 reviews; checkpoint/threshold selection'],
              ['Trip-MA test','1,474 segments','111 reviews; follow-up mapped pair evaluation']]
        widths=[1.02,.73,1.70]
    elif key=='vocabulary':
        caption='TABLE II\nPROCESSING COVERAGE ON CLEANED BOOKING ITALY'
        headers=['Cohort / outcome','SentiWordNet','Hybrid'];rows=[]
        for subdir, label in [('booking-cleaned500','500'),('booking-all','3,089')]:
            data=read_csv(RUN/subdir/'coverage.csv')
            systems=list(dict.fromkeys(r['system'] for r in data))
            for status, title in [('complete','Complete'),('partial','Partial'),('unsupported','Unsupported')]:
                rows.append([f'{label}: {title}',*[str(next(r['reviews'] for r in data if r['system']==sys and r['status']==status)) for sys in systems]])
            vals=[]
            for sys in systems:
                group=[r for r in data if r['system']==sys]
                n=int(group[0]['submitted'])
                scored=sum(int(r['reviews']) for r in group if r['status'] in {'complete','partial'})
                vals.append(f'{scored:,} ({100*scored/n:.2f}%)')
            rows.append([f'{label}: Any scored',*vals])
        widths=[1.35,1.05,1.05]
    elif key=='compact_coverage':
        caption='TABLE II\nREAL REVIEW PROCESSING OUTCOMES'
        headers=['Cohort / method','C','P','U'];rows=[]
        for subdir,label in [('random200','Random 200'),('booking-cleaned500','Italy 500'),('booking-all','Italy 3,089')]:
            data=read_csv(RUN/subdir/'coverage.csv')
            systems=list(dict.fromkeys(r['system'] for r in data))
            for sys,name in zip(systems,['SentiWordNet','Hybrid']):
                rows.append([label+' / '+name,*[next(r['reviews'] for r in data if r['system']==sys and r['status']==status) for status in ('complete','partial','unsupported')]])
        widths=[1.90,.50,.55,.50]
    elif key=='compact_lexical':
        caption='TABLE III\nMAPPED SEMEVAL DEVELOPMENT PERFORMANCE'
        headers=['Measure','SentiWordNet','Hybrid'];s,h=metrics
        rows=[['Correct / eligible',f'{s["correct"]}/148',f'{h["correct"]}/148'],
              ['Accuracy (%)',f'{100*float(s["accuracy"]):.2f}',f'{100*float(h["accuracy"]):.2f}'],
              ['Coverage (%)',f'{100*float(s["coverage"]):.2f}',f'{100*float(h["coverage"]):.2f}'],
              ['Macro-F1',f'{float(s["macro_f1"]):.4f}',f'{float(h["macro_f1"]):.4f}']]
        for label,k in [('Pair precision','tuple_precision'),('Pair recall','tuple_recall'),('Pair-F1','tuple_f1')]:
            rows.append([label,f'{float(s[k]):.4f}',f'{float(h[k]):.4f}'])
        widths=[1.45,1,1]
    elif key=='metrics':
        caption='TABLE IV\nSEMEVAL DEVELOPMENT COMPARISON'
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
        caption='TABLE V\nCLASS SUPPORT AND F1 ON THE SEMEVAL MAPPING'
        headers=['Class','Support','SWN F1','Hybrid F1'];rows=[]
        for label in ['Negative','Neutral','Positive']:
            s,h=[r for r in classes if r['label']==label]
            rows.append([label,s['support'],f'{float(s["f1"]):.4f}',f'{float(h["f1"]):.4f}'])
        widths=[.88,.56,1.0,1.01]
    elif key=='dl_training':
        caption='TABLE III\nDEEP LEARNING TRAINING CONFIGURATION'
        headers=['Parameter','Value']
        settings=json.loads((DL_RUN/'frozen_settings.json').read_text())
        rows=[['Usable segments / pairs',f'{settings["admitted_training_segments"]:,} / {settings["training_pairs"]:,}'],
              ['Epochs / selected epoch',f'{settings["epochs"]} / {settings["best_epoch"]}'],
              ['Batch / accumulation','8 / 2 (effective 16)'],
              ['Encoder / head learning rate','2 × 10⁻⁵ / 2 × 10⁻⁴'],
              ['Optimizer / decay','AdamW / 0.01'],
              ['Schedule / clipping','Linear, 10% warmup / 1.0'],
              ['Max pair / seed','160 tokens / 172026'],
              ['Training device','RTX 2050; mixed precision'],
              ['Encoder / head updates','Both trained; 3,057 steps']]
        widths=[1.65,1.8]
    elif key=='dl_metrics':
        caption='TABLE IV\nTRIP-MA CATEGORY POLARITY PAIR PERFORMANCE'
        headers=['Scope / method','P (%)','R (%)','F1 (%)','Exact (%)'];rows=[]
        for r in read_csv(DL/'metrics.csv'):
            scope='All' if r['scope']=='all_test' else 'Unresolved'
            method='Hybrid' if r['system']=='Hybrid' else 'Hybrid + DL'
            rows.append([scope+' / '+method,*[f'{100*float(r[k]):.2f}' for k in ('precision','recall','pair_micro_f1','exact_segment_match')]])
        widths=[1.17,.53,.53,.57,.65]
    elif key=='dl_categories':
        caption='TABLE V\nMAPPED TRIP-MA CATEGORY PERFORMANCE'
        headers=['Category','Gold pairs','Hybrid F1','DL route F1'];rows=[]
        data=read_csv(DL/'per_category_comparison.csv')
        for c in ['Room','Cleanliness','Service','Food','Facilities']:
            a,b=[r for r in data if r['category']==c]
            rows.append([c,a['gold_pairs'],f'{float(a["pair_micro_f1"]):.4f}',f'{float(b["pair_micro_f1"]):.4f}'])
        widths=[1.0,.65,.85,.95]
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


def summation(items):
    n=OxmlElement('m:nary');pr=OxmlElement('m:naryPr');ch=OxmlElement('m:chr');ch.set(qn('m:val'),'∑');pr.append(ch);n.append(pr)
    low=OxmlElement('m:sub');low.append(mr('j = 1'));high=OxmlElement('m:sup');high.append(mr('B'));body=OxmlElement('m:e')
    for item in items:body.append(item)
    n.extend([low,high,body]);return n


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
    elif key=='dl_prob':
        items=[sub('p','c'),mr(' = softmax('),sub('f','θ'),mr('(u, '),sub('q','c'),mr('))')];number=4
    elif key=='dl_loss':
        numerator=[summation([sub('w','yⱼ'),mr(' log '),sub('p','j,yⱼ')])]
        denominator=[summation([sub('w','yⱼ')])]
        items=[mr('L = −'),frac(numerator,denominator)];number=5
    elif key=='dl_direction':
        items=[sub('d','c'),mr(' = '),frac([sub('p','+'),mr(' − '),sub('p','−')],[sub('p','+'),mr(' + '),sub('p','−')])];number=6
    elif key=='metrics':
        items=[mr('Accuracy = '),frac([mr('C')],[mr('N')]),mr('   Coverage = '),frac([mr('S')],[mr('N')])];number=7
    else:raise ValueError(key)
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
        if block=='## III. Architectural Diagram':continue
        if block.startswith('## '):doc.add_paragraph(block[3:].upper(),'Heading 1');continue
        if block.startswith('### '):doc.add_paragraph(block[4:],'Heading 2');continue
        if block.startswith('{{WIDEFIG:'):
            name,caption=block[10:-2].split('|',1);wide_architecture(doc,name,caption);continue
        if block.startswith('{{FIG:'):
            name,caption=block[6:-2].split('|',1);image(doc,name,caption);continue
        if block.startswith('{{ALG:'):algorithm(doc,int(block[6:-2]));continue
        if block.startswith('{{TABLE:'):table(doc,block[8:-2]);continue
        if block.startswith('{{EQ:'):equation(doc,block[5:-2]);continue
        if block=='{{REFERENCES}}':
            for number,text in refs.items():
                p=paragraph(doc,f'[{number}]  {text}',first_line_indent=Inches(-.19),left_indent=Inches(.19),space_after=Pt(1),keep_together=True)
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
    print(f'{len(refs)} references, {len(re.findall(r"{{ALG:",raw))} algorithms, {len(re.findall(r"{{(?:WIDE)?FIG:",raw))} figures, {len(re.findall(r"{{TABLE:",raw))} tables; {len(raw.split())} prose/source words before references and algorithms.')


if __name__=='__main__':build()
