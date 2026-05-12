# Contributing

Thanks for helping improve KnowledgeForward.

## Development Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp config.example.yaml config.yaml
```

Set a local token in `config.yaml` before running the server. Do not commit `config.yaml`.

## Checks

Run these before opening a pull request:

```bash
make test
make security-check
```

## Security Rules

- Do not commit real notes, vaults, logs, SQLite databases, tokens, or local absolute paths.
- Use `fixtures/sample_vault` or synthetic test data only.
- Keep default behavior local-first and private-by-default.
- Do not add external network calls, telemetry, or broad filesystem access without an explicit design discussion.

## Pull Requests

Keep changes focused. Include tests for behavior changes and update README/docs when user-facing behavior changes.
