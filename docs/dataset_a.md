# Dataset A Workflow

Dataset A is the first OSF-bound dataset. Use this page plus `scripts/run_dataset_a.sh`
to generate reproducible outputs without exposing PHI.

## 1. Prepare the data
1. Drop the encrypted CSV into `data/dataset_a/raw.csv` (see `data/dataset_a/README.md`).
2. Ensure `PRDT_ANON_KEY` is exported.

## 2. Run the pipeline
```bash
export PRDT_ANON_KEY="$(openssl rand -hex 32)"  # or load from .env
DATASET_A_INPUT="/secure/path/raw.csv" \
DATASET_A_OUTDIR="/secure/path/outputs/dataset-a" \
scripts/run_dataset_a.sh
```
- Do **not** set `ALLOW_PHI_EXPORT` during production runs—the guardrail should only
  be bypassed for synthetic demos.
- Outputs include `interim_clean.csv`, `report.json`, `alerts.json`, `phi_quarantine.csv`,
  plots, manifests, and drift checks. Attach the `outputs/dataset-a/` directory to OSF once reviewed.

## 3. Review artifacts
- `report.json` → sanity-check descriptives, Cronbach’s α/ω, missingness, alerts.
- `hist_phq9_total.png`, `missingness.png`, `trend_phq9_total.png` → include when posting updates.
- `phi_quarantine.csv` → verify only expected PHI columns were removed.

## 4. Demo assets
For admissions decks or README screenshots, re-run the pipeline against the public
sample data:
```bash
export PRDT_ANON_KEY="demo-key-demo-key-demo-key-demo-key"
DATASET_A_INPUT="$(pwd)/data/examples/surveys.csv" \
DATASET_A_OUTDIR="$(pwd)/docs/assets/dataset-a-demo" \
ALLOW_PHI_EXPORT=1 \
scripts/run_dataset_a.sh
```
This produces the files stored under `docs/assets/dataset-a-demo/`. Only keep the
non-sensitive artifacts (histograms, missingness plot, report excerpt) in git.

## 5. Publish checklist
- Run the psych-research-workflow-organizer checklist script.
- Update `PortfolioHub.md` (Dataset A section) and `MASTER_TIMELINE.md` once the OSF upload is live.
- Note the lab hub DOI + component URL: Stephen M. Jerge — Clinical Science Lab (DOI: https://doi.org/10.17605/OSF.IO/BX76K) and Dataset A component https://osf.io/jcnp5/ (PRDT: Dataset A — Anonymized Synthetic Survey Data).
