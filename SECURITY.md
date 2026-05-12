# Security Policy

KnowledgeForward is local-first software intended to index only explicitly allowed local folders and to use local Ollama models by default. Security reports should never include real private notes, API tokens, private runtime `config.yaml` contents, SQLite databases, logs, PID files, local absolute paths, or screenshots that expose private data.

## Supported Versions

Until the first stable release, security fixes target the `main` branch only.

## Reporting a Vulnerability

Use GitHub private vulnerability reporting or GitHub Security Advisories for this repository when available. If private reporting is unavailable, contact the repository owner through a private channel before opening a public issue.

Please include:

- A concise description of the vulnerability.
- Reproduction steps using synthetic test data only.
- The affected version or commit.
- The expected impact and any known mitigations.

Do not disclose vulnerabilities publicly until a fix or mitigation plan has been published.

## Security Boundaries

KnowledgeForward should preserve these boundaries:

- No external LLM API calls by default.
- No external search API calls by default.
- No telemetry by default.
- Only folders explicitly listed in `config.yaml` may be indexed.
- Real runtime files must stay outside the public repository. This includes private runtime `config.yaml`, `data/`, `logs/`, `run/`, PID files, Ollama management files, SQLite databases, and real private notes.
- `KNOWLEDGE_FORWARD_HOME` should point to a private runtime outside the public repository for real use.
- `KNOWLEDGE_FORWARD_CONFIG` may point to an explicit config file, but that config must remain local and must not be committed.
- repo-local `config.yaml`, `data/`, and `tmp/` are legacy compatibility paths only and should not be used for real private data.
- The server should bind to `127.0.0.1` by default.
- Remote phone access should use a private network path such as Tailscale Serve, not direct public exposure.
- Retrieved documents are untrusted evidence, not executable instructions.
