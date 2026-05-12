from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import secrets
import shlex
import shutil
from typing import Iterable

from .config import CONFIG_PATH_ENV, RUNTIME_HOME_ENV, resolve_config_path


@dataclass(frozen=True)
class RuntimePaths:
    repo_root: Path
    config_path: Path
    runtime_home: Path
    run_dir: Path
    logs_dir: Path
    data_dir: Path
    pid_file: Path
    log_file: Path
    ollama_pid_file: Path
    ollama_marker_file: Path
    ollama_log_file: Path
    is_external: bool
    config_source: str


@dataclass(frozen=True)
class InitRuntimeResult:
    runtime_home: Path
    config_path: Path
    created: tuple[Path, ...]
    skipped: tuple[Path, ...]
    warnings: tuple[str, ...]


def resolve_runtime_paths(repo_root: str | Path, config_path: str | Path | None = None) -> RuntimePaths:
    repo = Path(repo_root).expanduser().resolve()
    env_home = os.environ.get(RUNTIME_HOME_ENV, "").strip()
    env_config = os.environ.get(CONFIG_PATH_ENV, "").strip()
    resolved_config = resolve_config_path(config_path)
    config_source = _config_source(config_path, env_config, env_home)
    is_external = config_source != "legacy"

    if env_home:
        runtime_home = Path(env_home).expanduser().resolve()
    elif config_source in {"argument", "env_config"}:
        runtime_home = resolved_config.parent
    else:
        runtime_home = repo / "tmp"

    run_dir = runtime_home / "run"
    logs_dir = runtime_home / "logs"
    data_dir = runtime_home / "data" if is_external else repo / "data"
    return RuntimePaths(
        repo_root=repo,
        config_path=resolved_config,
        runtime_home=runtime_home,
        run_dir=run_dir,
        logs_dir=logs_dir,
        data_dir=data_dir,
        pid_file=run_dir / "knowledgeforward.pid",
        log_file=logs_dir / "knowledgeforward.log",
        ollama_pid_file=run_dir / "ollama.pid",
        ollama_marker_file=run_dir / "ollama.managed",
        ollama_log_file=logs_dir / "ollama.log",
        is_external=is_external,
        config_source=config_source,
    )


def init_runtime(target: str | Path, repo_root: str | Path) -> InitRuntimeResult:
    repo = Path(repo_root).expanduser().resolve()
    runtime_home = Path(target).expanduser().resolve()
    if runtime_home == repo or _is_relative_to(runtime_home, repo):
        raise ValueError("Runtime home must be outside the public repository.")

    created: list[Path] = []
    skipped: list[Path] = []
    warnings: list[str] = []

    _mkdir(runtime_home, created)
    for directory in (runtime_home / "data", runtime_home / "logs", runtime_home / "run"):
        _mkdir(directory, created)

    gitignore = runtime_home / ".gitignore"
    if gitignore.exists():
        skipped.append(gitignore)
    else:
        gitignore.write_text("config.yaml\ndata/\nlogs/\nrun/\n.DS_Store\n", encoding="utf-8")
        created.append(gitignore)

    sample_source = repo / "fixtures" / "sample_vault"
    sample_target = runtime_home / "sample_vault"
    if sample_target.exists():
        skipped.append(sample_target)
    else:
        shutil.copytree(sample_source, sample_target)
        created.append(sample_target)

    config_path = runtime_home / "config.yaml"
    if config_path.exists():
        skipped.append(config_path)
    else:
        token = secrets.token_urlsafe(32)
        config_path.write_text(_runtime_config_text(token), encoding="utf-8")
        created.append(config_path)

    remote_warning = _git_remote_warning(runtime_home)
    if remote_warning:
        warnings.append(remote_warning)

    return InitRuntimeResult(
        runtime_home=runtime_home,
        config_path=config_path,
        created=tuple(created),
        skipped=tuple(skipped),
        warnings=tuple(warnings),
    )


