#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
PYTHON="$REPO_ROOT/.venv/bin/python"
HOST="127.0.0.1"
PORT="8765"
HEALTH_URL="http://${HOST}:${PORT}/health"
OLLAMA_TAGS_URL="http://127.0.0.1:11434/api/tags"

# shellcheck disable=SC1091
source "$SCRIPT_DIR/runtime_env.sh"

info() {
  printf 'INFO: %s\n' "$*"
}

warn() {
  printf 'WARN: %s\n' "$*" >&2
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

is_knowledgeforward_pid() {
  local pid="$1"
  local command_line

  if ! [[ "$pid" =~ ^[0-9]+$ ]]; then
    return 1
  fi
  if ! kill -0 "$pid" >/dev/null 2>&1; then
    return 1
  fi
  command_line="$(ps -p "$pid" -o command= 2>/dev/null || true)"
  [[ "$command_line" == *"uvicorn"* && "$command_line" == *"knowledge_forward.api:app"* ]]
}

is_ollama_pid() {
  local pid="$1"
  local command_line

  if ! [[ "$pid" =~ ^[0-9]+$ ]]; then
    return 1
  fi
  if ! kill -0 "$pid" >/dev/null 2>&1; then
    return 1
  fi
  command_line="$(ps -p "$pid" -o command= 2>/dev/null || true)"
  [[ "$command_line" == *"ollama"* && "$command_line" == *"serve"* ]]
}

port_pids() {
  command -v lsof >/dev/null 2>&1 || return 0
  lsof -nP -iTCP:"$PORT" -sTCP:LISTEN -t 2>/dev/null || true
}

ensure_repo_root() {
  cd "$REPO_ROOT"
  git rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "Not inside a Git work tree: $REPO_ROOT"
  [ -f "$REPO_ROOT/knowledge_forward/api.py" ] || die "Could not locate KnowledgeForward app files under $REPO_ROOT"
}

check_virtualenv() {
  [ -d "$REPO_ROOT/.venv" ] || die ".venv does not exist. Create it and install requirements.txt first."
  [ -x "$PYTHON" ] || die "Python executable not found at $PYTHON"
}

check_dependencies() {
  [ -f "$REPO_ROOT/requirements.txt" ] || die "requirements.txt is missing."
  "$PYTHON" - <<'PY'
import importlib
import sys

modules = {
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "PyYAML": "yaml",
    "pytest": "pytest",
    "httpx": "httpx",
}
missing = []
for requirement_name, module_name in modules.items():
    try:
        importlib.import_module(module_name)
    except Exception:
        missing.append(requirement_name)
if missing:
    print("Missing Python dependency modules: " + ", ".join(missing), file=sys.stderr)
    sys.exit(1)
PY
}

check_config() {
  [ -f "$CONFIG_PATH" ] || die "Config file is missing: $CONFIG_PATH. Run './knowledgeforward init-runtime <path>' or create a config file there."

  if [ "$RUNTIME_IS_EXTERNAL" = "1" ]; then
    if path_is_inside_repo "$CONFIG_PATH" || path_is_inside_repo "$RUNTIME_HOME"; then
      die "Explicit KnowledgeForward runtime paths must be outside the repository directory."
    fi
  else
    warn "Using legacy repo-local config/tmp runtime. For real use, set KNOWLEDGE_FORWARD_HOME outside the repository directory."
    if git ls-files --error-unmatch config.yaml >/dev/null 2>&1; then
      die "config.yaml is tracked by Git. It must remain local and Git-untracked."
    fi
    if ! git check-ignore -q config.yaml; then
      warn "config.yaml is untracked, but it is not ignored by Git."
    fi
  fi

  "$PYTHON" - <<'PY'
from pathlib import Path
import os
import sys
import yaml

from knowledge_forward.config import ConfigError, INSECURE_AUTH_TOKENS, load_config
from knowledge_forward.source_safety import MAX_DEFAULT_QUERY_DAYS, validate_startup_allowed_sources

repo = Path.cwd().resolve()
config_path = Path(os.environ["KNOWLEDGE_FORWARD_CONFIG"])
raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
auth = raw.get("auth") or {}
config_token = str(auth.get("token", "")).strip()
env_token = os.environ.get("KNOWLEDGE_FORWARD_AUTH_TOKEN", "").strip()

if not config_token:
    print("auth.token is missing in the config file.", file=sys.stderr)
    sys.exit(1)
if config_token in INSECURE_AUTH_TOKENS:
    print("auth.token is still an insecure placeholder.", file=sys.stderr)
    sys.exit(1)
if env_token in INSECURE_AUTH_TOKENS:
    print("KNOWLEDGE_FORWARD_AUTH_TOKEN is set to an insecure placeholder.", file=sys.stderr)
    sys.exit(1)

try:
    config = load_config()
except ConfigError as exc:
    print(f"config file failed validation: {exc}", file=sys.stderr)
    sys.exit(1)

if config.server.host != "127.0.0.1" or config.server.port != 8765:
    print("server.host/server.port must remain 127.0.0.1:8765 for this operational phase.", file=sys.stderr)
    sys.exit(1)

source_errors, query_filtered_sources = validate_startup_allowed_sources(config, repo)
if source_errors:
    print("allowed_sources contains unsupported enabled source(s):", file=sys.stderr)
    for error in source_errors:
        print(f"  - {error}", file=sys.stderr)
    print(
        "Allowed enabled sources are ./tmp/private_test_vault, ./fixtures/sample_vault, "
        "or obsidian sources with require_query_filter=true and "
        f"default_query_days from 1 to {MAX_DEFAULT_QUERY_DAYS}.",
        file=sys.stderr,
    )
    sys.exit(1)

cloud_label = "i" + "Cloud"
if query_filtered_sources:
    source_summary = ", ".join(
        f"{source.name} ({source.query_filter_status})" for source in query_filtered_sources
    )
    print(f"OK: query-filtered enabled source(s): {source_summary}")
print(
    "OK: config file is local, token is non-placeholder, and allowed_sources passed startup safety checks. "
    f"No real Vault or {cloud_label} discovery is performed."
)
PY
}

ollama_responds() {
  curl -fsS --max-time 2 "$OLLAMA_TAGS_URL" >/dev/null 2>&1
}

wait_for_ollama() {
  for _ in $(seq 1 30); do
    if ollama_responds; then
      return 0
    fi
    sleep 1
  done
  return 1
}

remove_stale_ollama_state() {
  local pid=""

  if [ -f "$OLLAMA_PID_FILE" ]; then
    pid="$(head -n 1 "$OLLAMA_PID_FILE" 2>/dev/null | tr -d '[:space:]')"
  fi

  if [ -f "$OLLAMA_MARKER_FILE" ] && grep -qx 'managed_by=KnowledgeForward' "$OLLAMA_MARKER_FILE" 2>/dev/null && [ -n "${pid:-}" ] && is_ollama_pid "$pid"; then
    return 0
  fi

  if [ -f "$OLLAMA_MARKER_FILE" ] || [ -f "$OLLAMA_PID_FILE" ]; then
    warn "Removing stale Ollama management files under $RUNTIME_RUN_DIR."
    rm -f "$OLLAMA_MARKER_FILE" "$OLLAMA_PID_FILE"
  fi
}

check_ollama_model() {
  "$PYTHON" - <<'PY'
import json
import sys
import urllib.error
import urllib.request

from knowledge_forward.config import ConfigError, load_config


def matches_model(requested: str, available: set[str]) -> bool:
    return requested in available or (":" not in requested and f"{requested}:latest" in available)


try:
    config = load_config()
except ConfigError as exc:
    print(f"config file failed validation: {exc}", file=sys.stderr)
    sys.exit(1)

url = config.ollama.base_url.rstrip("/") + "/api/tags"
try:
    with urllib.request.urlopen(url, timeout=2) as response:
        payload = json.loads(response.read().decode("utf-8"))
except (OSError, urllib.error.URLError, json.JSONDecodeError):
    print("Ollama is responding inconsistently; could not read /api/tags.", file=sys.stderr)
    sys.exit(1)

available: set[str] = set()
for item in payload.get("models", []):
    if not isinstance(item, dict):
        continue
    for key in ("name", "model"):
        value = str(item.get(key, "")).strip()
        if value:
            available.add(value)

if not matches_model(config.ollama.model, available):
    print(f"Configured Ollama model was not found: {config.ollama.model}", file=sys.stderr)
    print(f"Install it manually with: ollama pull {config.ollama.model}", file=sys.stderr)
    sys.exit(1)

print(f"OK: configured Ollama model is available: {config.ollama.model}")
PY
}

start_ollama() {
  local pid
  local existing_pid=""
  local process_start

  if ollama_responds; then
    info "Ollama is already responding at $OLLAMA_TAGS_URL; using the existing instance."
    return 0
  fi

  if [ -f "$OLLAMA_PID_FILE" ]; then
    existing_pid="$(head -n 1 "$OLLAMA_PID_FILE" 2>/dev/null | tr -d '[:space:]')"
    if is_ollama_pid "$existing_pid"; then
      die "Ollama PID $existing_pid is running, but $OLLAMA_TAGS_URL is not responding. Inspect $OLLAMA_LOG_FILE or stop the process manually."
    fi
  fi

  command -v ollama >/dev/null 2>&1 || die "Ollama is not responding at $OLLAMA_TAGS_URL, and the ollama command was not found in PATH."

  mkdir -p "$(dirname "$OLLAMA_PID_FILE")" "$(dirname "$OLLAMA_LOG_FILE")"
  touch "$OLLAMA_LOG_FILE"

  info "Starting Ollama with 'ollama serve'."
  nohup ollama serve >> "$OLLAMA_LOG_FILE" 2>&1 &
  pid="$!"
  printf '%s\n' "$pid" > "$OLLAMA_PID_FILE"
  process_start="$(ps -p "$pid" -o lstart= 2>/dev/null | sed 's/^[[:space:]]*//' || true)"
  {
    printf 'managed_by=KnowledgeForward\n'
    printf 'pid=%s\n' "$pid"
    printf 'command=ollama serve\n'
    printf 'started_at=%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    printf 'process_start=%s\n' "$process_start"
  } > "$OLLAMA_MARKER_FILE"

  if wait_for_ollama; then
    info "Ollama started with PID $pid."
    info "Ollama log file: $OLLAMA_LOG_FILE"
    return 0
  fi

  warn "Ollama did not respond at $OLLAMA_TAGS_URL after startup."
  if is_ollama_pid "$pid"; then
    warn "Stopping Ollama PID $pid that was started by KnowledgeForward."
    kill "$pid" >/dev/null 2>&1 || true
  fi
  rm -f "$OLLAMA_PID_FILE" "$OLLAMA_MARKER_FILE"
  die "Ollama failed to start. Check $OLLAMA_LOG_FILE. If port 11434 is already in use, inspect that process manually."
}

check_ollama() {
  remove_stale_ollama_state
  start_ollama
  check_ollama_model
}

check_tailscale() {
  local status_output

  command -v tailscale >/dev/null 2>&1 || die "Tailscale CLI is not available in PATH."
  if ! status_output="$(tailscale status 2>&1)"; then
    printf '%s\n' "$status_output" >&2
    die "tailscale status failed."
  fi
  if printf '%s\n' "$status_output" | grep -Eqi 'failed to load preferences|failed to start'; then
    printf '%s\n' "$status_output" >&2
    die "tailscale status did not complete successfully."
  fi
  info "tailscale status succeeded."
}

wait_for_knowledgeforward() {
  local code

  for _ in $(seq 1 30); do
    code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 1 "$HEALTH_URL" 2>/dev/null || true)"
    if [ "$code" = "401" ]; then
      return 0
    fi
    sleep 1
  done
  return 1
}

