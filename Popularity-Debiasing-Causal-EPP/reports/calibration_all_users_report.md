# Actual all-user calibration comparison — 20 November 2026

## Conclusion

**Adding POI popularity calibration did not improve the supplied LightGCN+CausalEPP checkpoint.** Base CausalEPP, CP_H and CP_Im produced identical rankings/metrics at K=10 and K=20 for all 272 evaluated test users. This is an actual executed comparison, not a synthetic example or a claim of improvement.

The original checkpoint was loaded strictly; its saved configuration records 25 epochs, but original training logs/provenance are unavailable. No retraining was performed for these results. Validation fitting covered 413 users; testing covered all 272 held-out users, 2,426 interaction rows, and an indexed catalog of 11,185 items. This does not represent all users in the real world or all future periods.

## Overall ranking accuracy and popularity metrics

Each value below applies equally to **LightGCN+CausalEPP**, **LightGCN+CausalEPP+CP_H**, and **LightGCN+CausalEPP+CP_Im**. All absolute/relative changes are zero for these metrics.

| Metric | K=10 | K=20 |
|---|---:|---:|
| Recall@K | 0.03168432 | 0.04679755 |
| Precision@K | 0.00919118 | 0.00661765 |
| NDCG@K | 0.02094376 | 0.02488294 |
| HitRate@K | 0.08088235 | 0.11397059 |
| PopularityJSD | 0.44265119 | 0.44265119 |
| AverageRecommendedPopularity | 493.36139152 | 391.27297199 |
| PopLift | 23.96407423 | 18.89823449 |
| CatalogCoverage@K | 0.00357622 | 0.00545373 |

At K=20, **Precision=0.662%**, **Recall=4.680%**, and **HitRate=11.397%** (31 of 272 users received at least one held-out item in the top 20). NDCG=.024883. Precision means the fraction of recommended slots that are hits; recall averages each user's recovered fraction of held-out items. They are not conventional binary classification accuracy.

## Different popularity groups at K=20

Results are again identical across the three methods. Groups are imbalanced in this held-out population; comparisons should show sample sizes.

| Group | Users | Recall@20 | Precision@20 | NDCG@20 | HitRate@20 | Popularity JSD |
|---|---:|---:|---:|---:|---:|---:|
| LowPop | 146 | 0.008834 | 0.003425 | 0.008823 | 0.068493 | 0.553533 |
| MedPop | 108 | 0.070425 | 0.009722 | 0.039410 | 0.148148 | 0.338316 |
| HighPop | 18 | 0.212963 | 0.013889 | 0.067991 | 0.277778 | 0.169288 |

LowPop users have substantially lower observed ranking accuracy and higher popularity mismatch than HighPop users in this test population. This is descriptive evidence, not a causal explanation or proof of future behavior. Activity-group summaries are in the aggregate JSON/CSV.

## Why the calibration has no effect here

For every test user, all 150 shortlisted candidates belong to just one popularity tier. Selecting any K of them yields the same tier distribution. Consequently the JSD calibration term cannot distinguish the candidate choices. CP_H validation search selected lambda=0 for every group at both K values; CP_Im's lambda=1 also leaves the sorted list unchanged under these ties.

This is not fixed by claiming a different “accuracy” number or arbitrarily increasing lambda. A future controlled experiment should test broader or popularity-diverse candidate retrieval, while preserving the baseline list and tuning only on validation. That would be an explicitly labeled candidate-generation extension, not an unannounced change to the paper equations. No such research change was applied in this run.

## Execution and limitations

Exact command from the source root:

```bash
.venv/bin/python -B evaluate_calibration.py --checkpoint outputs/Ciao/causalepp_ciao.pt --data-dir data/Ciao --output work/calibration_comparison/all_users --k 10 20 --threads 2
```

Exit 0; evaluator runtime 32.207 seconds; two CPU threads; a 300-second external timeout was not reached. No GPU or model download. PyTorch emitted the previously documented sparse-invariant-check warning at models.py:76; no execution failure occurred.

Weights were selected on validation, not test. Test exclusion history includes training+validation; popularity/graph/forecasts use training data. The report retains the original audit's fixed-bin/sliding-window mismatch, timestamp-unit bug, duplicate-positive semantics, popularity expectation and grouping conventions. These results characterize this implementation and checkpoint, not a faithful reproduction of either paper.

Paired user-bootstrap intervals for method differences are [0,0] because all lists are identical. They do not imply certainty about a new training run or future users. The existing checkpoint has no original dataset fingerprint, so its training provenance cannot be certified. Input dataset fingerprints and checkpoint SHA are recorded for this evaluation.

Raw local evidence: `work/calibration_comparison/all_users/metrics.csv`, `comparison.json`, per-user JSON files, `execution.json`, and `evaluation.log`. Per-user recommendation artifacts are not published in the source repository. The public aggregate results omit individual user IDs.

## Reusable code

See [CALIBRATION_API_GUIDE.md](../CALIBRATION_API_GUIDE.md) for all-user evaluation, explicit end-to-end training and the local recommendation API. Known users use the trained LightGCN snapshot. Unknown users receive a labeled popularity fallback, optionally calibrated to supplied history; that fallback's predictive quality has not been established. The API is not automatic online learning or an authenticated production deployment.