def shell_env_lines(paths: RuntimePaths) -> tuple[str, ...]:
    values = {
        "CONFIG_PATH": paths.config_path,
        "RUNTIME_HOME": paths.runtime_home,
        "RUNTIME_RUN_DIR": paths.run_dir,
        "RUNTIME_LOGS_DIR": paths.logs_dir,
        "RUNTIME_DATA_DIR": paths.data_dir,
        "PID_FILE": paths.pid_file,
        "LOG_FILE": paths.log_file,
        "OLLAMA_PID_FILE": paths.ollama_pid_file,
        "OLLAMA_MARKER_FILE": paths.ollama_marker_file,
        "OLLAMA_LOG_FILE": paths.ollama_log_file,
        "RUNTIME_IS_EXTERNAL": "1" if paths.is_external else "0",
        "RUNTIME_CONFIG_SOURCE": paths.config_source,
    }
    return tuple(f"{key}={shlex.quote(str(value))}" for key, value in values.items())


def _config_source(config_path: str | Path | None, env_config: str, env_home: str) -> str:
    if config_path is not None:
        return "argument"
    if env_config:
        return "env_config"
    if env_home:
        return "env_home"
    return "legacy"


def _mkdir(path: Path, created: list[Path]) -> None:
    if path.exists():
        return
    path.mkdir(parents=True, exist_ok=True)
    created.append(path)


def _runtime_config_text(token: str) -> str:
    return f"""server:
  host: 127.0.0.1
  port: 8765

auth:
  token: {token}

database:
  path: ./data/knowledgeforward.sqlite3

ollama:
  base_url: http://127.0.0.1:11434
  model: llama3.2
  timeout_seconds: 180
  temperature: 0.2
  hide_thinking: true

indexing:
  max_file_bytes: 1048576
  chunk_max_chars: 1400
  chunk_overlap_chars: 160
  excluded_dirs:
    - .git
    - .obsidian
    - node_modules
    - attachments
    - .venv
    - venv
    - __pycache__
  markdown_extensions:
    - .md
    - .markdown

allowed_sources:
  - name: sample_vault
    path: ./sample_vault
    type: obsidian
    enabled: true
    require_query_filter: true
    default_query_days: 30
"""


def _git_remote_warning(path: Path) -> str | None:
    git_dir = _git_dir(path)
    if git_dir is None:
        return None
    config_path = git_dir / "config"
    if config_path.exists() and "[remote " in config_path.read_text(encoding="utf-8", errors="replace"):
        return "Runtime target is a Git worktree with a remote; no remote was changed."
    return None


def _git_dir(path: Path) -> Path | None:
    git_entry = path / ".git"
    if git_entry.is_dir():
        return git_entry
    if not git_entry.is_file():
        return None
    first_line = git_entry.read_text(encoding="utf-8", errors="replace").splitlines()[0:1]
    if not first_line or not first_line[0].startswith("gitdir:"):
        return None
    git_dir = Path(first_line[0].removeprefix("gitdir:").strip()).expanduser()
    if not git_dir.is_absolute():
        git_dir = path / git_dir
    return git_dir.resolve()


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _print_lines(lines: Iterable[str]) -> None:
    for line in lines:
        print(line)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m knowledge_forward.runtime")
    subparsers = parser.add_subparsers(dest="command", required=True)

    shell_parser = subparsers.add_parser("shell-env")
    shell_parser.add_argument("--repo-root", required=True)

    init_parser = subparsers.add_parser("init-runtime")
    init_parser.add_argument("path")
    init_parser.add_argument("--repo-root", required=True)

    args = parser.parse_args(argv)
    if args.command == "shell-env":
        _print_lines(shell_env_lines(resolve_runtime_paths(args.repo_root)))
        return 0
    if args.command == "init-runtime":
        try:
            result = init_runtime(args.path, args.repo_root)
        except ValueError as exc:
            print(f"ERROR: {exc}")
            return 1
        print(f"Runtime home: {result.runtime_home}")
        print(f"Config file: {result.config_path}")
        for path in result.created:
            print(f"Created: {path}")
        for path in result.skipped:
            print(f"Skipped existing: {path}")
        for warning in result.warnings:
            print(f"WARN: {warning}")
        print("Set KNOWLEDGE_FORWARD_HOME to this runtime home before start/status/stop.")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
