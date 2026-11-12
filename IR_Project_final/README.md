# Modeling Beyond Keywords:Probabilistic Latent Semantic Analysis

This is the repository contains our IR
project  implementing Probabilistic Latent Semantic Analysis (PLSA) and studying its use in document retrieval. It compares PLSA with TF-IDF/VSM and Latent Semantic Indexing (LSI)
on 20 Newsgroups. Seven experiments examine corpus/relevance choices, topic
count, retrieval scoring, validation, query wording, ensembles and synthetic
topic-mixture responses.

**Repository:** https://github.com/Animesh2609/Probablisitic-Latent-Semantic-Analysis

## 1. Recommended evaluator approach

1. Read this guide and open [`Result.ipynb`](Result.ipynb) to understand the
   supplied results and the common workflow/metric definitions.
2. Read the seven source notebooks in `experiments/` in their numbered order.
   Each contains the research question, settings, calls to shared modules,
   evaluation and artifact-saving code.
3. Inspect `src/` for the PLSA EM and fold-in implementation, TF-IDF/LSI models,
   scoring, metrics, ensembles and mixture generation.
4. Choose **report verification** below for a quick inspection of the saved
   evidence, or **full reproduction** to prepare data and retrain the models.
5. Read the report's closing discussion for what each experiment changes,
   why it is tried, and whether the saved results actually improve PLSA.

`Result.ipynb` **loads result artifacts**. It neither imports/executes the
seven source notebooks nor duplicates their training code. Its comments and
Markdown explain the outputs. `run_project.py` is the optional execution
wrapper that runs the original notebooks in isolated kernels.

## 2. Clone and create an environment

Use **Python 3.11 or Python 3.12**, Git and an internet connection for package
installation. The documented scientific packages and report execution were
validated in a clean Python 3.12 environment. Windows, macOS and Linux commands
are provided; the verification environment was Linux, not all three systems.
The models run on CPU; a GPU is not required.

### macOS / Linux

```bash
git clone https://github.com/Animesh2609/Tendering.git
cd Tendering/IR_Project_final
python3 --version  # Must be Python 3.11 or 3.12
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

### Windows PowerShell

```powershell
git clone https://github.com/Animesh2609/Tendering.git
cd Tendering\IR_Project_final
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

Python 3.11 users can substitute `py -3.11`. If PowerShell blocks activation,
run `.\.venv\Scripts\python.exe` instead of `python` in the commands below.
In Command Prompt, activation is `.venv\Scripts\activate.bat`.

**Working directory:** all commands below are run from `Tendering/IR_Project_final`,
where `run_project.py`, `Result.ipynb`, `src/`, `experiments/` and `results/` live.

## 3. Quick path: view and verify the submitted results

You can view the committed report in GitHub without installation. For local
viewing or refreshing its outputs, install only the report dependencies:

```bash
python -m pip install -r requirements-report.txt
python run_project.py report
python -m jupyterlab
```

Open **`Result.ipynb`** in JupyterLab. The report runner refreshes that file in
place. It reads the committed artifacts, displays the seven result sections,
shows all 14 saved plots, checks summary arithmetic and validation choices,
and finishes with the PLSA improvement discussion/comparison tables. The
supplied artifact set passes **14 consistency checks**. These are checks of
saved results, not a fresh training run.

This path does not need spaCy, the raw dataset or the preprocessed corpus.
It does not change any CSV/JSON/PNG/NPZ files under `results/`.

## 4. Full reproduction: install the model dependencies

In the same activated environment:

```bash
python -m pip install -r requirements.txt
python run_project.py check
```

`requirements.txt` includes the reporting/Jupyter dependencies plus NumPy,
SciPy, scikit-learn, matplotlib, spaCy, psutil and the pinned English model
`en_core_web_sm==3.8.0`. The English model is installed from its official GitHub
release as part of the requirements; there is no additional model download
step. `check` tests the actual imports and loads that model. A message saying
the corpus is not generated is expected on a fresh clone.

The scientific versions are pinned to the environment used to verify this
submission. [`requirements-lock.txt`](requirements-lock.txt) records its full
resolved package set for an additional Linux/Python 3.12 reference. It is not
a recovered lockfile from the teammate's original training machine. Start with
`requirements.txt` on other supported platforms.

## 5. Dataset preparation

