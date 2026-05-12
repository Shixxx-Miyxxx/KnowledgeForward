#!/usr/bin/env bash
set -euo pipefail

issue_count=0

report_issue() {
  local kind="$1"
  local file="$2"
  local line="${3:-}"

  issue_count=$((issue_count + 1))
  if [ -n "$line" ]; then
    printf 'ERROR: %s at %s:%s\n' "$kind" "$file" "$line"
  else
    printf 'ERROR: %s at %s\n' "$kind" "$file"
  fi
}

tracked_path_exists() {
  git ls-files -- "$1" | grep -q .
}

check_untracked_path() {
  local path="$1"
  local kind="$2"

  if tracked_path_exists "$path"; then
    while IFS= read -r file; do
      report_issue "$kind tracked" "$file"
    done < <(git ls-files -- "$path")
  fi
}

check_tracked_filename_pattern() {
  local kind="$1"
  local pattern="$2"

  while IFS= read -r file; do
    [ -n "${file:-}" ] || continue
    report_issue "$kind tracked" "$file"
  done < <(git ls-files | grep -E "$pattern" || true)
}

is_allowed_credential_line() {
  local file="$1"
  local text="$2"

  case "$text" in
    *"<token>"*|*"<your-token>"*|*"safe-test-token"*|*"prompt-injection-token"*|*"test-token"*)
      return 0
      ;;
    *"outside-only-token"*|*"symlink-only-token"*|*"included-token"*|*"replace-with-a-long-random-token"*)
      return 0
      ;;
    *"change-me-local-token"*|*"binarysecret"*|*"excludedsecret"*|*"nodesecret"*|*"injectiondummy"*)
      return 0
      ;;
    *"Bearer \${tokenInput.value}"*)
      return 0
      ;;
  esac

  case "$file" in
    scripts/security_check.sh)
      case "$text" in
        *"scan_tracked_text "*)
          return 0
          ;;
      esac
      ;;
    README.md)
      case "$text" in
        *"Authorization: Bearer"*|*"auth.token"*|*"Token"*|*"tokenizer"*|*"secrets.token_urlsafe"*)
          return 0
          ;;
      esac
      ;;
  esac

  return 1
}

scan_tracked_text() {
  local kind="$1"
  local pattern="$2"
  local grep_flag="${3:-}"

  while IFS=: read -r file line text; do
    [ -n "${file:-}" ] || continue
    if is_allowed_credential_line "$file" "${text:-}"; then
      continue
    fi
    report_issue "$kind" "$file" "$line"
  done < <(
    if [ -n "$grep_flag" ]; then
      git grep -nI -E "$grep_flag" "$pattern" || true
    else
      git grep -nI -E "$pattern" || true
    fi
  )
}

is_allowed_path_line() {
  local file="$1"
  local text="$2"

  case "$file" in
    scripts/security_check.sh)
      case "$text" in
        *"scan_tracked_path_text "*)
          return 0
          ;;
      esac
      ;;
    README.md|fixtures/sample_vault/*)
      case "$text" in
        *"Obsidian Vault"*|*"サンプルVault"*|*"テストVault"*|*"sample_vault"*)
          return 0
          ;;
      esac
      ;;
    tests/*)
      case "$text" in
        *"tmp_path"*|*"小さなVault"*|*"vault"*|*"Vault"*)
          return 0
          ;;
      esac
      ;;
  esac

  return 1
}

scan_tracked_path_text() {
  local kind="$1"
  local pattern="$2"

  while IFS=: read -r file line text; do
    [ -n "${file:-}" ] || continue
    if is_allowed_path_line "$file" "${text:-}"; then
      continue
    fi
    report_issue "$kind" "$file" "$line"
  done < <(git grep -nI -E "$pattern" || true)
}

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  printf 'ERROR: not inside a Git work tree\n'
  exit 1
fi

check_untracked_path "config.yaml" "local config"
check_untracked_path "data" "local data directory"
check_untracked_path "tmp" "temporary directory"
check_untracked_path ".venv" "virtualenv directory"
check_tracked_filename_pattern "SQLite database" '(^|/)[^/]+\.(sqlite|sqlite3|db)(-(shm|wal))?$'
check_tracked_filename_pattern "dotenv file" '(^|/)\.env($|[.])'
check_tracked_filename_pattern "private key-like file" '(^|/)(id_rsa|id_dsa|id_ecdsa|id_ed25519|identity)$'
check_tracked_filename_pattern "private key-like file" '(^|/).*\.(pem|key|p12|pfx)$'
check_tracked_filename_pattern "credential-like file" '(^|/)(secrets?|credentials?)([._-].*)?$'

scan_tracked_text "credential: private key block" 'BEGIN (RSA|OPENSSH|.*PRIVATE KEY)'
scan_tracked_text "credential: SSH public key" 'ssh-rsa[[:space:]]+[A-Za-z0-9+/=]{80,}'
scan_tracked_text "credential: AWS access key" '(AKIA|ASIA)[0-9A-Z]{16}'
scan_tracked_text "credential: Google API key" 'AIza[0-9A-Za-z_-]{35}'
scan_tracked_text "credential: GitHub token" '(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{30,}'
scan_tracked_text "credential: GitHub fine-grained token" 'github_pat_[A-Za-z0-9_]{20,}'
scan_tracked_text "credential: Slack token" 'xox[baprs]-[A-Za-z0-9-]{20,}'
scan_tracked_text "credential: OpenAI-style key" 'sk-[A-Za-z0-9_-]{20,}'
scan_tracked_text "credential: bearer token literal" 'Authorization:[^[:cntrl:]]*Bearer[[:space:]]+[A-Za-z0-9._~+/=-]{16,}'
scan_tracked_text "credential: generic YAML secret value" '^[[:space:]]*(token|secret|password|api[_-]?key|apikey):[[:space:]]*["'\'']?[A-Za-z0-9_./+=-]{24,}' "-i"
scan_tracked_text "credential: generic quoted secret assignment" '(token|secret|password|api[_-]?key|apikey)[[:space:]]*=[[:space:]]*["'\''][A-Za-z0-9_./+=-]{24,}["'\'']' "-i"

home_path_prefix='/'"Users"'/'
project_docs_path='Documents/'"10_projects"

scan_tracked_path_text "local path: home directory" "${home_path_prefix}"'[^[:space:]")'\'']+'
scan_tracked_path_text "local path: iCloud" '(Mobile Documents|iCloud Drive|iCloud)'
scan_tracked_path_text "local path: project docs" "$project_docs_path"
scan_tracked_path_text "local path: vault-like absolute path" '/[^[:space:]")'\'']*(Obsidian|Vault)[^[:space:]")'\'']*'
scan_tracked_path_text "local path: vault-like config path" 'path:[[:space:]]*[^#]*(Obsidian|Vault|Mobile Documents|iCloud|'"${home_path_prefix}"')'

if [ "$issue_count" -gt 0 ]; then
  printf 'Security check failed with %s issue(s).\n' "$issue_count"
  exit 1
fi

printf 'Security check passed.\n'
