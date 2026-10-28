"""Prepare traceable, model-independent Booking demo records as JSON intermediates.

Only whitespace/control cleanup, blank removal and exact cleaned-text deduplication
are performed. No analyzer, grammar, sentiment score, category or gold label is used
for eligibility or random sampling. Final two-column CSVs use the JS export builder.
"""
from collections import Counter
from hashlib import sha256
from pathlib import Path
import csv
import json
import random
import re

ROOT = Path(__file__).resolve().parents[1]
SEED = 172026


def cleaned_text(text):
    # The prepared input joins original feedback fields with newlines. Exact
    # standalone N/A markers carry no feedback; do not remove words like nothing.
    text='\n'.join(line for line in text.splitlines() if line.strip().upper() not in {'N/A','NA','N.A.'})
    text = ''.join(c for c in text if ord(c)>=32 or c in '\t\r\n')
    return re.sub(r'\s+', ' ', text).strip()


def prepare(source):
    records=[];audit=[];seen={};counts=Counter()
    with Path(source).open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f)
        if reader.fieldnames!=['sr.no','review']: raise ValueError('Expected original two-column Booking inputs.')
        for row in reader:
            original=row['review'];text=cleaned_text(original);ordinal=row['sr.no']
            status='retained';duplicate=''
            if not text: status='blank_removed'
            elif text in seen: status='duplicate_removed';duplicate=seen[text]
            else:
                seen[text]=ordinal
                records.append({'source_row':ordinal,'review':text,'original_sha256':sha256(original.encode()).hexdigest(),
                                'cleaned_sha256':sha256(text.encode()).hexdigest()})
            counts[status]+=1
            audit.append({'source_row':ordinal,'status':status,'duplicate_of_source_row':duplicate,
                          'original_sha256':sha256(original.encode()).hexdigest(),
                          'cleaned_sha256':sha256(text.encode()).hexdigest()})
    sample=random.Random(SEED).sample(records,min(500,len(records)))
    return {'records':records,'sample':sample,'audit':audit,'manifest':{
        'source':'Crawl Feeds Booking Hotel Reviews Dataset',
        'source_url':'https://huggingface.co/datasets/crawlfeeds/Booking-Hotel-Reviews-Dataset',
        'license':'CC BY-NC 4.0','input_file':Path(source).relative_to(ROOT).as_posix(),
        'input_sha256':sha256(Path(source).read_bytes()).hexdigest(),'source_rows':sum(counts.values()),
        'cleaning_counts':dict(counts),'demo_rows':len(sample),'seed':SEED,
        'selection':'Uniform random sample of unique nonblank cleaned reviews; no model outputs, aspect vocabulary or grammar filters.',
        'cleaning':'Remove exact standalone N/A/NA/N.A. marker lines and nonprinting C0 controls; collapse whitespace; strip; remove blank bodies and exact cleaned-text duplicates. Retain ordinary words such as nothing.',
        'wording':'No spell correction, paraphrasing, sentiment edits, punctuation repair or sentence extraction.',
        'evaluation_role':'Real-data demonstration and coverage comparison; inspected development corpus without independent aspect gold.'}}


if __name__=='__main__':
    result=prepare(ROOT/'output/datasets/booking_italy/booking_italy_all.csv')
    out=ROOT/'tmp/booking-clean-builder';out.mkdir(parents=True,exist_ok=True)
    (out/'inputs.json').write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(result['manifest'],indent=2))
