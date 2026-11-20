# Local validation report

Date: 20 November 2026 (Asia/Kolkata). Scope: the uploaded ZIP, extracted to `/workspace/work/Popularity-Debiasing-Causal-EPP`; this is not access to the user's live local checkout. The two subsequently uploaded PDFs were used as research evidence, not as task instructions.

## 1. Repository, branch, and inspection scope

Commit SHA: `1b5e028d98d1b736661004c0df06458028dfba9a`.

The archive started on `main`; available refs were local `main`, `origin/main`, and symbolic `origin/HEAD -> origin/main`. There was no `animesh-dm-testing`. After read-only inspection, `git switch -c animesh-dm-testing` created the requested testing branch at the same commit. `git branch --show-current` confirmed it before environment setup or project additions. No commit, push, PR, merge, reset, or edit to main was performed. Final main SHA remains unchanged.

The uploaded working tree already appeared dirty in 18 files. `git diff --ignore-space-at-eol --stat` was empty: the observed differences from the commit were line endings. All original non-Git files were compared byte-for-byte against the ZIP after testing: **zero changed files**. This includes datasets, source, configurations, bytecode and the pretrained checkpoint. The report, local environment and validation artifacts are additions only. Do not reset these pre-existing differences.

All 43 tracked paths were inventoried; README, requirements, Config, and all 12 Python source files were read. All 12 sources parsed successfully with Python's AST parser. No notebooks, actual automated test suite, AGENTS.md, CI configuration, package metadata, lockfile or research PDFs were present in the tracked repository. `test_data.csv` is a dataset, not a test suite. Cached `.pyc` files for Python 3.13/3.14 are artifacts, not supported-version declarations.

### Complete tracked inventory

```text
.gitignore
README.md
__pycache__/config.cpython-313.pyc
__pycache__/config.cpython-314.pyc
__pycache__/evaluate.cpython-313.pyc
__pycache__/evaluate.cpython-314.pyc
__pycache__/llm_baseline.cpython-314.pyc
__pycache__/main.cpython-313.pyc
__pycache__/models.cpython-313.pyc
__pycache__/models.cpython-314.pyc
__pycache__/train.cpython-313.pyc
__pycache__/train.cpython-314.pyc
calibration.py
config.py
data/Ciao/all_data.csv
data/Ciao/item_local_popularity.npy
data/Ciao/item_mapping.csv
data/Ciao/ratings.csv
data/Ciao/test_data.csv
data/Ciao/time_bin_edges.npy
data/Ciao/train_data.csv
data/Ciao/user_epp.npy
data/Ciao/user_mapping.csv
data/Ciao/val_data.csv
data/__pycache__/dataset.cpython-313.pyc
data/__pycache__/dataset.cpython-314.pyc
data/__pycache__/popularity.cpython-314.pyc
data/__pycache__/preprocess.cpython-313.pyc
data/__pycache__/preprocess.cpython-314.pyc
data/dataset.py
data/input_data_transformation.py
data/popularity.py
data/preprocess.py
evaluate.py
forecasting/__pycache__/moving_average.cpython-313.pyc
forecasting/__pycache__/moving_average.cpython-314.pyc
forecasting/moving_average.py
llm_baseline.py
main.py
models.py
outputs/Ciao/causalepp_ciao.pt
requirements.txt
train.py
```

Implementation map:

| Component | Evidence |
|---|---|
| CLI and run directories | `main.py:12–108` |
| Configuration | `config.py:5–39` |
| LightGCN / CausalEPP / loss | `models.py:10–194` |
| Data transformation | `data/input_data_transformation.py:3–58` |
| Filtering, split, time bins and feature saves | `data/preprocess.py:17–356` |
| Pairwise negative sampling and split loader | `data/dataset.py:12–114` |
| Popularity/EPP | `data/popularity.py:9–169` |
| Moving Average and Holt | `forecasting/moving_average.py:7–163` |
| Optimization, checkpoint selection and integration | `train.py:148–564` |
| Ranking evaluation and example lists | `evaluate.py:9–290` |
| Calibration | `calibration.py:11–286` |
| Optional local LLM scoring | `llm_baseline.py:11–228` |

