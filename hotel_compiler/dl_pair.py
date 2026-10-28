"""Category-conditioned transformer fine-tuning and local independent inference.

No diagnostic selector, generative LLM, synthetic test labels, or lexical scorer.
The transformer and classification head both receive supervised gradient updates.
"""
from hashlib import sha256
import json
from pathlib import Path

from .routed_data import HEADS, STATES

QUERIES = {
    'Room': 'Room and accommodation: bedrooms, beds, bathrooms, comfort and space.',
    'Cleanliness': 'Cleanliness and hygiene of the hotel and its rooms.',
    'Service': 'Service and staff assistance, hospitality, reception and check-in.',
    'Food': 'Food and drinks provided by the hotel, meals and breakfast.',
    'Facilities': 'Hotel building, communal facilities, equipment and business amenities.',
    'Excluded': 'Location, surrounding area, price, cost and value for money.',
    'Other': 'Other overall hotel opinions outside the specific aspect categories.',
    'NotRelated': 'Travel narrative or content unrelated to opinions about this hotel.',
}


def eligible_text(tokenizer, text, max_length):
    return all(len(tokenizer(text, QUERIES[c], truncation=False)['input_ids']) <= max_length for c in HEADS)


class LocalDLModel:
    def __init__(self, folder, *, device='cpu'):
        folder = Path(folder).resolve()
        m = json.loads((folder/'routed_manifest.json').read_text(encoding='utf-8'))
        if m.get('model_type') != 'dl_category_pair' or tuple(m['heads']) != HEADS or tuple(m['states']) != STATES:
            raise ValueError('Unsupported DL category-pair schema.')
        if m['queries'] != QUERIES: raise ValueError('Category query contract changed.')
        for name, digest in m['files'].items():
            p = (folder/name).resolve()
            if not p.is_relative_to(folder) or sha256(p.read_bytes()).hexdigest() != digest:
                raise ValueError('DL model integrity check failed.')
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        self.torch = torch; self.device = device
        self.tokenizer = AutoTokenizer.from_pretrained(str(folder/'transformer'), local_files_only=True)
        self.model = AutoModelForSequenceClassification.from_pretrained(str(folder/'transformer'), local_files_only=True).to(device).eval()
        self.thresholds = m['thresholds']; self.max_length = m['max_length']; self.model_id = m['model_id']

    def predict_many(self, texts):
        indices = [i for i, text in enumerate(texts) if eligible_text(self.tokenizer, text, self.max_length)]
        output = [None]*len(texts)
        requests = [(i, c) for i in indices for c in HEADS]
        for i in indices: output[i] = {}
        with self.torch.inference_mode():
            for start in range(0, len(requests), 16):
                group = requests[start:start+16]
                tokens = self.tokenizer([texts[i] for i,c in group], [QUERIES[c] for i,c in group],
                    padding=True, truncation=False, return_tensors='pt').to(self.device)
                probabilities = self.model(**tokens).logits.softmax(-1).cpu().tolist()
                for (i, c), p in zip(group, probabilities): output[i][c] = dict(zip(STATES, map(float,p)))
        return output


