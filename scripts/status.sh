#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
PYTHON="$REPO_ROOT/.venv/bin/python"
PORT="8765"
HEALTH_URL="http://127.0.0.1:${PORT}/health"
OLLAMA_TAGS_URL="http://127.0.0.1:11434/api/tags"

# shellcheck disable=SC1091
source "$SCRIPT_DIR/runtime_env.sh"

section() {
  printf '\n== %s ==\n' "$*"
}

status_line() {
  printf '%-34s %s\n' "$1" "$2"
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

tailscale_output_failed() {
  local output="$1"
  printf '%s\n' "$output" | grep -Eqi 'failed to load preferences|failed to start'
}

show_knowledgeforward_process() {
  local pid=""
  local port_pid
  local found=0

  if [ -f "$PID_FILE" ]; then
    pid="$(head -n 1 "$PID_FILE" 2>/dev/null | tr -d '[:space:]')"
    if is_knowledgeforward_pid "$pid"; then
      status_line "PID file" "$PID_FILE -> running PID $pid"
      found=1
    else
      status_line "PID file" "$PID_FILE -> stale or not KnowledgeForward"
    fi
  else
    status_line "PID file" "missing ($PID_FILE)"
  fi

  for port_pid in $(port_pids); do
    if is_knowledgeforward_pid "$port_pid"; then
      status_line "Port 127.0.0.1:${PORT}" "KnowledgeForward listening with PID $port_pid"
      found=1
    else
      status_line "Port 127.0.0.1:${PORT}" "occupied by non-KnowledgeForward PID $port_pid"
    fi
  done

  if [ "$found" -eq 0 ]; then
    status_line "KnowledgeForward process" "not running"
  fi
}

show_health() {
  local unauth_code
  local auth_code

  unauth_code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 2 "$HEALTH_URL" 2>/dev/null || true)"
  if [ "$unauth_code" = "401" ]; then
    status_line "Unauthenticated /health" "OK, rejected with 401"
  elif [ -z "$unauth_code" ] || [ "$unauth_code" = "000" ]; then
    status_line "Unauthenticated /health" "no response"
  else
    status_line "Unauthenticated /health" "unexpected HTTP $unauth_code"
  fi

  if [ ! -x "$PYTHON" ]; then
    status_line "Authenticated /health" ".venv Python not found"
    return 0
  fi

  auth_code="$("$PYTHON" - <<'PY'
import sys
import urllib.error
import urllib.request

from knowledge_forward.config import load_config

try:
    config = load_config()
    request = urllib.request.Request(
        "http://127.0.0.1:8765/health",
        headers={"Authorization": "Bearer " + config.auth.token},
    )
    with urllib.request.urlopen(request, timeout=2) as response:
        print(response.status)
except urllib.error.HTTPError as exc:
    print(exc.code)
except Exception as exc:
    print("ERROR:" + exc.__class__.__name__)
PY
)"
  if [ "$auth_code" = "200" ]; then
    status_line "Authenticated /health" "OK, token accepted"
  else
    status_line "Authenticated /health" "failed ($auth_code)"
  fi
}

show_loaded_ollama_models() {
  local loaded_output=""
  local loaded_models=""

  if ! command -v ollama >/dev/null 2>&1; then
    status_line "Loaded Ollama models" "not checked; ollama command not found"
    return 0
  fi

  if loaded_output="$(ollama ps 2>&1)"; then
    loaded_models="$(printf '%s\n' "$loaded_output" | awk 'NR > 1 && $1 != "" && $1 != "NAME" { if (out) out=out ", " $1; else out=$1 } END { print out }')"
    if [ -n "$loaded_models" ]; then
      status_line "Loaded Ollama models" "$loaded_models"
    else
      status_line "Loaded Ollama models" "none reported by ollama ps"
    fi
  else
    status_line "Loaded Ollama models" "ollama ps failed"
    printf '%s\n' "$loaded_output"
  fi
}

