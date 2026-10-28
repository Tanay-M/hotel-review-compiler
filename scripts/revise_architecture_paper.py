"""Apply the faculty's single-figure architecture and stage-label revision."""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
import re,shutil,sys,io
import pdfplumber
from pypdf import PdfReader,PdfWriter
from pypdf.generic import ContentStream,TextStringObject,ByteStringObject,ArrayObject,FloatObject
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas
from pdf2image import convert_from_path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/paper'
SOURCE=Path('C:/Users/asus/Downloads/All_Modules_single_page (2).pdf')
ARCHIVE=OUT/'archive/pre-single-architecture-2026-10-23.zip'
if not ARCHIVE.exists():
    with ZipFile(ARCHIVE,'w',ZIP_DEFLATED) as z:
        for p in OUT.iterdir():
            if p.is_file():z.write(p,'paper/'+p.name)
        for p in (OUT/'assets').iterdir():
            if p.is_file():z.write(p,'paper/assets/'+p.name)
        for name in ['docs/conference_manuscript.md','scripts/build_conference_paper.py','scripts/audit_conference_paper.py','scripts/render_conference_pages.py']:
            z.write(ROOT/name,name)
        z.write(SOURCE,'supplied-architecture.pdf')

# Edit PDF text operators, retaining vector boxes, arrows and source layout.
reader=PdfReader(SOURCE);page=reader.pages[0]
stream=ContentStream(page.get_contents(),reader)
replacements={'To Module 2':'To lexical analysis',
    'Normalized text (from Module 1)':'Normalized text',
    'AST (to Module 3)':'AST to semantic analysis',
    'AST (from Module 2)':'AST from syntax analysis',
    'Lexical score L (to Module 4)':'Lexical score L to adjustments',
    'From Module 3':'From semantic analysis'}
source_page=pdfplumber.open(SOURCE).pages[0]
overlay_buffer=io.BytesIO()
overlay=canvas.Canvas(overlay_buffer,pagesize=(float(page.mediabox.width),float(page.mediabox.height)))
for old,new in replacements.items():
    match=source_page.search(re.escape(old))[0]
    size=match['chars'][0]['size']
    overlay.setFont('Times-Italic',size)
    overlay.drawString(match['x0'],source_page.height-match['bottom']+size*.217,new)
overlay.save();overlay_buffer.seek(0)
last_tm=None
for args,op in stream.operations:
    if op==b'Tm':last_tm=args
    if op==b'Tj' and isinstance(args[0],str) and 'Module' in args[0]:
        old=str(args[0]);new=re.sub(r'Module \d+:\s*','',old)
        args[0]=TextStringObject(new)
        if last_tm is not None:
            delta=(stringWidth(old,'Times-Roman',9)-stringWidth(new,'Times-Roman',9))/2
            last_tm[4]=FloatObject(float(last_tm[4])+delta)
    elif op==b'TJ':
        old=''.join(str(v) for v in args[0] if isinstance(v,str))
        if old in replacements:args[0]=ArrayObject([ByteStringObject(b'')])
page.replace_contents(stream)
page.merge_page(PdfReader(overlay_buffer).pages[0])
page.cropbox.lower_left=(108,24);page.cropbox.upper_right=(488,817)
page.mediabox.lower_left=(108,24);page.mediabox.upper_right=(488,817)
writer=PdfWriter();writer.add_page(page)
asset=OUT/'assets/architecture_single.pdf'
with asset.open('wb') as f:writer.write(f)
assert not re.search(r'\bmodule\b',PdfReader(asset).pages[0].extract_text(),re.I)
convert_from_path(str(asset),dpi=450,first_page=1,last_page=1,use_cropbox=True)[0].save(OUT/'assets/architecture_single.png')
if '--figure-only' in sys.argv:
    print('Refreshed supplied diagram with PDF text encoding preserved.')
    raise SystemExit(0)

