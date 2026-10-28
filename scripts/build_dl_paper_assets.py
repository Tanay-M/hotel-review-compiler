"""Unified vector architecture and measured two-method DL paper figures."""
from pathlib import Path
import csv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/paper/assets'
RUN=ROOT/'output/neural/2026-10-23-dl-pair-evaluation'


def rows(path):
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))


def save(fig,name):
    for ext in ('svg','pdf','png'):fig.savefig(OUT/f'{name}.{ext}',dpi=400,bbox_inches='tight',pad_inches=.04)
    plt.close(fig)


def architecture():
    fig,ax=plt.subplots(figsize=(7.2,6.6));ax.set(xlim=(0,7.2),ylim=(-.25,8.95));ax.axis('off')
    fig.subplots_adjust(left=.01,right=.99,top=.99,bottom=.01)
    def group(y,h,title):
        ax.add_patch(Rectangle((.1,y),7,h,fill=False,linestyle=(0,(4,3)),linewidth=.85))
        ax.text(.25,y+h-.17,title,fontsize=10,fontweight='bold',va='center',bbox=dict(facecolor='white',edgecolor='none',pad=1))
    def block(x,y,label,w=1.0,h=.48,library=False):
        ax.add_patch(Rectangle((x-w/2,y-h/2),w,h,facecolor='.86' if library else 'white',edgecolor='black',linewidth=.95))
        ax.text(x,y,label,ha='center',va='center',fontsize=8.2)
    def arrow(a,b,label=None):
        ax.add_patch(FancyArrowPatch(a,b,arrowstyle='-|>',mutation_scale=8,linewidth=.85,color='black'))
        if label:ax.text((a[0]+b[0])/2+.06,(a[1]+b[1])/2,label,fontsize=7,ha='left',va='center',bbox=dict(facecolor='white',edgecolor='none',pad=.3))
    def chain(xs,y,labels,libraries=()):
        for i,(x,label) in enumerate(zip(xs,labels)):
            block(x,y,label,library=i in libraries)
            if i:arrow((xs[i-1]+.5,y),(x-.5,y))
    ax.text(3.6,8.77,'Review inputs: SemEval 266 sentences; Booking random 200; Booking Italy 3,089 (including demo 500)',ha='center',fontsize=7.1)
    ax.text(3.6,8.55,'Trip-MA test: 1,474 segments for pipeline evaluation; gold labels are evaluation only',ha='center',fontsize=7.1)
    group(7.12,1.25,'A  Preprocessing and Validation')
    chain([.85,2.22,3.59,4.96,6.33],7.72,['UTF-8\nDecoding','Field\nValidation','Duplicate\nFlagging','Source\nRetention','Working\nCopies'])
    # Retained source views feed each independent lexical path.
    arrow((6.33,7.48),(6.33,7.25));arrow((6.33,7.25),(.18,7.25))
    arrow((.18,7.25),(.18,6.44));arrow((.18,6.44),(.65,6.44));arrow((.65,6.44),(.65,6.40))
    arrow((6.33,7.25),(6.97,7.25));arrow((6.97,7.25),(6.97,6.44));arrow((6.97,6.44),(4.15,6.44));arrow((4.15,6.44),(4.15,6.40))
    group(5.65,1.24,'B  Lexical and Grammatical Analysis')
    ax.text(1.85,6.56,'SentiWordNet path',ha='center',fontsize=8,fontstyle='italic')
    ax.text(5.35,6.56,'Independent Hybrid path',ha='center',fontsize=8,fontstyle='italic')
    left=[.65,1.85,3.05];right=[4.15,5.35,6.55]
    chain(left,6.16,['Token\nScanning','Phrase\nMatching','Predictive\nParsing'])
    chain(right,6.16,['Pattern\nParsing','Phrase\nChunking','Opinion\nAttachment'],libraries=(0,1))
    group(4.22,1.17,'C  Semantic Attachment and Scoring')
    arrow((3.05,5.92),(3.05,5.49));arrow((3.05,5.49),(.18,5.49));arrow((.18,5.49),(.18,5.08));arrow((.18,5.08),(.65,5.08));arrow((.65,5.08),(.65,5.02))
    arrow((6.55,5.92),(6.55,5.08));arrow((6.55,5.08),(4.15,5.08));arrow((4.15,5.08),(4.15,5.02))
    chain(left,4.78,['Category\nMapping','Sense\nLookup','P/N\nScoring'],libraries=(1,2))
    chain(right,4.78,['Aspect\nMapping','VADER and\nTextBlob','Evidence\nFusion'],libraries=(1,))
    group(2.81,1.17,'D  Adjustment and Final Records')
    arrow((3.05,4.54),(3.05,4.08));arrow((3.05,4.08),(.18,4.08));arrow((.18,4.08),(.18,3.67));arrow((.18,3.67),(.65,3.67));arrow((.65,3.67),(.65,3.61))
    arrow((6.55,4.54),(6.55,3.67));arrow((6.55,3.67),(4.15,3.67));arrow((4.15,3.67),(4.15,3.61))
    chain(left,3.37,['Domain\nRules','Scoped\nNegation','Aspect\nRecords'])
    chain(right,3.37,['Context\nRules','Score\nAggregation','Status\nAssignment'])
    ax.text(1.85,3.0,'Baseline output retained for comparison',ha='center',fontsize=7.2,fontstyle='italic')
    # Status gate consumes only the Hybrid status, never baseline scores.
    block(6.0,2.35,'Status\nGate',w=1.05)
    arrow((6.55,3.13),(6.55,2.72));arrow((6.55,2.72),(6,2.72));arrow((6,2.72),(6,2.59))
    block(3.7,2.35,'Retain\nHybrid',w=1.0);arrow((5.475,2.35),(4.2,2.35),'Complete')
    ax.text(.25,2.36,'Invalid input / processing error: retain failure',fontsize=7.1,va='center')
    group(.24,1.65,'E  Independent Deep Learning Reanalysis')
    arrow((6.0,2.11),(6.0,1.98));arrow((6,1.98),(.18,1.98));arrow((.18,1.98),(.18,1.47));arrow((.18,1.47),(.85,1.47));arrow((.85,1.47),(.85,1.39))
    ax.text(3.4,2.02,'Partial / Unsupported: read the original review',ha='center',fontsize=7.3,bbox=dict(facecolor='white',edgecolor='none',pad=.2))
    chain([.85,2.22,3.59,4.96,6.33],1.15,['Original\nSentences','Category\nQueries','Fine-tuned\nMiniLM','Threshold\nChecks','Selected\nResult'])
    ax.text(3.59,.68,'Independent category / polarity output or abstention; original Hybrid evidence retained',ha='center',fontsize=7.3)
    ax.add_patch(Rectangle((.42,.36),.18,.12,facecolor='.86',edgecolor='black',linewidth=.8))
    ax.text(.68,.42,'Existing library component',fontsize=7.3,va='center')
    ax.add_patch(Rectangle((3.7,.36),.18,.12,facecolor='white',edgecolor='black',linewidth=.8))
    ax.text(3.96,.42,'Project processing / integration',fontsize=7.3,va='center')
    ax.text(3.6,.08,'Offline DL supervision: Trip-MA human labels — 2,038 usable training segments; validation 602',ha='center',fontsize=7.1)
    ax.text(3.6,-.13,'Test labels never supervise training; accepted category output is not a verified Complete review',ha='center',fontsize=7.1)
    save(fig,'architecture_single')


