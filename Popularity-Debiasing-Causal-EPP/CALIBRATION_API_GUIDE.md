# LightGCN + CausalEPP, with and without POI popularity calibration

This workflow answers a different question from the LLM comparison: **does adding calibration to the same trained LightGCN+CausalEPP model improve recommendations?** It evaluates all eligible held-out users, including popularity and activity groups. “PUI” is interpreted here as the previously discussed POI-paper calibration; there is no separate PUI algorithm.

See [the actual all-user results](reports/calibration_all_users_report.md). The supplied checkpoint showed **no improvement**: all top-150 candidate pools contained one popularity tier, so reranking could not change their popularity mix. Do not present these results as evidence that calibration helps. The existing research/data limitations still apply.

## Evaluate an existing LightGCN checkpoint

Activate the project environment and supply the existing processed Ciao directory and checkpoint from your original project. No downloads or training occur:

```bash
python -B evaluate_calibration.py \
  --checkpoint outputs/Ciao/causalepp_ciao.pt \
  --data-dir data/Ciao \
  --output outputs/calibration_evaluation_001 \
  --k 10 20 --candidate-pool 150 --threads 2
```

This fits each K's group calibration weights using validation only, then compares CausalEPP, CP_H and CP_Im on the same test users and candidates. It writes:

- `comparison.json`: aggregate/group metrics, fitted weights, sample counts, candidate-tier diagnostics, paired differences and conditional bootstrap intervals.
- `metrics.csv`: overall and group results suitable for a spreadsheet.
- `per_user_at_10.json`, `per_user_at_20.json`: per-user ranked lists and metrics for local diagnosis. Treat these as user-level experiment artifacts; they are not published with the source.

Precision@K, Recall@K, NDCG@K and HitRate@K describe ranking accuracy. JSD describes popularity-distribution mismatch. ARP, PopLift and coverage describe other aspects. There is no meaningful conventional classification accuracy here because no labeled set of all negative user/item pairs is evaluated. HitRate is the fraction of evaluated users with at least one held-out item recommended.

Both popularity groups (LowPop, MedPop, HighPop) and activity groups (1–10, 11–50, over 50 unique training items) are reported. Empty groups return `users=0, metrics=null`, not fabricated scores. Popularity membership follows the original implementation's train+validation history at test time, using training-derived thresholds. Activity groups use training history only. Bootstrap intervals resample users and condition on the fitted model/lambdas; they do not cover training-seed or future-data uncertainty.

## Run the full training-to-evaluation pipeline

This is explicit training and requires a chosen runtime budget. A new output directory is mandatory:

```bash
python -B run_lightgcn_calibration.py \
  --data-dir data/Ciao \
  --output outputs/fresh_calibration_001 \
  --epochs 1 --seed 42 --forecast-method moving_average \
  --k 10 20 --candidate-pool 150 --threads 2
```

The model is trained **once**, with its best checkpoint selected on validation NDCG. The same checkpoint is evaluated without calibration and with both calibration variants. This avoids attributing unrelated training differences to the reranker. One epoch checks the whole pipeline but is not a converged experiment. Choose a larger epoch budget and multiple independently evaluated seeds before research conclusions. Holt is available through `--forecast-method holt`.

The new checkpoint records data fingerprints. Existing checkpoints without fingerprints remain evaluable, but their provenance cannot be certified from dimensions alone. No source equation, dataset or existing output is overwritten. Existing timestamp/sliding-window/sampling limitations are deliberately not silently corrected.

## Reusable recommendation API

Start the local API after producing a calibration report for the exact checkpoint/data snapshot:

```bash
python -B recommendation_api.py \
  --checkpoint outputs/Ciao/causalepp_ciao.pt \
  --data-dir data/Ciao \
  --calibration-report outputs/calibration_evaluation_001/comparison.json \
  --port 8000 --threads 2
```

The server binds to **127.0.0.1 only**. It is a local demonstration/service component, not an authenticated production deployment. There is no production authentication, rate limiting, durable storage or concurrent-serving infrastructure. Stop with Ctrl+C. Model loading/graph propagation happen at startup, not for every request. Serving requires the training CSV, mapping, temporal feature arrays and fitted calibration report; validation/test label files are not required by the API.

Health check:

```bash
curl http://127.0.0.1:8000/health
```

Known user, including recently observed item IDs:

```bash
curl -X POST http://127.0.0.1:8000/recommend \
  -H 'Content-Type: application/json' \
  -d '{"user_id":483,"history_items":[0,1],"k":20,"mode":"CP_H"}'
```

Use `mode="CausalEPP"` for the base model or `mode="CP_Im"` for calibration-first ranking. `CP_H` requires validation-fitted weights for the requested K. Invalid requests return HTTP 400. IDs are the dataset's **mapped integer IDs**, not arbitrary original IDs; translate using your `user_mapping.csv` and `item_mapping.csv`.

New user with some observed history:

```bash
curl -X POST http://127.0.0.1:8000/recommend \
  -H 'Content-Type: application/json' \
  -d '{"user_id":null,"history_items":[12,57],"k":20,"mode":"CP_H"}'
```

A new user has no learned LightGCN embedding. The service explicitly labels its result `cold_start_training_popularity_fallback`, using training item counts and the supplied history for exclusions/calibration. If no history is supplied, it returns the popularity fallback without claiming a personalized popularity preference. It does not silently assign the new user another user's embedding. Group weights fitted on known users are not empirically validated for cold-start users.

Response fields include the backend used, whether the user is new, applied calibration weight, popularity group, checkpoint SHA-256, snapshot policy and item IDs/titles. Scores are ranking scores, not probabilities or confidence estimates. Previously seen items are excluded; lists are unique and can be shorter than K when insufficient unseen items remain.

Python callers can reuse the same service without HTTP:

```python
from recommendation_api import RecommendationService
service = RecommendationService(checkpoint, data_dir, calibration_report)
result = service.recommend(user_id=483, history_items=[0, 1], k=20, mode="CP_H")
```

## What “different users at all times” does and does not mean

- No fixed six-user sample or hardcoded user limit: evaluation uses all eligible users, and the API accepts arbitrary valid mapped users plus explicit cold-start requests.
- Any dataset with the documented processed schema, matching mappings/features and a matching trained checkpoint can be used with `--data-dir`.
- Additional observed history updates exclusions and calibration profiles. It does **not** silently update LightGCN weights, forecast histories or the training graph.
- A frozen checkpoint does not guarantee accuracy forever. For new items, shifting preferences or new training periods, produce new validated data/model/calibration snapshots and restart the service after evaluation. Do not change ID meanings under a loaded snapshot.
- The current data has a documented timestamp-unit bug. The service returns its stored numeric training cutoff for traceability; do not interpret that value as a correct Unix timestamp until preprocessing is deliberately repaired.

## Tested

The all-user supplied-checkpoint evaluation ran on CPU. A real local HTTP smoke test passed health checks, known/new-user requests, history exclusions and invalid-input cases; the server was stopped afterward. Self-contained tests also exercise HTTP behavior on synthetic data. These checks demonstrate execution and guard behavior, not improved accuracy for new users or future periods.
