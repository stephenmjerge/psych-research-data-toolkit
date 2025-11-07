# Psych Research Data Toolkit

A clean, reproducible toolkit for psychological and psychiatric research: CSV cleaning, anonymization, descriptives, correlations, and clinical data visualizations (histograms, time-trend).

## Features (v0.1.0)
- Normalize headers and basic CSV cleaning  
- HMAC-based ID anonymization via `PRDT_ANON_KEY`  
- Descriptives, Pearson correlations, Cronbach’s alpha, missingness counts + percents (JSON)  
- Histograms for selected score columns  
- Simple time-trend plot by participant  
- CLI subcommands for focused workflows (`clean`, `stats`, `plot`, `run`)  

## Quickstart

1. **Create and activate a virtual environment** (keeps dependencies isolated):

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. **Install PRDT and its dependencies**:

   ```bash
   pip install -e .
   ```

3. **Set the anonymization key**. This secret is required whenever `participant_id` is present; the CLI will exit if it is missing. Generate a random value (example uses `openssl`) and export it before every session:

   ```bash
   export PRDT_ANON_KEY="$(openssl rand -hex 32)"
   ```

   On Windows PowerShell use: `setx PRDT_ANON_KEY (New-Guid)` and restart the shell.

4. **Run the CLI** on the sample data to verify everything works (subcommand defaults to `run`, which executes the full pipeline):

   ```bash
   prdt run --input data/examples/surveys.csv --outdir outputs/run1 \
     --score-cols phq9_total gad7_total
   ```

   Use `python -m prdt.cli run ...` if the console script is unavailable in your shell.

If you prefer to install dependencies without editable mode, `pip install -r requirements.txt` also works, but the console script entry point (`prdt`) is only available after `pip install -e .` or `pip install .`. Add `--skip-anon` if you explicitly want to retain `participant_id` during local debugging.

## Commands
- `prdt clean`: Clean/anonymize CSV and write `interim_clean.csv`.
- `prdt stats`: Clean, validate score columns, and write `report.json`.
- `prdt plot`: Clean, validate score columns, and generate `hist_*.png` plus `trend_*.png`.
- `prdt run`: Full pipeline (equivalent to running `clean`, `stats`, `plot`). Invoked automatically if no subcommand is supplied.

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
- Additional reliability metrics (e.g., McDonald’s ω)
- More granular missingness visualizations
- CLI config profiles (pre-set pipelines)
- CI job to run `pytest`
