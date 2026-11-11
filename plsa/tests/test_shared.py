import ast
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.sparse import csr_matrix

from src.config import EXPERIMENTS, SUPERGROUPS
from src.dataset import map_supergroups
from src.metrics import metrics_at_k
from src.plsa_model import PLSA, train_plsa_restarts
from src.preprocessing import split_train_test, vectorize_counts
from src.retrieval import plsa_query_log_likelihood
from src.results import build_report, export_results, load_latest

ROOT = Path(__file__).resolve().parents[1]


def test_em_probabilities_and_fold_in():
    counts = csr_matrix([[5, 4, 0, 0], [3, 6, 0, 1], [0, 0, 6, 4], [0, 1, 3, 5], [0, 0, 0, 0]])
    model = PLSA(n_topics=2, max_iter=60, tol=1e-8).fit(counts)
    assert np.all(np.diff(model.log_likelihoods) >= -1e-7)
    np.testing.assert_allclose(model.theta_.sum(axis=1), 1)
    np.testing.assert_allclose(model.phi_.sum(axis=1), 1)
    assert np.isfinite(model.phi_).all()
    phi = model.phi_.copy()
    inferred = model.fold_in(csr_matrix([[2, 3, 0, 0], [0, 0, 0, 0]]))
    np.testing.assert_array_equal(model.phi_, phi)
    np.testing.assert_allclose(inferred.sum(axis=1), 1)
    np.testing.assert_allclose(inferred[1], [.5, .5])
    np.testing.assert_allclose(model.theta_, PLSA(n_topics=2, max_iter=60, tol=1e-8).fit(counts).theta_)
    with pytest.raises(ValueError, match='same fitted vocabulary'):
        model.fold_in(csr_matrix([[1, 2]]))


def test_restarts_select_largest_training_likelihood():
    model, runs = train_plsa_restarts(csr_matrix([[2, 0, 1], [0, 3, 0], [1, 1, 1]]), n_topics=2, n_restarts=3, max_iter=5)
    assert model.log_likelihoods[-1] == max(score for _, score in runs)
    assert len({run.random_state for run, _ in runs}) == 3


def test_shared_metrics_hand_calculated():
    result = metrics_at_k([4, 3, 2, 1], [1, 0, 1, 1], 1, k=3)
    assert result['Precision@3'] == pytest.approx(2 / 3)
    assert result['Recall@3'] == pytest.approx(2 / 3)
    assert result['AP@3'] == pytest.approx((1 + 2 / 3) / 3)
    assert result['NDCG@3'] == pytest.approx(1.5 / (1 + 1 / np.log2(3) + .5))
    assert result['MRR'] == 1
    assert metrics_at_k([1], [1], 1, k=10)['Precision@10'] == 1
    assert all(value == 0 for value in metrics_at_k([], [], 1).values())
    assert all(value == 0 for value in metrics_at_k([1], [0], 1).values())


def test_query_likelihood_matches_dense_equation():
    theta = np.array([[.8, .2], [.1, .9]])
    phi = np.array([[.7, .2, .1], [.1, .3, .6]])
    q = csr_matrix([[2., 0., 1.]])
    background = np.array([.3, .3, .4])
    expected = np.log(.95 * (theta @ phi) + .05 * background) @ q.toarray()[0]
    actual = plsa_query_log_likelihood(q, theta, phi, background_probability=background, background_weight=.05)
    np.testing.assert_allclose(actual, expected)
    np.testing.assert_array_equal(plsa_query_log_likelihood(csr_matrix((1, 3)), theta, phi), [0, 0])


def test_train_only_vocabulary_and_aligned_split():
    train = ['apple pear', 'apple pear', 'apple pear', 'orange grape', 'orange grape', 'orange grape']
    vectorizer, x, heldout = vectorize_counts(train, ['unseen apple'])
    assert 'unseen' not in vectorizer.vocabulary_
    assert heldout.sum() == 1
    docs = np.arange(40)
    labels = np.repeat([0, 1], 20)
    a, b, ya, yb, oa, ob = split_train_test(docs, labels, docs + 100, test_size=.2)
    np.testing.assert_array_equal(a + 100, oa)
    np.testing.assert_array_equal(b + 100, ob)
    assert not set(a) & set(b)
    assert len(b) == 8


