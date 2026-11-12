#!/usr/bin/env python3
"""Run the final project's existing notebooks with the current Python environment.

Examples:
    python run_project.py check
    python run_project.py report
    python run_project.py preprocess
    python run_project.py experiments --only 01 04
    python run_project.py all

Experiments write results/<experiment>/ themselves. Their executed copies go to
executed_notebooks/. Report mode refreshes Result.ipynb in the project root.
No experiment equations, hyperparameters or query sets are changed by this runner.
"""
import argparse
from importlib import import_module, metadata
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
EXPERIMENTS = {
    '01': '01_plsa_baseline.ipynb',
    '02': '02_six_category_experiment.ipynb',
    '03': '03_all20_k_study.ipynb',
    '04': '04_retrieval_scoring_investigation.ipynb',
    '05': '05_retrieval_validation_query_study.ipynb',
    '06': '06_bagging_experiment.ipynb',
    '07': '07_topic_boundary_experiment.ipynb',
}
DATA = ROOT / 'data' / '20news_preprocessed.npz'


def check_environment():
    """Check actual imports and the spaCy model before a costly experiment run."""
    if sys.version_info[:2] not in {(3, 11), (3, 12)}:
        print('Use Python 3.11 or 3.12 for the documented environment.', file=sys.stderr)
        return 1
    failures = []
    for module in ('numpy', 'pandas', 'scipy', 'sklearn', 'matplotlib', 'spacy',
                   'psutil', 'nbformat', 'nbclient', 'ipykernel', 'jupyterlab'):
        try:
            loaded = import_module(module)
            print(f'{module}: {getattr(loaded, "__version__", "import OK")}')
        except Exception as exc:
            failures.append(f'{module}: {exc}')
    try:
        import spacy
        spacy.load('en_core_web_sm', disable=['ner', 'parser'])
        print('en_core_web_sm: model load OK')
    except Exception as exc:
        failures.append(f'en_core_web_sm: {exc}')
    print('Preprocessed corpus:', 'present' if DATA.exists() else 'not generated; run preprocess or all')
    if failures:
        print('\n'.join(failures), file=sys.stderr)
        print('Install: python -m pip install -r requirements.txt', file=sys.stderr)
    return int(bool(failures))


def run_notebook(source, destination, timeout):
    """Run in project-root cwd, save outputs, and close the kernel on failure too."""
    import nbformat
    from nbclient import NotebookClient
    from jupyter_client import KernelManager

    notebook = nbformat.read(source, as_version=4)
    manager = KernelManager(kernel_name='python3')
    manager.kernel_spec.argv = [sys.executable, '-m', 'ipykernel_launcher', '-f', '{connection_file}']

    def progress(cell, cell_index, **kwargs):
        if cell.cell_type == 'code':
            print(f'  {source.name}: code cell {cell_index + 1}/{len(notebook.cells)}', flush=True)

    client = NotebookClient(notebook, km=manager, timeout=timeout, on_cell_start=progress,
                            resources={'metadata': {'path': str(ROOT)}})
    destination.parent.mkdir(parents=True, exist_ok=True)
    print(f'Running {source.relative_to(ROOT)}', flush=True)
    try:
        client.execute(cwd=str(ROOT), cleanup_kc=True)
    except Exception:
        failure = ROOT / 'executed_notebooks' / (source.stem + '.failed.ipynb')
        failure.parent.mkdir(parents=True, exist_ok=True)
        nbformat.write(notebook, failure)
        print(f'Execution stopped. Diagnostic notebook: {failure}', file=sys.stderr)
        raise
    nbformat.write(notebook, destination)
    print(f'Saved {destination.relative_to(ROOT)}', flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('mode', choices=['check', 'report', 'preprocess', 'experiments', 'all'])
    parser.add_argument('--only', nargs='+', choices=list(EXPERIMENTS), metavar='ID',
                        help='Experiment IDs for experiments mode, e.g. --only 01 04')
    parser.add_argument('--timeout', type=int, default=7200, help='Seconds per notebook cell; default 7200')
    args = parser.parse_args(argv)
    if args.only and args.mode != 'experiments':
        parser.error('--only is supported only with experiments mode')
    if args.timeout <= 0:
        parser.error('--timeout must be positive')
    if args.mode == 'check':
        return check_environment()
    if args.mode == 'preprocess' or (args.mode == 'all' and not DATA.exists()):
        run_notebook(ROOT / 'src' / 'preprocessing.ipynb',
                     ROOT / 'executed_notebooks' / 'preprocessing.ipynb', args.timeout)
    if args.mode in {'experiments', 'all'}:
        if not DATA.exists():
            parser.error('Missing data/20news_preprocessed.npz. Run: python run_project.py preprocess')
        if args.mode == 'all':
            print('Using existing processed corpus. Run preprocess explicitly to rebuild it.', flush=True)
        for identifier in dict.fromkeys(args.only or EXPERIMENTS):
            name = EXPERIMENTS[identifier]
            run_notebook(ROOT / 'experiments' / name, ROOT / 'executed_notebooks' / name, args.timeout)
    if args.mode in {'report', 'all'}:
        run_notebook(ROOT / 'Result.ipynb', ROOT / 'Result.ipynb', args.timeout)
    # Record this machine's versions separately from the teammate's supplied references.
    versions = {'python': sys.version, 'command': sys.argv, 'mode': args.mode}
    for package in ['numpy', 'pandas', 'scipy', 'scikit-learn', 'matplotlib', 'spacy',
                    'en-core-web-sm', 'psutil', 'nbclient', 'nbformat']:
        try:
            versions[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            versions[package] = None
    destination = ROOT / 'executed_notebooks' / 'last_run_environment.json'
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(versions, indent=2) + '\n', encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
