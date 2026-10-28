"""Offline two-system experiments; tabular evidence precedes UI integration."""
from collections import Counter, defaultdict
from datetime import datetime, timezone
from hashlib import sha256
from importlib import metadata, resources
from pathlib import Path
import csv
import platform
import statistics
from time import perf_counter
from zipfile import ZipFile, ZIP_DEFLATED

from .batch import analysis_fingerprint
from .csv_input import read_review_csv
from .exports import _spreadsheet_cell
from .hybrid import HybridEngine, analyze_hybrid_review
from .pipeline import analyze_review
from .research_data import load_semeval
from .research_metrics import (classification_metrics, clustered_accuracy_interval,
                               coarse_category, map_semeval_category, LABELS)
from .sentiment_policy import overall_polarity
from .compiler_profiles import current_profile

SYSTEMS = ('SentiWordNet compiler', 'VADER-TextBlob hybrid')
STRENGTHS = ('Strong Negative','Weak Negative','Neutral','Weak Positive','Strong Positive','Unavailable')


def system_names():
    return (('SentiWordNet compiler (expanded)' if current_profile()=='expanded' else SYSTEMS[0]), SYSTEMS[1])


def write_table(path, rows, fields=None):
    rows=list(rows)
    fields=fields or (list(rows[0]) if rows else [])
    with Path(path).open('x',encoding='utf-8-sig',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=fields);writer.writeheader()
        writer.writerows({k:_spreadsheet_cell(r.get(k)) for k in fields} for r in rows)


def run_metadata(source, engine, role, **extra):
    digest=sha256()
    for name in ('hybrid.py','hybrid_nlp.py','hybrid_vocabulary.py','resources/hybrid_domain.json','resources/hybrid_vocabulary.json','sentiment_policy.py','research_runner.py','research_metrics.py','research_data.py','research_plots.py','research_cli.py'):
        digest.update(name.encode()+b'\0'+resources.files('hotel_compiler').joinpath(name).read_bytes())
    return {
        'created_utc':datetime.now(timezone.utc).isoformat(), 'dataset_role':role,
        'source':str(Path(source).resolve()),'source_sha256':sha256(Path(source).read_bytes()).hexdigest(),
        'analysis_fingerprint':analysis_fingerprint(),'research_code_fingerprint':digest.hexdigest(),
        'compiler_profile':current_profile(),
        'vader_weight':engine.policy.vader_weight,
        'textblob_weight':1-engine.policy.vader_weight,
        'neutral_boundary':engine.policy.bands.neutral,'strong_boundary':engine.policy.bands.strong,
        **engine.versions,**engine.lexicon_hashes,
        'matplotlib':metadata.version('matplotlib'),'numpy':metadata.version('numpy'),
        'python':platform.python_version(),'platform':platform.platform(),
        'processor':platform.processor(),'logical_cpus':__import__('os').cpu_count(),
        'hybrid_version':'independent-pattern-grammar-v2 + reviewed vocabulary 2026-10-18',
        'whole_text_fusion':'Both have evidence: w*VADER + (1-w)*TextBlob. Only one has evidence: use its score. Component failure: unavailable. Subjectivity is not confidence.',
        'aspect_fusion':'Same lexical fusion, with explicit category-context rules where applicable. Rule IDs and pre-rule lexical fusion are exported.',
        'missing_evidence':'Neither lexical nor contextual domain evidence => unavailable, not neutral.',
        'vocabulary_policy':'Category-guarded canonical scoring copy for reviewed native-unknown terms. Original text and pre-normalization scores retained; original library lexicons, fusion weights and contextual rules unchanged.',
        'strength_policy':'Descriptive score intervals, not independently validated five-class human labels.',
        'compiler_scope':f'{current_profile()} deterministic six-category grammar; partial means recognized opinions only.',
        'hybrid_scope':'Independent TextBlob Pattern POS/NP/VP chunks and rule attachment; six-category lexicon separate from baseline. No dependency parser or trained hotel classifier.',
        'evaluation_design':'Development/exploratory comparison; previously inspected SemEval errors mean this is not an untouched holdout.',
        **extra,
    }


