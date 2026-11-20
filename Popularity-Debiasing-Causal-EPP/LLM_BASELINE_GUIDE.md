# LLM baseline, CausalEPP and popularity calibration

This package compares **LightGCN + CausalEPP** with **frozen Qwen text features + CausalEPP**, before and after popularity-calibrated reranking. It retains Moving Average and Holt forecasting. “POI calibration” refers to the transferable popularity-calibration method from the POI paper; no separate PUI algorithm, location modeling, LORE or USG is implemented.

**No measured full-dataset improvement is claimed.** The real Qwen encoder passed a 32-title CPU benchmark (11 seconds total, 3.09 seconds encoding, 3.81 GiB peak RAM). Six automated tests passed, including tiny synthetic training/comparison and checkpoint reevaluation. Full-data encoding/training/comparison have not been executed. The known data/methodology limitations below still apply.

## 1. What is included

| File | Purpose |
|---|---|
| `llm_embedding_baseline.py` | Encodes item text once; replaces LightGCN with frozen features and trainable projections |
| `compare_backbones.py` | Trains both backbones under matched settings; evaluates base/CP_H/CP_Im; exports comparison CSV/JSON; reloads checkpoints |
| `download_qwen_weights.py` | Explicit optional model download, pinned revision, 3 GB cap and weight checksum verification |
| `train.py`, `models.py` | Existing CausalEPP training/scoring/losses; optional backend hook added to trainer |
| `forecasting/moving_average.py` | Moving Average and Holt |
| `calibration.py` | Popularity tiers, validation-selected CP_H and calibration-first CP_Im |
| `evaluate.py` | Full-catalog ranking and recommendation examples |
| `data/*.py`, `config.py` | Original preprocessing, features, dataset and configuration |
| `tests/` | Small CPU tests using self-contained synthetic data |
| `reports/` | Inspection findings and actual encoder benchmark evidence |

The original generation-based `--llm-baseline` in `main.py` is retained for reference. **Use the new commands below for the faster frozen-feature approach.** These are different methods; neither is claimed to be a faithful replacement with identical accuracy.

## 2. Checkout and environment

From GitHub, use the testing branch:

```bash
git clone --branch animesh-dm-testing https://github.com/Animesh2609/Tendering.git
cd Tendering/Popularity-Debiasing-Causal-EPP
git branch --show-current
```

The last command must print `animesh-dm-testing`. Do not perform these experiments on main.

Use Python 3.12. The tested environment was Linux CPU, Python 3.12.14, torch 2.15.0+cpu, transformers 4.57.1. The lower-bound dependency file is not an assurance that every combination is compatible; the benchmark dependency freeze is included for reference.

```bash
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell instead:
# .venv\Scripts\Activate.ps1
python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements-llm-baseline.txt
python -m pip check
python -B -m unittest discover -s tests -v
```

A virtual environment keeps these libraries separate from system Python. Tests need no data download, Qwen weights or GPU. On Windows, a launcher named `py -3.12` may be used to create the venv. Do not install system software just to run this package without deciding on that separately.

## 3. Bring your existing processed Ciao data

Copy the original `data/Ciao/` directory from your uploaded project into this package. The source distribution intentionally does not publish datasets, old experiment outputs, cached features, pretrained checkpoints, Qwen weights or PDFs.

Required files:

```text
data/Ciao/train_data.csv
data/Ciao/val_data.csv
data/Ciao/test_data.csv
data/Ciao/item_local_popularity.npy
data/Ciao/user_epp.npy
data/Ciao/time_bin_edges.npy
data/Ciao/item_mapping.csv
```

Splits are tab-separated with `user,item,rating,timestamp,time_bin` headers. The item mapping is comma-separated with `raw_item,item`. IDs must match feature columns and mapping rows. Read `reports/local_validation_report.md` before treating these experiments as paper reproduction. In particular, the original date conversion and temporal feature definitions need a deliberate, reviewed correction. These commands use the existing processed files; they do not preprocess or overwrite them.

## 4. Obtain weights once

If you already have a local Hugging Face Qwen3-0.6B snapshot with tokenizer/config/safetensors files, reuse it. Otherwise, the following command explicitly downloads approximately 1.52 GB, within its built-in 3 GB cap:

```bash
python download_qwen_weights.py --output work/models/Qwen3-0.6B
```

This helper downloads only revision `c1899de289a04d12100db370d81485cdf75e47ca`. A partial failed download is left in its new directory for inspection; use a fresh destination when retrying. Model loading itself uses `local_files_only=True` and disables remote code. Do not run another download if you can reuse the existing snapshot.

## 5. Benchmark, then create the complete item cache

First run a small CPU benchmark:

```bash
python -B llm_embedding_baseline.py encode \
  --model-path work/models/Qwen3-0.6B \
  --output work/cache/qwen_32_items.npz \
  --max-items 32 --batch-size 4 --max-tokens 64 --threads 2
```

The benchmark is partial: it cannot train a full-catalog recommender. `--threads 2` limits CPU parallelism; no GPU is selected. The command prints model-loading and encoding times. The code does not impose a timeout itself; the earlier benchmark used an external 300-second subprocess timeout.

After agreeing on the runtime budget, encode all items:

```bash
python -B llm_embedding_baseline.py encode \
  --model-path work/models/Qwen3-0.6B \
  --output work/cache/qwen_all_items.npz \
  --max-items 0 --batch-size 4 --max-tokens 64 --threads 2
```