show_ollama() {
  local pid=""
  local model_status=""
  local model_state=""
  local model_detail=""

  if curl -fsS --max-time 2 "$OLLAMA_TAGS_URL" >/dev/null 2>&1; then
    status_line "Ollama localhost:11434" "responding"
  else
    status_line "Ollama localhost:11434" "no response"
  fi

  if [ -f "$OLLAMA_MARKER_FILE" ]; then
    status_line "Ollama management" "managed by KnowledgeForward"
  else
    status_line "Ollama management" "external / already running / not managed"
  fi

  if [ -f "$OLLAMA_PID_FILE" ]; then
    pid="$(head -n 1 "$OLLAMA_PID_FILE" 2>/dev/null | tr -d '[:space:]')"
    if is_ollama_pid "$pid"; then
      status_line "Ollama PID file" "$OLLAMA_PID_FILE -> running PID $pid"
    else
      status_line "Ollama PID file" "$OLLAMA_PID_FILE -> stale or not ollama serve"
    fi
  else
    status_line "Ollama PID file" "missing ($OLLAMA_PID_FILE)"
  fi

  if ! curl -fsS --max-time 2 "$OLLAMA_TAGS_URL" >/dev/null 2>&1; then
    status_line "Ollama model" "not checked because Ollama is not responding"
    status_line "Loaded Ollama models" "not checked because Ollama is not responding"
    return 0
  fi
  if [ ! -x "$PYTHON" ]; then
    status_line "Ollama model" ".venv Python not found"
    show_loaded_ollama_models
    return 0
  fi

  model_status="$("$PYTHON" - <<'PY'
import json
import sys
import urllib.error
import urllib.request

from knowledge_forward.config import ConfigError, load_config


def matches_model(requested: str, available: set[str]) -> bool:
    return requested in available or (":" not in requested and f"{requested}:latest" in available)


try:
    config = load_config()
except ConfigError:
    print("CONFIG_ERROR\tconfig file could not be validated")
    sys.exit(0)

try:
    with urllib.request.urlopen(config.ollama.base_url.rstrip("/") + "/api/tags", timeout=2) as response:
        payload = json.loads(response.read().decode("utf-8"))
except (OSError, urllib.error.URLError, json.JSONDecodeError):
    print("UNAVAILABLE\tcould not read /api/tags")
    sys.exit(0)

available: set[str] = set()
for item in payload.get("models", []):
    if not isinstance(item, dict):
        continue
    for key in ("name", "model"):
        value = str(item.get(key, "")).strip()
        if value:
            available.add(value)

if matches_model(config.ollama.model, available):
    print(f"AVAILABLE\t{config.ollama.model}")
else:
    print(f"MISSING\t{config.ollama.model}")
PY
)"
  model_state="${model_status%%$'\t'*}"
  model_detail="${model_status#*$'\t'}"
  case "$model_state" in
    AVAILABLE)
      status_line "Ollama model" "available ($model_detail)"
      ;;
    MISSING)
      status_line "Ollama model" "missing ($model_detail); run: ollama pull $model_detail"
      ;;
    CONFIG_ERROR)
      status_line "Ollama model" "not checked ($model_detail)"
      ;;
    *)
      status_line "Ollama model" "not checked ($model_detail)"
      ;;
  esac

  show_loaded_ollama_models
}

