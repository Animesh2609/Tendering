# Accuracy-first calibration revision — 21 November 2026

## Honest conclusion

**This revision did not meet the requested accuracy-increase goal.** It repairs the single-tier candidate bottleneck and yields measurable popularity-calibration improvement, but on the reused 272-user test set, precision/recall/hit rate stayed unchanged and NDCG decreased slightly. It is an experimental variant, not a replacement proven better than LightGCN+CausalEPP. The existing recommendation API default was not switched to it.

Earlier smoke-test PASS labels established execution, not research correctness or better accuracy. They should not have been read as proving successful calibration. This report distinguishes those claims explicitly.

## What was changed

New module: `accuracy_first_calibration.py`. CausalEPP's scoring, BPR/quality loss, frozen weights, popularity definitions and original data were not changed.

1. Preserve the base model's exact top-K before adding relevance-ranked candidates from each popularity tier. At pool=150 and K=20, the quota is floor((150-20)/3)=43 per tier; overlapping selections are deduplicated and remaining slots are filled by relevance. No held-out positive is injected into retrieval.
2. Keep the existing greedy relevance/JSD reranker, but select weights with an **accuracy-first validation guard**, rather than the original CP_H harmonic objective. A weight is eligible only if validation NDCG, recall, precision and hit rate do not decrease and JSD does not increase within that user group. Eligible weights are ranked by NDCG, then recall, then lower JSD, then smaller weight. Lambda=0 retains the exact baseline as a fallback.
3. Separate `fit` and `test` commands. Fit reads training and validation data only. The test command checks the frozen checkpoint and training/validation hashes before reading test labels. Existing result files are not overwritten.

This candidate-generation/selection procedure is explicitly a project extension. It is not a claim of exact POI-paper reproduction. Validation non-regression does not guarantee test non-regression, as this run demonstrates.

## What “held-out test users” means here

The same 272 users were retained. Their future test interactions were held out; their earlier training interactions were available to LightGCN. The users are not entirely disjoint from training. This is temporal known-user recommendation, not cold-start evaluation.

The test interactions did not choose retrieval parameters, lambda, the objective or the checkpoint in this revision. The same checkpoint was used for baseline and calibrated scoring. Training statistics/forecast histories remained training-only. Validation history was available for test-time seen-item exclusions and popularity profiles, as in the earlier evaluation.

However, this test split was already inspected during the earlier diagnosis. It is **reused evaluation, not a fresh blind holdout**. No result-driven retuning was performed after the one test application of this revision. Strong final research claims require a genuinely untouched future split or external dataset and independently trained runs.

## Validation selection (413 users)

The fixed grid was 0, .005, .01, .02, .05, .1, .2, .4, .7, 1. The selected group weights were LowPop=.2, MedPop=.2, HighPop=.4. All validation candidate pools now contain multiple tiers.

Crucially, the selected weights did **not increase validation NDCG**: they tied baseline ranking accuracy and improved JSD. The selection rule permits such accuracy ties; this should not be marketed as an accuracy gain.

| Group | Users | Weight | Baseline NDCG | Selected NDCG | Baseline JSD | Selected JSD |
|---|---:|---:|---:|---:|---:|---:|
| LowPop | 206 | 0.2 | 0.01892665 | 0.01892665 | 0.58355023 | 0.57602523 |
| MedPop | 187 | 0.2 | 0.02522983 | 0.02522983 | 0.32878404 | 0.32807330 |
| HighPop | 20 | 0.4 | 0.01677534 | 0.01677534 | 0.16468915 | 0.09040127 |

## Frozen test evaluation: all 272 users, K=20

| Metric | LightGCN+CausalEPP | Revised calibration | Absolute change |
|---|---:|---:|---:|
| Recall@K | 0.04679755 | 0.04679755 | +0.00000000 |
| Precision@K | 0.00661765 | 0.00661765 | +0.00000000 |
| NDCG@K | 0.02488294 | 0.02482149 | -0.00006145 |
| HitRate@K | 0.11397059 | 0.11397059 | +0.00000000 |
| PopularityJSD | 0.44265119 | 0.43698589 | -0.00566530 |
| AverageRecommendedPopularity | 391.27297199 | 390.60036188 | -0.67261011 |
| PopLift | 18.89823449 | 18.88976319 | -0.00847131 |
| CatalogCoverage@K | 0.00545373 | 0.00563254 | +0.00017881 |

Seventeen recommendation lists changed. All test candidate pools contain multiple tiers. Baseline metrics exactly match the earlier full-test baseline: candidate diversification preserved its top-K performance.

NDCG fell by 0.247% relative (.02488294 -> .02482149), affecting two users' NDCG adversely; no user had an NDCG increase. Popularity JSD fell by approximately 1.280% relative (.44265119 -> .43698589). Precision remained .662%, recall 4.680%, and hit rate 11.397%. The paired user-bootstrap NDCG-difference interval is approximately [-.00016690, 0], conditional on this checkpoint and validation selection; it does not cover training-seed uncertainty or restore a blind holdout.

## Reproduction

From the source root and activated environment:

```bash
python -B accuracy_first_calibration.py fit   --checkpoint outputs/Ciao/causalepp_ciao.pt --data-dir data/Ciao   --output work/accuracy_first/frozen_validation_policy.json   --k 20 --candidate-pool 150 --threads 2

python -B accuracy_first_calibration.py test   --policy work/accuracy_first/frozen_validation_policy.json   --output work/accuracy_first/test_once.json --threads 2
```

These commands were executed. Fit took 10.530 seconds; test evaluation took 6.515 seconds (both CPU). Test exit code was 0. The policy SHA-256 before and after testing was `b68824d1382c9c2125dc4468dc476a211165194caaac479d699bb03019153e3c`. No full training, GPU job or new weight download ran. The existing PyTorch sparse-invariant warning appeared; no runtime failure occurred.

The original split's timestamp/window, repeated-interaction and checkpoint-provenance limitations remain, as documented in the earlier validation report. No original datasets, weights or experiment settings were overwritten.

Tests check baseline-preserving candidate diversification, seen-item exclusion, calibration on a hand-constructed validation improvement, fallback when calibration hurts validation accuracy, exact lambda-zero baseline behavior, and fitting successfully when no test file exists at all. The last test establishes that the fitting path does not require test labels. This does not establish absence of every possible methodological bias.

## Next research decision

Do not claim an accuracy improvement or promote this variant as the better default. The honest next step is to define a new untouched evaluation period, resolve the existing temporal/data issues, and investigate model/retrieval quality using validation only. More lambda tuning on this test set would not be credible. Holding out entire users would instead require a separately designed cold-start model and is not what these results evaluate.