p=ROOT/'docs/conference_manuscript.md';s=p.read_text(encoding='utf-8')
s=re.sub(r'\{\{FIG:module[1-4]_[^\n]+\}\}\n\n','',s)
old='The architecture contains four modules: preprocessing, lexical and grammatical analysis, semantic attachment and scoring, and adjustment and result generation. Figures 1-4 use short block labels and dashed module groups. Gray denotes established methods; white denotes project integration. Preprocessing is the first processing block. The paths remain independent after validation and retain their own records throughout comparison.'
new='The architecture comprises preprocessing and validation, lexical and grammatical analysis, semantic attachment and scoring, and adjustment and result generation. The independent analysis paths retain their own outputs throughout comparison. Figure 1 depicts the SentiWordNet compiler path; the VADER-TextBlob path uses independent shallow grammatical extraction and lexical fusion as described below.'
assert old in s;s=s.replace(old,new)
section='''## III. Architectural Diagram

{{WIDEFIG:architecture_single|Fig. 1. SentiWordNet compiler architecture: (a) preprocessing and validation, (b) lexical and syntax analysis, (c) semantic analysis and lexical lookup, and (d) adjustment and final records. The independent VADER-TextBlob hybrid is described in Section IV.}}

'''
s=s.replace('## III. Proposed Systems',section+'## IV. Proposed Systems')
for old,new in [('IV. Results and Implementation','V. Results and Implementation'),('V. Performance and Metrics','VI. Performance and Metrics'),('VI. Conclusion','VII. Conclusion')]:s=s.replace('## '+old,'## '+new)
s=re.sub(r'(?m)^(### [A-Z]\. )Module [1-4] ',r'\1',s)
titles={'### B. Implementation Results':'### B. Preprocessing and Validation Implementation',
        '### C. Implementation Results':'### C. Lexical and Grammatical Implementation',
        '### D. Implementation Results':'### D. Semantic Attachment and Scoring Implementation',
        '### E. Implementation Results':'### E. Adjustment and Reporting Implementation'}
for old,new in titles.items():s=s.replace(old,new)
for old,new in [(5,2),(6,3),(7,4),(8,5)]:
    s=s.replace(f'Fig. {old}.',f'Fig. {new}.').replace(f'Fig. {old} ',f'Fig. {new} ').replace(f'Figure {old} ',f'Figure {new} ')
s=s.replace('Table III and Fig. 7','Table III and Fig. 4')
assert not re.search(r'\bmodules?\b',s,re.I)
p.write_text(s,encoding='utf-8')

p=ROOT/'scripts/build_conference_paper.py';s=p.read_text(encoding='utf-8')
needle='\ndef table(doc,key):'
helper='''
def wide_architecture(doc,name,caption):
    # A single full-page figure area preserves the supplied tall architecture.
    section=doc.add_section(WD_SECTION_START.CONTINUOUS)
    section._sectPr.find(qn('w:cols')).set(qn('w:num'),'1')
    doc.add_page_break()
    doc.add_paragraph('III. ARCHITECTURAL DIAGRAM','Heading 1')
    p=doc.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent=Pt(0);p.paragraph_format.space_after=Pt(0)
    p.paragraph_format.keep_with_next=True
    run=p.add_run();run.add_picture(str(ASSETS/f'{name}.png'),height=Inches(8.55))
    run._r.xpath('.//wp:docPr')[0].set('descr',caption)
    p=doc.add_paragraph(caption,'Caption');p.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
    section=doc.add_section(WD_SECTION_START.NEW_PAGE)
    cols=section._sectPr.find(qn('w:cols'));cols.set(qn('w:num'),'2');cols.set(qn('w:space'),'360')

'''
if 'def wide_architecture(' not in s:s=s.replace(needle,'\n'+helper+needle)
s=s.replace("        if block.startswith('## '):doc.add_paragraph(block[3:].upper(),'Heading 1');continue", "        if block=='## III. Architectural Diagram':continue\n        if block.startswith('## '):doc.add_paragraph(block[3:].upper(),'Heading 1');continue")
needle="        if block.startswith('{{FIG:'):"
s=s.replace(needle,"        if block.startswith('{{WIDEFIG:'):\n            name,caption=block[10:-2].split('|',1);wide_architecture(doc,name,caption);continue\n"+needle)
s=s.replace('33 references, 4 algorithms, 8 figures, 4 tables;','33 references, 4 algorithms, 5 figures, 4 tables;')
p.write_text(s,encoding='utf-8')

p=ROOT/'scripts/render_conference_pages.py';s=p.read_text(encoding='utf-8').replace('26.1015.12040','26.1020.11127').replace('tmp/paper-qa-two-system-2026-10-21','tmp/paper-qa-single-architecture-2026-10-23');p.write_text(s,encoding='utf-8')
print('Archived prior paper; removed numbered terminology; prepared single supplied vector diagram and revised manuscript/builder.')