The final code uses the complete **20 Newsgroups** corpus through
`sklearn.datasets.fetch_20newsgroups(subset='all')` (18,846 documents, 20
categories), removing headers, footers and quotes. spaCy then filters spaces,
punctuation, numeric/non-alphabetic tokens and stop words, lowercases lemmas,
and discards lemmas shorter than two characters.

Prepare it with:

```bash
python run_project.py preprocess
```

This executes [`src/preprocessing.ipynb`](src/preprocessing.ipynb) and creates:

```text
data/raw/                      # scikit-learn download/cache
data/20news_preprocessed.npz    # documents, labels, category_names
```

The data directory is generated locally and ignored by Git. The download is
performed by scikit-learn from its configured upstream dataset host. The
preprocessed archive uses string and numeric arrays and is read with
`allow_pickle=False` by the experiments. The archive from the teammate's ZIP
is not required: the repository contains the full code to generate it.

Preprocessing is a common, document-local cleanup step. **Vocabulary selection,
TF-IDF fitting and LSI fitting happen separately inside each experiment using
its training partition only.** Test/validation documents do not fit those
representations. Labels define splits, relevance and diagnostics, not PLSA's
unsupervised EM fitting objective.

## 6. Run the research experiments

### One command for the complete workflow

```bash
python run_project.py all
```

On a fresh clone this prepares the corpus, executes experiments 01–07 in order,
then refreshes `Result.ipynb`. If `data/20news_preprocessed.npz` already exists,
it reuses that file. Run `preprocess` explicitly before `all` if you want to
rebuild it with the installed spaCy version.

### Run stages independently

```bash
python run_project.py preprocess
python run_project.py experiments
python run_project.py report
```

### Rerun selected experiments

```bash
python run_project.py experiments --only 01 04
python run_project.py report
```

`--only` accepts any of `01 02 03 04 05 06 07` and applies to `experiments` mode
only. Each experiment is self-contained after preprocessing: it does not rely
on variables or fitted models from a preceding notebook. Numbered order is
recommended to follow the research narrative. The runner does not change
hyperparameters, subsample data or replace any original model functions.

### Run interactively instead

```bash
python -m jupyterlab
```

Open `src/preprocessing.ipynb` and run its cells in order once. Then open each
notebook in `experiments/` and choose **Restart Kernel and Run All**. Finish by
running `Result.ipynb`. Launch Jupyter from the project directory and select
the Python environment where you installed the requirements. The CLI runner
always uses its own Python interpreter, avoiding an unrelated global kernel.

## 7. Which file answers which question?

| File | Data / split | What it tests | Saved output folder |
|---|---|---|---|
| [`01_plsa_baseline.ipynb`](experiments/01_plsa_baseline.ipynb) | All 20 categories; 75/25 | K=5 PLSA, five restarts; cosine versus TF-IDF/LSI; topics, convergence and mixtures | `results/plsa_baseline/` |
| [`02_six_category_experiment.ipynb`](experiments/02_six_category_experiment.ipynb) | All 20 categories mapped to six broad groups; 80/20 | K=6, six group queries; topic/group alignment, centroids and mixtures | `results/six_category_experiment/` |
| [`03_all20_k_study.ipynb`](experiments/03_all20_k_study.ipynb) | All 20 categories; 60/20/20 | K=2,5,8,10,20; validation-selected K for each PLSA scorer; test sensitivity curves | `results/all20_k_study/` |
| [`04_retrieval_scoring_investigation.ipynb`](experiments/04_retrieval_scoring_investigation.ipynb) | Six original categories; 75/25 | Same K=6 PLSA fit: topic cosine versus query likelihood, ranking agreement | `results/retrieval_scoring_investigation/` |
| [`05_retrieval_validation_query_study.ipynb`](experiments/05_retrieval_validation_query_study.ipynb) | Six original categories; 60/20/20 | 18 queries; K/background tuning, query families, vocabulary coverage and resource profiling | `results/retrieval_validation_query_study/` |
| [`06_bagging_experiment.ipynb`](experiments/06_bagging_experiment.ipynb) | Same six broad groups as 02; 80/20 | Full-data references, five-restart PLSA and matched bootstrap ensembles; rank aggregation | `results/bagging_experiment/` |
| [`07_topic_boundary_experiment.ipynb`](experiments/07_topic_boundary_experiment.ipynb) | All 20 categories; 75% training sources; held-out partition unused | Single/restart/bootstrap PLSA topic probabilities for known source-token mixtures | `results/topic_boundary_experiment/` |

