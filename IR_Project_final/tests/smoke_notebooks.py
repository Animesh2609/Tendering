"""Bounded integration check of the original preprocessing and all seven notebooks.

Run from IR_Project_final/: python tests/smoke_notebooks.py
Downloads/caches the real 20 Newsgroups corpus, selects 15 documents per source
category, runs real spaCy preprocessing, and caps PLSA fits/fold-in at three
iterations. Original grids, loops, evaluation and artifact saving still run.
All generated artifacts live in executed_notebooks/smoke/; they are not research
results and never replace the reference results/ directory.
"""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import shutil
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from sklearn.datasets import fetch_20newsgroups
from src.plsa_model import PLSA


def limited_fetch(*args, **kwargs):
    # Cache the full download outside the smoke workspace for later full runs.
    kwargs['data_home'] = str(ROOT / 'data' / 'raw')
    corpus = fetch_20newsgroups(*args, **kwargs)
    rng = np.random.default_rng(42)
    ids = np.concatenate([
        rng.choice(np.flatnonzero(corpus.target == label), 15, replace=False)
        for label in np.unique(corpus.target)
    ])
    corpus.data = [corpus.data[i] for i in ids]
    corpus.target = corpus.target[ids]
    if hasattr(corpus, 'filenames'):
        corpus.filenames = corpus.filenames[ids]
    return corpus


original_fit, original_fold = PLSA.fit, PLSA.fold_in


def bounded_fit(self, counts):
    self.max_iter = min(3, self.max_iter)
    return original_fit(self, counts)


def bounded_fold(self, counts, max_iter=100):
    return original_fold(self, counts, max_iter=min(3, max_iter))


@contextmanager
def working_directory(path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def execute(path):
    scope = {'__name__': '__main__'}
    notebook = json.loads(path.read_text(encoding='utf-8'))
    for index, cell in enumerate(notebook['cells']):
        if cell['cell_type'] == 'code':
            print(f'{path.name}: cell {index + 1}', flush=True)
            exec(compile(''.join(cell['source']), f'{path.name}:cell{index + 1}', 'exec'), scope)
            plt.close('all')
    print(f'PASS {path.name}', flush=True)


def main():
    work = ROOT / 'executed_notebooks' / 'smoke'
    work.mkdir(parents=True, exist_ok=True)
    for folder in ['src', 'experiments']:
        shutil.copytree(ROOT / folder, work / folder, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('__pycache__', '.ipynb_checkpoints'))
    with working_directory(work), patch('sklearn.datasets.fetch_20newsgroups', limited_fetch):
        execute(work / 'src' / 'preprocessing.ipynb')
    with working_directory(work), patch.object(PLSA, 'fit', bounded_fit), patch.object(PLSA, 'fold_in', bounded_fold):
        for path in sorted((work / 'experiments').glob('*.ipynb')):
            execute(path)
    print('PASS: preprocessing + seven experiment code paths. Smoke outputs are not research findings.')


if __name__ == '__main__':
    main()
