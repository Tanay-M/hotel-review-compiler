"""Vector architecture and grayscale paper charts, using measured CSV values."""
from pathlib import Path
import csv
from html import escape
from math import atan2, cos, sin
from reportlab.pdfgen import canvas
from pdf2image import convert_from_path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output'/'paper'/'assets'
RUN=ROOT/'output'/'experiments'/'2026-10-21'/'hybrid-vocabulary-paper'
WIDTH=252


class Figure:
    def __init__(self,name,height):
        self.name=name;self.height=height;self.svg=[]
        self.c=canvas.Canvas(str(OUT/f'{name}.pdf'),pagesize=(WIDTH,height))
        self.c.setTitle(name.replace('_',' '));self.c.setAuthor('Tanay Mohta and Aditya Rawat')

    def text(self,x,y,text,size=8,bold=False,italic=False,anchor='middle'):
        font='Times-Bold' if bold else 'Times-Italic' if italic else 'Times-Roman'
        self.c.setFont(font,size);self.c.setFillColorRGB(0,0,0)
        method=self.c.drawCentredString if anchor=='middle' else self.c.drawRightString if anchor=='end' else self.c.drawString
        method(x,y,text)
        style='font-weight="bold"' if bold else 'font-style="italic"' if italic else ''
        self.svg.append(f'<text x="{x}" y="{self.height-y}" font-family="Times New Roman,serif" font-size="{size}" text-anchor="{anchor}" {style}>{escape(text)}</text>')

    def rect(self,x,y,w,h,fill=1,dashed=False):
        self.c.setStrokeColorRGB(0,0,0);self.c.setFillColorRGB(fill,fill,fill);self.c.setLineWidth(.7)
        self.c.setDash([3,2] if dashed else [])
        self.c.rect(x,y,w,h,stroke=1,fill=0 if dashed else 1);self.c.setDash([])
        self.svg.append(f'<rect x="{x}" y="{self.height-y-h}" width="{w}" height="{h}" fill="{"none" if dashed else f"rgb({int(fill*255)},{int(fill*255)},{int(fill*255)})"}" stroke="black" stroke-width="0.7" {"stroke-dasharray=\"3 2\"" if dashed else ""}/>')

    def line(self,points,arrow=False,dashed=False):
        self.c.setStrokeColorRGB(0,0,0);self.c.setLineWidth(.65);self.c.setDash([2,2] if dashed else [])
        for a,b in zip(points,points[1:]):self.c.line(*a,*b)
        self.c.setDash([])
        self.svg.append('<polyline points="'+' '.join(f'{x},{self.height-y}' for x,y in points)+'" fill="none" stroke="black" stroke-width="0.65"/>')
        if arrow:
            a,b=points[-2:];angle=atan2(b[1]-a[1],b[0]-a[0]);length=3.7
            triangle=[b,(b[0]-length*cos(angle-.43),b[1]-length*sin(angle-.43)),(b[0]-length*cos(angle+.43),b[1]-length*sin(angle+.43))]
            p=self.c.beginPath();p.moveTo(*triangle[0]);p.lineTo(*triangle[1]);p.lineTo(*triangle[2]);p.close()
            self.c.setFillColorRGB(0,0,0);self.c.drawPath(p,fill=1,stroke=0)
            self.svg.append('<polygon points="'+' '.join(f'{x},{self.height-y}' for x,y in triangle)+'" fill="black"/>')

    def node(self,x,y,label,established=False,w=64,h=30):
        assert 1<=len(label.replace('\n',' ').split())<=3,label
        self.rect(x,y,w,h,.84 if established else 1)
        lines=label.split('\n');base=y+h/2+(len(lines)-1)*4-2.8
        for index,line in enumerate(lines):self.text(x+w/2,base-index*8,line,size=8)

    def legend(self,y):
        self.rect(12,y-2,8,6,.84);self.text(24,y-1,'Established methods',6.7,anchor='start')
        self.rect(135,y-2,8,6,1);self.text(147,y-1,'Project implementation',6.7,anchor='start')

    def group(self,top,title,labels,established=(),reverse=False):
        self.rect(3,top-103,246,103,dashed=True);self.text(126,top-11,title,8.4,bold=True)
        xs=[14,94,174];ys=[top-49,top-91]
        positions=[(x,ys[0]) for x in xs]+[(x,ys[1]) for x in reversed(xs)]
        if reverse:positions=[(x,ys[0]) for x in reversed(xs)]+[(x,ys[1]) for x in xs]
        for i,((x,y),label) in enumerate(zip(positions,labels)):self.node(x,y,label,i in established)
        for (x,y),(nx,ny) in zip(positions,positions[1:]):
            if y==ny:self.line([(x+(64 if nx>x else 0),y+15),(nx+(0 if nx>x else 64),ny+15)],True)
            else:self.line([(x+32,y),(nx+32,ny+30)],True)
        return positions

    def save(self):
        self.c.showPage();self.c.save()
        (OUT/f'{self.name}.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}pt" height="{self.height}pt" viewBox="0 0 {WIDTH} {self.height}">'+'\n'.join(self.svg)+'</svg>',encoding='utf-8')
        convert_from_path(str(OUT/f'{self.name}.pdf'),dpi=450,fmt='png',single_file=True)[0].save(OUT/f'{self.name}.png')


