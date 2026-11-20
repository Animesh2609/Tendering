# Comparison implementation validation

Six tests passed on Python 3.12.14 and CPU PyTorch 2.15.0+cpu. Command:

```bash
python -B -m unittest discover -s tests -v
```

Checks cover train-only profile aggregation, trainable projections and frozen vectors; no LightGCN module in the text backend; invalid features; mapping hashes; early rejection of conflicting backends; both forecast paths and calibration; original baseline regression; zero-baseline percentage handling; negative improvements; rejecting incomplete caches; paired training and comparison; checkpoint reloading with identical base and calibrated metrics; and rejection of changed data.

The fixtures use synthetic feature vectors. Their results must not be presented as pretrained LLM accuracy. Full Ciao training was not run. The separate real encoder benchmark establishes only encoding execution, timing and finite outputs.

Research logic and original dataset/configuration files were preserved. Only an optional backend construction hook was added to the original trainer. The new comparison runner applies identical splits, hyperparameters and validation selection rules to both backbones and writes actual improvements or regressions without assuming a winner.
