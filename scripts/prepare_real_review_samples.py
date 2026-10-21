"""Prepare traceable real-review demo and random samples without model-output selection.

No compiler, VADER or TextBlob call is used to select rows. Inputs retain only
sr.no/review. Source fields and selection criteria live in separate audit files.
"""
from collections import Counter
import csv
import hashlib
import io
import json
from pathlib import Path
import random
import re
import shutil
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/vendor/real-hotel-research'
OUT = ROOT / 'output/datasets'
AUDIT = OUT / 'provenance'
SEED = 17102026
VOCABULARY_PATH = ROOT / 'hotel_compiler/resources/domain.json'
KNOWN_OPINIONS = set(json.loads(VOCABULARY_PATH.read_text(encoding='utf-8'))['opinions'])
GROUPS = {
    'Room': r'rooms?|beds?|bedrooms?|bathrooms?',
    'Staff': r'staff|receptionists?|personnel',
    'Service': r'(?:room )?service|check[ -]in|check[ -]out',
    'Food': r'breakfast|food|dinner|lunch|meals?|restaurant',
    'Cleanliness': r'cleanliness|hygiene',
    'Facilities': r'wi[ -]?fi|internet|(?:swimming )?pool|air conditioning|air conditioner|lift|elevator|facilities',
}
PATTERNS = {
    name: re.compile(r'^(?:the )?(?:' + terms + r')\s+(?:was|were|is|are)\s+'
                     r'(?:(?:not|very|really|quite|so|extremely|slightly|fairly)\s+){0,2}'
                     r'(?P<opinion>[A-Za-z][A-Za-z-]*)[.!]?$', re.I)
    for name, terms in GROUPS.items()
}
OUTSIDE = re.compile(r'\b(?:location|price|prices|value|expensive|cheap|cheaper|cost|costs|euros?|pounds?)\b|[$£€]', re.I)
QUOTAS = {'Room':20,'Staff':20,'Service':15,'Food':20,'Cleanliness':2,'Facilities':23}

def digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()

def components(row):
    result=[]
    for field, missing in [('Positive_Review','no positive'),('Negative_Review','no negative')]:
        text=row[field].strip()
        if text and text.casefold()!=missing:
            result.append((field,text))
    return result

def reservoir(pool, item, seen, size, rng):
    if len(pool)<size:
        pool.append(item)
    else:
        index=rng.randrange(seen)
        if index<size: pool[index]=item

def write_csv(path, columns, rows):
    with path.open('w',encoding='utf-8-sig',newline='') as handle:
        writer=csv.writer(handle);writer.writerow(columns);writer.writerows(rows)