def test_group_mapping_covers_original_categories():
    names = sorted(name for group in SUPERGROUPS.values() for name in group)
    mapped = map_supergroups(np.arange(20), names)
    assert len(mapped) == 20
    assert set(mapped) == set(range(6))
    with pytest.raises(ValueError):
        map_supergroups([0], ['unknown'])


def test_notebooks_import_shared_implementations():
    forbidden = {'PLSA', 'preprocess_texts', 'train_plsa_restarts', 'metrics_at_k', 'make_mixed_document', 'plsa_query_log_likelihood'}
    for experiment in EXPERIMENTS:
        notebook = json.loads((ROOT / f'{experiment}.ipynb').read_text())
        code = '\n'.join(''.join(c['source']) for c in notebook['cells'] if c['cell_type'] == 'code')
        tree = ast.parse(code)
        assert not {n.name for n in ast.walk(tree) if isinstance(n, (ast.ClassDef, ast.FunctionDef))} & forbidden
        assert 'from src.plsa_model import PLSA' in code
        assert 'load_corpus(CONFIG["corpus"]' in code
        assert 'export_results(EXPERIMENT' in code
        assert not any(x in code for x in ['fetch_20newsgroups(', 'CountVectorizer(', 'TfidfVectorizer(', 'spacy.load('])


def test_result_export_and_report(tmp_path):
    name = 'PLSA_Baseline'
    table = pd.DataFrame({'method': ['PLSA', 'PLSA'], 'AP@k': [.5, 1.0], 'Precision@k': [.4, .8]})
    export_results(name, {'evaluation_df': table, 'docs_train': ['a'], 'SEED': 42}, tmp_path, run_kind='smoke')
    report, summary = build_report(tmp_path)
    assert summary['MAP@10'].iloc[0] == .75
    assert summary['Precision@10'].iloc[0] == pytest.approx(.6)
    assert summary['run_kind'].iloc[0] == 'smoke'
    assert not summary['source_changed'].iloc[0]
    assert 'Not run yet' in report.read_text()
    assert 'do not report these numbers' in report.read_text()
    run, manifest = load_latest(tmp_path, name)
    manifest['source_hashes'] = {}
    (run / 'manifest.json').write_text(json.dumps(manifest))
    _, summary = build_report(tmp_path)
    assert summary['source_changed'].iloc[0]


@pytest.mark.parametrize('fail', [False, True])
def test_notebook_runner_uses_current_python_and_stops_kernel(tmp_path, monkeypatch, fail):
    import sys
    import nbformat
    import jupyter_client
    from nbclient.exceptions import CellExecutionError
    import Result

    managers = []
    original_manager = jupyter_client.KernelManager

    def tracked_manager(*args, **kwargs):
        manager = original_manager(*args, **kwargs)
        managers.append(manager)
        return manager

    monkeypatch.setattr(jupyter_client, 'KernelManager', tracked_manager)
    monkeypatch.setattr(Result, 'ROOT', tmp_path)
    code = 'raise ValueError("intentional test error")' if fail else (
        f'import sys, os\nassert sys.executable == {sys.executable!r}\n'
        'assert os.environ["PLSA_RUN_KIND"] == "full"\nprint("runner passed")'
    )
    notebook = nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell(code)])
    nbformat.write(notebook, tmp_path / 'check.ipynb')
    output = tmp_path / 'results'
    if fail:
        with pytest.raises(CellExecutionError):
            Result.run_notebook('check', output, 30)
        assert not (output / 'executed_notebooks/check.ipynb').exists()
    else:
        Result.run_notebook('check', output, 30)
        saved = nbformat.read(output / 'executed_notebooks/check.ipynb', as_version=4)
        assert 'runner passed' in saved.cells[0].outputs[0].text
    assert len(managers) == 1
    assert not managers[0].has_kernel
