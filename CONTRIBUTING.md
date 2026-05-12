# Contributing

Thanks for helping improve KnowledgeForward.

## Development Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
RUNTIME_HOME="$HOME/.knowledgeforward-local-dev"
./knowledgeforward init-runtime "$RUNTIME_HOME"
export KNOWLEDGE_FORWARD_HOME="$RUNTIME_HOME"
```

Use the generated private runtime for local manual runs. Do not put real notes, tokens, logs, SQLite databases, PID files, or local absolute paths in the repository directory or Git tracking. Tests should use `tmp_path`, `fixtures/sample_vault`, or synthetic data instead of a developer's real runtime.

## Checks

Run these before opening a pull request. Security commands are developer/maintainer repository checks; they are not required for normal end-user operation.

```bash
./knowledgeforward test
./knowledgeforward security-check
./knowledgeforward security-audit
```

## Security Rules

- Do not commit real notes, vaults, logs, SQLite databases, tokens, or local absolute paths.
- Use `fixtures/sample_vault` or synthetic test data only.
- Keep private runtime files outside the repository. This includes `config.yaml`, `data/`, `logs/`, `run/`, and PID files.
- Keep default behavior local-first and private-by-default.
- Do not add external network calls, telemetry, or broad filesystem access without an explicit design discussion.

## Pull Requests

Keep changes focused. Include tests for behavior changes and update README/docs when user-facing behavior changes.