def export_metadata(out, values):
    write_table(Path(out)/'run_metadata.csv',({'field':k,'value':v} for k,v in values.items()))
    # Capture the exact project code/resources with the evidence. No raw input,
    # credentials, local environments or unrelated project files are included.
    if 'research_code_fingerprint' in values:
        with ZipFile(Path(out)/'source_snapshot.zip','x',compression=ZIP_DEFLATED) as archive:
            root=Path(__file__).resolve().parent
            for path in sorted(root.glob('*.py')):
                archive.write(path,f'hotel_compiler/{path.name}')
            for path in sorted((root/'resources').rglob('*')):
                if path.is_file():archive.write(path,'hotel_compiler/'+path.relative_to(root).as_posix())
            archive.write(root.parent/'pyproject.toml','pyproject.toml')
        installed=sorted(f'{d.metadata["Name"]}=={d.version}' for d in metadata.distributions()
                         if d.metadata['Name'] and d.metadata['Name'].lower()!='team17-hotel-compiler')
        (Path(out)/'environment_lock.txt').write_text('\n'.join(installed)+'\n',encoding='utf-8')


def compare_csv(path, out, engine, role, *, repeats=5, text_column='review', id_column='sr.no'):
    SYSTEMS=system_names()
    source=read_review_csv(path,text_column=text_column,id_column=id_column)
    rows=[];opinions=[];diagnostics=[];valid=[];token_rows=[];phrase_rows=[];segment_rows=[]
    for item in source.rows:
        identifier=f'research-{item.ordinal:06d}'
        row={'row_id':identifier,'supplied_id':item.supplied_review_id,'review':item.review_text,
             'execution_status':'invalid_input' if item.issues else 'analyzed',
             'compiler_status':'','compiler_overall':'','compiler_mean':None,'compiler_score_scope':'unavailable',
             'compiler_net_band':'Unavailable','hybrid_aspect_mean':None,'hybrid_aspect_overall':'Unanalyzed',
             'hybrid_aspect_status':'not_run','hybrid_diagnostics':'','hybrid_extracted_aspects':0,
             'hybrid_aspect_net_band':'Unavailable','hybrid_scored_aspects':0,'extracted_aspects':0,
             'hybrid_whole_text_score':None,'hybrid_whole_text_label':'Unanalyzed',
             'hybrid_whole_text_band':'Unavailable','hybrid_whole_text_status':'not_run',
             'vader_compound':None,'textblob_polarity':None,'textblob_subjectivity':None,
             'component_disagreement':False,'token_count':0,'clause_count':0,'diagnostics':'',
             'review_sha256':sha256(item.review_text.encode()).hexdigest()}
        if item.issues:
            row['diagnostics']='; '.join(i.code for i in item.issues)
            rows.append(row);continue
        base=analyze_review(item.review_text,identifier)
        hybrid=analyze_hybrid_review(item.review_text,identifier,engine=engine)
        valid.append(item.review_text)
        whole=hybrid.whole_text
        row.update(compiler_status=base.status,compiler_overall=base.overall,
                   compiler_mean=base.review_score,compiler_score_scope=base.review_score_scope,
                   compiler_net_band=base.net_score_band,hybrid_aspect_mean=hybrid.aspect_mean_score,
                   hybrid_aspect_status=hybrid.aspect_analysis_status,
                   hybrid_diagnostics='; '.join(d.code for d in hybrid.diagnostics),
                   hybrid_extracted_aspects=len(hybrid.records),
                   hybrid_aspect_overall=hybrid.overall,
                   hybrid_aspect_net_band=engine.policy.bands.strength(hybrid.aspect_mean_score),
                   hybrid_scored_aspects=sum(r.score is not None for r in hybrid.records),
                   extracted_aspects=len(base.records),hybrid_whole_text_score=whole.score,
                   hybrid_whole_text_label=whole.polarity,hybrid_whole_text_band=whole.strength,
                   hybrid_whole_text_status=whole.status,vader_compound=whole.vader_compound,
                   textblob_polarity=whole.textblob_polarity,textblob_subjectivity=whole.textblob_subjectivity,
                   component_disagreement=whole.component_disagreement,token_count=len(base.tokens),
                   clause_count=len(base.ast.clauses),diagnostics='; '.join(d.code for d in base.diagnostics))
        rows.append(row)
        for d in base.diagnostics:
            diagnostics.append({'row_id':identifier,'system':SYSTEMS[0],'stage':d.stage,'code':d.code,
                                'start':d.start,'end':d.end,'message':d.message})
        for d in hybrid.diagnostics:
            diagnostics.append({'row_id':identifier,'system':SYSTEMS[1],'stage':d.stage,'code':d.code,
                                'start':d.start,'end':d.end,'message':d.message})
        for index,b in enumerate(base.records,1):
            e=b.evidence
            opinions.append({'row_id':identifier,'system':SYSTEMS[0],'opinion_id':index,'category':b.category,'issue':b.issue,
                             'original_opinion_expression':b.opinion_expression,'source_start':b.start,'source_end':b.end,
                             'swn_synset':e.synset,'swn_positive':e.positive_score,'swn_negative':e.negative_score,
                             'swn_objective':e.objective_score,'swn_lexical':e.lexical_score,'domain_score':e.domain_score,
                             'domain_rule_id':e.domain_rule_id,'intensity_multiplier':e.intensity_multiplier,
                             'negation_multiplier':e.negation_multiplier,'compiler_final':b.score,
                             'compiler_polarity':b.polarity,'compiler_strength':b.strength})
        for index,h in enumerate(hybrid.records,1):
            he=h.evidence
            opinions.append({'row_id':identifier,'system':SYSTEMS[1],'opinion_id':index,'category':h.category,'issue':h.issue,
                             'original_opinion_expression':h.opinion_expression,'source_start':h.start,'source_end':h.end,
                             'aspect_term':h.aspect_term,'aspect_start':h.aspect_start,'aspect_end':h.aspect_end,
                             'grammar_pattern':h.grammar_pattern,'inherited_subject':h.inherited,
                             'hybrid_score':he.score,'hybrid_polarity':he.polarity,'hybrid_strength':he.strength,
                             'hybrid_status':he.status,'hybrid_context_scope':h.context_scope,
                             'vader_compound':he.vader_compound,'vader_pos':he.vader_positive,
                             'vader_neu':he.vader_neutral,'vader_neg':he.vader_negative,
                             'textblob_polarity':he.textblob_polarity,'textblob_subjectivity':he.textblob_subjectivity,
                             'textblob_assessed_phrases':'; '.join(' '.join(a[0]) for a in he.textblob_assessments),
                             'component_disagreement':he.component_disagreement,'hybrid_errors':'; '.join(he.errors),
                             'fusion_rule':he.fusion_rule,'lexical_fusion_score':he.lexical_fusion_score,
                             'hybrid_domain_rule_id':he.domain_rule_id,'domain_matched_text':he.domain_matched_text,
                             'vocabulary_scoring_text':(he.vocabulary_normalization or {}).get('scoring_text',''),
                             'vocabulary_aliases':'; '.join(f"{m['original']} -> {m['canonical']}" for m in (he.vocabulary_normalization or {}).get('matches',[])),
                             'original_vader_compound':(he.vocabulary_normalization or {}).get('original_evidence',{}).get('vader_compound',he.vader_compound),
                             'original_textblob_polarity':(he.vocabulary_normalization or {}).get('original_evidence',{}).get('textblob_polarity',he.textblob_polarity)})
        if hybrid.language:
            token_rows.extend({'row_id':identifier,**vars(t)} for t in hybrid.language.tokens)
            phrase_rows.extend({'row_id':identifier,**p} for p in hybrid.language.noun_phrases)
            segment_rows.extend({'row_id':identifier,**s,'candidate_indexes':','.join(map(str,s['candidate_indexes']))} for s in hybrid.language.segments)
    write_table(out/'review_results.csv',rows)
    write_table(out/'opinion_results.csv',opinions,fields=list(dict.fromkeys(k for r in opinions for k in r)) if opinions else
                ['row_id','opinion_id','category','issue','compiler_final','hybrid_score'])
    write_table(out/'diagnostics.csv',diagnostics,fields=['row_id','system','stage','code','start','end','message'])
    write_table(out/'hybrid_tokens.csv',token_rows,['row_id','text','pos','chunk','preposition','start','end','sentence'])
    write_table(out/'hybrid_noun_phrases.csv',phrase_rows,['row_id','text','start','end'])
    write_table(out/'hybrid_segments.csv',segment_rows,['row_id','text','start','end','sentence','candidate_indexes'])
    counts=Counter(r['compiler_status'] or r['execution_status'] for r in rows)
    hybrid_counts=Counter(r['hybrid_aspect_status'] if r['execution_status']=='analyzed' else r['execution_status'] for r in rows)
    write_table(out/'coverage.csv',[{'system':system,'status':status,'reviews':counter[status],'submitted':len(rows),
                'percent':100*counter[status]/len(rows) if rows else None,'scope':role}
                for system,counter in zip(SYSTEMS,(counts,hybrid_counts))
                for status in ('complete','partial','unsupported','invalid_input','processing_error')])
    strengths=[]
    for system,key in [(SYSTEMS[0],'compiler_net_band'),(SYSTEMS[1],'hybrid_aspect_net_band')]:
        counts_strength=Counter(r[key] for r in rows)
        strengths.extend({'system':system,'scope':'recognized-aspect review mean','band':band,
                          'reviews':counts_strength[band],'submitted':len(rows)} for band in STRENGTHS)
    write_table(out/'strength_distribution.csv',strengths)
    write_table(out/'dataset_description.csv',[{'dataset_role':role,'submitted':len(rows),'valid':len(valid),
                'unique_supplied_texts':len({r['review'] for r in rows}),
                'mean_characters':statistics.mean(map(len,valid)) if valid else None,
                'gold_sentiment_labels':'not provided; no accuracy or F1 inferred',
                'compiler_extracted_opinions':sum(r['extracted_aspects'] for r in rows),
                'hybrid_extracted_opinions':sum(r['hybrid_extracted_aspects'] for r in rows)}])
    modules=[{'module':'1 Preprocessing and lexical analysis','measure':'tokens','count':sum(r['token_count'] for r in rows)},
             {'module':'2 Syntax and semantic analysis','measure':'clauses','count':sum(r['clause_count'] for r in rows)},
             {'module':'2 Syntax and semantic analysis','measure':'baseline recognized opinions','count':sum(r['extracted_aspects'] for r in rows)},
             {'module':'2 Syntax and semantic analysis','measure':'hybrid attached contexts','count':sum(r['hybrid_extracted_aspects'] for r in rows)},
             {'module':'2 Syntax and semantic analysis','measure':'TextBlob POS/chunk tokens','count':len(token_rows)},
             {'module':'3 Sentiment and strength','measure':'hybrid scored whole texts','count':sum(r['hybrid_whole_text_score'] is not None for r in rows)},
             {'module':'4 Synthesis and reporting','measure':'preserved review rows','count':len(rows)}]
    write_table(out/'module_results.csv',modules)
    timing=benchmark(valid,engine,repeats) if valid and repeats else []
    write_table(out/'runtime_runs.csv',timing,['system','reviews','repeat','seconds','timing_scope'])
    runtime_summary=[]
    for (system,size),group in _group(timing,lambda r:(r['system'],r['reviews'])).items():
        times=[r['seconds'] for r in group]
        runtime_summary.append({'system':system,'reviews':size,'repeats':len(times),
                                'mean_seconds':statistics.mean(times),'median_seconds':statistics.median(times),
                                'stdev_seconds':statistics.stdev(times) if len(times)>1 else 0,
                                'reviews_per_second':size/statistics.mean(times)})
    write_table(out/'runtime_summary.csv',runtime_summary,['system','reviews','repeats','mean_seconds','median_seconds','stdev_seconds','reviews_per_second'])
    export_metadata(out,run_metadata(path,engine,role,repeats=repeats,
                    timing_scope='Warm independent end-to-end core runs. Hybrid includes frontend, expression scores and whole text; compiler includes frontend and SentiWordNet. Excludes I/O, plots and package initialization.'))
    from .research_plots import comparison_figures
    comparison_figures(out,rows,strengths,runtime_summary)
    _write_notes(out,role,len(rows),counts,len(opinions),runtime_summary,hybrid_counts)
    return rows