def main():
    OUT.mkdir(parents=True,exist_ok=True);AUDIT.mkdir(exist_ok=True)
    candidate_pools={name:[] for name in GROUPS}; candidate_counts=Counter()
    group_rng={name:random.Random(SEED+i) for i,name in enumerate(GROUPS)}
    random_pool=[]; rng=random.Random(SEED); eligible=0;seen_text=set();exclusions=Counter()
    source_rows=0
    with zipfile.ZipFile(RAW / 'booking_515k.zip') as archive:
        source_name=next(n for n in archive.namelist() if n.lower().endswith('.csv'))
        with archive.open(source_name) as source:
            reader=csv.DictReader(io.TextIOWrapper(source,encoding='utf-8-sig',newline=''))
            for source_row,row in enumerate(reader,1):
                source_rows+=1; parts=components(row)
                # Only trim outside field whitespace and remove exact missing-field sentinels.
                # Newline joins the supplied fields, without adding sentiment labels or punctuation.
                text='\n'.join(value for _,value in parts)
                if not text or not re.search(r'[A-Za-z]',text):
                    exclusions['no_alphabetic_feedback']+=1;continue
                if len(text)>10000:
                    exclusions['over_10000_characters']+=1;continue
                key=digest(' '.join(text.casefold().split()))
                if key in seen_text:
                    exclusions['duplicate_normalized_text']+=1;continue
                seen_text.add(key);eligible+=1
                record={'source_row':source_row,'review':text,'text_sha256':digest(text),
                        'rating':row['Reviewer_Score'],'hotel':row['Hotel_Name'],
                        'positive_original':row['Positive_Review'],'negative_original':row['Negative_Review'],
                        'fields_used':'+'.join(field for field,_ in parts)}
                reservoir(random_pool,record,eligible,1000,rng)
                # Demo criteria are content-based and frozen before sentiment execution.
                # One supplied feedback field, short explicit aspect predicate, original text.
                if len(parts)!=1 or not 15<=len(text)<=180 or not 3<=len(text.split())<=30:
                    continue
                if OUTSIDE.search(text) or any(ord(c)>127 and c.isalpha() for c in text):
                    continue
                match_groups=[name for name,pattern in PATTERNS.items()
                              if (match:=pattern.search(text)) and match.group('opinion').lower() in KNOWN_OPINIONS]
                if len(match_groups)!=1:
                    continue
                group=match_groups[0];candidate_counts[group]+=1
                reservoir(candidate_pools[group],record,candidate_counts[group],100,group_rng[group])

    selected=[]
    for name,quota in QUOTAS.items():
        choices=candidate_pools[name]
        group_rng[name].shuffle(choices)
        if len(choices)<quota:
            raise ValueError(f'Insufficient untouched real reviews for {name}: {len(choices)} < {quota}')
        selected.extend((name,record) for record in choices[:quota])
    random.Random(SEED+100).shuffle(selected)
    selected_ids={record['source_row'] for _,record in selected}
    rng.shuffle(random_pool)
    holdout=[record for record in random_pool if record['source_row'] not in selected_ids][:200]
    assert len(holdout)==200

    files=[('real_hotel_demo_100.csv',selected),('real_hotel_random_200.csv',[('Random',r) for r in holdout])]
    for filename,records in files:
        write_csv(OUT / filename,['sr.no','review'],[(i,record['review']) for i,(_,record) in enumerate(records,1)])
        columns=['sr.no','source_dataset','source_csv','source_data_row','selection_group','review_sha256',
                 'fields_used','reviewer_score_proxy','hotel_name','positive_original','negative_original']
        write_csv(AUDIT / filename.replace('.csv','_sources.csv'),columns,
                  [(i,'Booking515k',source_name,r['source_row'],group,r['text_sha256'],r['fields_used'],
                    r['rating'],r['hotel'],r['positive_original'],r['negative_original'])
                   for i,(group,r) in enumerate(records,1)])

    # A readable view of every source sentence; XML remains the authoritative gold.
    xml=ET.parse(RAW / 'semeval2015_hotels.xml').getroot()
    sentences=[(review.get('rid'),sentence) for review in xml.iter('Review') for sentence in review.iter('sentence')]
    write_csv(OUT / 'semeval_hotels_266_sentences.csv',['sr.no','review'],
              [(i,s.findtext('text') or '') for i,(_,s) in enumerate(sentences,1)])
    write_csv(AUDIT / 'semeval_sentence_sources.csv',['sr.no','source_review_id','source_sentence_id','gold_opinion_count'],
              [(i,rid,s.get('id'),len(list(s.iter('Opinion')))) for i,(rid,s) in enumerate(sentences,1)])
    with zipfile.ZipFile(RAW / 'tripadvisor_20k.zip') as archive:
        name=next(n for n in archive.namelist() if n.lower().endswith('.csv'))
        target=OUT / 'tripadvisor_original_20491.csv'
        with archive.open(name) as source,target.open('wb') as destination:
            shutil.copyfileobj(source,destination)

    summary={'seed':SEED,'source_rows':source_rows,'eligible_unique_rows':eligible,
             'pre_sampling_exclusions':dict(exclusions),'demo_candidate_counts':dict(candidate_counts),
             'demo_quotas':QUOTAS,'random_rows':len(holdout),'demo_rows':len(selected),
             'selection_uses_model_outputs':False,'cross_set_source_overlap':0,
             'demo_scope':'Explicit aspect predicate with a configured canonical opinion; curated demonstration only',
             'vocabulary_sha256':hashlib.sha256(VOCABULARY_PATH.read_bytes()).hexdigest(),
             'raw_booking_sha256':hashlib.sha256((RAW / 'booking_515k.zip').read_bytes()).hexdigest()}
    # CSV is the human-facing protocol record. JSON is only a temporary builder input.
    write_csv(AUDIT / 'selection_summary.csv',['setting','value'],
              [(key,json.dumps(value,ensure_ascii=False) if isinstance(value,dict) else value) for key,value in summary.items()])
    (ROOT / 'tmp/real_sample_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    for filename,_ in files:
        with (OUT / filename).open(encoding='utf-8-sig',newline='') as handle:
            rows=list(csv.DictReader(handle))
        assert list(rows[0])==['sr.no','review'] and len({r['review'] for r in rows})==len(rows)
    print(json.dumps(summary,indent=2))
    print('First three selected reviews:',*[r['review'] for _,r in selected[:3]],sep='\n')

if __name__=='__main__':main()
