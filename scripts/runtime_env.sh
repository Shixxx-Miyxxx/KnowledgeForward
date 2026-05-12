# shellcheck shell=bash

resolve_runtime_env() {
  local runtime_python
  local output

  runtime_python="$PYTHON"
  if [ ! -x "$runtime_python" ]; then
    runtime_python="python3"
  fi

  output="$("$runtime_python" -m knowledge_forward.runtime shell-env --repo-root "$REPO_ROOT")"
  eval "$output"
  export KNOWLEDGE_FORWARD_CONFIG="$CONFIG_PATH"
}

path_is_inside_repo() {
  local path="$1"
  case "$path" in
    "$REPO_ROOT"|"$REPO_ROOT"/*)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}