ensure_not_already_running() {
  local pid=""
  local existing_pids
  local port_pid
  local command_line

  if [ -f "$PID_FILE" ]; then
    pid="$(head -n 1 "$PID_FILE" 2>/dev/null | tr -d '[:space:]')"
    if is_knowledgeforward_pid "$pid"; then
      info "KnowledgeForward is already running with PID $pid."
      return 0
    fi
    if [ -n "${pid:-}" ] && kill -0 "$pid" >/dev/null 2>&1; then
      die "$PID_FILE points to PID $pid, but it is not a KnowledgeForward uvicorn process."
    fi
    warn "Removing stale PID file: $PID_FILE"
    rm -f "$PID_FILE"
  fi

  existing_pids="$(port_pids)"
  for port_pid in $existing_pids; do
    if is_knowledgeforward_pid "$port_pid"; then
      mkdir -p "$(dirname "$PID_FILE")"
      printf '%s\n' "$port_pid" > "$PID_FILE"
      info "KnowledgeForward is already listening on ${HOST}:${PORT} with PID $port_pid."
      return 0
    fi
    command_line="$(ps -p "$port_pid" -o command= 2>/dev/null || true)"
    die "Port ${HOST}:${PORT} is already in use by PID $port_pid: $command_line"
  done

  return 1
}

