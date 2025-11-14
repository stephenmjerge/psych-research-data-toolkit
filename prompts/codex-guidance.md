# Codex Guidance

- Prefer `python -m pytest tests` before handing work back; the `tests/test_cli.py` suite catches most regressions.
- Follow the data-handling rules in `KEY_HANDLING.md` whenever touching example datasets or anonymization helpers.
- Summarize code changes in `CHANGELOG.md` under an `[Unreleased]` heading and link to the relevant LAUNCHPAD item when possible.
- Keep documentation edits mirrored in both `README.md` and `docs/quickstart.md` so new collaborators stay in sync.
