# launchd notes

KnowledgeForward can eventually be run from a macOS LaunchAgent so it starts when the Mac user logs in. This repository does not install a LaunchAgent yet, and this phase should continue to use `scripts/start.sh`, `scripts/stop.sh`, and `scripts/status.sh` for daily operation.

Tailscale Serve persistence and KnowledgeForward process persistence are separate things. `tailscale serve --bg localhost:8765` persists the Tailscale proxy configuration inside Tailscale, but it does not keep the Python `uvicorn` process alive after reboot or logout. The current scripts may also start Ollama when it is not already responding, but `scripts/stop.sh` unloads only the configured model and does not stop the Ollama server.

If a LaunchAgent is added later, keep these constraints:

- Do not generate or load a plist automatically from the current scripts.
- Do not run `launchctl load`, `launchctl bootstrap`, or similar install commands until the operational flow has been verified manually.
- Use the repository-local virtualenv and keep the working directory pinned to the repository root.
- Write stdout/stderr to repo-local logs under `tmp/logs/`.
- Preserve the Ollama ownership rule: do not stop the Ollama server from the stop script. Unload only the configured model with `ollama stop <model>` unless `KNOWLEDGE_FORWARD_SKIP_MODEL_UNLOAD=1` is set.
- Keep KnowledgeForward bound to `127.0.0.1:8765`; do not use `0.0.0.0`.
- Keep `config.yaml`, `data/`, and `tmp/` out of Git.
- Do not enable automatic startup before real Vault onboarding has been reviewed and explicitly approved.
