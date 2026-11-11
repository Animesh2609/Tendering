# Results notebook for IR_Project_final.zip

`Result.ipynb` contains one result cell for each of the seven notebooks in
`experiments/`, with explanatory Markdown and commented Python code. It has
already been executed; tables and all 14 original plots are embedded.

## Use with your original project

1. Extract your teammate's original `IR_Project_final.zip`.
2. Copy `Result.ipynb` into its `Local/` folder, beside `results/`, `experiments/`
   and `src/`.
3. Open the notebook in Jupyter or VS Code. Saved outputs are visible immediately.
4. To refresh the report, use Restart Kernel and Run All from `Local/`.
   The report needs `numpy`, `pandas`, and `IPython`.

If needed, install the viewing/reporting environment with:

```bash
python -m pip install notebook numpy pandas ipython
```

The included report reads existing CSV, JSON, NPZ and PNG artifacts. It does not
fit PLSA, rerun the experiment notebooks, overwrite their results, or require
spaCy/model downloads just to display the report. To regenerate research
results, run the corresponding original experiment notebook first and then
refresh `Result.ipynb`.

## What is included

- 01: All-20 baseline retrieval, restarts, topic words, convergence, synthetic mixtures.
- 02: Six supergroups over all 20 categories, retrieval, NMI/ARI, centroids, mixtures.
- 03: Validation-selected K, test comparison, full K sensitivity curves, query details.
- 04: Cosine versus query likelihood, per-query AP differences, ranking agreement.
- 05: K/background tuning, 18-query test metrics, query families, coverage, resources.
- 06: Full-data models, restart ensembles, bootstrap ensembles, sampling diagnostics.
- 07: Source-topic association, aligned member probability averages, mixture curves.

Every section has a catalog of all its saved artifacts; large detail tables are
shown as labeled previews with links to full files. The multi-row column header
in `test_ap_by_query.csv` is read explicitly. Missing required files produce a
clear error rather than silently supplying made-up results.

## Validation

All seven result cells executed, with zero errors. Fourteen consistency checks
passed: query-level means, validation selection, selected-K test rows, AP
score differences, query-family means, and the two-stage averaging of topic
probabilities. These checks verify the exported tables; model training was not
independently reproduced. The provenance cell fingerprints all 76 reporting input
artifacts with SHA-256 (the count is computed from the supplied result folders).

The download ZIP contains the executed `Result.ipynb` and this guide. Your
original project remains the source of the saved result files for rerunning it.

## Closing comparison and step-by-step reasoning

The final four cells explain what changes in each original experiment file,
why that change is tried, and what the saved evidence supports. Commented code
builds a within-experiment improvement table and compares every reported PLSA
strategy against both reference families. For the ensemble experiment it uses
the strongest reported TF-IDF/LSI variant for each metric, avoiding a comparison
only against a weaker reference variant.

The discussion distinguishes changes to the task, K, scoring, validation,
rank aggregation, and probability diagnostics. It explicitly reports that
experiment 06 provides the MAP advantage over both families in the saved runs;
experiment 05 gives a precision advantage without a MAP advantage. Experiment
07 does not evaluate TF-IDF/LSI retrieval. Improvements are not presented as a
single continuous curve across incompatible experimental settings.