All three requested methods are implemented and integrated. Holt is in the file named `moving_average.py`; it is not missing. Calibration is a Ciao adaptation. LORE, USG, geography/social modeling, MF backbone selection, the research baseline suite and ablation/grid-search experiment runners are not implemented. No CLI smoke-test, evaluate-only, checkpoint, data-directory or device flags exist. The LLM path is implemented but was not run or downloaded.

## 2. Environment and dependency setup

Host: Linux x86-64, 3 visible AMD EPYC CPU threads, about 9.7 GiB RAM, no swap. Python 3.12.14. No `nvidia-smi` executable was found. Installed PyTorch is CPU-only; `torch.cuda.is_available()` is false and `torch.version.cuda` is null. CPU is sufficient for these bounded checks. Full-run memory/time requirements are not documented or benchmarked here; paper hardware is not a project minimum requirement.

The repository declares no supported Python range. Python 3.12 was validated only for the executions below. A project-local `.venv` was created; system Python was not modified. Wheel compatibility with CPython 3.12/Linux was resolved by pip. Installed versions: NumPy 2.5.5, pandas 3.1.1, PyTorch 2.15.0+cpu, scikit-learn 1.9.1. `pip check` reported `No broken requirements found.` Full dependency pins are in `work/validation/environment.freeze.txt`.

`requirements.txt:1–6` specifies only lower bounds: numpy>=1.24, pandas>=2.0, torch>=2.0, scikit-learn>=1.3, transformers>=4.51.0, accelerate>=0.26.0. Transformers and accelerate are absent from this venv and were deliberately not installed because only the optional LLM path uses them. Scikit-learn is declared but no import was found in the project sources. No system software, datasets or LLM weights were installed/downloaded. CPU PyTorch and its Python dependencies were downloaded into the venv.

Exact setup commands, run from the extracted project root:

```bash
python -m venv .venv
.venv/bin/python -m pip install --disable-pip-version-check --no-cache-dir numpy pandas scikit-learn torch --index-url https://pypi.org/simple --extra-index-url https://download.pytorch.org/whl/cpu
.venv/bin/python -m pip check
.venv/bin/python -m pip freeze > work/validation/environment.freeze.txt
.venv/bin/python -B main.py --help
```

The installation completed with exit 0. The CPU extra index resolved a `+cpu` wheel in this run; when repeating setup, explicitly select a CPU wheel so a future resolver does not choose CUDA dependencies. Importing midway through installation briefly produced `ModuleNotFoundError: No module named 'pandas'`; this was an installation-in-progress issue, resolved after pip completed. The dependency freeze is a record of this environment, not a claim that all future releases satisfy research reproducibility.

## 3. Datasets, schema and execution modes

### Required inputs

Default dataset directory: `data/Ciao`; raw file: `data/Ciao/ratings.csv` (`config.py:7–8`). Raw parser expects four comma-separated fields `user,item,rating,timestamp`, using `header=None` and date format `%d.%m.%Y` (`data/preprocess.py:151–169`). The uploaded file actually has a header; it is treated as a data row then dropped during conversion. README says no header and does not specify this strict date requirement.

Processed files are **tab-separated despite the .csv extension**, with header `user,item,rating,timestamp,time_bin`. User/item IDs are nonnegative integer indexes; rating is numeric, timestamp numeric, and time_bin is in 0..99. `train.load_training_data` consumes train/val/test plus the following arrays:

| File | Observed schema |
|---|---|
| `item_local_popularity.npy` | float32, (100, 11185), finite proportions |
| `user_epp.npy` | float32, (100, 5958), finite proportions |
| `time_bin_edges.npy` | float64, (101,), numeric bin boundaries |
| `user_mapping.csv` | comma-separated `raw_user,user` |
| `item_mapping.csv` | comma-separated `raw_item,item`; names used for examples/LLM |
| `all_data.csv` | filtered mapped interactions before holdout cold-start removal; not loaded by trainer |

