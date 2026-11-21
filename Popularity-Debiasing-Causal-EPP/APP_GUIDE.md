# Streamlit + FastAPI + PostgreSQL

This is a local research console. Streamlit is the visible interface, FastAPI computes
recommendations, and PostgreSQL saves request/result history. It is not an authenticated
multi-tenant public service: anyone holding the shared API key can see all saved runs.
Keep both servers bound to localhost. Public deployment requires individual login,
authorization, HTTPS, rate limiting and a retention policy. No cloud database is provisioned.

## Start locally (Linux/macOS shell)

From this project directory on `animesh-dm-testing`:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-app.txt
cp .env.example .env
```

Edit `.env`: choose a random URL-safe database password, put that same password in
`DATABASE_URL`, and choose a separate random API key (at least 24 characters).
Set paths to your existing Ciao data, model and calibration report. Do not commit `.env`.
On a CPU-only machine, install PyTorch from its CPU wheel index before installing
requirements to avoid downloading unnecessary CUDA wheels.

With Docker installed, start PostgreSQL. This downloads its image on first use:

```bash
docker compose --env-file .env -f compose.app.yml up -d
```

Create a reviewed calibration report from an existing LightGCN checkpoint (evaluation,
not training). Use a fresh output directory for each experiment:

```bash
python -m teammate_v2.evaluate --checkpoint outputs/Ciao/causalepp_ciao.pt --data-dir data/Ciao --output work/reviewed_calibration --k 10 20 --threads 2
```

Set `CALIBRATION_REPORT=work/reviewed_calibration/comparison.json` in `.env`.
The API reads the report's policy version and uses the corresponding candidate builder.
The original report remains supported. New requests never read test labels.
Training history supplies the serving snapshot; offline test evaluation additionally
excludes validation history. These are intentionally different observation times.

Load variables, then run the API in terminal 1:

```bash
set -a
source .env
set +a
python -m uvicorn app.backend:app --host 127.0.0.1 --port 8000
```

In terminal 2, activate the same environment and load the same variables, then:

```bash
python -m streamlit run app/frontend.py --server.address 127.0.0.1 --server.port 8501
```

Open http://localhost:8501. API documentation is at http://localhost:8000/docs.
All catalog/recommendation/history endpoints require the `X-API-Key` header; the
Streamlit server adds it. `/health` checks database connectivity.

## Meaning of the results

- Existing mapped users: frozen LightGCN + CausalEPP scores.
- New visitors: explicitly labeled training-popularity fallback; extra history changes
  exclusion/calibration, not the learned user embedding. This is not online learning.
- CP_H: validation-selected popularity calibration, not guaranteed better accuracy.
- CP_Im: calibration-first; can sharply reduce relevance.
- Scores are ranking scores, never confidence or accuracy percentages.
- Saved runs store mapped user/item IDs and results locally in PostgreSQL. Do not share
  the database or grant untrusted people the shared key.

A missing checkpoint/data error means you must supply your local research files;
these large/private artifacts are deliberately not published. A 422 response means
an input is invalid, or calibration was not fitted at the requested K. A 401 means
the frontend/API keys differ. A PostgreSQL connection error means check Docker,
the password and DATABASE_URL. `docker compose -f compose.app.yml down` stops the DB;
the named volume preserves records. Do not use `down -v` unless you intend to erase them.

## Reviewed teammate implementation

Original experiment modules are preserved. `teammate_v2/` contains the supplied
update with explicit correctness fixes; it changes the calibration candidate strategy
and interaction weighting, so results must be labeled as a separate experiment.
The CausalEPP model/loss equations are unchanged.

```bash
python -m teammate_v2.run --data-dir data/Ciao --output outputs/reviewed_ma --epochs 1
python -m teammate_v2.run --data-dir data/Ciao --output outputs/reviewed_holt --epochs 1 --forecast-method holt
python -m teammate_v2.run --data-dir data/Ciao --output outputs/reviewed_cal --epochs 1 --calibrate
```

These commands train the full supplied data for one epoch; they are not tiny tests.
Estimate resources first. The CPU runner supports `--llm-baseline --llm-model-path
/path/to/existing/model` but full generative LLM runs remain expensive and were not
executed. GPU batching exists in the scorer for explicitly configured experiments;
this safe runner deliberately selects CPU. For the alternative cached-text backbone,
see LLM_BASELINE_GUIDE.md. The dashboard currently serves LightGCN checkpoints only.

Run bounded synthetic regression tests:

```bash
python -m unittest discover -s tests -v
```

See reports/teammate_update_review.md for measured results and verification limits.
