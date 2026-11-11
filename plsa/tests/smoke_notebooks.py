"""Execute every notebook on a small real-corpus sample with bounded EM budgets.

Run: python -m tests.smoke_notebooks
This is an integration check, NOT a reproduction of full experiment scores.
The shared loader and real spaCy pipeline run normally. Only corpus size and
PLSA fit/fold-in iteration budgets are patched for this test process. Every
notebook cell executes in order with its original study loops and K grids.
Results go to results-smoke/ and are explicitly tagged smoke.
"""
import json
import os
from pathlib import Path
from unittest.mock import patch

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from IPython.display import display

from src.config import EXPERIMENTS
from src.dataset import Corpus, load_corpus
from src.plsa_model import PLSA
from src.results import ROOT, build_report


def sampled_corpus(*args, **kwargs):
    corpus = load_corpus(*args, **kwargs)
    rng = np.random.default_rng(42)
    # Include each original category even when relevance uses supergroups.
    indices = np.concatenate([
        rng.choice(np.flatnonzero(corpus.original_labels == label), 15, replace=False)
        for label in np.unique(corpus.original_labels)
    ])
    return Corpus(corpus.documents[indices], corpus.labels[indices], corpus.target_names,
                  corpus.original_labels[indices], corpus.source_category_names)


original_fit, original_fold = PLSA.fit, PLSA.fold_in


def bounded_fit(self, x):
    self.max_iter = min(self.max_iter, 3)
    return original_fit(self, x)


def bounded_fold(self, x, max_iter=100):
    return original_fold(self, x, max_iter=min(max_iter, 3))


def main():
    os.environ['PLSA_RESULTS_DIR'] = str(ROOT / 'results-smoke')
    os.environ['PLSA_RUN_KIND'] = 'smoke'
    with patch('src.dataset.load_corpus', sampled_corpus), patch.object(PLSA, 'fit', bounded_fit), patch.object(PLSA, 'fold_in', bounded_fold):
        for experiment in EXPERIMENTS:
            namespace = {'__name__': '__main__', 'display': lambda *args, **kwargs: None}
            notebook = json.loads((ROOT / f'{experiment}.ipynb').read_text())
            for i, cell in enumerate(notebook['cells']):
                if cell['cell_type'] != 'code':
                    continue
                print(f'{experiment}: cell {i}', flush=True)
                exec(compile(''.join(cell['source']), f'{experiment}:cell{i}', 'exec'), namespace)
                plt.close('all')
            assert 'result_directory' in namespace
            print(f'PASS {experiment}', flush=True)
    report, _ = build_report(ROOT / 'results-smoke')
    print(report)


if __name__ == '__main__':
    main()