def train(data_dir, output_dir, *, device='cuda', epochs=3, seed=172026, ai_labels=None):
    import os
    os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false'); os.environ.setdefault('HF_HUB_DISABLE_XET', '1')
    from time import perf_counter
    from collections import Counter
    from importlib.metadata import version
    import random
    import math
    import numpy as np
    import torch
    from torch.utils.data import DataLoader
    from transformers import AutoTokenizer, AutoModelForSequenceClassification, get_linear_schedule_with_warmup
    from huggingface_hub import snapshot_download
    from .neural_training import BASE_MODEL, BASE_REVISION, read_rows
    from .neural_data import write_csv
    from .routed_training import choose_thresholds, decoded, pairs, metrics
    out, data = Path(output_dir), Path(data_dir)
    if out.exists(): raise ValueError('Training output exists; use a new run name.')
    if not isinstance(epochs,int) or epochs < 1 or epochs > 5: raise ValueError('Use a bounded 1–5 epoch pilot.')
    if device == 'cuda' and not torch.cuda.is_available(): raise RuntimeError('CUDA unavailable.')
    manifest = json.loads((data/'manifest.json').read_text(encoding='utf-8'))
    for name, digest in manifest['files'].items():
        if sha256((data/name).read_bytes()).hexdigest() != digest: raise ValueError('Prepared source data changed.')
    torch.set_num_threads(4); torch.manual_seed(seed); np.random.seed(seed); random.seed(seed)
    if device == 'cuda': torch.cuda.manual_seed_all(seed); torch.cuda.reset_peak_memory_stats()
    out.mkdir(parents=True); started = perf_counter()
    snapshot = snapshot_download(BASE_MODEL, revision=BASE_REVISION, allow_patterns=['*.json','*.txt','*.safetensors','README.md'])
    tokenizer = AutoTokenizer.from_pretrained(snapshot, local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(snapshot, num_labels=4,
        id2label=dict(enumerate(STATES)), label2id={s:i for i,s in enumerate(STATES)}, local_files_only=True).to(device)
    max_length = 160
    train_rows = read_rows(data/'train.csv'); validation = read_rows(data/'validation.csv')
    provenance = {'human_training_segments':len(train_rows),'ai_training_segments':0,'ai_labels_sha256':None}
    if ai_labels:
        extra = read_rows(ai_labels)
        # AI labels never enter evaluation; exact normalized text leakage guards.
        from .routed_data import normalized
        forbidden = {normalized(r['text']) for split in ('validation','test') for r in read_rows(data/f'{split}.csv')}
        seen = {normalized(r['text']) for r in train_rows}
        for r in extra:
            if r['label_source'] != 'AI_assistant' or r['human_reviewed'] != 'false' or r['split'] != 'train':
                raise ValueError('AI training provenance must remain explicit.')
            if normalized(r['text']) in forbidden or normalized(r['text']) in seen:
                raise ValueError('AI text overlaps training/evaluation text.')
            labels = json.loads(r['labels'])
            if any(c not in HEADS or s not in STATES[1:] for c,s in labels.items()): raise ValueError('Unsupported AI label.')
            seen.add(normalized(r['text'])); train_rows.append(r)
        provenance.update(ai_training_segments=len(extra),ai_labels_sha256=sha256(Path(ai_labels).read_bytes()).hexdigest())
        write_csv(out/'ai_training_labels.csv', extra, list(extra[0]))
    exclusions=[]
    def select(rows, split):
        valid=[]
        for r in rows:
            if eligible_text(tokenizer,r['text'],max_length):valid.append(r)
            else:exclusions.append({'split':split,'id':r['id'],'reason':'paired_token_length_limit'})
        return valid
    admitted=select(train_rows,'train'); valid=select(validation,'validation')
    requests=[(r['text'],QUERIES[c],STATES.index(json.loads(r['labels']).get(c,'Absent')))
              for r in admitted for c in HEADS]
    # Pre-tokenize on CPU once; dynamic batch padding keeps the small GPU budget.
    encoded=tokenizer([x[0] for x in requests],[x[1] for x in requests],truncation=False)
    examples=[{k:encoded[k][i] for k in encoded} | {'labels':requests[i][2]} for i in range(len(requests))]
    def collate(batch):
        y=torch.tensor([r['labels'] for r in batch],dtype=torch.long)
        x=tokenizer.pad([{k:v for k,v in r.items() if k!='labels'} for r in batch],padding=True,return_tensors='pt')
        x['labels']=y;return x
    loader=DataLoader(examples,batch_size=8,shuffle=True,collate_fn=collate,num_workers=0,
                      generator=torch.Generator().manual_seed(seed))
    counts=Counter(r[2] for r in requests)
    weights=torch.tensor([math.sqrt(len(requests)/(4*counts[i])) for i in range(4)],device=device)
    weights=weights/weights.mean()
    loss_fn=torch.nn.CrossEntropyLoss(weight=weights)
    body=[p for n,p in model.named_parameters() if not n.startswith('classifier.')]
    head=[p for n,p in model.named_parameters() if n.startswith('classifier.')]
    optimizer=torch.optim.AdamW([{'params':body,'lr':2e-5},{'params':head,'lr':2e-4}],weight_decay=.01)
    accumulation=2;updates_per_epoch=math.ceil(len(loader)/accumulation)
    scheduler=get_linear_schedule_with_warmup(optimizer,max(1,int(.1*epochs*updates_per_epoch)),epochs*updates_per_epoch)
    scaler=torch.amp.GradScaler('cuda',enabled=device=='cuda')
    encoder_name,encoder_weight=next((n,p) for n,p in model.named_parameters() if 'encoder.layer.0.attention.self.query.weight' in n)
    before=sha256(encoder_weight.detach().cpu().numpy().tobytes()).hexdigest()
    history=[]; losses=[]; best=-1.;best_epoch=None;step=0
    def predict(rows, all_rows):
        model.eval(); output=[None]*len(all_rows); index={r['id']:i for i,r in enumerate(all_rows)}
        req=[(r,c) for r in rows for c in HEADS]
        for r in rows:output[index[r['id']]]={}
        with torch.inference_mode():
            for offset in range(0,len(req),32):
                group=req[offset:offset+32]
                x=tokenizer([r['text'] for r,c in group],[QUERIES[c] for r,c in group],padding=True,truncation=False,return_tensors='pt').to(device)
                prob=model(**x).logits.softmax(-1).cpu().tolist()
                for (r,c),p in zip(group,prob):output[index[r['id']]][c]=dict(zip(STATES,map(float,p)))
        return output
    gold=[json.loads(r['labels']) for r in validation]
    for epoch in range(1,epochs+1):
        model.train();optimizer.zero_grad(set_to_none=True);total=0.; t=perf_counter()
        for batch_number,batch in enumerate(loader,1):
            batch={k:v.to(device) for k,v in batch.items()};y=batch.pop('labels')
            with torch.autocast(device_type=device,dtype=torch.float16,enabled=device=='cuda'):
                logits=model(**batch).logits;loss=loss_fn(logits,y)
            total+=float(loss.detach());scaler.scale(loss/accumulation).backward()
            if batch_number%accumulation==0 or batch_number==len(loader):
                scaler.unscale_(optimizer);torch.nn.utils.clip_grad_norm_(model.parameters(),1.)
                scaler.step(optimizer);scaler.update();scheduler.step();optimizer.zero_grad(set_to_none=True);step+=1
            if batch_number%200==0:
                print(f'Epoch {epoch}/{epochs}, batch {batch_number}/{len(loader)}, mean loss={total/batch_number:.4f}',flush=True)
        values=predict(valid,validation);thresholds=choose_thresholds(gold,values)
        scores=metrics([pairs(g) for g in gold],decoded(values,thresholds))
        entry={'epoch':epoch,'optimizer_steps':step,'mean_training_loss':total/len(loader),
               'epoch_seconds':perf_counter()-t,**scores};history.append(entry)
        print(json.dumps(entry),flush=True)
        write_csv(out/'epoch_metrics.csv',history,list(entry))
        if scores['pair_micro_f1']>best:
            best=scores['pair_micro_f1'];best_epoch=epoch;folder=out/'models/best';folder.mkdir(parents=True,exist_ok=True)
            model.save_pretrained(str(folder/'transformer'),safe_serialization=True);tokenizer.save_pretrained(str(folder/'transformer'))
            checkpoint={'model_type':'dl_category_pair','heads':HEADS,'states':STATES,'queries':QUERIES,
                        'max_length':max_length,'thresholds':thresholds,'epoch':epoch,'validation':scores}
            checkpoint['files']={str(p.relative_to(folder)).replace('\\','/'):sha256(p.read_bytes()).hexdigest()
                                 for p in folder.rglob('*') if p.is_file() and p.name!='routed_manifest.json'}
            checkpoint['model_id']='minilm-dl-pair-'+sha256(json.dumps(checkpoint['files'],sort_keys=True).encode()).hexdigest()[:12]
            (folder/'routed_manifest.json').write_text(json.dumps(checkpoint,indent=2),encoding='utf-8')
    after=sha256(encoder_weight.detach().cpu().numpy().tobytes()).hexdigest()
    if before==after:raise RuntimeError('Transformer weights did not update; do not claim DL fine-tuning.')
    settings={'model_type':'fine-tuned category-conditioned MiniLM transformer','best_epoch':best_epoch,
        'selection':'validation pair micro-F1 only; first epoch wins ties','epochs':epochs,'seed':seed,'max_length':max_length,
        'batch_size':8,'gradient_accumulation':2,'encoder_learning_rate':2e-5,'classifier_learning_rate':2e-4,
        'weight_decay':.01,'class_weights':weights.cpu().tolist(),'training_state_counts':dict(counts),
        'admitted_training_segments':len(admitted),'training_pairs':len(requests),'optimizer_steps':step,
        'encoder_parameter':encoder_name,'encoder_hash_before':before,'encoder_hash_after':after,
        'base_model':BASE_MODEL,'base_revision':BASE_REVISION,'data_provenance':provenance,'source_data_manifest':manifest,
        'versions':{n:version(n) for n in ('torch','transformers','numpy')},
        'total_seconds':perf_counter()-started,'peak_tensor_bytes':torch.cuda.max_memory_allocated() if device=='cuda' else 0,
        'gpu':torch.cuda.get_device_name(0) if device=='cuda' else None,
        'evaluation_scope':'Previously inspected Trip-MA benchmark; later follow-up results are exploratory, not a new untouched test.'}
    # No test labels/predictions are used to select epoch or thresholds.
    (out/'frozen_settings.json').write_text(json.dumps(settings,indent=2),encoding='utf-8')
    write_csv(out/'length_exclusions.csv',exclusions,['split','id','reason'])
    print(f'Training complete. Best validation epoch={best_epoch}; pair F1={best:.4f}. No test scored by trainer.',flush=True)
    return settings


def main(argv=None):
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--data-dir',required=True);p.add_argument('--output-dir',required=True)
    p.add_argument('--epochs',type=int,default=3);p.add_argument('--device',choices=['cpu','cuda'],default='cuda');p.add_argument('--ai-labels')
    args=p.parse_args(argv);train(args.data_dir,args.output_dir,epochs=args.epochs,device=args.device,ai_labels=args.ai_labels)


if __name__=='__main__':main()
