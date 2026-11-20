# Teammate workflow verification — 21 November 2026

The packaged source passed **17 CPU tests** using:

```bash
python -B -m unittest discover -s tests -v
```

New checks exercised the Douban-style schema adapter on timestamped synthetic interactions and then executed all three original modes (Moving Average, Holt, calibration), one tiny epoch each. Each mode returned exit code 0, saved a checkpoint and finite ranking metrics; calibration also saved CP_H/CP_Im metrics. These checks do not demonstrate real-data accuracy or real-Douban compatibility beyond the supported input schema.

Additional checks verify unchanged raw input bytes, refusal to overwrite output directories, strict train/validation/test chronology, correct Unix seconds from second/millisecond/text-date inputs, headerless TSV column mapping and explicit failure on invalid timestamp rows. The full suite also retains the earlier LLM, comparison, API and holdout-fitting tests.

No real Douban dataset was supplied or downloaded. No fresh full Ciao/Douban training was performed in this delivery. Karan's original scoring/loss/forecast/calibration algorithms remain the workflow defaults. The adapter fixes datetime resolution only in its new preprocessing path; existing Ciao data and original preprocessing code remain untouched.

See TEAMMATE_WORKFLOW.md for commands and the documented distinction between execution success, paper fidelity and accuracy improvement. Existing POI audit findings remain unresolved methodological differences rather than silently changed equations.
