# PRDT Key Handling

PRDT relies on a secret key to anonymize identifiers via HMAC. Handle it with the same care as any credential.

## Requirements
- Use a long, random string (≥32 hex characters) for `PRDT_ANON_KEY`.
- Never commit the key to git, `.env`, or config files.
- Rotate keys if you suspect they leaked or after sharing data externally.

## Recommended Workflow
1. Generate a key once per project (e.g., `openssl rand -hex 64`).
2. Store it in a secure secret manager or `.env` file that is excluded from version control.
3. Export the key in your shell before running PRDT (or let PRDT load it from `.env`).

## Loading from .env
Create a local `.env` file (ignored by git) and add:

```
PRDT_ANON_KEY=your-long-random-value
```

PRDT will automatically load this file if it exists in the working directory.

## Validation Guardrails
PRDT refuses to run when:
- `PRDT_ANON_KEY` is missing.
- The key is shorter than 32 characters.
- The key matches a known placeholder value (e.g., `changeme`, `testkey`, `default`).

## Rotation
When rotating the key, re-run your pipelines so anonymized IDs stay consistent within each release. Document the key’s scope (project/clinic) so collaborators understand what data it protects.