`--max-items 0` means the complete mapping. The earlier 32-title result extrapolated to about 18 minutes for all 11,185 items, **but that is not a validated runtime**: those titles were only 2–13 tokens long. Longer titles, hardware and batching change throughput. Keep the complete cache to reuse across epochs, seeds, calibration and forecasting comparisons. Existing output files are refused rather than replaced.

## 6. Train and test both models under the same conditions

Start only after approving the full-data runtime. A one-epoch comparison is a pipeline experiment, not convergence or paper reproduction:

```bash
python -B compare_backbones.py run \
  --data-dir data/Ciao \
  --cache work/cache/qwen_all_items.npz \
  --output outputs/comparison_ma_seed42 \
  --epochs 1 --seeds 42 \
  --forecast-method moving_average \
  --k 20 --candidate-pool 150 --batch-size 2048 \
  --dim 64 --layers 3 --threads 2
```

The runner performs two training runs: LightGCN and frozen-LLM features. It uses identical data hashes, seed, epoch count, forecast method, CausalEPP hyperparameters, evaluation K and calibration candidate pool. Model architectures/parameter counts differ. Each run selects its best epoch using validation NDCG and learns its calibration weights on validation; test data is used for reporting, not selection. It saves base CausalEPP, CP_H and CP_Im results from each model, so no separate training is needed merely to compare calibration variants.

To compare Holt, rerun with `--forecast-method holt` and a new `--output`. For a more reliable multi-seed experiment, use `--seeds 42 43 44` and an agreed larger epoch budget. Do not choose the best settings using the resulting test metrics; preselect or tune on validation. More seeds multiply training cost. There is no automatic early stopping.

Output layout:

```text
outputs/comparison_ma_seed42/
  comparison.csv
  comparison.json
  raw_results.json
  seed_42/
    lightgcn/
      causalepp_ciao.pt
      test_metrics.json
      popularity_calibrated_test_metrics.json
      calibration_lambdas.json
      recommendation_examples.json
      global_item_counts.npy
      expected_item_popularity.npy
      run_manifest.json
    llm/
      ...same files...
```

No previous output directory is overwritten. Manifests record dataset hashes, settings, backend and versions. The LLM checkpoint includes frozen item/user features, trainable projections, quality and conformity parameters; subsequent testing does not need the original Qwen model or cache.

## 7. Test saved models again without training

```bash
python -B compare_backbones.py evaluate \
  --run-dir outputs/comparison_ma_seed42/seed_42/lightgcn \
  --data-dir data/Ciao \
  --output outputs/lightgcn_retest.json --threads 2

python -B compare_backbones.py evaluate \
  --run-dir outputs/comparison_ma_seed42/seed_42/llm \
  --data-dir data/Ciao \
  --output outputs/llm_retest.json --threads 2
```

This loads the best checkpoint, verifies dataset hashes, reconstructs forecasts, applies saved validation-selected calibration parameters and evaluates test data. It performs no gradient updates, downloads or test-set calibration tuning. It rejects changed datasets. Exact equality with saved metrics was verified in the tiny CPU regression tests; different library versions/platforms may introduce numerical variation.

## 8. Reading the comparison

Each row in `comparison.csv` contains seed, mode, metric, LightGCN value, LLM value, absolute delta and relative percentage change:

`delta = LLM - LightGCN`

`relative change (%) = 100 * (LLM - LightGCN) / LightGCN`

A baseline of zero gives an empty/null relative percentage, not infinity or a fictional improvement. Negative deltas can be regressions. Higher Recall/Precision/NDCG is better; lower JSD means better calibration. PopLift should be considered relative to zero, not simply minimized; negative values mean under-recommending popular items relative to history. ARP and coverage describe other behavior and are not substitutes for accuracy. JSON also contains per-seed results and mean/sample-standard-deviation of paired differences. It does not claim statistical significance.

Example only, not a result: NDCG .020 -> .022 means +.002 absolute and +10% relative. Actual outcomes can favor either model.

Run timing includes training, validation, test and calibration. It excludes one-time Qwen download/encoding. Report these preparation costs separately when comparing total computational cost. Full POI group metrics remain in each model's `popularity_calibrated_test_metrics.json`; the summary CSV compares the overall group.

## 9. Research boundaries and known issues

- This is a frozen-LLM-feature recommender, not Qwen fine-tuning. Mean training-history item vectors plus learned projections replace LightGCN. Ordinary decoder hidden states are not guaranteed to provide useful semantic embeddings.
- CausalEPP scoring/quality/BPR equations and POI calibration logic are preserved, including the original implementation's limitations. We have not silently fixed date units, sliding windows, popularity expectation weighting, repeated-positive evaluation, or example-list edge cases.
- The existing Ciao features use fixed bins rather than the paper's six-month sliding windows. Date units in the supplied processed data are wrong. See the validation report for exact evidence.
- Calibration matches observed historical popularity preferences; those histories can already contain exposure bias. Its effect may conflict with debiasing objectives.
- Default calibration K=20 differs from the POI paper's K=10. Ciao and full-catalog LightGCN comparisons cannot reproduce the POI paper's geographic/social experiments.
- No metric/weight substitution has been made: its intended definition is still unspecified. Forecast smoothing, training quality-loss weight and reranking lambda serve different purposes.
- The original README describes the original entry points. This guide is authoritative for the new experiment runner.

## 10. Verification performed

Six automated tests passed in the development workspace, including comparison deltas for a zero baseline and a regression; rejecting a partial cache; training both models; comparing all three ranking modes; reloading both checkpoints and reproducing base/calibrated metrics; and rejecting changed data. These tests use synthetic features/interactions and do not demonstrate predictive improvement. The actual pretrained-Qwen encoding benchmark is documented separately in `reports/qwen_cpu_benchmark.md`.
