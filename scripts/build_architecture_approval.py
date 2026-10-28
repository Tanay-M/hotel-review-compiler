"""Standalone approval draft; never overwrites the manuscript or paper assets."""
from pathlib import Path
from hashlib import sha256
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon, FancyArrowPatch

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/architecture_review'
PROTECTED = [ROOT/'output/paper/Team_17_IEEE_Conference_Paper.docx',
             ROOT/'output/paper/Team_17_IEEE_Conference_Paper.pdf',
             ROOT/'output/paper/assets/architecture_single.svg',
             ROOT/'docs/conference_manuscript.md']


def build():
    before = {str(p.relative_to(ROOT)): sha256(p.read_bytes()).hexdigest() for p in PROTECTED}
    OUT.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({'font.family':'Times New Roman', 'font.size':9,
                         'svg.fonttype':'none', 'pdf.fonttype':42})
    fig, ax = plt.subplots(figsize=(8.3, 11.7))
    ax.set(xlim=(0,16), ylim=(0,22.3)); ax.axis('off')
    fig.subplots_adjust(left=.015,right=.985,top=.99,bottom=.015)

    def txt(x,y,s,fs=9,**kw):
        return ax.text(x,y,s,ha='center',va='center',fontsize=fs,**kw)

    def box(x,y,s,w=2.4,h=.67,kind='process',lib=False,fs=9):
        fill='.86' if lib else 'white'
        if kind=='data':
            points=[(x-w/2+.17,y-h/2),(x+w/2,y-h/2),
                    (x+w/2-.17,y+h/2),(x-w/2,y+h/2)]
            p=Polygon(points,facecolor=fill,edgecolor='black',linewidth=.95)
        elif kind=='decision':
            p=Polygon([(x-w/2,y),(x,y+h/2),(x+w/2,y),(x,y-h/2)],
                      facecolor='white',edgecolor='black',linewidth=.95)
        else:
            p=Rectangle((x-w/2,y-h/2),w,h,facecolor=fill,edgecolor='black',linewidth=.95)
        ax.add_patch(p);txt(x,y,s,fs)

    def line(points,dash=False):
        for a,b in zip(points[:-2],points[1:-1]):
            ax.plot([a[0],b[0]],[a[1],b[1]],color='black',lw=.85,
                    linestyle='--' if dash else '-')
        ax.add_patch(FancyArrowPatch(points[-2],points[-1],arrowstyle='-|>',
                    mutation_scale=8,lw=.85,color='black',linestyle='--' if dash else '-'))

    def group(x,y,w,h,title):
        ax.add_patch(Rectangle((x,y),w,h,fill=False,lw=.85,linestyle=(0,(5,3))))
        ax.text(x+.35,y+h-.23,title,ha='left',va='center',fontsize=10.2,fontweight='bold',
                    bbox=dict(facecolor='white',edgecolor='none',pad=.7))

    def chain(xs,y,labels,w=2.15,libs=()):
        for i,(x,s) in enumerate(zip(xs,labels)):
            box(x,y,s,w=w,lib=i in libs)
            if i:line([(xs[i-1]+w/2,y),(x-w/2,y)])

    txt(8,22.04,'Full Architecture: Dataset Inputs, Analysis and Evaluation',12,fontweight='bold')
    group(.25,18.25,15.5,3.38,'A  Preprocessing and Validation')
    sources=[(2.05,'SemEval Hotels\n266 sentences'),(6.0,'Booking Sample\n200 reviews'),
             (9.95,'Booking Italy\n3,089 reviews; demo 500'),(13.9,'Trip-MA Test\n1,474 text segments')]
    for x,s in sources:
        box(x,20.73,s,w=3.35,h=.75,kind='data',fs=8.4)
        line([(x,20.355),(x,20.06)])
    ax.plot([2.05,13.9],[20.06,20.06],lw=.85,color='black')
    line([(2.05,20.06),(1.8,20.06),(1.8,19.535)])
    xs=[1.8,4.9,8,11.1,14.2]
    chain(xs,19.2,['UTF-8\nDecoding','Field\nValidation','Duplicate\nFlagging','Source\nRetention','Working\nCopies'])
    # An explicit split connects each path's FIRST processing block.
    line([(14.2,18.865),(14.2,18.57),(15.52,18.57),(15.52,18.03)])
    ax.plot([.48,15.52],[18.03,18.03],color='black',lw=.85)
    line([(.48,18.03),(.48,16.83),(1.7,16.83),(1.7,16.735)])
    line([(15.52,18.03),(15.52,16.83),(9.2,16.83),(9.2,16.735)])

    left=[1.7,4.25,6.8];right=[9.2,11.75,14.3]
    group(.25,15.6,15.5,2.15,'B  Lexical and Grammatical Analysis')
    txt(4.4,17.04,'SentiWordNet path',8.5,fontstyle='italic',bbox=dict(facecolor='white',edgecolor='none',pad=.4))
    txt(11.8,17.04,'Independent Hybrid path',8.5,fontstyle='italic',bbox=dict(facecolor='white',edgecolor='none',pad=.4))
    chain(left,16.4,['Token\nScanning','Phrase\nMatching','Predictive\nParsing'])
    chain(right,16.4,['Pattern\nParsing','Phrase\nChunking','Opinion\nAttachment'],libs=(0,1))

    def transition(y_from,y_to):
        for xs_,edge in ((left,.48),(right,15.52)):
            line([(xs_[-1],y_from-.335),(xs_[-1],y_from-.8),
                  (edge,y_from-.8),(edge,y_to+.56),(xs_[0],y_to+.56),(xs_[0],y_to+.335)])

    transition(16.4,14.0)
    group(.25,13.2,15.5,2.15,'C  Semantic Attachment and Scoring')
    chain(left,14.0,['Category\nMapping','Sense\nLookup','P/N\nScoring'],libs=(1,2))
    chain(right,14.0,['Aspect\nMapping','VADER +\nTextBlob','Evidence\nFusion'],libs=(1,))
    transition(14.0,11.6)
    group(.25,10.65,15.5,2.3,'D  Adjustment and Final Records')
    chain(left,11.6,['Domain\nRules','Scoped\nNegation','Aspect\nRecords'])
    chain(right,11.6,['Context\nRules','Score\nAggregation','Status\nAssignment'])
    txt(4.4,10.98,'Baseline results retained',8.2,fontstyle='italic')
    # Compare baseline independently; it never controls the DL routing decision.
    line([(6.8,11.265),(6.8,10.48),(.07,10.48),(.07,.57),
          (8.25,.57),(8.25,2.28),(10.0,2.28)])

    # The detailed decision/retention/failure section is omitted at user request.
    # A labelled connector preserves the implemented selective-DL input rule.
    line([(14.3,11.265),(14.3,9.6),(.48,9.6),(.48,7.21),(1.7,7.21),(1.7,6.935)])
    txt(7.3,9.78,'Partial / Unsupported only',8.3,bbox=dict(facecolor='white',edgecolor='none',pad=.4))
    group(.25,5.45,15.5,2.85,'E  Independent Deep Learning Reanalysis')
    ex=[1.7,4.65,7.6,10.55,13.5]
    chain(ex,6.6,['Original\nSentences','Category\nQueries','Fine-tuned\nMiniLM','Threshold\nChecks','Selected\nResult'])
    txt(8,7.55,'Category / polarity output or abstention; original Hybrid evidence retained',8.3)
    line([(13.5,6.265),(13.5,4.98)])
    box(13.5,4.62,'Pipeline\nResults',w=2.5,kind='data',fs=8.5)
    line([(13.5,4.98),(13.5,4.955)])

    # Proper dataset/process nodes for offline model learning and validation.
    group(.25,.77,7.15,3.73,'Offline DL Training')
    box(2.0,3.75,'Trip-MA Train\n2,038 usable segments',w=3.05,h=.65,kind='data',fs=8.0)
    box(5.7,3.75,'Trip-MA Validation\n602 segments',w=3.05,h=.65,kind='data',fs=8.0)
    txt(3.83,3.27,'Human category / polarity labels',8.1)
    box(2.0,2.66,'Category-pair\nFine-tuning',w=3.05,h=.65,fs=8.5)
    box(5.7,2.66,'Checkpoint +\nThreshold Selection',w=3.05,h=.65,fs=8.2)
    line([(2,3.425),(2,2.985)])
    line([(5.7,3.425),(5.7,2.985)])
    line([(3.525,2.66),(4.175,2.66)])
    box(5.7,1.48,'Frozen Model\n+ Thresholds',w=3.05,h=.65,kind='data',fs=8.3)
    line([(5.7,2.335),(5.7,1.805)])
    # Distinct dashed configuration arrows, never a test-label training arrow.
    line([(7.225,1.48),(7.65,1.48),(7.65,4.8),(7.6,4.8),(7.6,6.265)],dash=True)
    line([(7.6,4.8),(10.55,4.8),(10.55,6.265)],dash=True)
    txt(3.4,1.0,'Training only; no test-label input',8.0)

    group(8.5,.77,7.25,3.42,'Evaluation Only')
    box(10.3,3.44,'SemEval Gold\nHuman annotations',w=3.0,h=.65,kind='data',fs=8.1)
    box(13.8,3.44,'Trip-MA Test Gold\n1,474 segments',w=3.0,h=.65,kind='data',fs=8.1)
    box(12.3,2.28,'Matched-cohort\nMetric Calculation',w=4.6,h=.67,fs=8.6)
    line([(10.3,3.115),(10.3,2.88),(11.0,2.88),(11,2.615)])
    line([(13.8,3.115),(13.8,2.88),(13.4,2.88),(13.4,2.615)])
    line([(13.5,4.285),(15.53,4.285),(15.53,2.28),(14.6,2.28)])
    box(12.3,1.32,'Precision / Recall / F1\nAccuracy / Coverage',w=5.35,h=.67,kind='data',fs=8.7)
    line([(12.3,1.945),(12.3,1.655)])

    # Legend uses the same shapes as the diagram, with a clear dashed-line key.
    ax.add_patch(Rectangle((.6,.15),.24,.18,facecolor='.86',edgecolor='black',lw=.8))
    ax.text(.94,.24,'Library component',fontsize=7.6,va='center')
    box(5.4,.24,'',w=.45,h=.22,kind='data')
    ax.text(5.75,.24,'Data / output',fontsize=7.6,va='center')
    line([(9,.24),(9.7,.24)],dash=True)
    ax.text(9.82,.24,'Model configuration',fontsize=7.6,va='center')
    for ext in ('svg','pdf','png'):
        fig.savefig(OUT/f'Team_17_Architecture_Dataset_Blocks_DRAFT.{ext}',dpi=240,
                    bbox_inches='tight',pad_inches=.06)
    plt.close(fig)
    after={str(p.relative_to(ROOT)):sha256(p.read_bytes()).hexdigest() for p in PROTECTED}
    assert before==after, 'The approved paper must remain unchanged.'
    (OUT/'draft_manifest.json').write_text(json.dumps({'status':'Awaiting user approval',
        'paper_unchanged':before==after,'protected_sha256':after,
        'dataset_roles':'Text inputs go to preprocessing; human train/validation labels go to offline training; gold test labels go only to evaluation.'},indent=2),encoding='utf-8')
    print('Standalone architecture draft generated; paper and embedded figure unchanged.')


if __name__=='__main__':build()