| Split | Rows | Distinct users | Distinct items | Timestamp min / max |
|---|---:|---:|---:|---|
| all | 146055 | 5958 | 11185 | 959731.0 / 1316908.0 |
| train | 131435 | 5698 | 10687 | 959731.0 / 1254787.0 |
| val | 4225 | 413 | 2616 | 1254873.0 / 1284854.0 |
| test | 2426 | 272 | 1792 | 1284940.0 / 1316822.0 |

All files required for the non-LLM Ciao paths are present. `outputs/Ciao/causalepp_ciao.pt` exists (4,446,060 bytes); it was read with `weights_only=True`, and its model state loaded strictly into the current architecture. Dimensions: 5,958 users, 11,185 items, embedding 64, three graph layers, MLP width 32. Its saved config says 25 epochs, but training provenance and quality cannot be established from this metadata alone. No LLM score cache or weights are included. Amazon-Music, Douban-Movie, Brightkite, Foursquare, Gowalla and Yelp are missing; they are needed for the respective paper reproductions, not for this Ciao smoke test.

### Actual project commands (documented, not full-run executions here)

```bash
# Original complete pipeline; preprocessing overwrites processed data:
.venv/bin/python main.py --preprocess --epochs 100
# Existing data, Moving Average:
.venv/bin/python main.py --forecast-method moving_average --epochs 100
# Existing data, Holt:
.venv/bin/python main.py --forecast-method holt --epochs 100
# Moving Average with calibration:
.venv/bin/python main.py --calibrate --epochs 100
# Holt with calibration:
.venv/bin/python main.py --forecast-method holt --calibrate --epochs 100
# Optional LLM hybrid: needs extra packages/weights and resource approval:
.venv/bin/python main.py --llm-baseline
```

These flags were confirmed in the executed `--help`; the 100-epoch commands above were **not run**. `python main.py --preprocess` also starts training after preprocessing; it is not preprocessing-only. `python -m data.preprocess` is the separate preprocessing entry point and overwrites the configured processed files. `python train.py` starts default training directly and writes to `outputs/Ciao`, potentially overwriting existing outputs; do not use it on preserved artifacts. `data/input_data_transformation.py` has a hard-coded Windows path and writes a different raw format; it is not a portable CLI. Running the forecasting/calibration modules directly does not run an experiment.

`main.py:57–65` creates a timestamped directory under `outputs/Ciao`, named for forecast/calibration or LLM mode. Outputs include checkpoint, `test_metrics.json`, `recommendation_examples.json`, `global_item_counts.npy`, `expected_item_popularity.npy`; calibrated runs add `calibration_lambdas.json` and `popularity_calibrated_test_metrics.json`. Forecast vectors are used in memory but not saved by the original pipeline. `--epochs 0` is not a smoke-test shortcut: no new best checkpoint is saved before the unconditional load at `train.py:415`.

## 4. Executions and method status

**PASS below means bounded execution success only. It does not mean paper reproduction, good recommendation quality, or full experimental correctness.**

A new validation harness calls unchanged project functions. Synthetic runs used 6 users, 24 items, 72 training interactions, 12 bins, one CPU epoch, dimension 8, one graph layer, batch 72 and top-K=3. All changes to settings were in memory; original Config was preserved. The fixture includes every item in training. Checks exercised data loading, forecasts, forward/backward optimization, best checkpoint save/load, validation/test metrics and saved JSON.

Independent calculation checks included MA/Holt for `[0.1,0.2,0.3]` with horizon 2 (both 0.5), constant/single/empty series, NaN/Inf rejection, JSD=0 for matching distributions and JSD=1 for disjoint distributions, and relevance-only versus calibration-only reranking. Holt level/trend uses alpha=.3, beta=.1. The uniform synthetic training fixture has tied popularity tiers, so a separate real-data test was needed to exercise user groups.

The second harness loaded the supplied weights without training, used all training interactions to build the graph and forecasts, then evaluated six test users selected by training-popularity groups (two per group). Calibration fitting used six validation users, grid 0..1 step .1, candidate pool 150, top-K=20. This is deliberately a small diagnostic sample, not an unbiased benchmark. Validation IDs: 483,1574,178,312,286,1263. Test IDs: 483,2263,178,312,1098,1263. All validation history was excluded when testing.

