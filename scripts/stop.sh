#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
PYTHON="$REPO_ROOT/.venv/bin/python"
PID_FILE="$REPO_ROOT/tmp/run/knowledgeforward.pid"
PORT="8765"
OLLAMA_TAGS_URL="http://127.0.0.1:11434/api/tags"

info() {
  printf 'INFO: %s\n' "$*"
}

warn() {
  printf 'WARN: %s\n' "$*" >&2
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

port_pids() {
  command -v lsof >/dev/null 2>&1 || return 0
  lsof -nP -iTCP:"$PORT" -sTCP:LISTEN -t 2>/dev/null || true
}

tailscale_output_failed() {
  local output="$1"
  printf '%s\n' "$output" | grep -Eqi 'failed to load preferences|failed to start'
}

stop_pid() {
  local pid="$1"

  if ! is_knowledgeforward_pid "$pid"; then
    warn "PID $pid is not a KnowledgeForward uvicorn process; leaving it untouched."
    return 1
  fi

  info "Stopping KnowledgeForward PID $pid."
  kill "$pid" >/dev/null 2>&1 || true
  for _ in $(seq 1 10); do
    if ! kill -0 "$pid" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done

  warn "PID $pid did not stop after SIGTERM; sending SIGKILL."
  kill -KILL "$pid" >/dev/null 2>&1 || true
}

stop_knowledgeforward() {
  local pid
  local port_pid
  local stopped=0

  if [ -f "$PID_FILE" ]; then
    pid="$(head -n 1 "$PID_FILE" 2>/dev/null | tr -d '[:space:]')"
    if [ -n "${pid:-}" ]; then
      if stop_pid "$pid"; then
        stopped=1
      fi
    fi
    rm -f "$PID_FILE"
  else
    info "PID file does not exist: $PID_FILE"
  fi

  for port_pid in $(port_pids); do
    if is_knowledgeforward_pid "$port_pid"; then
      if stop_pid "$port_pid"; then
        stopped=1
      fi
    else
      warn "Port 127.0.0.1:${PORT} is used by PID $port_pid, but it is not KnowledgeForward; leaving it untouched."
    fi
  done

  if [ "$stopped" -eq 0 ]; then
    info "No KnowledgeForward process was stopped."
  fi
}

disable_tailscale_serve() {
  local output

  if ! command -v tailscale >/dev/null 2>&1; then
    warn "Tailscale CLI is not available; cannot remove Serve config."
    return 0
  fi

  info "About to run: tailscale serve --bg localhost:8765 off"
  if output="$(tailscale serve --bg localhost:8765 off 2>&1)" && ! tailscale_output_failed "$output"; then
    [ -z "$output" ] || printf '%s\n' "$output"
  else
    printf '%s\n' "$output" >&2
    warn "Targeted Serve disable failed; trying without --bg."
    info "About to run: tailscale serve localhost:8765 off"
    if output="$(tailscale serve localhost:8765 off 2>&1)" && ! tailscale_output_failed "$output"; then
      [ -z "$output" ] || printf '%s\n' "$output"
    else
      printf '%s\n' "$output" >&2
      warn "Targeted Serve disable failed."
      # This reset is only a fallback for removing KnowledgeForward's Serve config after the
      # targeted documented off commands are rejected. It may clear every Serve setting
      # on this node, so the script prints that risk before running it.
      warn "Fallback will run 'tailscale serve reset'; this may remove all Tailscale Serve settings on this node, not only KnowledgeForward."
      info "About to run: tailscale serve reset"
      if output="$(tailscale serve reset 2>&1)" && ! tailscale_output_failed "$output"; then
        [ -z "$output" ] || printf '%s\n' "$output"
      else
        printf '%s\n' "$output" >&2
        warn "Could not remove Tailscale Serve config automatically."
      fi
    fi
  fi

  info "tailscale serve status:"
  if output="$(tailscale serve status 2>&1)"; then
    [ -z "$output" ] && printf '(no serve status output)\n' || printf '%s\n' "$output"
  else
    printf '%s\n' "$output" >&2
    warn "tailscale serve status failed."
  fi
}

read_configured_ollama_model() {
  if [ ! -f "$REPO_ROOT/config.yaml" ]; then
    warn "config.yaml is missing; skipping Ollama model unload."
    return 1
  fi
  if [ ! -x "$PYTHON" ]; then
    warn "Python executable not found at $PYTHON; skipping Ollama model unload."
    return 1
  fi

  "$PYTHON" - <<'PY'
import sys
import yaml

try:
    raw = yaml.safe_load(open("config.yaml", encoding="utf-8")) or {}
except Exception:
    print("Could not read config.yaml.", file=sys.stderr)
    sys.exit(1)

ollama = raw.get("ollama") or {}
if not isinstance(ollama, dict):
    print("config.yaml ollama section is not a mapping.", file=sys.stderr)
    sys.exit(1)

model = str(ollama.get("model", "llama3.2")).strip()
if not model:
    print("config.yaml ollama.model is empty.", file=sys.stderr)
    sys.exit(1)

print(model)
PY
}

unload_configured_ollama_model() {
  local model
  local output

  if [ "${KNOWLEDGE_FORWARD_SKIP_MODEL_UNLOAD:-}" = "1" ]; then
    info "Skipping Ollama model unload because KNOWLEDGE_FORWARD_SKIP_MODEL_UNLOAD=1."
    return 0
  fi

  if ! command -v ollama >/dev/null 2>&1; then
    warn "Ollama CLI is not available; skipping model unload."
    return 0
  fi

  if ! curl -fsS --max-time 2 "$OLLAMA_TAGS_URL" >/dev/null 2>&1; then
    warn "Ollama is not responding at $OLLAMA_TAGS_URL; skipping model unload."
    return 0
  fi

  if ! model="$(read_configured_ollama_model 2>/dev/null)"; then
    warn "Could not read config.yaml ollama.model; skipping model unload."
    return 0
  fi

  info "Unloading configured Ollama model: $model"
  if output="$(ollama stop "$model" 2>&1)"; then
    [ -z "$output" ] || printf '%s\n' "$output"
    info "Ollama model unload requested."
    return 0
  fi

  if printf '%s\n' "$output" | grep -Eqi 'not loaded|not running|no loaded|not found|does not exist'; then
    [ -z "$output" ] || printf '%s\n' "$output"
    info "Ollama model is already unloaded or unavailable; continuing."
    return 0
  fi

  printf '%s\n' "$output" >&2
  warn "Could not unload Ollama model $model; continuing."
  return 0
}

main() {
  cd "$REPO_ROOT"
  stop_knowledgeforward
  disable_tailscale_serve
  unload_configured_ollama_model
}

main "$@"
