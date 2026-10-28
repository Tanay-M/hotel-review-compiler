"""Collect existing input CSVs for faculty demos without changing source bytes."""
from pathlib import Path
import csv
import json
import shutil
from hashlib import sha256

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'dataset'
FILES=[
 ('output/datasets/booking_cleaned/booking_italy_cleaned_demo_500.csv','booking_italy_cleaned_demo_500.csv','Real Booking Italy; random cleaned demo subset'),
 *[(f'output/datasets/booking_cleaned/booking_italy_cleaned_part_{i:02d}.csv',f'booking_italy_cleaned_part_{i:02d}.csv','Real Booking Italy; consecutive part of full cleaned corpus') for i in range(1,5)],
 ('output/datasets/real_hotel_demo_100.csv','real_booking_curated_100.csv','Real older Booking source; intentionally curated demonstration'),
 ('output/datasets/real_hotel_random_200.csv','real_booking_random_200.csv','Real older Booking source; random eligible sample'),
 ('output/datasets/semeval_hotels_266_sentences.csv','semeval_hotel_benchmark_266.csv','Real benchmark sentences; human annotations remain in original XML'),
 ('examples/hotel_reviews_100.csv','synthetic_reviews_100.csv','Authored synthetic examples; not organic reviews'),
 ('examples/bulk_demo.csv','synthetic_bulk_regression.csv','Authored regression examples; includes deliberately invalid rows'),
 ('hotel_compiler/web_assets/demo.csv','synthetic_ui_demo_12.csv','Authored UI demo; includes deliberate invalid-input cases'),
 ('output/batches/inputs/demo-100.csv','synthetic_load_test_100.csv','Repeated authored cases used for bulk tests'),
 ('output/batches/inputs/demo-500.csv','synthetic_load_test_500.csv','Repeated authored cases used for bulk tests'),
 ('output/datasets/booking_cleaned/booking_italy_cleaned_all.csv','full_corpus/booking_italy_cleaned_all_3089.csv','Same cleaned Italy corpus; exceeds 1000-row UI limit'),
]

def main():
    DEST.mkdir(exist_ok=True)
    entries=[]
    for source,name,role in FILES:
        src=ROOT/source;target=DEST/name
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists() and target.read_bytes()!=src.read_bytes():
            raise RuntimeError(f'Refusing to overwrite a different dataset copy: {target}')
        shutil.copyfile(src,target)
        with target.open(encoding='utf-8-sig',newline='') as f:
            reader=csv.reader(f);headers=next(reader);rows=list(reader)
        assert headers in (['sr.no','review'],['review_id','review_text']), (source,headers)
        assert sha256(src.read_bytes()).digest()==sha256(target.read_bytes()).digest()
        entries.append({'file':name,'source':source,'role':role,'rows':len(rows),'columns':headers,
                        'sha256':sha256(target.read_bytes()).hexdigest(),'ui_uploadable':len(rows)<=1000})
    (DEST/'manifest.json').write_text(json.dumps({'purpose':'Local faculty demonstration copies of existing input datasets',
        'training':'No new model was trained. These files served demonstration, regression, vocabulary-development or evaluation roles.',
        'copy_policy':'Byte-identical copies; original files are retained. No review editing or success-based selection.',
        'files':entries},indent=2),encoding='utf-8')
    table='\n'.join(f'| `{r["file"]}` | {r["rows"]:,} | {r["role"]} |' for r in entries)
    readme='''# Faculty demonstration datasets

Start with **booking_italy_cleaned_demo_500.csv** for the real-data demonstration.
Open CSV & dashboard, choose SentiWordNet or Hybrid, and upload a file. The page detects the standard `sr.no,review` headers and the earlier `review_id,review_text` demo headers; no manual column fields are needed.

There was **no new model training**. These are the input files used for demonstrations, authored regression/load tests, vocabulary development and evaluation. Output scores, metrics and source-map CSVs are deliberately not mixed into the upload folder.

| Input | Rows | Role |
|---|---:|---|
'''+table+'''

## Important distinctions

- The four cleaned Italy parts contain 1,000, 1,000, 1,000 and 89 reviews. They reconstruct the same 3,089-review corpus; the random 500 is a subset, not additional independent data.
- The file in `full_corpus/` is for offline analysis or viewing in a spreadsheet. It exceeds the website's 1,000-row limit; upload the parts individually.
- Booking Italy is the cleaned derivative: missing markers/control characters and whitespace were processed, blank bodies and exact cleaned duplicates removed. Review wording was not paraphrased or selected based on successful analysis.
- The older real Booking 100/200 are separate previously used samples. The curated 100 intentionally favors explicit language and is not an unbiased accuracy test.
- SemEval input contains the 266 original sentences. Gold annotations are in `data/vendor/real-hotel-research/semeval2015_hotels.xml`, not in the upload CSV. The paper evaluates only the declared mapped scope of 148 classification cases; a whole-file UI run is not that gold-label evaluation.
- Synthetic files are authored/repeated cases. Some include blank text/duplicate IDs intentionally to exercise diagnostics. Never present them as organic reviews.
- The downloaded 20,491-row TripAdvisor source was not used in the paper's reported comparison and is not included as a claimed test set.
- These are copies: original sources remain in place and byte equality is verified in `manifest.json`.
- Dataset attribution and license details: `../output/datasets/ATTRIBUTION.md` and `../data/README.md`. SemEval is a local demonstration copy; redistribution permission has not been established. Do not publish it merely because it is present here.
'''
    (DEST/'README.md').write_text(readme,encoding='utf-8')
    print(json.dumps({'folder':str(DEST),'csv_files':len(entries),'inputs':[{'file':r['file'],'rows':r['rows']} for r in entries]},indent=2))

if __name__=='__main__':main()
