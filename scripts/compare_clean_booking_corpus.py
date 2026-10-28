"""Compare both expanded approaches on every cleaned Booking body, in UI-sized parts."""
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory
import argparse
import csv
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from hotel_compiler.compiler_profiles import compiler_profile
from hotel_compiler.hybrid import HybridEngine
from hotel_compiler.research_runner import compare_csv, write_table, system_names


def read(path):
    with path.open(encoding='utf-8-sig',newline='') as stream:return list(csv.DictReader(stream))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args();destination=args.output_dir.resolve()
    if destination.exists():parser.error('Use a new output directory; old evidence is protected.')
    destination.parent.mkdir(parents=True,exist_ok=True)
    inputs=ROOT/'output/datasets/booking_cleaned'
    all_inputs=read(inputs/'booking_italy_cleaned_all.csv')
    source_map=read(inputs/'all_source_map.csv');rows=[]
    engine=HybridEngine()
    with compiler_profile('expanded'),TemporaryDirectory(prefix='.booking-comparison-',dir=destination.parent) as tmp:
        out=Path(tmp)/'results';out.mkdir()
        for index,part in enumerate(sorted(inputs.glob('booking_italy_cleaned_part_*.csv')),1):
            run=out/f'part_{index:02d}';run.mkdir()
            results=compare_csv(part,run,engine,'inspected_vocabulary_development',repeats=0)
            for row in results:
                ordinal=len(rows)+1
                assert row['review']==all_inputs[ordinal-1]['review']
                assert row['review_sha256']==source_map[ordinal-1]['cleaned_sha256']
                row=dict(row,row_id=f'booking-cleaned-{ordinal:06d}',source_row=source_map[ordinal-1]['source_row'])
                rows.append(row)
            print(f'Completed part {index}: {len(results)} reviews',flush=True)
        assert len(rows)==len(all_inputs)==len(source_map)
        write_table(out/'all_reviews.csv',rows)
        coverage=[]
        for system,key in zip(system_names(),['compiler_status','hybrid_aspect_status']):
            counts=Counter(row[key] for row in rows)
            for status in ['complete','partial','unsupported','invalid_input','processing_error']:
                coverage.append({'system':system,'status':status,'reviews':counts[status],
                                 'submitted':len(rows),'percent':100*counts[status]/len(rows)})
        write_table(out/'coverage.csv',coverage)
        (out/'README.md').write_text(f'# Full cleaned Booking comparison\n\nBoth systems receive the same {len(rows)} cleaned, unique, nonblank source reviews. The 500-review demo is a subset of this corpus, not extra independent data. `all_reviews.csv` retains one result per cleaned source review; part directories retain detailed independent opinions and traces. This inspected development corpus has no independent aspect sentiment labels: coverage and processing status are not accuracy. All model inputs retain source wording after the documented placeholder/whitespace cleanup.\n',encoding='utf-8')
        out.rename(destination)
    print(f'Exported {len(rows)} paired reviews: {destination}')


if __name__=='__main__':main()
