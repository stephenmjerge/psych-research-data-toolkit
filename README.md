# PRDT — Psych Research Data Toolkit
[![Release](https://img.shields.io/github/v/release/stephenmjerge/psych-research-data-toolkit)](https://github.com/stephenmjerge/psych-research-data-toolkit/releases/latest)
[![Demo](https://img.shields.io/badge/CLI-prdt%20demo-blue)](#tldr)

> **Research-use only:** PRDT is a lab notebook for data-cleaning and QA. Do not deploy it for diagnosis or treatment decisions unless your workflow is IRB-approved, validated, and overseen by licensed clinicians with HIPAA-compliant safeguards.

## Overview

Psych Research Data Toolkit (PRDT) is a reproducible CLI for cleaning, anonymizing, and summarizing mental-health CSVs. It handles HMAC-based identifiers, PHI scrubbing, descriptive stats, reliability checks, and visualization so trainees can ship trustworthy analyses without reinventing pipelines.

### TL;DR
- `prdt demo` — one-command demo with bundled sample data (outputs in `outputs/demo_*`)
- `prdt --config configs/anxiety.toml` — full pipeline with the bundled profile
- `prdt run --input data/examples/surveys.csv --outdir outputs/demo --score-cols phq9_total gad7_total`
- `prdt doctor` — environment check (Python, deps, key, input path if provided)
- `--dry-run` to validate without writing outputs; `--html-report` to emit a simple HTML summary
- Requirements: Python 3.9+ with pandas, numpy, matplotlib (installed via the wheel or `pip install -e ".[dev]"`)

### Visual snapshot

Record a 60-second screen capture of `prdt run` plus sample plots and place it in `docs/` (e.g., `docs/prdt-demo.gif`). Use it in admissions decks or lab walk-throughs.

## Features
- Normalize headers and basic CSV cleaning  
- HMAC-based ID anonymization via `PRDT_ANON_KEY`  
- Descriptives, Pearson correlations, Cronbach’s alpha & McDonald’s ω (overall + per-scale), missingness counts + percents (JSON)  
- Optional alert thresholds for reliability and column-level missingness  
- Automatic PHI detector (emails/phones/SSNs/etc.) with quarantine + alerts  
- Built-in scoring for PHQ-9, GAD-7, PCL-5, AUDIT + custom scale definitions (alpha, omega, item-total stats)
- Data dictionary + run manifest per execution for reproducibility  
- Drift detection compares scale means vs last run (`drift.json` + alerts)  
- Histograms for selected score columns + missingness bar chart  
- Simple time-trend plot by participant  
- CLI subcommands for focused workflows (`clean`, `stats`, `plot`, `run`)

## Setup

1. **Create and activate the virtual environment**:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. **Install PRDT and dev dependencies**:

   ```bash
   pip install -e ".[dev]"
   # optional pinned environment
   pip install -r requirements-lock.txt
   ```

3. **Configure environment variables** (export before running PRDT):

| Variable | Purpose | Example |
| --- | --- | --- |
| `PRDT_ANON_KEY` | Required when `participant_id` exists; used for HMAC anonymization | `export PRDT_ANON_KEY="$(openssl rand -hex 32)"` |
| `MPLCONFIGDIR` / `XDG_CACHE_HOME` *(optional)* | Point Matplotlib caches at writable dirs on locked-down machines | `export MPLCONFIGDIR=$PWD/.cache/mpl` |
| `PRDT_DISABLE_PLOTS` *(optional)* | Skip plot rendering for headless/CI runs | `export PRDT_DISABLE_PLOTS=1` |

On Windows PowerShell use `setx PRDT_ANON_KEY (New-Guid)` and restart the shell.

Headless or locked-down machines: set `PRDT_DISABLE_PLOTS=1` to skip Matplotlib renders and point `MPLCONFIGDIR`/`XDG_CACHE_HOME` at writable paths (examples above) to avoid cache errors.

4. **Run the sample workflow** to verify everything works:

   ```bash
   prdt run --input data/examples/surveys.csv --outdir outputs/run1 \
     --score-cols phq9_total gad7_total
   ```

   Use `python -m prdt.cli run ...` if the console script is unavailable. Add `--skip-anon` if you need to retain `participant_id` for local debugging only.
   Fastest first run: `prdt demo` (bundled sample data, outputs under `outputs/demo_*`, no config/key required).

## CLI cheatsheet

| Command | Purpose | Example |
| --- | --- | --- |
| `prdt clean` | Clean + anonymize CSV, emit `interim_clean.csv` and data dictionary | `prdt clean --input data/examples/surveys.csv --outdir outputs/clean` |
| `prdt stats [--alpha]` | Validate score columns, compute descriptives/reliability/missingness; `--alpha` prints Cronbach’s α for `--score-cols` | `prdt stats --input data/examples/surveys.csv --outdir outputs/stats --score-cols phq9_total gad7_total --alpha` |
| `prdt plot` | Generate histogram, trend, and missingness plots for selected columns | `prdt plot --input data/examples/surveys.csv --outdir outputs/plots --score-cols phq9_total` |
| `prdt run` | Full pipeline (`clean` + `stats` + `plot`), default command when omitted | `prdt run --input data/examples/surveys.csv --outdir outputs/run1` |
| `prdt doctor` | Environment check (Python, deps, key, input path) | `prdt doctor` |
| `--dry-run` | Validate inputs/config and stop before writing outputs | `prdt run ... --dry-run` |
| `--html-report` | Save a simple HTML summary alongside `report.json` | `prdt stats ... --html-report` |

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

  [prdt.phi]
  keywords = ["contact", "address"]
  ignore_columns = ["note"]
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
   - `scale_scores` section inside `report.json` summarizing mean/std and severity labels based on cutoffs.

Sample `alerts.json` (generated because every `note` entry is missing, GAD-7 reliability is low, and contact info contains emails in the example data):

```json
[
  {"type": "missingness", "column": "note", "percent": 100.0, "threshold": 10.0},
  {"type": "reliability", "target": "gad7", "metric": "cronbach_alpha", "value": 0.0, "threshold": 0.75},
  {"type": "phi", "column": "contact", "matches": [{"pattern": "email", "count": 2}], "message": "PHI-like data detected in column 'contact'. Column removed from outputs."}
]
```

The CLI also prints a short summary so you notice issues immediately.

Run the same profile again after a new batch of data and PRDT will also emit `drift.json` whenever a scale’s mean shifts by ≥1 point compared with the previous run.

### Dataset A playbook

Dataset A lives outside the repo (secure share). The `configs/dataset_a.toml` profile
describes how to clean/anonymize it:

```bash
export PRDT_ANON_KEY="..."  # rotate per KEY_HANDLING.md
prdt --config configs/dataset_a.toml
```

- `input` points at `data/dataset_a/raw.csv` (drop-in placeholder—update to the
  secure path on your machine).
- Outputs land in `outputs/dataset-a/` with the full manifest/report stack so you
  can attach them to OSF once PHI checks pass.
- Score columns cover PHQ-9, GAD-7, and PCL-5 totals; adjust the config if the
  instrument list changes.
- `scripts/run_dataset_a.sh` wraps the CLI so you can override `DATASET_A_INPUT`
  / `DATASET_A_OUTDIR` without editing the profile.
- See `docs/dataset_a.md` for the full checklist plus demo artifacts under
  `docs/assets/dataset-a-demo/`.
- OSF demo bundle (synthetic Dataset A) with manifest + config: Stephen M. Jerge — Clinical Science Lab (DOI: https://doi.org/10.17605/OSF.IO/BX76K); PRDT component: https://osf.io/qs8ag/; Dataset A sub-component: https://osf.io/n4buw/ (generated Nov 14, 2025 via `scripts/run_dataset_a_osf_demo.sh`).

Copy this section into `docs/PortfolioHub.md` once Dataset A publishes to OSF so the
workflow is discoverable.

#### Rebuild the OSF bundle

When admissions reviewers or collaborators need the Dataset A artifact, regenerate it with the helper script and stash the outputs inside `docs/assets/dataset-a-osf/`:

```bash
export PRDT_ANON_KEY="$(openssl rand -hex 32)"
DATASET_A_INPUT="/secure/raw/dataset_a.csv" \
DATASET_A_OUTDIR="$(pwd)/outputs/dataset-a-osf" \
scripts/run_dataset_a.sh
```

Copy the sanitized outputs (`interim_clean.csv`, `report.json`, plots, alerts) into a staging folder, zip them (`dataset-a-osf-bundle-YYYYMMDD.zip`), and drop the archive under `docs/assets/dataset-a-osf/bundle/`. Move the latest `run_manifest_*.json` into `docs/assets/dataset-a-osf/provenance/` so the OSF README can cite the exact command + git SHA. See `docs/assets/dataset-a-osf/README.md` for the upload checklist.

## Documentation
- [/docs/README.md](docs/README.md): links to a non-technical walkthrough, concept notes, and a copy/paste quickstart for new teammates or admissions reviewers.
- [/docs/clinician_quickstart.md](docs/clinician_quickstart.md): one-page instructions + troubleshooting for clinicians.

## Alerts
- `report.json` contains an `alerts` array. Each entry describes either:
  - `type = "missingness"` when a column’s missing percent exceeds `missing_pct`.
  - `type = "reliability"` when Cronbach’s α or McDonald’s ω drops below the configured minimum (overall or per-scale).
- `type = "phi"` when the PHI scanner removes columns (emails, phones, MRNs, etc.).
- Alerts are informational only; the CLI still writes outputs so you can review and decide on follow-up cleaning.
- When alerts exist, the CLI prints a brief summary and writes `alerts.json` for quick review.

### PHI guardrail
PRDT now aborts when PHI-like columns are detected to prevent accidental exports.

- Inspect the columns listed in the error and clean or drop them.
- If the columns are expected (e.g., you plan to scrub them downstream), either list them under `[prdt.phi.allow_columns]`
  or set `--allow-phi-export` / `allow_phi_export = true` in your config.
- `phi_quarantine.csv` still records the flagged data for auditing, even when the guardrail fires.

### Outputs
- `interim_clean.csv`
- `report.json` (descriptives, correlations, reliability, missing, alerts)
- `alerts.json` (only created when thresholds trigger)
- `data_dictionary.csv` (column name, dtype, missing pct, example)
- `run_manifest.json` (PRDT version, git SHA, config hash, input hash)
- `phi_quarantine.csv` (only created when columns are removed for PHI risk)
- `drift.json` (only created when scale means change ≥ 1 point vs prior run)
- `hist_*.png`, `trend_*.png`, `missingness.png`
- `scale_summary.png`, `scale_items_<scale>.png` (only when scale scoring is enabled)

## Installing from a Wheel
1. Build artifacts (already present under `dist/`, or run `python -m build`).
2. Install the wheel anywhere—no repository clone required:

   ```bash
   pip install dist/prdt-0.1.4-py3-none-any.whl
   ```

Attach the wheel to GitHub Releases so reviewers can `pip install` PRDT directly.

### Reproducibility & Safety
- Never commit PHI/PII; keep only synthetic data in-repo
- Externalize secrets via `PRDT_ANON_KEY`
- Read `KEY_HANDLING.md` for best practices (long random key, `.env` usage, rotation)
- Prefer small, incremental commits with clear messages
- Record version/tags in release notes

### Roadmap (Next)
- Additional reliability metrics (e.g., McDonald’s ω)
- More granular missingness visualizations
- Configurable alert thresholds for reliability/missingness
- CI job to run `pytest`
