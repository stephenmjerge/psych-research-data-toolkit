# Dataset A (Live Data) Replication Plan

This checklist captures everything needed to rerun the Dataset A cleaning/anonymization workflow once the live data drop is approved. Treat it as a runbook so the OSF update is a repeatable, auditable task.

## Goals

- Pull the approved Dataset A export into a quarantine/drop-zone directory.
- Reuse `configs/dataset_a.toml` + `scripts/run_dataset_a_osf_demo.sh` as the baseline, swapping in the live CSV paths.
- Produce a cleaned/anonymized bundle that mirrors the synthetic demo (manifest, plots, README, and ZIP) and upload it to the existing OSF project/DOI entry.

## Prerequisites

- [ ] Data sharing agreement + IRB/PI approval stored in `docs/data_access/` (reference location before touching PHI).
- [ ] Secure drop zone provisioned (e.g., `data/private/dataset_a_live/raw/`) with disk encryption enabled.
- [ ] Hash seeds + suppression rules reviewed against `KEY_HANDLING.md` and `DATA_SECURITY.md`.
- [ ] OSF credentials/API token confirmed locally (see `scripts/osf_push_template.sh`).

## Runbook

### 1. Secure ingest

1. [ ] Create/confirm the drop-zone folder (`data/private/dataset_a_live/raw/`). Never sync this directory to Git or cloud storage.
2. [ ] Copy the raw CSV export + data dictionary exactly as provided. Record hashes in `docs/audits/dataset_a_live_ingest.md`.
3. [ ] Redact/replace any unexpected PHI columns before they ever reach PRDT (date of birth, MRNs, etc.). Update `configs/dataset_a.toml` if new columns appear.

### 2. Clean + anonymize

1. [ ] Create an isolated virtualenv or activate the repo environment.
2. [ ] Dry-run the config with column sampling enabled:
   ```bash
   python -m prdt run configs/dataset_a.toml \
     --input data/private/dataset_a_live/raw/dataset_a.csv \
     --output outputs/dataset_a_live/check_01 \
     --sample 50
   ```
3. [ ] Fix any schema mismatches, PHI detections, or assertion failures (the CLI exits non-zero if PHI is present unless `--allow-phi-export` is explicitly set — do **not** set that flag for the live run).
4. [ ] Run the full cleaning + anonymization export to `outputs/dataset_a_live/final/` and capture logs under `logs/dataset_a_live/`.
5. [ ] Generate the descriptive plots and tables via `scripts/run_dataset_a_osf_demo.sh` (pass the live paths using env vars or a wrapper script so the recipe stays identical to the synthetic demo).

### 3. QA + OSF update

1. [ ] Use `python -m prdt summary ...` (or open the generated `README`) to verify value ranges, missingness, and anonymization notes.
2. [ ] Spot-check a handful of rows against the manual scoring key or clinic reference sheet if available.
3. [ ] Zip the cleaned outputs + README + manifest via `scripts/run_dataset_a_osf_demo.sh --mode osf` (or replicate the commands manually if credentials differ).
4. [ ] Upload the ZIP plus any refreshed plots to the existing OSF registration (`https://doi.org/10.17605/OSF.IO/BX76K`) and note the upload timestamp/revision in `docs/audits/dataset_a_live_ingest.md`.
5. [ ] Update `PortfolioHub.md`, `PRDT/README.md`, and `LAUNCHPAD/next-actions.md` with the new "live dataset" status.

## Artifacts to capture

- Drop-zone manifest (filenames, hashes, ingest date).
- PRDT CLI logs (store in `logs/dataset_a_live/`).
- Cleaned output folder zipped for OSF + local backup.
- README snippet describing what changed between the synthetic demo and the live run.
- LAUNCHPAD note linking to the OSF revision + QA status.
