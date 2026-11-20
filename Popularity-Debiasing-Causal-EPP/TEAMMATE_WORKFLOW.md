# Karan's requested workflow: three runs, POI audit and Douban compatibility

This is the entry point for the work described in Karan's messages. The original uploaded ZIP is treated as his pushed snapshot (commit metadata `1b5e028d98d1b736661004c0df06458028dfba9a`). Work is published to `Animesh2609/Tendering`, branch `animesh-dm-testing`, inside `Popularity-Debiasing-Causal-EPP/`. Main and the unrelated IR project are preserved.

## Workstream A: run the three modes and validate POI calibration

The default workflow uses **LightGCN+CausalEPP**. LLM modes are separate experiments and are not run by this entry point.

### Setup

```bash
git clone --branch animesh-dm-testing https://github.com/Animesh2609/Tendering.git
cd Tendering/Popularity-Debiasing-Causal-EPP
git branch --show-current
python -m venv .venv
source .venv/bin/activate
python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements-core.txt
python -m pip check
```

The branch command must print `animesh-dm-testing`. On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1` instead of `source`. Python 3.12 is the tested version. A virtual environment isolates Python packages; these commands do not install system software or Qwen weights.

Copy your existing `data/Ciao/` from the original ZIP into this directory. Source publishing intentionally excludes raw/processed datasets and model weights. The trainer requires tab-separated train/validation/test files, time-bin edges, popularity/EPP arrays and an item mapping, as listed in the original validation report. Do not rerun preprocessing over the preserved originals.

### Quick executable checks, no real dataset needed

```bash
python -B -m unittest discover -s tests -v
```

Tests build their own synthetic fixtures. The new workflow test converts a timestamped interaction fixture to the expected schema and actually trains/evaluates Moving Average, Holt and calibration for one tiny CPU epoch each. This establishes pipeline execution and schema compatibility, not real-Douban correctness or paper accuracy.

### Run all three modes

After deciding on a runtime budget:

```bash
python -B teammate_workflow.py \
  --data-dir data/Ciao \
  --output outputs/karan_ciao_run_001 \
  --epochs 1 --mode all --threads 2
```

This runs three separate experiments:

1. `moving_average`: normal LightGCN+CausalEPP with moving-average forecasting.
2. `holt`: the same training pipeline with Holt level/trend forecasting.
3. `calibration`: moving-average LightGCN+CausalEPP plus the existing CP_H and CP_Im calibration implementation.

`--epochs 1` checks end-to-end execution but is not converged training. Increase it only after choosing an appropriate resource budget. `--threads 2` limits CPU parallelism. The runner is CPU-only, never triggers LLM downloads and never preprocesses data. Each experiment gets its own output directory and the same seed. It stops on the first failure, preserves the traceback and verifies that input hashes did not change.

For individual runs use a new output directory each time:

```bash
python -B teammate_workflow.py --data-dir data/Ciao --output outputs/ma_001 --epochs 1 --mode moving_average
python -B teammate_workflow.py --data-dir data/Ciao --output outputs/holt_001 --epochs 1 --mode holt
python -B teammate_workflow.py --data-dir data/Ciao --output outputs/calibration_001 --epochs 1 --mode calibration
```

`execution_summary.json` records settings, elapsed seconds, per-mode exit codes and actual metrics. Each mode also has a `.log` with output/warnings/errors, a checkpoint and saved evaluation artifacts. `PASS_EXECUTION_ONLY` means the run completed; it does not certify paper correctness, debiasing or better accuracy.

The original CLI remains available:

```bash
python main.py --forecast-method moving_average --epochs 1
python main.py --forecast-method holt --epochs 1
python main.py --calibrate --epochs 1
```

Use the new runner for dataset/output control and structured logs. Do not use `--preprocess` on preserved originals. Original `main.py --preprocess` also proceeds to training.

### Check the POI paper honestly

| Question | Current finding |
|---|---|
| Is greedy relevance/JSD reranking implemented? | Yes. |
| Are CP_H weights selected on validation? | Yes. |
| Is CP_Im calibration-first with lambda=1? | Yes. |
| Is the entire POI paper reproduced? | No: Ciao replaces POI data; geographic/social LORE/USG models are absent. |
| Are user popularity groups identical to the paper? | No: this code averages log interaction counts; the paper discusses normalized check-in frequency. |
| Is top-K identical? | Default K=20 here; the POI study uses top-10. |
| Does calibration improve this supplied checkpoint? | No; the original all-user evaluation produced identical rankings because candidate pools contained one tier. |
| Did the later experimental repair increase accuracy? | No. It reduced JSD, but test NDCG decreased slightly. It is not the default here. |

Read `reports/local_validation_report.md` for line-level evidence; `reports/calibration_all_users_report.md` for actual all-user results; and `reports/accuracy_first_calibration_report.md` for the clearly separated experimental revision. Do not call successful execution a successful paper reproduction.

For a matched before/after calibration comparison, train once and evaluate that same checkpoint using `run_lightgcn_calibration.py` or use an existing checkpoint with `evaluate_calibration.py`. See `CALIBRATION_API_GUIDE.md`. The three-mode runner reproduces Karan's requested modes; the matched-checkpoint evaluator isolates the effect of reranking.

## Workstream B: make timestamped Douban interactions use the same model pipeline

No real Douban dataset was supplied. The new adapter supports explicitly mapped CSV/TSV interaction tables, not every possible Douban download. It does not invent timestamps, decode MATLAB files, merge arbitrary tables, or claim real-Douban validation. A dataset without interaction times cannot support the temporal experiment as specified without an explicit methodological change.

Required source fields are user ID, item ID, numeric rating and timestamp. The example below assumes a header with `user_id,item_id,rating,timestamp`; replace these names with your file's actual columns. Inspect your schema first.

```bash
python -B prepare_douban.py \
  --input /path/to/douban_interactions.csv \
  --output data/Douban_processed_v1 \
  --user-col user_id --item-col item_id \
  --rating-col rating --time-col timestamp \
  --timestamp-unit s --min-user 10 --min-item 10
