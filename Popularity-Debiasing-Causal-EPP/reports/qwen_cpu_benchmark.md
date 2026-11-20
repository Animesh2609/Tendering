# Qwen3-0.6B CPU benchmark — 20 November 2026

## Outcome

PASS: actual pretrained Qwen3 text encoding of 32 item titles. Exit code 0; no timeout. No full-catalog encoding, recommender training, LLM fine-tuning or GPU execution occurred.

| Measurement | Result |
|---|---:|
| Selected model download | 1,519,193,708 bytes (1.519 GB; cap 3 GB) |
| Download wall time | 296.04 seconds |
| Whole benchmark subprocess | 11.008 seconds |
| Tokenizer/model loading interval | 2.456 seconds |
| Encoding eight batches of four titles | 3.092 seconds |
| Encoding throughput | 10.348 items/second |
| Peak subprocess resident memory | 3,997,144 KiB (3.812 GiB) |
| Cache matrix | 32 x 1024 float32 |
| Distinct vectors | 32 |
| Original title token lengths | 2–13 |
| Titles truncated at 64 tokens | 0 |

Total time includes interpreter/import startup and cache writing, so it exceeds loading plus encoding. Memory is Linux child-process maximum RSS, not model file size or whole-system usage. Download timing is separate from the 300-second benchmark timeout. Model-file download total excludes the small Python dependency installation.

## Exact setup and execution

Branch checked before changes: animesh-dm-testing. Main remains 1b5e028d98d1b736661004c0df06458028dfba9a.

Installed `transformers==4.57.1` and its dependencies only into the existing project-local .venv. Existing torch is 2.15.0+cpu, Python 3.12.14. `pip check` passed; AutoModel/AutoTokenizer imports passed; CUDA was false. No system installations. Pip emitted a global-cache ownership warning and disabled that cache; no benchmark warnings/errors appeared in the captured model log.

Model: Qwen/Qwen3-0.6B, immutable revision `c1899de289a04d12100db370d81485cdf75e47ca`. Downloaded only config, safetensors weights, tokenizer assets and license; actual file lengths matched manifest sizes. The weights' SHA-256 matched the Hugging Face LFS manifest. Per-file SHA-256 values and download receipt are saved.

The benchmark runner enforces `subprocess.run(..., timeout=300)` and uses these environment settings:

```text
CUDA_VISIBLE_DEVICES=
OMP_NUM_THREADS=2
MKL_NUM_THREADS=2
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1
TOKENIZERS_PARALLELISM=false
HF_HOME=<project>/work/llm_prototype/hf_cache
```

Exact encoder command:

```bash
.venv/bin/python -B llm_embedding_baseline.py encode --model-path work/llm_prototype/Qwen3-0.6B/c1899de289a04d12100db370d81485cdf75e47ca --output work/llm_prototype/qwen_32_items.npz --max-items 32 --batch-size 4 --max-tokens 64 --threads 2
```

Executed wrapper: `python work/llm_prototype/benchmark_qwen.py`. Post-run inspection: `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/python -B work/llm_prototype/inspect_qwen_cache.py` (exit 0).

The existing prototype loaded Qwen3Model using local files only and remote code disabled. It performed forward passes, not text generation, took each title's last nonpadding-token representation and normalized it. Weights were frozen via inference mode. This tests the encoder component of the proposed LightGCN replacement; it does not train/test that replacement's recommendations with real pretrained vectors.

## Inspected outputs and limits

All 32 expected item IDs (0–31) are present. All vector entries are finite; row norms range 0.999999821–1.000000119. All 32 vectors are distinct. Off-diagonal cosine similarity ranges 0.316916–0.974145. These checks verify numerical output, not semantic/recommendation usefulness.

This is the first 32 mapped item titles, not a random representative sample. Their short lengths (2–13 tokens) limit extrapolation. At the observed throughput, 11,185 items would take approximately 18.0 minutes for encoding alone by simple multiplication. **That estimate is unvalidated**, excludes recommender training/evaluation, and may be optimistic for longer text or different hardware. No measured speedup ratio against the previous seven-to-eight-hour pipeline is claimed: it generated user-specific scores, whereas this one caches item features.

The 32-item cache is explicitly marked `complete=false`; the training CLI rejects it for full-data training. It is not a trained recommender checkpoint. The earlier research issues (timestamps, sliding windows, popularity expectation, calibration definitions and evaluation protocol) remain unresolved.

Recommended next step: a representative-length encoder sample and then a controlled recommendation-quality experiment using the same splits/catalog as LightGCN. Full-catalog work requires a separate agreed resource budget. No additional work was started beyond the approved benchmark.

## Evidence

All paths are relative to the extracted repository:

- `work/llm_prototype/qwen_32_items.npz`: actual pretrained features.
- `work/llm_prototype/qwen_benchmark_result.json`: command, exit, timing and peak RSS.
- `work/llm_prototype/qwen_cache_inspection.json`: output checks and explicit extrapolation caveat.
- `work/llm_prototype/qwen_benchmark.log`: captured encoder output; no warnings/errors observed.
- `work/llm_prototype/download_receipt.json`, `hf_manifest.json`, `download.log`: pinned model provenance, sizes and hashes.
- `work/llm_prototype/benchmark_environment.freeze.txt`, `transformers_install.log`: Python environment evidence.
- `work/llm_prototype/download_qwen.py`, `benchmark_qwen.py`, `inspect_qwen_cache.py`: reproducible harnesses.

This benchmark supersedes only the earlier notes' statement that pretrained encoding had not yet been executed. Recommendation quality remains untested. No original model, dataset, experiment configuration or existing experiment output was overwritten. No new algorithm/source changes were needed in this turn; train.py retains the previously reviewed prototype hook. No commit, push or PR.
