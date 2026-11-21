# Review of teammate updates and recommendation app

Date: 21 November 2026. Source branch confirmed `animesh-dm-testing` before editing.
Original source commit: `1b5e028d98d1b736661004c0df06458028dfba9a`.
The four supplied text files were reviewed as source evidence, not instructions.
Original datasets, model weights and experiment outputs remain preserved.

## Verdict

The teammate update addresses the intended **candidate diversity, diagnostics, caching
and batching** problems. It does not establish an accuracy improvement or implement
an entirely LLM-based replacement of LightGCN. POI means point of interest; there is
no separate PUI algorithm identifiable in these files. The implementation remains a
Ciao adaptation of the supplied POI popularity-calibration paper.

Think of LightGCN as a librarian estimating which books you like, CausalEPP as an
adjustment for changing popularity, and calibration as choosing a reading list with
a popularity mix resembling your history. A better mix need not give you more books
you actually want. An LLM supplies a different relevance signal, not proof of relevance.

## Verified code findings

- `teammate_v2/calibration.py:78`: preserve the base top-K and balance remaining
  candidates across training-derived popularity tiers. This fixes the old single-tier
  candidate bottleneck when other tiers are available. It changes the experimental
  policy and is deliberately opt-in, not a silent replacement of the original module.
- `teammate_v2/calibration.py:21`: more efficient active-user mask; train-derived
  grouping. Validation-selected group membership is frozen for the updated test path.
- Target distributions now count historical interactions rather than unique items.
  Therefore old versus new JSD values must not be compared as though their definitions
  were identical. Ranking metrics remain comparable for the same original lists.
- `teammate_v2/calibration.py:326`: selection still optimizes a harmonic mean of NDCG
  and calibration quality. This is a trade-off, not an accuracy-improvement constraint.
- Supplied baseline metrics called greedy reranking at lambda=0 while saved original
  lists came from torch.topk. Tied scores could disagree. The reviewed `_rerank` now
  returns the protected original list exactly at zero weight; a regression test proves it.
- Supplied list comparison indexed unequal-length lists without a guard. Fixed and tested.
- `teammate_v2/llm_baseline.py:87`: batch generation with left padding and per-request
  retries is present. A stub-model regression test verifies request/result ordering.
  **Real GPU batching speed and real generated-score quality were not tested.**
- `teammate_v2/llm_baseline.py:240`: CPU batch size is forced to 1. Merely changing
  `llm_batch_size=4` does not solve CPU generation time. Output budgets remain at least
  512 tokens and can be much larger for users with long histories; three retries remain.
- `teammate_v2/llm_baseline.py:210`: cache keys include training rows, mapping and
  settings. Model ID is not an immutable revision/content hash: replacing weights at
  the same path can reuse stale scores. Use versioned local model directories and a
  single writer per cache. Cache writes now use replace-after-write to avoid leaving
  truncated JSON after interruption; this is not a multi-process cache locking system.
- Malformed nonnumeric LLM JSON values previously raised ValueError. They are now
  treated as missing and pass through the existing retry/fallback path. The neutral
  0.5 fallback remains a limitation, not a measured prediction.
- `teammate_v2/train.py:219`: still constructs LightGCN. LLM replaces only matching
  m_ui; graph-derived conformity remains. This is a hybrid, not a complete backbone
  replacement. The separate frozen-text experiment remains available in the earlier guide.
- Candidate pools contain all training positives plus popular items, so pool size is
  not a hard cap. Training and evaluation with this restricted LLM pool is not directly
  comparable with full-catalog LightGCN evaluation; report candidate recall and identical
  candidate protocols before interpreting differences as model improvements.
- Supplied README's 4.1 GB default-model statement is not supported by the earlier
  pinned Qwen-0.6B download (about 1.52 GB files). Runtime precision/memory differ from
  download size. The cache now lives in the output parent's `.llm_cache` directory.