show_tailscale() {
  local output
  local serve_output=""
  local funnel_output=""
  local iphone_url=""
  local serve_status_ok=0

  if ! command -v tailscale >/dev/null 2>&1; then
    status_line "Tailscale CLI" "not found"
    return 0
  fi
  status_line "Tailscale CLI" "$(command -v tailscale)"

  if output="$(tailscale status 2>&1)"; then
    if tailscale_output_failed "$output"; then
      status_line "tailscale status" "failed"
      printf '%s\n' "$output"
    else
      status_line "tailscale status" "OK"
      printf '%s\n' "$output" | sed -n '1,12p'
    fi
  else
    status_line "tailscale status" "failed"
    printf '%s\n' "$output"
  fi

  if serve_output="$(tailscale serve status 2>&1)" && ! tailscale_output_failed "$serve_output"; then
    serve_status_ok=1
    status_line "tailscale serve status" "available"
    [ -z "$serve_output" ] && printf '(no serve status output)\n' || printf '%s\n' "$serve_output"
  else
    status_line "tailscale serve status" "failed"
    printf '%s\n' "$serve_output"
  fi

  if funnel_output="$(tailscale funnel status 2>&1)" && ! tailscale_output_failed "$funnel_output"; then
    status_line "tailscale funnel status" "checked only; not modified"
    [ -z "$funnel_output" ] && printf '(no funnel status output)\n' || printf '%s\n' "$funnel_output"
  else
    status_line "tailscale funnel status" "check failed; not modified"
    printf '%s\n' "$funnel_output"
  fi

  iphone_url="$(printf '%s\n' "$serve_output" | grep -Eo 'https?://[^[:space:]]+' | grep -Ev '127\.0\.0\.1|localhost' | head -n 1 || true)"
  if [ -n "$iphone_url" ]; then
    status_line "iPhone URL" "$iphone_url"
  elif [ "$serve_status_ok" -eq 0 ]; then
    status_line "iPhone URL" "unavailable because tailscale serve status failed"
  else
    status_line "iPhone URL" "not found; Serve may be disabled or the status output has no URL"
  fi
}

show_git_safety() {
  local git_status

  status_line "Runtime config" "$CONFIG_PATH"
  status_line "Runtime home" "$RUNTIME_HOME"

  if [ "$RUNTIME_IS_EXTERNAL" = "1" ]; then
    if path_is_inside_repo "$CONFIG_PATH" || path_is_inside_repo "$RUNTIME_HOME"; then
      status_line "Runtime location" "inside repository directory (should be outside)"
    else
      status_line "Runtime location" "external"
    fi
  else
    status_line "Runtime location" "legacy repo-local (prefer KNOWLEDGE_FORWARD_HOME outside repo)"
  fi

  if git ls-files --error-unmatch config.yaml >/dev/null 2>&1; then
    status_line "repo config.yaml Git state" "TRACKED (should be untracked)"
  elif git check-ignore -q config.yaml; then
    status_line "repo config.yaml Git state" "untracked and ignored"
  else
    status_line "repo config.yaml Git state" "untracked but not ignored"
  fi

  if [ -f "$REPO_ROOT/config.yaml" ] || [ -d "$REPO_ROOT/data" ] || [ -d "$REPO_ROOT/tmp" ]; then
    status_line "Repo-local runtime files" "present; do not publish by folder copy"
  else
    status_line "Repo-local runtime files" "absent"
  fi

  if git ls-files -- tmp/private_test_vault | grep -q .; then
    status_line "tmp/private_test_vault Git state" "TRACKED (should be untracked)"
  elif git check-ignore -q tmp/private_test_vault; then
    status_line "tmp/private_test_vault Git state" "untracked and ignored"
  else
    status_line "tmp/private_test_vault Git state" "untracked but not ignored"
  fi

  section "git status --short"
  git_status="$(git status --short)"
  [ -z "$git_status" ] && printf '(clean)\n' || printf '%s\n' "$git_status"
}

show_allowed_sources() {
  if [ ! -x "$PYTHON" ]; then
    status_line "allowed_sources" ".venv Python not found"
    return 0
  fi

  "$PYTHON" - <<'PY'
import sys

from knowledge_forward.config import ConfigError, load_config
from knowledge_forward.source_safety import safe_source_status_lines

try:
    config = load_config()
except ConfigError:
    print("allowed_sources\tconfig file could not be validated")
    sys.exit(0)

lines = safe_source_status_lines(config)
if not lines:
    print("allowed_sources\tnone configured")
else:
    for line in lines:
        print(line)
PY
}

main() {
  cd "$REPO_ROOT"
  resolve_runtime_env
  section "KnowledgeForward"
  show_knowledgeforward_process
  show_health
  section "Ollama"
  show_ollama
  section "Tailscale"
  show_tailscale
  section "Allowed Sources"
  show_allowed_sources
  section "Local Safety"
  show_git_safety
}

main "$@"