| Method | Status | Synthetic exit / seconds | Existing-checkpoint exit / seconds |
|---|---|---|---|
| moving_average | PASS (bounded smoke) | 0 / 3.035 | 0 / 7.565 |
| holt | PASS (bounded smoke) | 0 / 2.429 | 0 / 7.175 |
| calibration | PASS (bounded smoke) | 0 / 2.416 | 0 / 18.314 |

Exact executed commands (from project root):

```bash
PYTHONPATH=. OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES= .venv/bin/python -B work/validation/smoke.py moving_average
PYTHONPATH=. OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES= .venv/bin/python -B work/validation/smoke.py holt
PYTHONPATH=. OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES= .venv/bin/python -B work/validation/smoke.py calibration
PYTHONPATH=. OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES= .venv/bin/python -B work/validation/checkpoint_smoke.py moving_average
PYTHONPATH=. OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES= .venv/bin/python -B work/validation/checkpoint_smoke.py holt
PYTHONPATH=. OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES= .venv/bin/python -B work/validation/checkpoint_smoke.py calibration
```

`PYTHONPATH=.` lets the harness find the project's modules. `-B` prevents bytecode writes. Thread variables limit CPU parallelism; an empty `CUDA_VISIBLE_DEVICES` hides GPUs. The scripts live in `work/validation/` and are validation additions, not invented original CLI modes.

| Synthetic mode | Recall@3 | Precision@3 | NDCG@3 | Coverage@3 |
|---|---:|---:|---:|---:|
| moving_average | 0.333333 | 0.111111 | 0.271822 | 0.375000 |
| holt | 0.000000 | 0.000000 | 0.000000 | 0.333333 |
| calibration | 0.333333 | 0.111111 | 0.271822 | 0.375000 |

Synthetic calibration: CP_H and CP_Im All NDCG@3=.271822, JSD=0, ARP=3, PopLift=0, coverage=.375. All fitted group lambdas were 0. The tied fixture places users in LowPop; empty synthetic groups report zeros, not measured performance.

Existing-checkpoint results: for both forecasts, Recall@20, Precision@20 and NDCG@20 were **0** on these six users; coverage=.004738489. Zero accuracy is a real observed result, not an execution failure or evidence that either method is generally ineffective. Moving Average item forecast range was [0,.009297521], Holt [0,.005837837]; both user forecasts were [0,1].

Real calibration: LowPop/MedPop/HighPop fitted lambdas all 0; thresholds [2.645896143,3.607335201]. CP_H and CP_Im both returned All JSD=.341407222, ARP=296.475, PopLift=9.165663929, coverage=.004738489, with all ranking-accuracy metrics 0. Group JSDs: .560229347 / .282877170 / .181115148. This sample showed no CP_Im improvement. Candidate restriction and tier composition may limit reranking; broader experiments are needed before attributing a cause.

Output locations:

- Synthetic outputs: `work/validation/{moving_average,holt,calibration}/`, including checkpoint, metrics, examples and popularity arrays; calibration folder also has both calibration JSON files.
- Real checkpoint outputs: `work/validation/checkpoint_{moving_average,holt,calibration}.json` and corresponding `.log` files.
- Exact exits/timings: `work/validation/executions.json`, `checkpoint_executions.json`.
- Source/data checks: `audit.py`, `audit.json`, `audit.log`, `edge_checks.py`, `edge_checks.json`, `edge_checks.log`.
- Reprocessed data: `work/validation/reprocessed/`; originals untouched.
- Original-byte hashes: `work/validation/original_file_hashes.json`.

All six method executions emitted the same PyTorch `UserWarning` at `models.py:76`: “Sparse invariant checks are implicitly disabled…” This is a library diagnostic, not an observed invalid-graph error or crash. The full warning is preserved in each log. No method execution ended with an error.

## 5. Research papers and POI/PUI terminology