```

If timestamps are milliseconds, use `--timestamp-unit ms`. For text dates, replace the timestamp-unit argument with an explicit format, for example `--date-format '%Y-%m-%d'`. Do not guess units: seconds and milliseconds differ by a factor of 1,000.

For a headerless tab-separated file with columns user/item/rating/time in that order:

```bash
python -B prepare_douban.py \
  --input /path/to/douban.tsv --output data/Douban_processed_v1 \
  --sep '\t' --no-header \
  --user-col 0 --item-col 1 --rating-col 2 --time-col 3 \
  --timestamp-unit s
```

The adapter:

- Fails on missing fields and invalid values rather than silently dropping them. `--drop-invalid` is an explicit opt-in and records the number dropped.
- Converts dates to Unix seconds with explicit datetime resolution, avoiding the original Ciao converter's microsecond/nanosecond assumption.
- Applies configurable iterative k-core filtering (default 10 for Douban), maps IDs and reuses the original chronological split and training-only feature functions.
- Checks strict chronological separation and nonempty warm-start train/validation/test splits.
- Writes the same tab-separated split schema (`user,item,rating,timestamp,time_bin`), `.npy` features/edges and mapping CSVs expected by `train.py`.
- Refuses an existing output directory and records the source SHA-256, settings, retained/dropped rows and limitations in `preprocessing_manifest.json`.

Then use the **same model code**:

```bash
python -B teammate_workflow.py \
  --data-dir data/Douban_processed_v1 \
  --output outputs/karan_douban_run_001 \
  --epochs 1 --mode all --threads 2
```

Train a new checkpoint for Douban; do not load the Ciao checkpoint against a different user/item mapping. The inherited checkpoint filename `causalepp_ciao.pt` is a legacy name inside the selected output directory; it does not mean a Douban run used Ciao data.

Important limitations: fixed-bin popularity/EPP, full-data k-core/ID mapping, and original split/quality-loss conventions are retained. These are not silently corrected into a paper-faithful pipeline. `raw_item` contains raw Douban IDs; enrich it with genuine titles before an LLM text experiment. Matching the schema alone is insufficient to establish research reproduction.

## Scope and safety

Original source/model/data/configuration files are preserved except the previously documented optional trainer backend hook. New workflow/preprocessing code does not change the CausalEPP equations. Historical reports describe their respective snapshots; no claim is made that full Ciao or real-Douban training has been completed by this delivery.

Keep `.venv/`, `work/`, data directories, downloaded weights and outputs out of commits. Push only reviewed source/docs/tests to the testing branch. Main remains untouched. The LLM implementation and API remain available, but are not prerequisites for these two workstreams.