The six-original-category subset in 04/05 is `comp.graphics`, `misc.forsale`,
`rec.sport.baseball`, `sci.med`, `sci.space`, and `talk.politics.guns`. It is
**different from the six supergroups** used in 02/06. Every result folder has
`configuration.json` recording the precise category/group mapping, seed and
settings. Experiments use seed 42 plus the explicitly coded restart/bootstrap
seed offsets. See each notebook and its configuration for the full grids.

## 8. Project layout and shared code

```text
IR_Project_final/
├── README.md
├── requirements.txt            # Full environment, including the spaCy model
├── requirements-report.txt     # Report-only environment
├── requirements-lock.txt       # Verified environment's resolved versions
├── run_project.py              # check / preprocess / experiments / report / all
├── Result.ipynb                # Executed consolidated report and closing discussion
├── source_provenance.json      # Source-code hashes against the teammate archive
├── validation.json             # Scope and environment of submission verification
├── tests/                     # Runner tests and bounded notebook integration check
├── experiments/               # Seven original numbered experiment notebooks
├── src/
│   ├── preprocessing.ipynb     # Fetch, clean and save the common corpus
│   ├── text_processing.py      # Matching spaCy processing for queries
│   ├── plsa_model.py           # Shared EM, fold-in, top words, restart selection
│   ├── tfidf.py                # Training-only TF-IDF fit and transform
│   ├── lsi.py                  # Training-only SVD + normalization
│   ├── retrieval.py            # Cosine, query likelihood, background distribution
│   ├── evaluation.py           # Binary relevance metrics
│   ├── ensemble.py             # Negative mean-rank aggregation
│   └── synthetic_data.py       # Sample two-category token mixtures
├── results/                   # All supplied reference tables, plots and arrays
├── data/                      # Generated locally; not committed
└── executed_notebooks/         # CLI execution copies and diagnostics; not committed
```

All seven notebooks call the same PLSA class. Separate K values, restarts and
bootstrap samples necessarily produce separate fitted instances. There is no
single fitted model shared across incompatible experiments.

## 9. Outputs and how to interpret them

Source notebooks write CSV tables, PNG plots, JSON configuration/model-order
records and (for ensembles) NPZ bootstrap-index arrays. Those writes **replace
the corresponding files under `results/`** when you rerun an experiment.
The committed files are the teammate's reference results, so use a separate
clone or copy that directory if you want to retain them alongside a new run.

The CLI saves executed experiment/preprocessing notebooks under
`executed_notebooks/` and refreshes the root `Result.ipynb` after report mode.
It records package versions in `executed_notebooks/last_run_environment.json`.
On failure it stops, saves a `.failed.ipynb` there, and does not proceed to the
next experiment. A failed or partial rerun can leave a mixture of old/new
artifacts; finish the selected experiments successfully before interpreting a
refreshed report as one newly reproduced collection.

`Result.ipynb` includes:

- The common data/model/evaluation workflow and metric definitions.
- One result cell for each of the seven experiments, with comments explaining
  how its outputs are generated and what they measure.
- Principal tables and all 14 saved plots; expandable catalogs for all detail
  tables/settings/arrays, with labeled previews of large tables.
- Fourteen arithmetic/selection checks and SHA-256 fingerprints of 76 input
  artifacts in the supplied result set.
- A final step-by-step discussion of changes, motivation and measured gains,
  plus within-experiment PLSA-versus-baseline comparison tables.

### Metrics and methodological boundaries

Binary relevance is defined by the category or group label. Precision@10 is
hits divided by 10; Recall@10 is hits divided by the total relevant candidate
count. AP@10 sums precision at relevant ranks and divides by `min(10, total
relevant)`; MAP@10 is its mean across queries. NDCG uses logarithmic rank
discounts and ideal DCG normalization. These formulas are in `src/evaluation.py`.

The baseline includes all test documents; 02–06 exclude texts empty after
preprocessing. K in 03 and K/background weight in 05 are selected on
**validation**, not test scores. Topic IDs are arbitrary. Experiment 06 combines
ranks; 07 averages source-associated probabilities after within-model topic
association. Standard deviations in mixture plots describe generated-document
variation, not confidence intervals.

### What the supplied results support

In experiment 06, bagged PLSA cosine has MAP@10 **0.9196**, compared with
**0.8220** for the strongest reported TF-IDF variant and **0.7155** for the
strongest reported LSI variant on that six-query task. Experiment 05 gives
PLSA cosine a precision advantage without a MAP advantage. Experiments 01–04
show limitations and within-PLSA improvements, and 07 is a probability probe
without TF-IDF/LSI retrieval comparisons. The report does not claim that PLSA
wins every experiment or that scores across different tasks form one improvement
curve. No statistical significance test is supplied.