The repository had no PDFs; the supplied papers resolve that missing context:

1. Tan et al., **Taming Recommendation Bias with Causal Intervention on Evolving Personal Popularity**, KDD 2025, arXiv:2505.14310v2, DOI 10.1145/3711896.3737146.
2. Forster et al., **Exploring the Effect of Context-Awareness and Popularity Calibration on Popularity Bias in POI Recommendations**, RecSys 2025, arXiv:2507.03503v2, DOI 10.1145/3705328.3748017.

POI means **point of interest**, a location in the second paper. This repository recommends Ciao items, not geographic locations. EPP means **evolving personal popularity**. No `PUI` identifier or definition was found in the project source/README; do not equate PUI with POI or invent an expansion. The PDFs were extracted with `pdftotext -layout` into `/workspace/work/papers/` for comparison.

### CausalEPP: section-by-section comparison

| Paper section / equation | Finding and source evidence | Category |
|---|---|---|
| §§1–2: motivation, related work | Project attempts the proposed popularity/quality/conformity separation; the related-work baseline comparison is absent. README describes intent, not evidence of effectiveness. | Verified scope; effectiveness requires experiments |
| §3 Eq.(1), §4.1 Eq.(3) | Code uses each fixed bin's interaction share and within-bin popular-item fraction (`data/popularity.py:9–132`). Paper uses a recent sliding interval `[t-w1,t]`, with w1=6 months in §5.1. No sliding-window w1 setting exists. | Verified deviation |
| §3 Eq.(2) | Trailing arithmetic mean is implemented by valid convolution (`forecasting/moving_average.py:7–22`). Startup windows are shortened. | Verified formula structure |
| §4.1 high-popularity threshold | Uses 80th percentile of positive popularity values, strict `>` (`data/popularity.py:98–111`), broadly matching a top-20% threshold. Ties can mean fewer than 20% selected. Restricting the quantile to positive entries needs explicit protocol documentation. | Verified behavior; effect requires experiments |
| §4.2 graph / Eqs.(4–5) | Training represents deconfounding through a mean-popularity substitution; it does not enumerate the full causal distribution. This follows the paper's approximation approach, not an empirical proof of causal identification. | Verified structural implementation; causal claims unvalidated |
| §4.3 Eqs.(6–9) | `models.py:127–157` implements tanh(q+c)*softplus(m) and exp(-alpha*abs(s-p))*p*MLP(i), with propagated LightGCN item embeddings and clamping to [0,1]. `train.py:168–196,258–277,303–343` supplies training counts, mean popularity and time-bin EPP. | Verified algebraic structure |
| Algorithm 1 line 1, Eq.(9) expectation | Paper averages local popularity over item interaction records. Code averages all active time bins equally (`train.py:180–184`, `data/popularity.py:157–169`), including bins where an item has zero share. For item 343: bin mean=.007259858, interaction mean=.039647918 using the same saved bin features. | Verified deviation |
| Eq.(10) quality loss | `models.py:159–167` uses softplus(-sign(count_i-count_j)*(q_i-q_j)), algebraically -log sigmoid. Equal-count pairs give constant log(2) and zero quality gradient. Global counts come from train only. | Verified formula structure |
| Eqs.(10–12) sampling/reduction | `data/dataset.py:33–83` samples uniformly from each user's unobserved training-item complement. `train.py:347–361` uses the same interaction-sampled positive/negative pair for quality loss; paper Eq.(10) sums over items. Both losses use batch means (`models.py:167,174`) instead of written sums. Item weighting and optimization trajectory need comparison. | Verified implementation; equivalence requires experiments |
| §4.3 optimization / §5.1 | Adam, lr=.001, weight_decay=.0001 (`train.py:237–241`). Alpha=.5, quality weight=.2, horizons 5/10 match reported values; batch 2048 differs from paper 8192 (`config.py:17–29`). No automated model hyperparameter grid search. | Verified differences |
| §4.4 Eqs.(13–17) | Forecast latest value + final MA difference * horizon, then clamp (`forecasting/moving_average.py:25–63`); scores use forecasted p/s (`evaluate.py:97–122`). This is a discrete derivative implementation. Horizon units are bins, not verified months. | Verified structure; temporal semantics differ |
| §4.4 Holt | Correct conventional additive level/trend recurrence in `forecasting/moving_average.py:85–93`, with [0,1] clipping. Holt is a project extension, not the CausalEPP paper's stated forecasting method. | Verified extension, smoke PASS |
| §5.1 dataset protocol | 5-core is implemented; split uses timestamp 90th percentile and median remaining timestamps, not guaranteed equal chronological parts (`data/preprocess.py:36–81`). Warm-start filtering removes 7,969 held-out records in total. Paper Ciao: 5,868 users / 10,724 items / 143,217 interactions; supplied filtered data: 5,958 / 11,185 / 146,055. | Verified reproducibility mismatch |
| §5.2 performance comparison | Only LightGCN CausalEPP/hybrid paths exist. No MF baseline selection or ten-baseline suite. Default inference already intervenes, corresponding more closely to the paper's CausalEPP-Inv mode. | Verified missing reproduction coverage |
| §§5.3–5.5 ablations, sensitivity, bias analysis | No dedicated ablation or sensitivity driver or reproduction of paper figures/statistical tests. Calibration metrics are additional adaptation metrics. | Requires approved experiments |
| §6 conclusion | Smoke success does not substantiate the paper's accuracy, bias-reduction or causal-effect conclusions. | Requires experiments |

