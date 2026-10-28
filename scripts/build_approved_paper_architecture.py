"""Lay out the approved dataset-block diagram for a full-width IEEE figure."""
from pathlib import Path
from shutil import copyfile
import build_architecture_approval as draft

ROOT = Path(__file__).resolve().parents[1]


def build():
    # Reflow the vector drawing at native size; all labels retain their font size.
    # The approved nodes, arrows and dataset roles are unchanged.
    original_subplots = draft.plt.subplots
    def paper_subplots(*args, **kwargs):
        kwargs['figsize'] = (8.3, 9.5)
        return original_subplots(*args, **kwargs)
    draft.plt.subplots = paper_subplots
    draft.OUT = ROOT/'tmp/approved-architecture-paper-layout'
    draft.build()
    for ext in ('svg', 'pdf', 'png'):
        copyfile(draft.OUT/f'Team_17_Architecture_Dataset_Blocks_DRAFT.{ext}',
                 ROOT/f'output/paper/assets/architecture_approved.{ext}')
    print('Approved architecture paper assets generated.')


if __name__ == '__main__':build()
