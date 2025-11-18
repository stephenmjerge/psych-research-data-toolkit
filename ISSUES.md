# Issues

We track day-to-day bug triage in the private Notion board referenced from `meta/launchpad/next-actions.md`. When adding an entry, always include:

1. Dataset or config that reproduces the problem.
2. CLI command (usually `prdt --config <file> analyze`).
3. Expected vs. actual behavior plus any anonymization concerns.

If the issue is urgent, flag it inside Notion and drop a note in `docs/PortfolioHub.md` so it bubbles up during the weekly review.

## Issue: Dataset A cleaning profile
- Source: `meta/launchpad/next-actions.md` (PRDT section)
- Acceptance criteria:
  - Add a dedicated config under `configs/` for Dataset A with score sets + alerts.
  - Document how to run it inside `README.md` so admissions reviewers can follow along.
  - Capture the milestone in `ROADMAP.md` and link to OSF once the dataset publishes.
- Status: Completed (Nov 13, 2025).
