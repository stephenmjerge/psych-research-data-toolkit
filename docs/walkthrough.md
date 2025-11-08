# PRDT Walkthrough

This example shows how PRDT processes a small PHQ-9/GAD-7 export. You can follow along even if you have never used the command line before.

## 1. Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
pip install -r requirements-lock.txt  # optional but ensures matching versions
python -m build  # optional if you want wheels in ./dist
export PRDT_ANON_KEY="$(openssl rand -hex 64)"
```

## 2. Run the bundled profile
```bash
prdt --config configs/anxiety.toml
```

## 3. Inspect the outputs (all inside `outputs/anxiety-profile/`)

| File | Why it matters |
| --- | --- |
| `interim_clean.csv` | Cleaned + anonymized dataset. Safe to share. |
| `report.json` | Descriptives, correlations, reliability, missingness, alerts. |
| `alerts.json` | Plain-English issues (missingness, low α/ω, PHI, drift). |
| `phi_quarantine.csv` | Columns removed because they contained PHI. |
| `data_dictionary.csv` | Column glossary (dtype, % missing, example value). |
| `run_manifest_YYYYMMDDTHHMMSSZ.json` | Provenance (PRDT version, git SHA, config hash, input hash). |
| `drift.json` | Appears only when scale means shift ≥ 1 point vs last run. |
| `scale_summary.png`, `scale_items_<scale>.png` | Ready-to-paste visuals for reports. |
| `hist_*.png`, `trend_*.png`, `missingness.png` | Additional charts for QA. |

## 4. Rerun to detect drift
After collecting a new batch, run the same command again. Compare `drift.json` and `alerts.json` to see if any scale worsened. Because manifests are timestamped, you can keep a chronological trail for supervisors or auditors.

## 5. Use your own data
1. Copy `configs/anxiety.toml` and update:
   - `input` path to your CSV
   - `score_cols` + `[prdt.score]` to match your scales
   - `[prdt.schema]` rules so PRDT warns about type/range violations
   - `[prdt.phi]` keywords (e.g., `guardian`, `address`) to catch clinic-specific PHI
2. Run `prdt --config your_profile.toml`
3. Share only the anonymized outputs (never the original CSV).

That’s it—you now have a repeatable workflow that anonymizes IDs, catches PHI, enforces QC, and generates figures plus drift alerts with a single command.
