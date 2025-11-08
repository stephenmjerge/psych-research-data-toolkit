# Psych Research Data Toolkit

A clean, reproducible toolkit for psychological and psychiatric research: CSV cleaning, anonymization, descriptives, correlations, and clinical data visualizations (histograms, time-trend).

## Features
- Normalize headers and basic CSV cleaning  
- HMAC-based ID anonymization via `PRDT_ANON_KEY`  
- Descriptives, Pearson correlations, Cronbach’s alpha & McDonald’s ω (overall + per-scale), missingness counts + percents (JSON)  
- Optional alert thresholds for reliability and column-level missingness  
- Automatic PHI detector (emails/phones/SSNs/etc.) with quarantine + alerts  
- Built-in scoring for PHQ-9, GAD-7, PCL-5, AUDIT + custom scale definitions
- Data dictionary + run manifest per execution for reproducibility  
- Histograms for selected score columns + missingness bar chart  
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

## Profiles (`--config`)
- Create a TOML profile to avoid repeating CLI flags. Paths in the file are resolved relative to the config’s directory.
- Define reliability groups under `[prdt.scales.<name>]` so each scale gets its own Cronbach’s alpha and McDonald’s ω entries in `report.json`.
- Configure custom scale scoring under `[prdt.score]` and `[prdt.score.definitions.*]` (items, method, output column).
- Configure alert thresholds under `[prdt.alerts]` to highlight high missingness or low reliability in `report.json`.
- Example (`configs/anxiety.toml`):

  ```toml
  [prdt]
  command = "run"
  input = "../data/examples/surveys.csv"
  outdir = "../outputs/anxiety-profile"
  score_cols = ["phq9_total", "gad7_total"]
  skip_anon = false

  [prdt.score]
  scales = ["phq9", "gad7", "phq2_custom"]

  [prdt.score.definitions.phq2_custom]
  items = ["phq9_item1", "phq9_item2"]
  method = "sum"
  output = "phq2_score"

  [prdt.scales.phq9]
  items = ["phq9_item1", "phq9_item2"]

  [prdt.scales.gad7]
  items = ["gad7_item1", "gad7_item2"]

  [prdt.alerts]
  missing_pct = 10.0

  [prdt.alerts.reliability]
  cronbach_alpha_min = 0.75
  mcdonald_omega_min = 0.75

  [prdt.schema]
  required = ["participant_id", "date"]

  [prdt.schema.types]
  phq9_item1 = "numeric"
  gad7_item1 = "numeric"

  [prdt.schema.ranges.phq9_item1]
  min = 0
  max = 3
  ```

- Add additional `prdt.schema.ranges.*` tables for any numeric column that must stay within known bounds (alerts and manifests report violations).

- Invoke with `prdt --config configs/anxiety.toml` (you can still override any option on the command line).

## Example Run
1. Ensure your virtualenv is active and `PRDT_ANON_KEY` is set (see Quickstart).
2. Execute the bundled profile (mirrors a typical PHQ-9/GAD-7 workflow):

   ```bash
   prdt --config configs/anxiety.toml
   ```

3. Inspect outputs under `outputs/anxiety-profile/`:
   - `interim_clean.csv`: cleaned + anonymized data.
   - `report.json`: descriptives, correlations, reliability, missingness, alerts.
   - `alerts.json`: only present when a threshold is exceeded.
   - `data_dictionary.csv`: snapshot of every column’s dtype and completeness.
   - `run_manifest.json`: provenance (version, git SHA, config hash, input hash, timestamps).
   - `phi_quarantine.csv`: columns removed for PHI risk (e.g., emails in `contact`).
   - `hist_phq9_total.png`, `hist_gad7_total.png`, `trend_phq9_total.png`, `missingness.png`.

Sample `alerts.json` (generated because every `note` entry is missing, GAD-7 reliability is low, and contact info contains emails in the example data):

```json
[
  {"type": "missingness", "column": "note", "percent": 100.0, "threshold": 10.0},
  {"type": "reliability", "target": "gad7", "metric": "cronbach_alpha", "value": 0.0, "threshold": 0.75},
  {"type": "phi", "column": "contact", "matches": [{"pattern": "email", "count": 2}], "message": "PHI-like data detected in column 'contact'. Column removed from outputs."}
]
```

The CLI also prints a short summary so you notice issues immediately.

## Alerts
- `report.json` contains an `alerts` array. Each entry describes either:
  - `type = "missingness"` when a column’s missing percent exceeds `missing_pct`.
  - `type = "reliability"` when Cronbach’s α or McDonald’s ω drops below the configured minimum (overall or per-scale).
- `type = "phi"` when the PHI scanner removes columns (emails, phones, MRNs, etc.).
- Alerts are informational only; the CLI still writes outputs so you can review and decide on follow-up cleaning.
- When alerts exist, the CLI prints a brief summary and writes `alerts.json` for quick review.

### Outputs
- `interim_clean.csv`
- `report.json` (descriptives, correlations, reliability, missing, alerts)
- `alerts.json` (only created when thresholds trigger)
- `data_dictionary.csv` (column name, dtype, missing pct, example)
- `run_manifest.json` (PRDT version, git SHA, config hash, input hash)
- `phi_quarantine.csv` (only created when columns are removed for PHI risk)
- `hist_*.png`, `trend_*.png`, `missingness.png`

### Reproducibility & Safety
- Never commit PHI/PII; keep only synthetic data in-repo
- Externalize secrets via `PRDT_ANON_KEY`
- Prefer small, incremental commits with clear messages
- Record version/tags in release notes

### Roadmap (Next)
- Additional reliability metrics (e.g., McDonald’s ω)
- More granular missingness visualizations
- Configurable alert thresholds for reliability/missingness
- CI job to run `pytest`