## 10. Reproducibility, validation and practical limits

The supplied experiment notebooks record Python 3.11.x but do not include the
teammate's complete original dependency lockfile or exact spaCy package/model
versions. Consequently **bit-for-bit reproduction of those saved scores cannot
be promised**. Rebuilding preprocessing with another model version can change
lemmas, vocabulary and downstream rankings. Numerical libraries, SVD, tie ordering
and operating systems can also affect results. Fixed seeds and the pinned
verification environment make subsequent runs more controlled; resource timings
and whole-process RSS are inherently machine-dependent.

The original full-budget research runs have **not** been repeated during this
repository-packaging task. The verification performed is recorded in
[`validation.json`](validation.json): a clean dependency installation, real
module/model imports, the complete consolidated report, notebook schema/source
checks, and bounded sample execution of all seven experiment code paths.
Sample results are execution checks only and are not substituted for the
committed research results.

Full reproduction trains many PLSA fits and folds in thousands of documents.
It can take substantially longer than report verification. EM allocates arrays
scaling with nonzero document-word counts times topic count; multiple retained
models increase memory use. A machine with 16 GB RAM or more is a practical
recommendation, **not a measured minimum or guarantee**. Allow extra disk space
for the Python environment, dataset cache and executed notebooks.

The CLI default is **7,200 seconds per code cell**, not a two-hour bound on the
whole workflow. To allow longer cells:

```bash
python run_project.py all --timeout 14400
```

The timeout changes execution supervision, not model iteration settings.

### Rerun the verification checks

```bash
python -m unittest discover -s tests -v
python tests/smoke_notebooks.py
```

The smoke check downloads/caches the real corpus, selects 15 documents per
original category, performs real spaCy preprocessing, and executes all seven
original experiment code paths with PLSA fitting/fold-in capped at three
iterations. Its outputs go only to `executed_notebooks/smoke/`. Those outputs
are not research findings and do not replace the committed `results/` files.
The caps and sampling exist only in this test process, not in `run_project.py`
or in the source experiment notebooks.

## 11. Troubleshooting

| Symptom | Action |
|---|---|
| `No module named src` / wrong paths | Work from `Tendering/IR_Project_final`. Use the runner or launch Jupyter there; keep the whole folder structure. |
| `Missing ... 20news_preprocessed.npz` | Run `python run_project.py preprocess`, or use `all` to prepare it automatically if absent. |
| spaCy model missing (`E050`) | Install `requirements.txt` in the active environment and run `python run_project.py check`. The pinned model wheel comes from GitHub. |
| Imports work in terminal but fail in notebook | Select the correct environment/kernel. The runner uses the interpreter that launches it; check `python -c "import sys; print(sys.executable)"`. |
| Package install fails | Confirm Python 3.11/3.12, upgrade pip, and use a fresh virtual environment. Check network access to PyPI and the official spaCy model release. |
| Dataset download fails | Check internet/proxy access for scikit-learn's dataset host and retry preprocessing. Report-only mode does not need a dataset download. |
| Memory error or very slow EM | Close other memory-heavy processes and use a machine with more RAM. Run one experiment at a time. Reducing K/features/iterations changes the experiment and must be labeled as such. |
| Cell timeout | Review the `.failed.ipynb`, then rerun with a larger positive `--timeout`. This does not resume in the middle of a fit. |
| Result report says a file is missing or a consistency assertion fails | Restore the complete committed `results/` set or successfully rerun the relevant experiment; do not manually invent/edit summary scores to make checks pass. |
| Figures appear blank on GitHub | Download/open the notebook locally in JupyterLab; PNG originals are under the corresponding `results/` folder. |
| Windows activation is blocked | Use `.\.venv\Scripts\python.exe` directly instead of the activation script. |

## References and data

- Thomas Hofmann, *Probabilistic Latent Semantic Analysis*, UAI 1999.
- [scikit-learn: 20 Newsgroups dataset](https://scikit-learn.org/stable/datasets/real_world.html#the-20-newsgroups-text-dataset)
- [spaCy English model documentation](https://spacy.io/models/en)
- [Original project repository](https://github.com/Animesh2609/Probablisitic-Latent-Semantic-Analysis)

The raw dataset and pretrained spaCy model are obtained from their respective
providers. This repository does not assign a new license to those materials.