def architecture():
    f=Figure('module1_preprocessing',142)
    f.text(14,132,'Review records',7.7,italic=True,anchor='start')
    p=f.group(120,'Preprocessing and Validation',['UTF-8\nDecoding','Field\nMapping','Input\nValidation','Duplicate\nFlagging','Original\nRetention','Source\nIdentity'])
    f.line([(46,128),(46,101)],True)
    f.line([(46,29),(46,5)],True);f.text(53,7,'To Module 2',7.4,italic=True,anchor='start');f.save()

    f=Figure('module2_grammar',282);f.legend(272)
    f.text(14,255,'Original text to both paths',7.3,italic=True,anchor='start')
    f.group(244,'Baseline Lexical and Syntax',['Regex\nScanning','Phrase\nMatching','Token\nClassification','Predictive\nParsing','Clause\nRecovery','AST\nGeneration'])
    f.line([(46,253),(46,225)],True)
    f.line([(46,153),(46,134)],True);f.text(52,132,'Baseline AST to Module 3',6.9,italic=True,anchor='start')
    f.group(119,'Independent Hybrid Grammar',['Contraction\nExpansion','Source\nMapping','POS\nTagging','Phrase\nChunking','Noun\nPhrases','Clause\nSegmentation'],established=(2,3))
    f.line([(7,85),(14,85)],True);f.text(14,102,'Module 1',6.2,italic=True,anchor='start')
    f.line([(46,28),(46,2)],True);f.text(52,4,'Hybrid contexts to Module 3',6.9,italic=True,anchor='start');f.save()

    f=Figure('module3_scoring',326);f.legend(316)
    f.text(14,299,'Separate Module 2 paths',7.3,italic=True,anchor='start')
    f.group(288,'Baseline Semantics and Lookup',['Aspect\nBinding','Category\nMapping','Sense\nLookup','P/N\nExtraction','Lexical\nScore','Scoring\nTrace'],established=(2,3,4))
    f.line([(46,297),(46,269)],True)
    f.line([(46,197),(46,178)],True);f.text(52,176,'Baseline evidence to Module 4',6.9,italic=True,anchor='start')
    f.rect(3,16,246,147,dashed=True);f.text(126,152,'Hybrid Attachment and Scoring',8.4,bold=True)
    for x,label in [(14,'Aspect\nMatching'),(94,'Opinion\nAttachment'),(174,'Context\nSelection')]:f.node(x,114,label)
    f.line([(7,129),(14,129)],True)
    f.line([(78,129),(94,129)],True);f.line([(158,129),(174,129)],True)
    for x,label in [(174,'Native\nEvidence'),(94,'Guarded\nAliases'),(14,'Scoring\nCopy')]:f.node(x,72,label)
    f.line([(206,114),(206,102)],True)
    f.line([(174,87),(158,87)],True);f.line([(94,87),(78,87)],True)
    for x,label in [(14,'VADER\nScoring'),(94,'TextBlob\nScoring'),(174,'Component\nEvidence')]:f.node(x,28,label,established=x!=174)
    f.line([(46,72),(46,58)],True)
    f.line([(46,65),(126,65),(126,58)],True)
    f.line([(158,43),(174,43)],True)
    f.line([(46,28),(46,22),(206,22),(206,28)],True)
    f.line([(238,43),(246,43),(246,2)],True);f.text(131,4,'Hybrid evidence to Module 4',6.9,italic=True);f.save()

    f=Figure('module4_synthesis',301);f.legend(291)
    f.text(126,276,'Separate evidence from Module 3',7.3,italic=True)
    for top,title,labels,established in [
        (267,'Baseline Adjustments',['Domain\nPreference','Degree\nWeighting','Negation\nAdjustment'],(2,)),
        (192,'Independent Hybrid Integration',['Evidence\nFusion','Context\nRules','Trace\nRetention'],())]:
        f.rect(3,top-64,246,64,dashed=True);f.text(126,top-11,title,8.4,bold=True)
        for i,(x,label) in enumerate(zip([14,94,174],labels)):f.node(x,top-52,label,i in established)
        f.line([(78,top-37),(94,top-37)],True);f.line([(158,top-37),(174,top-37)],True)
        f.line([(46,top+5),(46,top-22)],True)
    f.line([(238,230),(248,230),(248,110),(206,110),(206,86)],True)
    f.line([(206,140),(206,86)],True)
    f.text(115,115,'Per-method results',7.1,italic=True)
    f.group(105,'Final Records and Evaluation',['Five\nBands','Review\nSynthesis','Result\nRecords','Coverage\nStatus','Benchmark\nMetrics','Paper\nExports'],reverse=True)
    f.save()


def read(path):
    with path.open(encoding='utf-8-sig',newline='') as h:return list(csv.DictReader(h))