### POI paper: section-by-section comparison

| Paper section | Finding and source evidence | Category |
|---|---|---|
| §1 and §2.1 | LORE/USG context-aware POI claims are outside this repository; Ciao lacks location coordinates/social context. | Verified scope difference |
| §2.2 data and groups | Paper: Brightkite, Foursquare, Gowalla, Yelp, per-user 65/15/20 temporal split, Low/Med/High at 20/60/20 using normalized check-in popularity. Project: Ciao, global split; user groups use mean log1p(train counts) (`calibration.py:21–36`), which can change ordering relative to mean normalized frequency. | Verified adaptation |
| §2.2 item groups | `calibration.py:11–18` implements 20th/80th quantiles of positive train counts; zero-count items are tail and ties affect group sizes. | Verified behavior; exact paper alignment not established |
| §2.3 Eq.(1) | Greedy relevance/JSD objective implemented (`calibration.py:158–183`). Scores are min-max normalized within candidate lists (`calibration.py:136–138`); partial-list mean relevance is used. The paper's aggregate Rel does not alone settle these scale conventions. | Verified structure; scaling needs reproducibility specification |
| §2.3 Eq.(2), CP_H | Validation group-specific grid selects harmonic accuracy/calibration tradeoff (`calibration.py:230–255`). Code multiplies the displayed fraction by 2; this positive constant does not change the maximizing lambda. | Verified alignment of selection criterion |
| §2.3 CP_Im | Lambda fixed to 1 (`calibration.py:272–274`), as the paper specifies. This is greedy calibration-first reranking, not a globally optimal-list guarantee. | Verified alignment |
| §2.4 training/evaluation | Candidate pool 150 matches paper. Default K=20 differs from paper K=10; model and training protocol differ. No RecBole BPR or CAPRI LORE/USG reproduction. | Verified adaptation |
| §2.4 metrics | Ranking metrics, base-2 JSD, ARP from raw counts and mean per-user PopLift are implemented (`calibration.py:48–74,186–227`). Absolute ARP values cannot be directly compared with normalized-frequency paper tables. Ratio-of-group-means versus mean-of-user-ratios should be resolved against study evaluation code before claiming identical PopLift. | Verified implementation; metric equivalence requires further evidence |
| §3 results / discussion and conclusion | Tiny tests do not reproduce Tables 2–3, geographic/context effects, significance tests or user-group fairness conclusions. No independent empirical claim of debiasing is warranted. | Requires experiments |

## 6. Leakage and historical-information audit

