---
name: Bug report
about: Flag a reproducible defect in PRDT’s CLI, pipelines, or docs.
title: "[BUG] "
labels: ["bug"]
assignees: []
---

## Summary
Short description of the failure and its impact on research workflows.

## Reproduction checklist
- [ ] Reproduces on the latest `main`
- [ ] Happens with a clean virtualenv (`pip install -e .`)
- [ ] Includes the anonymization key / config (`PRDT_ANON_KEY`) if required

### Steps to reproduce
1. …
2. …
3. …

### Sample command or script
```bash
prdt ... # include full CLI invocation or Python snippet
```

## Expected vs. actual
- **Expected:** …
- **Actual:** …

## Environment
- OS / version:
- Python version:
- Data source (e.g., `data/examples/surveys.csv`, custom CSV path):
- Optional configs (`configs/*.yaml`, env vars):

## Logs / artifacts
Attach stack traces, screenshots, generated CSV/JSON artifacts, or GitHub Actions links that capture the failure.