start_knowledgeforward() {
  local pid

  if ensure_not_already_running; then
    return 0
  fi

  mkdir -p "$(dirname "$PID_FILE")" "$(dirname "$LOG_FILE")"
  touch "$LOG_FILE"

  info "Starting KnowledgeForward on ${HOST}:${PORT}."
  cd "$REPO_ROOT"
  nohup "$PYTHON" -m uvicorn knowledge_forward.api:app --host "$HOST" --port "$PORT" >> "$LOG_FILE" 2>&1 &
  pid="$!"
  printf '%s\n' "$pid" > "$PID_FILE"

  if wait_for_knowledgeforward; then
    info "KnowledgeForward started with PID $pid."
    info "Log file: $LOG_FILE"
    return 0
  fi

  warn "KnowledgeForward did not become healthy. Stopping PID $pid."
  kill "$pid" >/dev/null 2>&1 || true
  rm -f "$PID_FILE"
  die "KnowledgeForward failed to start. Check $LOG_FILE for details."
}

enable_tailscale_serve() {
  local serve_output

  info "About to run: tailscale serve --bg localhost:8765"
  if ! serve_output="$(tailscale serve --bg localhost:8765 2>&1)"; then
    printf '%s\n' "$serve_output" >&2
    die "Failed to enable Tailscale Serve. No foreground serve process was left running."
  fi
  if printf '%s\n' "$serve_output" | grep -Eqi 'failed to load preferences|failed to start'; then
    printf '%s\n' "$serve_output" >&2
    die "Failed to enable Tailscale Serve. No foreground serve process was left running."
  fi
  [ -z "$serve_output" ] || printf '%s\n' "$serve_output"
  info "Tailscale Serve is configured for tailnet-only access to localhost:8765."
}

main() {
  ensure_repo_root
  resolve_runtime_env
  check_virtualenv
  check_dependencies
  check_config
  check_ollama
  start_knowledgeforward
  check_tailscale
  enable_tailscale_serve
  info "Done. Run ./knowledgeforward status to see the iPhone URL if Tailscale reports one."
}

main "$@"