def build():
    OUT.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.family':'Times New Roman','font.size':8,'pdf.fonttype':42,'svg.fonttype':'none'})
    architecture()
    values=rows(RUN/'metrics.csv')
    fig,ax=plt.subplots(figsize=(3.45,2.6),layout='constrained')
    for dx,system,color,label in [(-.18,'Hybrid','.7','Hybrid'),(.18,'Routed pipeline','.2','Hybrid + DL')]:
        chosen=[r for r in values if r['system']==system]
        bars=ax.bar([i+dx for i in range(2)],[100*float(r['pair_micro_f1']) for r in chosen],width=.35,color=color,edgecolor='black',label=label)
        for b in bars:ax.text(b.get_x()+b.get_width()/2,b.get_height()+1,f'{b.get_height():.2f}',ha='center',fontsize=7)
    ax.set_xticks([0,1],['All test\n(n = 1,474)','Unresolved\n(n = 1,113)']);ax.set_ylim(0,65)
    ax.set_ylabel('Category–polarity micro-F1 (%)');ax.legend(frameon=False,loc='upper left');ax.grid(axis='y',linestyle=':',alpha=.3)
    save(fig,'dl_joint_pair_f1')
    # Preserve the measured epoch and category figures, whose values use this run.
    import shutil
    source=ROOT/'output/neural/2026-10-23-dl-paper-evidence'
    for name in ('validation_f1','category_f1'):
        for ext in ('svg','pdf','png'):shutil.copyfile(source/f'fig_{name}.{ext}',OUT/f'dl_{name}.{ext}')
    print('Unified five-stage architecture and three DL charts generated.')


if __name__=='__main__':build()
