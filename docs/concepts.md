# PRDT Concepts

Use this page when you need to explain **why** PRDT reports certain numbers or alerts.

## Reliability
- **Cronbach’s α (alpha)** and **McDonald’s ω (omega)** measure internal consistency.
- PRDT also reports **item-total correlations** and **α if item dropped** so you can see which items weaken a scale.
- Config cutoffs (e.g., α ≥ 0.75) trigger alerts when reliability degrades.

## Missingness
- Every run includes `data_dictionary.csv` plus `missingness.png`.
- `[prdt.alerts].missing_pct` sets a global threshold. When exceeded, alerts list the column, percent missing, and threshold.
- Combine with schema ranges to catch impossible values (e.g., PHQ item outside 0–3).

## PHI controls
- PRDT anonymizes `participant_id` via deterministic HMAC.
- The PHI scanner redacts emails, phone numbers, MRNs, and configurable keywords, writing them to `phi_quarantine.csv`.
- You decide which columns to ignore or allow via `[prdt.phi]` in the config.
- Always follow [KEY_HANDLING.md](../KEY_HANDLING.md) so the anonymization key stays safe.

## Drift detection
- `drift.json` compares the latest scale means to the previous run. Any change ≥ 1 point generates a drift alert.
- The output helps you answer “Did the population’s PHQ-9 scores worsen this week?” without digging into raw CSVs.

## Provenance
- Each run writes two manifests: `run_manifest.json` (latest) and `run_manifest_<timestamp>.json`.
- Manifests include PRDT version, git commit, config hash, input hash, outputs, scale scores, and alert counts—everything you need for reproducibility.

Keep this page handy when presenting PRDT to supervisors, IRB reviewers, or admissions committees. It translates the JSON/alerts into plain language talking points.