def _group(rows,key):
    groups=defaultdict(list)
    for row in rows: groups[key(row)].append(row)
    return groups


def benchmark(texts,engine,repeats):
    SYSTEMS=system_names()
    # Sizes use only existing reviews, never fabricate/repeat rows to reach 500.
    sizes=sorted({min(20,len(texts)),min(50,len(texts)),min(100,len(texts)),len(texts)})
    analyze_review(texts[0]);analyze_hybrid_review(texts[0],engine=engine)
    records=[]
    for size in sizes:
        for repeat in range(1,repeats+1):
            order=(0,1) if repeat%2 else (1,0)
            for method in order:
                start=perf_counter()
                for text in texts[:size]:
                    if method==0:analyze_review(text)
                    else:analyze_hybrid_review(text,engine=engine)
                elapsed=perf_counter()-start
                records.append({'system':SYSTEMS[method],'reviews':size,'repeat':repeat,'seconds':elapsed,
                                'timing_scope':'warm independent pipelines; no I/O or plots'})
    return records


def evaluate_semeval(path,out,engine,*,bootstrap_repeats=1000):
    SYSTEMS=system_names()
    sentences=load_semeval(path);predictions=[];scope_rows=[];tuple_counts={s:Counter() for s in SYSTEMS}
    cases={s:[] for s in SYSTEMS};excluded=Counter()
    for sentence in sentences:
        gold=set()
        for opinion in sentence['opinions']:
            mapped=map_semeval_category(opinion['category'])
            if mapped is None:
                excluded[opinion['category']]+=1
            else:
                gold.add((mapped,opinion['polarity'].capitalize()))
        scope_rows.append({'parent_id':sentence['parent_id'],'sentence_id':sentence['sentence_id'],
                           'gold_annotations':len(sentence['opinions']),'mapped_coarse_pairs':len(gold),
                           'eligible_sentence':bool(gold)})
        if not gold:continue
        base=analyze_review(sentence['text'],sentence['sentence_id'])
        hybrid=analyze_hybrid_review(sentence['text'],sentence['sentence_id'],engine=engine)
        pair_sets=[{(coarse_category(r.category),r.polarity) for r in base.records},
                   {(coarse_category(r.category),r.polarity) for r in hybrid.records if r.score is not None}]
        for system,actual in zip(SYSTEMS,pair_sets):
            tuple_counts[system].update(gold=len(gold),predicted=len(actual),matched=len(gold&actual))
            for category in sorted({c for c,_ in gold}):
                gold_labels={p for c,p in gold if c==category}
                # Single gold polarity per coarse category is a declared scoring
                # subtask; conflicting coarse labels remain in extraction F1.
                if len(gold_labels)!=1:continue
                prediction=overall_polarity(p for c,p in actual if c==category)
                row={'system':system,'parent_id':sentence['parent_id'],'sentence_id':sentence['sentence_id'],
                     'text':sentence['text'],'category':category,'gold':next(iter(gold_labels)),
                           'prediction':prediction,'compiler_status':base.status,
                           'hybrid_status':hybrid.aspect_analysis_status}
                cases[system].append(row);predictions.append(row)
    if not cases[SYSTEMS[0]]:
        raise ValueError('No eligible unambiguous mapped gold classification cases were found.')
    metrics=[];class_rows=[];confusions=[]
    for system in SYSTEMS:
        result=classification_metrics(cases[system]);low,high=clustered_accuracy_interval(cases[system],repeats=bootstrap_repeats)
        tc=tuple_counts[system]
        metrics.append({'system':system,'task':'end-to-end coarse category sentiment; eligible mapped sentences',
                        **{k:v for k,v in result.items() if k!='classes'},'accuracy_ci95_low':low,'accuracy_ci95_high':high,
                        'gold_coarse_pairs':tc['gold'],'predicted_coarse_pairs':tc['predicted'],'matched_coarse_pairs':tc['matched'],
                        'tuple_precision':tc['matched']/tc['predicted'] if tc['predicted'] else 0,
                        'tuple_recall':tc['matched']/tc['gold'] if tc['gold'] else 0,
                        'tuple_f1':2*tc['matched']/(tc['gold']+tc['predicted']) if tc['gold']+tc['predicted'] else 0})
        class_rows.extend({'system':system,**r} for r in result['classes'])
        for actual in LABELS:
            for predicted in (*LABELS,'Mixed','Unanalyzed'):
                confusions.append({'system':system,'gold':actual,'prediction':predicted,
                                   'count':sum(r['gold']==actual and r['prediction']==predicted for r in cases[system])})
    write_table(out/'metrics.csv',metrics);write_table(out/'per_class_metrics.csv',class_rows)
    write_table(out/'predictions.csv',predictions);write_table(out/'confusion_counts.csv',confusions)
    write_table(out/'annotation_scope.csv',scope_rows)
    write_table(out/'excluded_annotations.csv',[{'original_category':k,'annotations':v,'reason':'outside fixed six-category crosswalk'} for k,v in excluded.items()])
    keys=[{(r['sentence_id'],r['category']) for r in cases[s] if r['prediction'] in LABELS} for s in SYSTEMS]
    common=keys[0]&keys[1]
    matched=[]
    for system in SYSTEMS:
        result=classification_metrics([r for r in cases[system] if (r['sentence_id'],r['category']) in common])
        matched.append({'system':system,'scope':'Paired common-scored category cases only; excludes extraction/abstention errors',
                        'common_cases':len(common),'all_eligible_classification_cases':len(cases[system]),
                        'accuracy':result['accuracy'],'macro_f1':result['macro_f1']})
    write_table(out/'paired_scored_subset.csv',matched)
    write_table(out/'dataset_description.csv',[{'reviews':len({s['parent_id'] for s in sentences}),
                'sentences':len(sentences),'opinions':sum(len(s['opinions']) for s in sentences),
                'eligible_sentences':sum(r['eligible_sentence'] for r in scope_rows),
                'classification_cases':len(cases[SYSTEMS[0]]),'excluded_original_annotations':sum(excluded.values()),
                'task':'Adapted coarse benchmark, not official SemEval ranking; no five-class gold labels'}])
    export_metadata(out,run_metadata(path,engine,'human-annotated benchmark',bootstrap_repeats=bootstrap_repeats,
                    mapping='ROOMS->Room; FACILITIES/ROOMS_AMENITIES->Facilities; FOOD_DRINKS->Food; SERVICE and predicted Staff->Service; HOTEL#CLEANLINESS->Cleanliness; prices/location/other HOTEL excluded',
                    evaluation='Set of coarse category/polarity pairs per sentence; classification only categories with one gold polarity; all such cases retained including Unanalyzed/Mixed predictions. Not span/issue accuracy.'))
    from .research_plots import benchmark_figures
    benchmark_figures(out,metrics,confusions)
    text=['# Adapted SemEval benchmark results','',
          'This run uses independent human labels under a declared coarse taxonomy. It is not a reproduction of the official SemEval task or a claim about the full benchmark ontology.',
          '',f'Eligible sentences: {sum(r["eligible_sentence"] for r in scope_rows)} / {len(sentences)}. Classification cases: {len(cases[SYSTEMS[0]])}.',
          'Accuracy includes missing/conflicting predictions as errors; conditional accuracy is reported separately. Macro-F1 uses the fixed three classes. Review-cluster bootstrap gives the accuracy interval.',
          'The two systems use independent extraction pipelines. Whole-text hybrid scores are not substituted for missing aspect predictions. Five-band counts are descriptive, not five-class accuracy.',
          'Development/exploratory evaluation: this benchmark was inspected before v2 implementation and must not be described as an untouched test set.', '']
    for metric in metrics:
        text.append(f'{metric["system"]}: correct {metric["correct"]}/{metric["cases"]}; accuracy {metric["accuracy"]:.4f}; macro-F1 {metric["macro_f1"]:.4f}; coarse tuple F1 {metric["tuple_f1"]:.4f}.')
    text+=['','Inference: this comparison measures extraction and scoring together; it does not isolate fusion quality. Do not claim unseen generalization or statistically significant improvement from these point estimates. Preserve this run for development evidence.']
    text+=['','paired_scored_subset.csv compares scoring on identical cases where both systems return a three-class label. This selected subset excludes extraction and abstention failures; its denominators must accompany any quoted accuracy and cannot replace the all-eligible results.']
    (out/'INFERENCES.md').write_text('\n'.join(text)+'\n',encoding='utf-8')
    latex_table(out/'comparison_table.tex',['System','Accuracy','Macro F1','Coverage','Tuple F1'],
                [[m['system'],f'{m["accuracy"]:.3f}',f'{m["macro_f1"]:.3f}',f'{m["coverage"]:.3f}',f'{m["tuple_f1"]:.3f}'] for m in metrics],
                'Two-system evaluation on the declared mapped SemEval scope.','tab:comparison')
    return metrics


