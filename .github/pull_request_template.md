## Summary

## Tests

- [ ] `./knowledgeforward test`
- [ ] `./knowledgeforward security-check`

## Security Checklist

- [ ] No real notes, logs, SQLite databases, tokens, or local absolute paths are committed.
- [ ] No private runtime `config.yaml`, `data/`, `logs/`, `run/`, PID files, or Ollama management files are committed.
- [ ] No new external network calls or telemetry are added without explicit discussion.
- [ ] Filesystem access remains allowlist-based.
