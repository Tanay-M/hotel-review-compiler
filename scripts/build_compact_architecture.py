"""Compact vector architecture with dataset roles and no measured predictions."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch

OUT=Path(__file__).resolve().parents[1]/'output/paper/assets'


def build():
    plt.rcParams.update({'font.family':'Times New Roman','pdf.fonttype':42,'svg.fonttype':'none'})
    fig,ax=plt.subplots(figsize=(3.45,4.65));ax.set(xlim=(0,3.45),ylim=(0,4.65));ax.axis('off')
    fig.subplots_adjust(left=.01,right=.99,bottom=.01,top=.99)
    def box(x,y,text,w=1.38,h=.40,gray=False,size=8):
        ax.add_patch(Rectangle((x-w/2,y-h/2),w,h,facecolor='.88' if gray else 'white',edgecolor='black',linewidth=.8))
        ax.text(x,y,text,ha='center',va='center',fontsize=size)
    def arrow(a,b,label=None):
        ax.add_patch(FancyArrowPatch(a,b,arrowstyle='-|>',mutation_scale=7,linewidth=.8,color='black'))
        if label:ax.text((a[0]+b[0])/2,(a[1]+b[1])/2,label,fontsize=6.7,ha='center',va='center',bbox=dict(facecolor='white',edgecolor='none',pad=.2))
    ax.text(1.725,4.50,'Review text: SemEval 266 sentences; Booking random 200',fontsize=7.1,ha='center')
    ax.text(1.725,4.34,'Booking Italy 3,089 reviews (nested demo: 500)',fontsize=7.1,ha='center')
    box(1.725,3.98,'Preprocessing / Validation',w=2.8,h=.42)
    # First processing block is preprocessing; dataset names are source annotations.
    arrow((1.725,3.77),(.80,3.45));arrow((1.725,3.77),(2.65,3.45))
    ax.text(.65,3.60,'SentiWordNet',fontsize=7.6,ha='center',fontstyle='italic',bbox=dict(facecolor='white',edgecolor='none',pad=.1))
    ax.text(2.80,3.60,'VADER–TextBlob',fontsize=7.6,ha='center',fontstyle='italic',bbox=dict(facecolor='white',edgecolor='none',pad=.1))
    for x,texts in [(.80,['Lexical / Syntax','Semantic / SWN','Adjustment / IR']),
                    (2.65,['POS / Chunking','Aspects / Fusion','Adjustment / Status'])]:
        for i,(y,label) in enumerate(zip([3.25,2.65,2.05],texts)):
            box(x,y,label,gray=i==1)
            if i:arrow((x,y+.40),(x,y+.20))
    box(.80,1.47,'Baseline Output',h=.36);arrow((.80,1.85),(.80,1.65))
    box(2.65,1.47,'Status Gate',h=.36);arrow((2.65,1.85),(2.65,1.65))
    # The Complete branch and residual branch remain distinct.
    box(.80,.93,'Retain Hybrid',h=.34)
    arrow((1.96,1.47),(1.30,1.10))
    ax.text(1.68,1.07,'Complete',fontsize=6.7,ha='center',bbox=dict(facecolor='white',edgecolor='none',pad=.1))
    box(2.65,.80,'DL Reanalysis',h=.40)
    arrow((2.65,1.29),(2.65,1.00))
    ax.text(3.03,1.145,'Partial /\nUnsupported',fontsize=6.5,ha='center',va='center')
    # Training is external to runtime review routing.
    box(.80,.29,'Trip-MA human labels\nTrain 2,038 usable\nValidation 602',w=1.55,h=.70,gray=True,size=7)
    arrow((1.58,.50),(1.96,.75))
    ax.text(1.78,.40,'Offline',fontsize=6.7,ha='center')
    box(2.65,.10,'Selected Result',h=.32);arrow((2.65,.60),(2.65,.26))
    ax.text(1.725,-.23,'Trip-MA test: 1,474 segments (labels: evaluation only)',ha='center',fontsize=7.1)
    ax.text(1.725,-.40,'Invalid input / processing errors retain their failure status.',ha='center',fontsize=7)
    # Extra plot room is assigned to explicit dataset-role footnotes.
    ax.set_ylim(-.5,4.65)
    for ext in ('svg','pdf','png'):
        fig.savefig(OUT/f'architecture_compact.{ext}',dpi=450,bbox_inches='tight',pad_inches=.04)
    plt.close(fig)
    print('Compact architecture includes runtime, training, validation and test dataset roles.')


if __name__=='__main__':build()