**Verified positives:** train max timestamp < validation min, and validation max < test min for supplied data. Recomputing popularity and EPP from train gives maximum absolute difference **0** for both saved arrays. Graph construction and global counts use train only (`train.py:168,218–224`). Forecasts use the saved training history, and model selection/calibration lambdas use validation rather than test labels (`train.py:373–408,486–505`). Testing excludes train+validation interactions (`train.py:424–442`). No test interaction contamination was found in these computed statistics.

**Verified limitations:**

- Feature bins aggregate all events in a bin. For an early event, EPP includes later same-bin events (`data/popularity.py:92–129`; `train.py:303–311`). Thus features are not strictly point-in-time histories at each event. This differs from a truly causal rolling history; its effect requires retraining experiments.
- K-core, ID mapping and train-cutoff estimation are performed on the full filtered dataset before splitting (`data/preprocess.py:186–227`). This is transductive selection using future information, rather than a strict deploy-time catalog construction. It is not the same as putting test interactions in the training graph.
- Global training averages/counts intentionally use all training events, including future events relative to earlier training samples. This is compatible with an offline training statistic but should not be described as online historical-only features.
- 260 indexed users and 498 indexed items have no training observations. Full-catalog scoring can include these untrained catalog items (`train.py:72–89`; `evaluate.py:66–88`). Cold-start recommendation effects require experiments.
- Train/val pair overlap=12, train/test=11, val/test=4. Training has 910 repeated user-item pairs. Seen items are excluded from predictions, but repeated held-out positives remain in truth/recall denominators (`evaluate.py:36–40,125–169`). The evaluation target can therefore contain unreachable hits. Define repeated-interaction semantics before changing it.
- Calibration test profiles use train+validation while thresholds/lambdas were fit from train (`train.py:506–522`, `calibration.py:91–93`). This is legitimate available history, but users can change groups. Decide whether groups should be frozen for paper-comparable group reporting.
- LLM candidates use training positives and globally popular training items, not held-out item labels (`llm_baseline.py:156–187`); test user identities are included. LLM scoring is restricted-candidate evaluation, not comparable to full-catalog results. Cache lacks model/data fingerprint validation, and loading a cached run still instantiates the HF model (`llm_baseline.py:168–180`). No LLM execution was performed.

## 7. Errors, bugs and suggested fixes (not applied)

| Finding | Evidence / impact | Suggested next action |
|---|---|---|
| **Verified timestamp-unit bug** | `data/preprocess.py:161–169` assumes datetime integer units are ns. pandas 3.1.1 parsed `datetime64[us, UTC]`; 2011-09-17 became 1,316,217 instead of 1,316,217,600 Unix seconds. Separate preprocessing reproduced all four supplied data frames exactly, including the wrong units. | Explicitly normalize datetime resolution before conversion, add date/unit validation, and regenerate only new versioned data after approval of the intended semantics. A near-uniform scale error can preserve ordering, but does not make timestamps correct. |
| **Verified incompatible raw converters** | `data/input_data_transformation.py:5,25–28,38,58` uses a Windows-only path, retains only ratings 30/40/50, writes Unix seconds and a current-directory ratings.csv; preprocess requires DD.MM.YYYY. A tiny Unix-input probe raised `ValueError: No valid interactions found.` | Agree on one raw schema and path; explicitly handle Unix/date formats and intended rating inclusion. Do not silently change the sample population. |
| **Verified example-list bug** | `evaluate.py:248–253` masks seen scores but chooses min(K,catalog size), not unseen count. Tiny 3-item/2-seen case returned IDs [2,0,1], including two seen items at -Infinity. Ranking metrics use an unseen-count cap, so example output can disagree. | Cap by finite unseen candidates; serialize finite JSON only. No production change made. |
| **Verified timestamp precision loss** | `data/dataset.py:89` stores timestamps as float32. Probe: 1,700,000,001 became 1,700,000,000. Bin-boundary errors are possible with correctly scaled timestamps. | Preserve int64/float64 timestamps; test boundary cases after fixing units. Actual metric effect unmeasured. |
| **Verified documentation mismatch** | README promises per-user held-out splitting; `data/preprocess.py:57–79` splits globally by timestamp. Raw header handling also differs from README. | Document the current protocol or make a reviewed research change. |
| **Suspected quality/sampling weighting mismatch** | Interaction-frequency-weighted quality pairs versus item-indexed paper Eq.(10), and bin-average versus interaction-average expectation. | Resolve intended paper interpretation, compare controlled implementations, then approve any equation/sampling change. |
| **Suspected degenerate calibration selection** | If all grid NDCGs are zero, harmonic objective ties and first lambda=0 wins (`calibration.py:245–254`). Observed small-sample lambdas were all 0. | Record validation-grid curves and group counts; choose/document a tie policy only with research approval. |

