# Final Information Retrieval Project — PLSA, LSI and TF-IDF

**Evaluator repository:** https://github.com/Animesh2609/Tendering

The complete final submission is in **[`IR_Project_final/`](IR_Project_final/)**.
It contains the seven experiment notebooks from the teammate's final project,
the shared source modules, all supplied result artifacts, and the executed
[`Result.ipynb`](IR_Project_final/Result.ipynb) that explains the results.

**Start with the [full setup and reproduction guide](IR_Project_final/README.md).**
It covers Windows/macOS/Linux installation, dataset preparation, notebook order,
command-line execution, result interpretation, dependencies and troubleshooting.

```bash
git clone https://github.com/Animesh2609/Tendering.git
cd Tendering/IR_Project_final
```

An evaluator can follow either path:

1. **Inspect the submitted results:** open `IR_Project_final/Result.ipynb`.
   Tables, plots and the closing experiment-by-experiment explanation are embedded.
   Use `python run_project.py report` after installing the report dependencies to
   verify/rebuild the report from the committed CSV/JSON/PNG/NPZ artifacts.
2. **Reproduce the research workflow:** install the full requirements, run
   `python run_project.py check`, then `python run_project.py all`. This prepares
   the corpus if absent, runs all seven original experiments, and refreshes the report.

Dataset downloads and model fitting are unnecessary for the first path. The
second path downloads 20 Newsgroups and trains many models; consult the guide
for runtime, memory and numerical reproducibility considerations.

The older `plsa/` directory and `plsa-refactored.zip` are retained as earlier
work. **Use `IR_Project_final/` for evaluation**: it is the seven-experiment
submission and does not depend on those older files or on a separate ZIP.
