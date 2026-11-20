# CausalEPP with LightGCN and frozen-LLM baselines

Start with [the complete run guide](LLM_BASELINE_GUIDE.md).

This source package includes both backbones, Moving Average/Holt, popularity calibration (CP_H/CP_Im), matched training/testing comparisons and checkpoint evaluation. It preserves the original research equations and documents their known implementation deviations.

Six CPU tests passed. A real pretrained Qwen3-0.6B encoder benchmark passed. **Full-dataset recommendation improvement has not been measured.**

Datasets, model weights, experiment outputs and PDFs are not included. Copy your existing processed Ciao data as explained in the guide. Tests use self-contained synthetic fixtures and need none of those artifacts.

See [the original README](README_original.md) for legacy CLI options and [the validation report](reports/local_validation_report.md) for unresolved methodology issues. The new guide describes the current comparison workflow.

## All-user calibration comparison and local recommendation API

[Run guide and API examples](CALIBRATION_API_GUIDE.md) · [Actual results](reports/calibration_all_users_report.md)

All 272 held-out users were evaluated on the supplied LightGCN+CausalEPP checkpoint. Adding CP_H/CP_Im did not improve results because each candidate pool contained a single popularity tier. The API supports known users, supplied recent history and explicitly labeled cold-start fallback. It serves a frozen snapshot and does not learn automatically. Nine self-contained tests pass, plus a real-checkpoint HTTP smoke test.
