"""Persist complete notebook runs and render an auditable, combined report."""
from datetime import datetime, timezone
from hashlib import sha256
from importlib.metadata import version, PackageNotFoundError
import json
import os
from pathlib import Path
import platform
import tempfile

import numpy as np
import pandas as pd

from .config import EXPERIMENTS
from .plsa_model import PLSA

ROOT = Path(__file__).resolve().parents[1]

WORKFLOW = """1. Load 20 Newsgroups with headers, footers and quoted text removed.
2. Select the corpus/relevance labels, then stratify raw documents into splits.
3. Lemmatize and filter text using the same spaCy pipeline for documents and queries.
4. Fit count and TF-IDF vocabularies on training text only; transform held-out text.
5. Fit the shared PLSA EM model (counts), TF-IDF and LSI baselines (TF-IDF).
   Choose PLSA restarts by training likelihood. Fold in held-out documents with
   topic-word probabilities fixed. Validation studies select settings on validation.
6. Rank the same candidates within each study using cosine or query likelihood;
   bagging combines member ranks. Category/group labels define binary relevance.
7. Compute per-query metrics, then macro-average across queries. Export every
   result table plus model convergence, top words, split sizes and source hashes.

Precision@k is the relevant fraction of the available top-k results. Recall@k
is the fraction of all relevant candidates retrieved. AP@k averages precision
at relevant ranks, divided by min(k, total relevant); mean AP across queries is
MAP. NDCG discounts hits at lower ranks and divides by ideal DCG. MRR here is
reciprocal rank truncated at k. Older supergroup tables call per-query AP 'MAP';
the combined summary correctly labels the average MAP@10.

Compare methods WITHIN a study. Corpus, split, queries and eligibility differ
between studies. Baseline includes empty texts; the others exclude texts empty
after preprocessing (which is different from having zero in-vocabulary counts).
The All20 K study reports every predeclared K; only validation chooses K.
Higher training likelihood is not evidence of higher retrieval quality.
"""

DESCRIPTIONS = {
    "PLSA_Baseline": "All 20 categories; 75/25 split; 20 queries; cosine retrieval, mixtures, K and beta sweeps.",
    "PLSA_Retrieval_Scoring_Investigation": "Six original categories; 75/25 split; six queries; cosine versus query likelihood, mixtures, K and beta sweeps.",
    "Six_Category_Experiment": "All 20 categories mapped to six supergroups; 80/20 split; six group queries, mixtures and NMI/ARI topic diagnostics.",
    "Bagging_Experiment": "Same supergroups and 80/20 split; full-data references, five-restart PLSA ensemble and matched bootstrap ensembles for all methods.",
    "Retrieval_Validation_Query_Study": "Six categories; 60/20/20 split; 18 queries; validation selects K and smoothing, followed by test metrics, coverage and resource profiling.",
    "All20_K_Study": "All 20 categories; 60/20/20 split; 20 queries; validation selects K separately per PLSA score; test comparison retains every predeclared K.",
}

TABLE_DESCRIPTIONS = {
    "evaluation_df": "Per-query held-out retrieval scores, before macro averaging.",
    "mean_metrics": "Mean retrieval metrics across the experiment's fixed queries.",
    "boundary_df": "Folded-in topic weights for each sampled two-category mixture and replicate.",
    "boundary_summary": "Mean and standard deviation of inferred topic weights at each known source-word ratio.",
    "k_df": "Independent fits at different K: training likelihood, iteration count, and alignment metrics where applicable.",
    "tempered_df": "Fixed-beta E-step sweep; this is exploratory tempering, not the full TEM procedure.",
    "similarity_df": "Training-only TF-IDF category-centroid similarities within and between supergroups.",
    "model_order_df": "Best training-likelihood restart for every predeclared K.",
    "validation_df": "Per-query validation scores used to select settings before test evaluation.",
    "validation_summary": "Validation query averages for each method and K.",
    "test_all_k_df": "Per-query held-out scores for all predeclared K; baseline scores repeat across K.",
    "test_plsa_df": "PLSA-only subset of the held-out K comparison.",
    "test_baselines_df": "TF-IDF and LSI held-out scores with duplicate K entries removed.",
    "test_summary": "Macro-averaged held-out retrieval scores.",
    "baseline_summary": "Macro-averaged TF-IDF and LSI held-out retrieval scores.",
    "likelihood_tuning": "Validation MAP/precision for each K and background-mixture weight.",
    "cosine_tuning": "Validation MAP/precision for each cosine model's K.",
    "val_ll": "Validation likelihood scores sorted for selecting K.",
    "val_cos": "Validation cosine scores sorted for selecting K.",
    "test_plsa_plot": "Held-out PLSA summary reshaped for the K comparison plot.",
    "plsa_by_category": "Per-category held-out PLSA scores across K.",
    "training_resources_df": "Timed training operation with sampled whole-process RSS memory.",
    "inference_resources_df": "Timed fold-in operations for selected models with sampled process RSS.",
    "query_coverage_df": "Unique processed query terms present/missing in the training count vocabulary.",
    "per_query_results": "Held-out query scores joined to vocabulary coverage.",
    "query_family_summary": "Test metrics averaged within direct, paraphrase and related-term query families.",
    "query_comparison": "Per-query AP with PLSA-minus-baseline differences.",
    "model_convergence": "Training log-likelihood at each EM iteration for retained fitted models.",
    "topic_words": "Highest-probability words in each retained model's topic-word distribution.",
}