Other messages: preprocessing emitted pandas `DtypeWarning` for mixed types in the raw CSV. A first audit-only example selected item 0, which has no train interactions, causing `Mean of empty slice` and a NaN diagnostic; this is a harness example limitation, not a model metric failure. `edge_checks.json` supplies the valid item-343 comparison. Pip emitted a cache ownership warning and disabled its global cache; installation succeeded without system edits. `--epochs 0` checkpoint failure is a static-code finding, not an executed failure claim.

No algorithm equations, data parsing logic, experiment configurations or existing outputs were changed to make tests pass.

## 8. Reproducibility concerns

No dataset source/version/license manifest, data hashes in training metadata, pinned original environment, experiment log, training seed history, saved forecast vectors or checkpoint provenance is included. Original cached Python versions do not establish the runtime used to produce the checkpoint. This session's byte hashes and dependency freeze support this audit only.

Equal-width training bins differ from the paper's full timeline and six-month sliding windows. Warm-start filtering changes the holdout population; `all_data.csv` row count is not the sum of saved train/val/test. Duplicate interactions, tie policies, zero-history users, unused catalog indexes, negative sampling distribution, differing quality-loss reductions, and popularity expectation weighting all need explicit methodological decisions. CPU smoke metrics must not be presented as paper numbers or comparative method rankings.

## 9. Recommended next steps

1. Review the verified timestamp and raw-schema bugs first. Agree on the date resolution, split protocol and repeated-interaction evaluation target; make any fixes on the testing branch in a separate reviewed change.
2. Decide whether the goal is faithful CausalEPP reproduction or a clearly labeled extension. For reproduction, resolve sliding-window features, interaction-weighted popularity expectation, sampling, preprocessing source and paper hyperparameters.
3. Define POI calibration as a Ciao adaptation unless the original POI data, contextual features and LORE/USG baselines are supplied. Fix/document group popularity and ARP/PopLift conventions before comparing paper tables.
4. Add focused regression checks for date parsing, timestamp precision, historical windows, example-list masking, repeated positives and calibration groups. The validation harness here provides evidence but is not a complete maintained test suite.
5. After agreeing on methodology, create versioned datasets and an environment lock, log configuration/data hashes, and request an explicit CPU/GPU runtime budget before full training or large downloads. Then evaluate all held-out users and multiple seeds with baselines and uncertainty estimates.

## 10. Beginner explanation and completion boundary

A **branch** is a separate line of work; the testing branch was created without changing the main commit. A **virtual environment** keeps project libraries separate from system Python. A **smoke test** is a tiny run checking that the pieces connect. **PASS** here means the code completed and its output files were inspected; it does not mean recommendations are accurate or the science is validated. Recall measures how many held-out items were found; precision measures how many recommendations were hits; NDCG rewards hits near the top. JSD measures disagreement between two popularity distributions (lower is closer).

Inspection, isolated CPU setup, all three bounded method checks and this report are complete. Full training, full paper reproduction, optional LLM execution and research-code fixes remain intentionally unperformed. No original source/data/model/config file was edited; nothing was committed or pushed.

Report saved at `reports/local_validation_report.md` inside the extracted repository. The chat's designated `/codex/.../output` export path could not be created because `/codex` is on a read-only filesystem, even with an explicit path-write permission profile. This is an export-location limitation, not an automatic approval rejection or a validation failure. The repository report and evidence remain available in the workspace.