def latex_table(path,headers,rows,caption,label):
    def escape(value):
        return ''.join({'&':r'\&','%':r'\%','_':r'\_','#':r'\#','$':r'\$'}.get(c,c) for c in str(value))
    environment='table*' if len(headers)>=4 else 'table'
    lines=[r'\begin{'+environment+'}[t]',r'\centering',r'\caption{'+caption+'}',r'\label{'+label+'}',
           r'\small',r'\begin{tabular}{'+'l'+'r'*(len(headers)-1)+'}',r'\hline',
           ' & '.join(map(escape,headers))+r' \\',r'\hline']
    lines+=[' & '.join(map(escape,row))+r' \\' for row in rows]
    lines += [r'\hline',r'\end{tabular}',r'\end{'+environment+'}']
    Path(path).write_text('\n'.join(lines)+'\n',encoding='utf-8')


def _write_notes(out,role,total,counts,opinions,timing,hybrid_counts):
    lines=['# Implementation and descriptive results','',f'Dataset role: {role}. Submitted: {total}. Extracted opinions: {opinions}.',
           'No independent sentiment gold labels were supplied for this CSV. Accuracy, precision, recall and F1 are intentionally not invented.',
           '', '## Module 1 Input preparation and lexical analysis','Review text and row identity are preserved. review_results.csv provides token counts and source-text hashes.',
          '', '## Module 2 Syntax and semantic interpretation',f'Baseline processing: {dict(counts)}. Independent hybrid processing: {dict(hybrid_counts)}. diagnostics.csv retains unsupported language. TextBlob POS, NP chunks and grammatical segments are exported separately.',
          '', '## Module 3 Sentiment evidence and five bands','opinion_results.csv has separate system rows, not a positional zip of unrelated extractions. It preserves baseline P/N and modifiers, hybrid component evidence, lexical fusion and any contextual domain rule. Both tools with evidence: weighted mean; only one with evidence: its score. The band distribution describes magnitude, not confidence or validated human intensity.',
           '', '## Module 4 Synthesis and experiments','review_results.csv keeps one row per submitted review. Aspect means and whole-text hybrid scores have different scopes. Mixed opinions remain distinct from a near-zero mean.',
           '', '## Figures and interpretation',
           'fig_strength: compares bands of recognized-aspect means under the same boundaries. Unavailable scores remain visible; the plot is not accuracy evidence.',
          'fig_availability: separates the two independent aspect processing outcomes from whole-text hybrid lexical evidence. Whole-text availability does not prove complete aspect understanding.',
           'fig_runtime: warm independent core runs with standard-deviation bars; the hybrid includes its additional whole-text scoring work. Cache/package initialization and report rendering are excluded.',
           '', 'Generated vector PDF/SVG and 300-dpi PNG figures can be inserted into the IEEE two-column template. CSV tables retain numeric values, and table snippets are provided as LaTeX supporting artifacts. The manuscript is a later step.',
           'CSV strings beginning with formula characters are apostrophe-escaped for spreadsheet display; hashes refer to original analyzed input. Empty numeric cells mean unavailable.',
           'Re-run into a new output directory; existing evidence is never overwritten.']
    (out/'INFERENCES.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    latex_table(out/'coverage_table.tex',['Outcome','SentiWordNet','Hybrid'],[[s,counts[s],hybrid_counts[s]] for s in ('complete','partial','unsupported','invalid_input','processing_error')],
                'Processing outcomes on the explicitly named dataset scope; these are not accuracy.','tab:coverage')