def source_hashes(experiment):
    paths = sorted((ROOT / "src").glob("*.py")) + [ROOT / (experiment + ".ipynb"), ROOT / "Result.py"]
    return {str(p.relative_to(ROOT)): sha256(p.read_bytes()).hexdigest() for p in paths}


def results_root():
    return Path(os.environ.get("PLSA_RESULTS_DIR", ROOT / "results")).resolve()


def export_results(experiment, namespace, output_dir=None, run_kind=None):
    """Export only after successful execution; no hard-coded numerical results.

    Each run has a unique directory. latest.json is updated last so an interrupted
    export cannot replace the pointer to a previously complete result.
    """
    if experiment not in EXPERIMENTS:
        raise ValueError(f"Unknown experiment: {experiment}")
    base = Path(output_dir) if output_dir is not None else results_root()
    parent = base / experiment
    parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    run = Path(tempfile.mkdtemp(prefix=now.strftime("%Y%m%dT%H%M%S-"), dir=parent))
    tables = {}
    for name, value in namespace.items():
        if not name.startswith("_") and isinstance(value, pd.DataFrame):
            # Preserve named indexes (method, query family, etc.) in CSV files.
            table = value.reset_index() if not isinstance(value.index, pd.RangeIndex) else value
            path = run / f"{name}.csv"
            table.to_csv(path, index=False)
            tables[name] = {"file": path.name, "rows": len(table)}

    model_rows, topic_rows = [], []
    models = {name: value for name, value in namespace.items() if isinstance(value, PLSA)}
    vectorizer = namespace.get("count_vectorizer")
    for name, model in models.items():
        for iteration, ll in enumerate(model.log_likelihoods, 1):
            model_rows.append(dict(model=name, K=model.n_topics, beta=model.beta,
                                   seed=model.random_state, iteration=iteration, train_log_likelihood=ll))
        if vectorizer is not None:
            for topic, words in model.top_words(vectorizer.get_feature_names_out(), n=12).items():
                for rank, (word, probability) in enumerate(words, 1):
                    topic_rows.append(dict(model=name, topic=topic, rank=rank, word=word, probability=probability))
    for name, rows in [("model_convergence", model_rows), ("topic_words", topic_rows)]:
        if rows:
            pd.DataFrame(rows).to_csv(run / f"{name}.csv", index=False)
            tables[name] = {"file": f"{name}.csv", "rows": len(rows)}

    versions = {"python": platform.python_version()}
    for package in ["numpy", "scipy", "scikit-learn", "pandas", "spacy", "en_core_web_sm"]:
        try:
            versions[package] = version(package)
        except PackageNotFoundError:
            versions[package] = "not installed"
    selected = {}
    for key in ["K", "K_GRID", "BACKGROUND_GRID", "N_RESTARTS", "BAGGING_ESTIMATORS", "best_ll", "best_cos", "best_k_ll", "best_k_cos"]:
        if key in namespace:
            selected[key] = namespace[key]
    metadata = dict(
        experiment=experiment, created_at_utc=now.isoformat(),
        run_kind=run_kind or os.environ.get("PLSA_RUN_KIND", "full"),
        config=EXPERIMENTS[experiment], seed=namespace.get("SEED", 42),
        split_sizes={split: len(namespace[f"docs_{split}"]) for split in ("train", "val", "test") if f"docs_{split}" in namespace},
        vocabulary_size=len(vectorizer.vocabulary_) if vectorizer is not None else None,
        settings=selected, versions=versions, source_hashes=source_hashes(experiment), tables=tables,
    )
    (run / "manifest.json").write_text(json.dumps(metadata, indent=2, default=_json_scalar) + "\n")
    pointer = parent / (run.name + ".tmp")
    pointer.write_text(json.dumps({"run": run.name}) + "\n")
    pointer.replace(parent / "latest.json")
    return run


