# Colab memory fix

Use CausalEPP_LLM_Colab_Memory_Fixed.ipynb. Original upload is preserved.

## Observed failure

The uploaded cell 15 hardcodes SAFE_BATCH_SIZE=4, ignoring BATCH_SIZE in cell 4.
Cell 13 processes all of each user's candidates together; CANDIDATE_POOL=50 is a
minimum, not a maximum. Padding makes shorter requests as wide as the longest.
The saved traceback fails in scaled_dot_product_attention during prompt prefill:
6.56 GiB allocation requested, only 1.91 GiB free on a 14.56 GiB GPU. This is a real
capacity problem; reserved-but-unused memory was only 1.30 GiB. Emptying the allocator
cache alone is not a sufficient fix. A retained traceback may also keep live tensors.
The following KeyError '4' occurs because incomplete user caches are indexed directly.

## Changes

- One BATCH_SIZE setting, default 2; larger values are upper bounds, not guarantees.
- FP16 model weights; pinned model revision and Transformers 4.57.1.
- Explicit non-thinking Qwen chat template.
- At most 16 candidates per prompt and 1,024 actual input tokens; at most 384 new tokens.
- No silent truncation or dropping candidate IDs. Overlong chunks split; a single
  overlong item/profile stops with an explicit diagnostic.
- OOM handling splits user batches, then item chunks, with a finite single-item stop.
- Temporary tensors released before retries; progress saved after each successful chunk.
- Existing 0.5 parse-failure fallback retained but item IDs are recorded separately.
- Original chunk boundaries retained during resume; valid saved scores are not overwritten.
- Missing users produce INCOMPLETE instead of a KeyError or false success.
- New versioned cache directory and manifest: do not mix old and new scores. Chunking,
  disabling thinking and FP16 can change score values; this is not bit-identical inference.
  Model/loss equations and the original candidate selection remain unchanged.

## Run

1. Upload the fixed notebook to Colab. Restart the session after the previous crash.
2. Enable a T4 GPU; set your PART_ID and DATA_DIR. Run from the first cell. Dependency
   or authentication issues must be resolved before subsequent cells; no credentials
   are embedded. Model weights download when you execute the loading cell in Colab.
3. Keep BATCH_SIZE=2 and MAX_JOBS=2 for the initial smoke check.
4. If the two chunks complete, change MAX_JOBS=0 and rerun the partition cell, then
   final validation. Initial INCOMPLETE is expected with the two-chunk smoke limit.
5. Use the same fixed version/settings for all ten partitions. Preserve original cache
   files, but regenerate into the new folder; do not bypass manifest mismatches.
6. Inspect the fallback count/file before treating a complete cache as useful scores.

## Executed verification

Seven local tests passed: cell syntax, bounded chunks with full candidate coverage,
overlong single-prompt rejection, simulated batch/item OOM splitting, single-item OOM
termination, parse retries/fallback recording, and missing-user final validation.
These tests do not establish successful GPU inference or output quality.
Local Ciao's largest unique training history had 522 candidates: 6,585 tokens in one
prompt versus 33 bounded prompts, maximum 570 tokens, with all 522 candidates preserved.
This check used the actual locally available Qwen tokenizer, with no model generation
or download. No T4, full scoring run, training, commit or push was performed for this fix.
