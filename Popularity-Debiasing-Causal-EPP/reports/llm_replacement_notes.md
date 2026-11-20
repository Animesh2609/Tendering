# Experimental LLM replacement — 20 November 2026

This extends the earlier local validation; it does not revise that report's findings or repair the research/data issues. Its line references describe the pre-extension source, retained at `work/llm_prototype/train.before.py`.

## Motivation and design

Original Qwen mode generates JSON relevance scores sequentially per user, retries incomplete answers, and still uses LightGCN for the conformity item vector. For the uploaded data, reconstructing its default candidate builder gives 5,698 user prompts, 310,786 user-item scores and a maximum pool of 522 items. First-attempt generation limits sum to 3,729,432 output tokens; this is a configured upper budget, NOT measured generated tokens. Retries can add work. The complete JSON score cache is rewritten after each user; main.py creates a new run directory, so another invocation does not automatically share the previous cache. No teammate runtime was profiled here.

New `llm_embedding_baseline.py` uses a local frozen decoder model as a text feature encoder, pooling the last nonpadding token for each item title. No autoregressive generation or JSON parsing occurs. Item vectors are cached once; user vectors average only training-interaction item vectors. Two trainable linear projections provide user/item vectors. Dot products supply matching scores; projected item vectors also supply the conformity MLP. There is no graph construction or LightGCN module in this backend. The historical `lightgcn.propagate` interface name is retained solely for compatibility with existing evaluators.

This is a frozen-LLM-feature recommender, not fine-tuning an LLM, and not equivalent to generative Qwen scoring. Plain Qwen hidden states are not guaranteed to be good retrieval embeddings. Item titles may be weak semantic evidence; averaging may lose recency/diversity and collaborative preferences. Users without train history receive a zero text profile. A smaller dedicated embedding model is a useful separate baseline, but should be accurately labeled as an encoder baseline rather than a generative LLM replacement. Neither paper guarantees this extension will improve recommendations.

The CausalEPP scoring equations, losses, popularity statistics, forecasts and calibration objective remain as before. `train.py` now accepts an optional `backend_factory`; its default LightGCN implementation remains the default. A conflict with the old generative LLM path is rejected before any inference. No Config defaults changed. No original data, checkpoints or outputs changed. Only train.py was changed among the original files; the new module and test file are additions. Branch: animesh-dm-testing. Main remains 1b5e028d98d1b736661004c0df06458028dfba9a. No commit or push.

## Tests actually executed

```bash
PYTHONPATH=. .venv/bin/python -B -m unittest discover -s tests -v
.venv/bin/python -B llm_embedding_baseline.py --help
.venv/bin/python -B llm_embedding_baseline.py encode --help
.venv/bin/python -B llm_embedding_baseline.py train --help
```

Four unittest cases passed, exit 0, final run 1.154 seconds. The pipeline case executes four tiny one-epoch CPU configurations: original LightGCN, synthetic-vector Moving Average, synthetic-vector Holt and synthetic-vector calibration. It also checks strict checkpoint state loading. Other checks cover training-only profile aggregation, nonzero projection gradients, frozen feature buffers, absence of LightGCN modules, rejection of nonfinite features, mapping fingerprint behavior and early rejection of conflicting backends. The original baseline reproduced its previous synthetic NDCG value (.2718216255952429). Text-backend synthetic scores are not evidence of LLM quality.

Evidence: `work/llm_prototype/tests.log`, `work/llm_prototype/test_metrics.json`. Tests construct their own small data fixture, and temporary checkpoints are cleaned up. No pretrained encoder was executed; no model weights downloaded; no full-data training performed. Transformers is not yet installed in this venv. The real tokenizer/AutoModel path and pretrained feature quality remain untested.

## Concrete next benchmark (not executed)

After obtaining an existing local Qwen3-0.6B snapshot and installing the required compatible transformers package, replace `/path/to/local/Qwen3-0.6B` with its actual directory:

```bash
.venv/bin/python -B llm_embedding_baseline.py encode \
  --model-path /path/to/local/Qwen3-0.6B \
  --output work/llm_prototype/qwen_32_items.npz \
  --max-items 32 --batch-size 4 --max-tokens 64 --threads 2
```

CPU-only; local-files-only; remote code disabled. Record model load time separately from encoding time, peak RAM externally, feature finiteness, title truncation and results on at least two batches. Apply an external five-minute execution timeout for the first benchmark. Do not promise a speedup before this executes. A 32-item cache cannot be used for full-data training; the runner explicitly rejects partial or mismatched mappings.

Full encoding, only after the benchmark supports a resource budget:

```bash
.venv/bin/python -B llm_embedding_baseline.py encode \
  --model-path /path/to/local/Qwen3-0.6B \
  --output work/llm_prototype/qwen_all_items.npz \
  --max-items 0 --batch-size 4 --max-tokens 64 --threads 2
```

The full dataset has 11,185 mapped items. Encoding all of them may still take substantial CPU time. Cache metadata records model path/class/config, mapping hash, pooling, truncation, PyTorch version and encoding times. Training stores the full cache SHA-256 in its checkpoint config. Existing cache/output paths are refused rather than overwritten. Encoder cache metadata does not provide a cryptographic provenance hash of the original model weights: record the downloaded model's exact revision separately.

Training command, only after full-cache preparation and runtime approval:

```bash
.venv/bin/python -B llm_embedding_baseline.py train \
  --cache work/llm_prototype/qwen_all_items.npz \
  --output outputs/Ciao/llm_text_experiment_001 \
  --epochs 1 --forecast-method moving_average --calibrate --threads 2
```

This is a real newly implemented CLI, not a flag added to main.py. Epochs are required explicitly. For Holt, change the supported forecast-method value to holt. It trains small projection layers, quality scalars and the conformity MLP; the language model is not loaded during training. Evaluation remains full-catalog, so comparison with LightGCN is more comparable than the old restricted Qwen candidate evaluation. Data split and metrics still need the earlier audit fixes/decisions.

## Combining the papers responsibly

Use a pipeline of matching model -> CausalEPP forecast-adjusted scores -> popularity-calibrated reranking. Treat their objectives separately: accuracy (e.g. NDCG) is a measurement; calibration lambda is a control weight. The training quality-loss weight, forecast smoothing alpha/beta and final reranking lambda have different roles. The user has not yet specified the intended metric/weight substitution, so no such formula was changed.

Calibration matches historical popularity preferences; those histories may themselves contain exposure bias. Therefore it can conflict with a goal of correcting that bias. Also, candidate lists may contain too few niche items for any reranker to provide them. Different score scales across backbones can affect CausalEPP's Softplus matching and the calibration tradeoff. These are research questions, not findings that the combination necessarily fails.

Recommended controlled experiments, after resolving data semantics: LightGCN+CausalEPP; LightGCN+CausalEPP+calibration; frozen-LLM+CausalEPP; frozen-LLM+CausalEPP+calibration. Hold split, catalog, evaluation K, forecasting and training budget constant; tune each model only on validation and report test accuracy plus calibration/group metrics and runtime. Compare forecasting alternatives separately rather than changing every component at once.
