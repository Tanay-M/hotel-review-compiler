"""Publication figures from saved experimental values, never dashboard screenshots."""
from collections import Counter
from pathlib import Path


def _plotting():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'DejaVu Serif','font.size':9,'axes.titlesize':10,
                         'axes.labelsize':9,'legend.fontsize':8,'pdf.fonttype':42,'svg.fonttype':'none'})
    return plt


def _save(fig,out,name):
    for extension in ('pdf','svg','png'):
        fig.savefig(Path(out)/f'{name}.{extension}',dpi=300,bbox_inches='tight')


def comparison_figures(out,rows,strengths,runtime):
    plt=_plotting();colors=['#0072B2','#D55E00']
    labels=['Strong\nnegative','Weak\nnegative','Neutral','Weak\npositive','Strong\npositive','Unavailable']
    systems=list(dict.fromkeys(r['system'] for r in strengths))
    fig,ax=plt.subplots(figsize=(6.9,2.8))
    for index,system in enumerate(systems):
        values=[r['reviews'] for r in strengths if r['system']==system]
        ax.bar([i+(-.2 if index==0 else .2) for i in range(6)],values,width=.38,color=colors[index],label=system)
    ax.set_xticks(range(6),labels);ax.set_ylabel('Review count')
    ax.set_title('Recognized-aspect mean score bands');ax.legend();ax.spines[['top','right']].set_visible(False)
    fig.tight_layout();_save(fig,out,'fig_strength');plt.close(fig)
    counts=Counter(r['compiler_status'] or r['execution_status'] for r in rows)
    hybrid=Counter(r['hybrid_aspect_status'] if r['execution_status']=='analyzed' else r['execution_status'] for r in rows)
    whole=Counter(r['hybrid_whole_text_status'] for r in rows)
    fig,axes=plt.subplots(1,3,figsize=(6.9,2.9))
    for ax,names,values,title,color in [
        (axes[0],['Complete','Partial','Unsupported','Invalid','Error'],[counts[k] for k in ['complete','partial','unsupported','invalid_input','processing_error']], 'SentiWordNet aspects',colors[0]),
        (axes[1],['Complete','Partial','Unsupported','Invalid','Error'],[hybrid[k] for k in ['complete','partial','unsupported','invalid_input','processing_error']], 'Independent hybrid aspects',colors[1]),
        (axes[2],['Scored','No lexical\nevidence','Error /\nnot run'],[whole['scored'],whole['no_lexical_evidence'],whole['processing_error']+whole['not_run']], 'Hybrid whole-text evidence',colors[1])]:
        ax.bar(range(len(names)),values,color=color);ax.set_xticks(range(len(names)),names,rotation=20,ha='right')
        ax.set_title(title);ax.set_ylabel('Review count');ax.spines[['top','right']].set_visible(False)
    fig.tight_layout();_save(fig,out,'fig_availability');plt.close(fig)
    if runtime:
        fig,ax=plt.subplots(figsize=(3.45,2.9))
        for index,system in enumerate(systems):
            points=sorted((r for r in runtime if r['system']==system),key=lambda r:r['reviews'])
            ax.errorbar([r['reviews'] for r in points],[r['mean_seconds'] for r in points],
                        yerr=[r['stdev_seconds'] for r in points],marker='o',capsize=3,
                        label='SentiWordNet' if index==0 else 'Hybrid',color=colors[index])
        ax.set_xlabel('Existing reviews in prefix');ax.set_ylabel('Warm core runtime (s)')
        ax.legend();ax.spines[['top','right']].set_visible(False)
        fig.tight_layout();_save(fig,out,'fig_runtime');plt.close(fig)


def benchmark_figures(out,metrics,confusions):
    plt=_plotting()
    fig,ax=plt.subplots(figsize=(3.45,2.8))
    for index,m in enumerate(metrics):
        ax.bar([i+(-.19 if index==0 else .19) for i in range(3)],
               [m['accuracy'],m['macro_f1'],m['tuple_f1']],width=.36,
               color=['#0072B2','#D55E00'][index],label='SentiWordNet' if index==0 else 'Hybrid')
    ax.set_xticks(range(3),['Accuracy','Macro-F1','Tuple-F1']);ax.set_ylim(0,1)
    ax.set_ylabel('Metric on mapped scope');ax.legend();fig.tight_layout()
    _save(fig,out,'fig_metrics');plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(6.9,2.6))
    labels=['Negative','Neutral','Positive'];predicted=labels+['Mixed','Unanalyzed']
    for ax,m in zip(axes,metrics):
        matrix=[[next(r['count'] for r in confusions if r['system']==m['system'] and r['gold']==g and r['prediction']==p)
                 for p in predicted] for g in labels]
        ax.imshow(matrix,cmap='Blues',aspect='auto',vmin=0)
        for i,row in enumerate(matrix):
            for j,value in enumerate(row):
                ax.text(j,i,str(value),ha='center',va='center',fontsize=8,
                        color='white' if value>max(map(max,matrix))/2 else 'black')
        ax.set_xticks(range(5),['Neg','Neu','Pos','Mixed','Abstain'],rotation=30,ha='right')
        ax.set_yticks(range(3),labels);ax.set_xlabel('Prediction');ax.set_ylabel('Gold')
        ax.set_title('SentiWordNet' if m==metrics[0] else 'VADER-TextBlob hybrid')
    fig.tight_layout();_save(fig,out,'fig_confusion');plt.close(fig)
