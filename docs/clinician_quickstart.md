# Clinician Quickstart

Minimal, copy/paste steps to prove PRDT works and to troubleshoot common blockers.

## 1) Install (non-developer)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install https://github.com/stephenmjerge/psych-research-data-toolkit/releases/latest/download/prdt-0.1.3-py3-none-any.whl
```

## 2) Fastest first run
```bash
prdt demo
```
Outputs land in `outputs/demo_*` and include anonymized CSV, report, and manifest.

## 3) Typical run (bundled profile)
```bash
prdt --config configs/anxiety.toml
```

## 4) Troubleshooting
- Missing anonymization key:  
  `export PRDT_ANON_KEY="$(openssl rand -hex 32)"` (PowerShell: `setx PRDT_ANON_KEY (New-Guid)`)
- PHI guardrail aborts: Confirm the flagged columns; for synthetic data rerun with `--allow-phi-export` or add to `[prdt.phi.allow_columns]`.
- Headless/locked-down machines:  
  `export PRDT_DISABLE_PLOTS=1`  
  `export MPLCONFIGDIR=$PWD/.cache/mpl`  
  `export XDG_CACHE_HOME=$PWD/.cache/xdg`
- Validate without writing outputs: add `--dry-run`.
- Environment check: `prdt doctor` (Python, deps, key, input path if provided).

## 5) Share safely
Send only the files under `outputs/...` (never the raw CSV or `.env`). Include the manifest path so reviewers can see the exact command and version.