## Executed existing-checkpoint experiment

Exact command:

```bash
.venv/bin/python -m teammate_v2.evaluate --checkpoint outputs/Ciao/causalepp_ciao.pt --output work/teammate_v2_evaluation --k 20 --threads 2
```

Exit 0; 14.048 seconds internal runtime; CPU; no training or downloads.
Validation: 413 users; test: all 272 eligible users. Lambda grid 0–1 in 0.1 increments;
selected LowPop=0.2, MedPop=0.2, HighPop=0.4 using validation only. No test retuning.

| Metric @20 | Original CausalEPP | Updated CP_H | CP_Im |
|---|---:|---:|---:|
| Recall | 0.04679755 | 0.04679755 | 0.03591543 |
| Precision | 0.00661765 | 0.00661765 | 0.00496324 |
| NDCG | 0.02488294 | 0.02483895 | 0.01647392 |
| Hit Rate | 0.11397059 | 0.11397059 | 0.08455882 |
| Popularity JSD, lower better | 0.44233324 | 0.43686691 | 0.00047507 |
| Catalog coverage | 0.00545373 | 0.00563254 | 0.00697363 |

CP_H changes 17 lists; zero single-tier candidate pools remain. Precision 0.00661765
means about 0.662% of the 20 recommended items were held-out positives on average;
Hit Rate 0.11397059 means at least one hit for 11.397% of users. These are different
metrics; neither is classification accuracy. **No ranking accuracy gain demonstrated.**

This test set was inspected in earlier experiments, so it is not a fresh blind holdout.
The checkpoint lacks certified training provenance. Prior timestamp, temporal-bin,
repeated-positive and split-protocol limitations in local_validation_report.md persist.
The shared candidate-builder extraction was checked by repeating this fixed experiment
without retuning and comparing its complete result object for equality.

Outputs: `work/teammate_v2_evaluation/comparison.json`, `metrics.csv`, `per_user_at_20.json`.
Only aggregate results are published; individual user lists and group assignments stay local.

## Application and verification

Added Streamlit UI, FastAPI API, SQLAlchemy persistence configured for PostgreSQL,
Docker Compose database setup and environment template. The API selects the reviewed
or original policy from the report and shares the reviewed candidate builder with
its evaluator. It rejects LLM-matching checkpoints rather than silently serving them
as ordinary LightGCN. It does not perform training inside a web request.

Verified API authorization, invalid inputs, catalog search, saved-request retrieval and
persistence across app restarts with SQLite as a **test substitute**. Also executed six
FastAPI requests using the real Ciao checkpoint (known/new user x three modes), checked
20 unique recommendations, exclusion of prior items and six persisted records.
Streamlit AppTest rendered the interface without exceptions; this is not visual browser QA.
Synthetic one-epoch updated training/calibration and mock LLM batch tests passed.
Python dependency resolution passed `pip check`. PyTorch emitted its existing sparse
invariant warning; FastAPI's installed Starlette emitted an httpx deprecation warning;
Streamlit emitted its expected bare-test ScriptRunContext warning.

**PostgreSQL integration remains unverified pending approval to download/run its Docker
image.** No database image was downloaded and no server was deployed publicly. Do not
interpret SQLite tests as a verified PostgreSQL deployment. Full Qwen scoring/training,
GPU benchmarks, fresh-seed full training and new-dataset generalization were not run.

## Next steps

1. Verify PostgreSQL with an approved temporary container; then follow APP_GUIDE.md.
2. Use a new temporal holdout and repeated training seeds before making improvement claims.
3. Compare same candidate sets, report candidate recall, pin model revisions, and record
   failed-score/fallback rates for the LLM experiment. Benchmark a bounded real batch.
4. Preserve the existing model as baseline; evaluate accuracy and calibration separately.
5. For broader users, add authenticated accounts and scheduled model refreshes; current
   new visitors get a clearly labeled popularity fallback, not learned personalization.
