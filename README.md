# Psych Research Data Toolkit

A clean, reproducible toolkit for psychological and psychiatric research: CSV cleaning, anonymization, descriptives, correlations, and clinical data visualizations (histograms, time-trend).

## Features (v0.1.0)
- Normalize headers and basic CSV cleaning  
- HMAC-based ID anonymization via `PRDT_ANON_KEY`  
- Descriptives, Pearson correlations, missing-value summary (JSON)  
- Histograms for selected score columns  
- Simple time-trend plot by participant  

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .

export PRDT_ANON_KEY="replace-with-a-long-random-string"
python -m prdt.cli --input data/examples/surveys.csv --outdir outputs/run1 \
  --score-cols phq9_total gad7_total
```
### Outputs
- `interim_clean.csv`
- `report.json` (descriptives, correlations, missing)
- `hist_*.png`, `trend_*.png`

### Reproducibility & Safety
- Never commit PHI/PII; keep only synthetic data in-repo
- Externalize secrets via `PRDT_ANON_KEY`
- Prefer small, incremental commits with clear messages
- Record version/tags in release notes

### Roadmap (Next)
- Cronbach’s alpha (internal consistency)
- Missingness detail (count and percent per column)
- CLI subcommands (`clean`, `stats`, `plot`)
- Basic unit tests (`pytest`)
