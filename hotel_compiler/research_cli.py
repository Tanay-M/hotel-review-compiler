"""Reproducible offline comparisons and source verification; no WebUI needed."""
import argparse
from pathlib import Path
from tempfile import TemporaryDirectory
import sys

from .hybrid import HybridEngine, HybridPolicy, HybridDependencyError
from .research_data import verify_real_samples
from .research_runner import compare_csv, evaluate_semeval, export_metadata, write_table
from .sentiwordnet import ResourceError


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    verify=sub.add_parser('verify-data',help='Verify samples against original downloaded source rows.')
    verify.add_argument('--dataset-dir',type=Path,default=Path('output/datasets'))
    verify.add_argument('--raw-dir',type=Path,default=Path('data/vendor/real-hotel-research'))
    compare=sub.add_parser('compare',help='One-row-per-review comparison, descriptive tables and scientific figures.')
    compare.add_argument('input',type=Path)
    compare.add_argument('--dataset-role',required=True,choices=['curated_demo','random_real','authored_development','other_declared'])
    compare.add_argument('--text-column',default='review');compare.add_argument('--id-column',default='sr.no')
    compare.add_argument('--repeats',type=int,default=5)
    evaluate=sub.add_parser('evaluate-semeval',help='Explicitly mapped human-gold coarse-category evaluation.')
    evaluate.add_argument('input',type=Path);evaluate.add_argument('--bootstrap-repeats',type=int,default=1000)
    for command in (verify,compare,evaluate):
        command.add_argument('--output-dir',type=Path,required=True,help='Must not already exist; protects prior evidence.')
    for command in (compare,evaluate):
        command.add_argument('--vader-weight',type=float,default=.5)
    args=parser.parse_args(argv)
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    if args.command=='compare' and not 0<=args.repeats<=100:
        parser.error('--repeats must be between 0 and 100 (0 skips timing).')
    if args.command=='evaluate-semeval' and not 100<=args.bootstrap_repeats<=10000:
        parser.error('--bootstrap-repeats must be between 100 and 10000.')
    destination=args.output_dir.resolve()
    if destination.exists():
        parser.error('Output directory already exists. Choose a new run name; prior evidence is protected.')
    try:
        destination.parent.mkdir(parents=True,exist_ok=True)
        with TemporaryDirectory(prefix='.research-build-',dir=destination.parent) as scratch:
            output=Path(scratch)/'results';output.mkdir()
            if args.command=='verify-data':
                rows,info=verify_real_samples(args.dataset_dir,args.raw_dir)
                write_table(output/'source_verification.csv',rows);export_metadata(output,info)
                summary=f'{len(rows)} reviews verified against original archive rows; no source overlap.'
            else:
                engine=HybridEngine(HybridPolicy(args.vader_weight))
                if args.command=='compare':
                    rows=compare_csv(args.input,output,engine,args.dataset_role,repeats=args.repeats,
                                     text_column=args.text_column,id_column=args.id_column)
                    summary=f'{len(rows)} review rows exported. Unlabeled data: no accuracy claim.'
                else:
                    metrics=evaluate_semeval(args.input,output,engine,bootstrap_repeats=args.bootstrap_repeats)
                    summary='\n'.join(f'{m["system"]}: {m["correct"]}/{m["cases"]} correct; macro-F1 {m["macro_f1"]:.4f}' for m in metrics)
            output.rename(destination)
        print(summary);print(f'Output: {destination}')
    except (OSError,ValueError,TypeError,ResourceError,HybridDependencyError) as error:
        print(f'Error: {error}',file=sys.stderr);return 2
    return 0


if __name__=='__main__':
    raise SystemExit(main())
