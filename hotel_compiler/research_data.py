"""Original-source integrity checks; no generated reviews or inferred gold labels."""
import csv
from hashlib import sha256
import io
from pathlib import Path
import xml.etree.ElementTree as ET
from zipfile import ZipFile


def verify_real_samples(dataset_dir, raw_dir):
    dataset_dir, raw_dir = Path(dataset_dir), Path(raw_dir)
    all_sources, outputs, subsets = {}, [], []
    for name, expected in [('real_hotel_demo_100',100),('real_hotel_random_200',200)]:
        path=dataset_dir/f'{name}.csv'
        with path.open(encoding='utf-8-sig',newline='') as handle:
            reader=csv.DictReader(handle)
            if reader.fieldnames != ['sr.no','review']:
                raise ValueError(f'Unexpected input schema: {name}')
            rows=list(reader)
        with (dataset_dir/'provenance'/f'{name}_sources.csv').open(encoding='utf-8-sig',newline='') as handle:
            source_rows=list(csv.DictReader(handle))
        if len(rows)!=expected or len(source_rows)!=expected:
            raise ValueError(f'Unexpected source/input count: {name}')
        ids=set()
        for row,source in zip(rows,source_rows):
            if row['sr.no']!=source['sr.no']:
                raise ValueError('Input/source serial numbers differ.')
            fields={'Positive_Review':source['positive_original'],'Negative_Review':source['negative_original']}
            expected_text='\n'.join(fields[field].strip() for field in source['fields_used'].split('+'))
            if row['review']!=expected_text or sha256(row['review'].encode()).hexdigest()!=source['review_sha256']:
                raise ValueError(f'Review text/source mismatch: {name}/{row["sr.no"]}')
            source_id=int(source['source_data_row']);ids.add(source_id)
            all_sources.setdefault(source_id,[]).append(source)
            outputs.append({'dataset':name,'sr.no':row['sr.no'],'source_data_row':source_id,
                            'text_matches_documented_source_preparation':True,
                            'review_sha256':source['review_sha256'],'original_archive_row_verified':False})
        if len(ids)!=expected:
            raise ValueError('Duplicate parent source rows.')
        subsets.append(ids)
    if subsets[0]&subsets[1]:
        raise ValueError('Demo and random sample overlap.')
    verified=set()
    archive_path=raw_dir/'booking_515k.zip'
    with ZipFile(archive_path) as archive:
        member=next(n for n in archive.namelist() if n.lower().endswith('.csv'))
        with archive.open(member) as handle:
            for number,row in enumerate(csv.DictReader(io.TextIOWrapper(handle,encoding='utf-8-sig',newline='')),1):
                for source in all_sources.get(number,[]):
                    if (source['positive_original']!=row['Positive_Review'] or
                            source['negative_original']!=row['Negative_Review']):
                        raise ValueError(f'Original archive content mismatch at source row {number}.')
                    verified.add(number)
    if verified!=set(all_sources):
        raise ValueError('Some mapped source rows were not found in the archive.')
    for row in outputs:
        row['original_archive_row_verified']=True
    return outputs, {'raw_archive_sha256':sha256(archive_path.read_bytes()).hexdigest(),
                     'verified_reviews':len(outputs),'parent_overlap':0,
                     'meaning':'Matches the published downloaded dataset; human authorship of each source review is not independently authenticated.',
                     'preparation':'Strip outer field whitespace, remove exact missing-field sentinels, join retained original fields with newline; never rewrite internal review wording.'}


def load_semeval(path):
    """Parse a local gold XML as data, never execute remote dataset loaders."""
    payload=Path(path).read_bytes()
    if b'<!DOCTYPE' in payload.upper() or b'<!ENTITY' in payload.upper():
        raise ValueError('External/entity declarations are not supported.')
    root=ET.fromstring(payload)
    return [{'parent_id':review.get('rid'), 'sentence_id':sentence.get('id'),
             'text':sentence.findtext('text') or '',
             'opinions':[dict(opinion.attrib) for opinion in sentence.iter('Opinion')]}
            for review in root.iter('Review') for sentence in review.iter('sentence')]