def charts():
    metrics=read(RUN/'semeval-development'/'metrics.csv')
    f=Figure('performance_comparison',151)
    x0,y0,w,h=29,29,211,99
    for tick in [0,.25,.5,.75,1]:
        y=y0+h*tick;f.line([(x0,y),(240,y)],dashed=True);f.text(24,y-2,f'{tick:.2f}',7,anchor='end')
    for i,(key,label) in enumerate([('accuracy','Accuracy'),('macro_f1','Macro-F1'),('tuple_f1','Tuple-F1')]):
        for method,m in enumerate(metrics):
            x=52+i*69+method*19;value=float(m[key]);f.rect(x,y0,17,h*value,0 if method==0 else .70)
            f.text(x+8.5,y0+h*value+3,f'{value:.3f}',6.5)
        f.text(70+i*69,16,label,7.3)
    f.text(10,138,'Score',7.5,anchor='start');f.rect(115,139,7,6,0);f.text(126,139,'SentiWordNet',6.7,anchor='start');f.rect(193,139,7,6,.70);f.text(204,139,'Hybrid',6.7,anchor='start');f.save()

    coverage=read(RUN/'random200'/'coverage.csv')
    f=Figure('random_coverage',155);base=29;h=97
    for tick in [0,50,100,150,200]:
        y=base+h*tick/200;f.line([(29,y),(240,y)],dashed=True);f.text(24,y-2,str(tick),7,anchor='end')
    for i,system in enumerate(['SentiWordNet compiler','VADER-TextBlob hybrid']):
        bottom=base
        for status,shade in [('complete',1),('partial',.70),('unsupported',.25)]:
            count=next(int(r['reviews']) for r in coverage if r['system']==system and r['status']==status)
            height=h*count/200;f.rect(65+i*100,bottom,39,height,shade)
            if count>10:
                if shade<.5:
                    f.c.setFillColorRGB(1,1,1);f.c.setFont('Times-Roman',8);f.c.drawCentredString(84.5+i*100,bottom+height/2-2,str(count));f.c.setFillColorRGB(0,0,0)
                else:f.text(84.5+i*100,bottom+height/2-2,str(count),8)
            bottom+=height
        f.text(84.5+i*100,16,'SentiWordNet' if i==0 else 'Hybrid',7.5)
    for x,label,shade in [(30,'Complete',1),(106,'Partial',.70),(168,'Unsupported',.25)]:
        f.rect(x,139,7,6,shade);f.text(x+11,139,label,6.8,anchor='start')
    f.save()

    timing=read(RUN/'random200'/'runtime_summary.csv')
    f=Figure('runtime_comparison',151);x0,y0,w,h=31,29,205,99
    ymax=max(float(r['mean_seconds'])+float(r['stdev_seconds']) for r in timing)*1.1
    for tick in [ymax*i/4 for i in range(5)]:
        y=y0+h*tick/ymax;f.line([(x0,y),(240,y)],dashed=True);f.text(26,y-2,f'{tick:.1f}',7,anchor='end')
    for method,system in enumerate(['SentiWordNet compiler','VADER-TextBlob hybrid']):
        points=[]
        for r in timing:
            if r['system']!=system:continue
            n=int(r['reviews']);x=x0+w*(n-20)/180;y=y0+h*float(r['mean_seconds'])/ymax
            error=h*float(r['stdev_seconds'])/ymax
            f.line([(x,y-error),(x,y+error)]);f.line([(x-2,y-error),(x+2,y-error)]);f.line([(x-2,y+error),(x+2,y+error)])
            f.rect(x-1.9,y-1.9,3.8,3.8,0 if method==0 else 1);points.append((x,y))
        f.line(points,dashed=method==1)
    for n in [20,50,100,200]:f.text(x0+w*(n-20)/180,18,str(n),7)
    f.text(130,5,'Number of original reviews',7.5);f.text(5,139,'Seconds',7.3,anchor='start')
    f.text(116,139,'SentiWordNet: solid',6.7,anchor='start');f.text(192,139,'Hybrid: dashed',6.7,anchor='start');f.save()

    f=Figure('booking_vocabulary_coverage',155);base=29;h=97
    for tick in [0,1000,2000,3000]:
        y=base+h*tick/3102;f.line([(29,y),(240,y)],dashed=True);f.text(24,y-2,str(tick),7,anchor='end')
    for i,counts in enumerate([(210,2403,489),(244,2457,401)]):
        bottom=base
        for count,shade in zip(counts,[1,.70,.25]):
            height=h*count/3102;f.rect(65+i*100,bottom,39,height,shade)
            if shade<.5:
                f.c.setFillColorRGB(1,1,1);f.c.setFont('Times-Roman',7);f.c.drawCentredString(84.5+i*100,bottom+height/2-2,str(count));f.c.setFillColorRGB(0,0,0)
            else:f.text(84.5+i*100,bottom+height/2-2,str(count),7)
            bottom+=height
        f.text(84.5+i*100,16,'Before' if i==0 else 'Expanded',7.5)
    for x,label,shade in [(30,'Complete',1),(106,'Partial',.70),(168,'Unsupported',.25)]:
        f.rect(x,139,7,6,shade);f.text(x+11,139,label,6.8,anchor='start')
    f.save()


if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True);architecture();charts()
    print(f'Four architecture diagrams and four measured charts written to {OUT}')