def _json_scalar(value):
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f"Cannot serialize {type(value).__name__}")


def load_latest(base, experiment):
    parent = Path(base) / experiment
    pointer = parent / "latest.json"
    if not pointer.exists():
        return None
    run = parent / json.loads(pointer.read_text())["run"]
    return run, json.loads((run / "manifest.json").read_text())


def retrieval_summary(run, metadata):
    """Normalize column names for display without pooling incompatible studies."""
    name = "test_all_k_df" if metadata["experiment"] == "All20_K_Study" else "evaluation_df"
    if name not in metadata["tables"]:
        return pd.DataFrame()
    table = pd.read_csv(run / metadata["tables"][name]["file"])
    table = table.rename(columns={"Precision@k": "Precision@10", "Recall@k": "Recall@10",
                                  "F1@k": "F1@10", "AP@k": "AP@10", "NDCG@k": "NDCG@10",
                                  "MAP@10": "AP@10"})
    metrics = [c for c in ["Precision@10", "Recall@10", "F1@10", "AP@10", "NDCG@10", "MRR"] if c in table]
    groups = ["method"] + (["K"] if "K" in table else [])
    # All20 stores repeated baseline scores for every K; report each baseline once.
    if "K" in table:
        plsa = table[table.method.str.startswith("PLSA")].groupby(groups)[metrics].mean().reset_index()
        baseline = table[~table.method.str.startswith("PLSA")].groupby("method")[metrics].mean().reset_index()
        summary = pd.concat([baseline, plsa], ignore_index=True)
    else:
        summary = table.groupby(groups)[metrics].mean().reset_index()
    return summary.rename(columns={"AP@10": "MAP@10", "MRR": "MRR@10"})


def build_report(base=None, experiments=None):
    """Read exported numerical tables; mark absent, smoke and changed-source runs."""
    base = Path(base) if base is not None else results_root()
    lines = ["# PLSA experiment results", "", "## How these results are generated", "", WORKFLOW]
    summaries = []
    for experiment in experiments or EXPERIMENTS:
        lines += ["", f"## {experiment}", "", DESCRIPTIONS[experiment]]
        loaded = load_latest(base, experiment)
        if loaded is None:
            lines += ["", "Not run yet. Run the notebook through its final export cell or use `python Result.py --run " + experiment + "`."]
            continue
        run, metadata = loaded
        stale = metadata["source_hashes"] != source_hashes(experiment)
        lines += ["", f"Run: {metadata['created_at_utc']} | kind: **{metadata['run_kind']}** | source changed since run: **{stale}**",
                  f"Splits: {metadata['split_sizes']} | vocabulary: {metadata['vocabulary_size']}",
                  "", f"Settings: `{json.dumps(metadata['settings'])}`", ""]
        if metadata["run_kind"] != "full":
            lines += ["**Smoke-test output verifies execution only; do not report these numbers as experimental findings.**", ""]
        summary = retrieval_summary(run, metadata)
        if not summary.empty:
            lines += ["```text", summary.to_string(index=False, float_format=lambda x: f"{x:.4f}"), "```", ""]
            summary.insert(0, "experiment", experiment)
            summary.insert(1, "run_kind", metadata["run_kind"])
            summary.insert(2, "source_changed", stale)
            summaries.append(summary)
        lines += ["All exported tables (full per-query results and diagnostics):", ""]
        for name, entry in metadata["tables"].items():
            relative = (run / entry["file"]).relative_to(base).as_posix()
            explanation = TABLE_DESCRIPTIONS.get(name, "Additional notebook result table.")
            lines.append(f"- [{name}]({relative}) — {entry['rows']} rows. {explanation}")
    base.mkdir(parents=True, exist_ok=True)
    report = base / "Result.md"
    report.write_text("\n".join(lines) + "\n")
    combined = pd.concat(summaries, ignore_index=True) if summaries else pd.DataFrame(columns=["experiment", "run_kind", "source_changed", "method"])
    combined.to_csv(base / "summary.csv", index=False)
    return report, combined
