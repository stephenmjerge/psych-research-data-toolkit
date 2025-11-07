# Changelog
All notable changes to this project will be documented in this file.

This project adheres to [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/)
and follows [Semantic Versioning](https://semver.org/).

## [Unreleased]
### Added
- Cronbach’s alpha (internal consistency)
- Missingness detail report (count and percent per column)
- CLI subcommands: `clean`, `stats`, `plot`, `run`
- Config profile loading via `--config path/to/profile.toml`
- Basic unit tests via `pytest` (CLI smoke test)

### Changed
- README quickstart and command documentation

### Fixed
- N/A

### Security
- N/A

---

## [v0.1.0] — 2025-11-06
### Added
- CLI that loads CSVs, performs basic cleaning, and writes `interim_clean.csv`.
- HMAC-based ID anonymization via `PRDT_ANON_KEY` (drops original ID, adds `anon_id`).
- Descriptive statistics, Pearson correlations, and missing-value summary written to `report.json`.
- Histogram generation for selected score columns (e.g., `phq9_total`, `gad7_total`).
- Simple time-trend plot by participant for the first score column when `date` and `anon_id` are present.

### Changed
- Normalize headers to lowercase with underscores (spaces and hyphens normalized).

### Fixed
- N/A

### Security
- Guidance to never commit PHI/PII and to externalize secrets via `PRDT_ANON_KEY`.
