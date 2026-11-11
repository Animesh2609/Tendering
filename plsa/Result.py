#!/usr/bin/env python3
"""Show results from every experiment and explain their complete workflow.

Usage (from the repository root):
    python Result.py                     # Read existing results; never invent missing scores.
    python Result.py --run all           # Execute all six notebooks, then build the report.
    python Result.py --run PLSA_Baseline  # Execute one named study and refresh the report.

Workflow:
  1. Each notebook imports data preparation, PLSA, scoring and metrics from src.
  2. Its own cells specify the experiment: corpus, split, queries, K, or bagging.
     One shared MODEL IMPLEMENTATION is used; different K values, restarts and
     bootstraps necessarily produce separately fitted model instances.
  3. The final cell exports actual DataFrames and provenance through src.results.
  4. This file aggregates the latest COMPLETE run of each study into Result.md
     and summary.csv. It keeps studies separate because their evaluation tasks
     differ. See the report's workflow/metric comments and linked detail tables.

Full execution can take considerable time and memory. It needs the dependencies,
spaCy English model and the sklearn dataset (downloaded once into .cache/).
Existing notebook outputs are not used as evidence for freshly generated results.
"""
import argparse
import os
from pathlib import Path
import sys

from src.config import EXPERIMENTS
from src.results import ROOT, build_report, results_root


def run_notebook(experiment, output_dir, timeout):
    """Execute an isolated kernel; export occurs only after every cell succeeds."""
    import nbformat
    from nbclient import NotebookClient
    from jupyter_client import KernelManager

    notebook = nbformat.read(ROOT / f"{experiment}.ipynb", as_version=4)
    # Use the interpreter running Result.py, including its installed dependencies.
    manager = KernelManager(kernel_name="python3")
    manager.kernel_spec.argv = [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"]
    client = NotebookClient(notebook, km=manager, timeout=timeout,
                            resources={"metadata": {"path": str(ROOT)}})
    env = dict(os.environ, PLSA_RESULTS_DIR=str(output_dir), PLSA_RUN_KIND="full")
    client.execute(env=env, cwd=str(ROOT), cleanup_kc=True)
    executed = output_dir / "executed_notebooks"
    executed.mkdir(parents=True, exist_ok=True)
    nbformat.write(notebook, executed / f"{experiment}.ipynb")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", nargs="+", choices=["all", *EXPERIMENTS], help="Notebook names without .ipynb")
    parser.add_argument("--results-dir", type=Path, default=results_root())
    parser.add_argument("--timeout", type=int, default=7200, help="Maximum seconds per notebook cell")
    args = parser.parse_args()
    output_dir = args.results_dir.resolve()
    if args.run:
        for experiment in (EXPERIMENTS if "all" in args.run else dict.fromkeys(args.run)):
            print(f"Running {experiment} ...", flush=True)
            run_notebook(experiment, output_dir, args.timeout)
    report, summary = build_report(output_dir)
    print(summary.to_string(index=False) if not summary.empty else "No completed runs yet; the report lists how to generate them.")
    print(f"\nWorkflow, per-study results and detail tables: {report}")
    print(f"Combined CSV: {output_dir / 'summary.csv'}")


if __name__ == "__main__":
    main()
