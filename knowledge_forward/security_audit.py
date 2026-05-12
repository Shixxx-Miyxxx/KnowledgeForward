from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import shutil
import subprocess  # nosec B404
import sys
from typing import Iterable, Literal


SecurityProfile = Literal["quick", "full"]
SecurityStatus = Literal["pass", "warn", "fail", "skipped"]

MAX_DETAILS_CHARS = 1800
DEFAULT_TIMEOUT_SECONDS = 90
ANSI_ESCAPE_RE = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


@dataclass(frozen=True)
class SecurityCheckResult:
    name: str
    status: SecurityStatus
    summary: str
    details: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "status": self.status,
            "summary": self.summary,
            "details": self.details,
        }


def run_security_checks(
    repo_root: Path,
    profile: SecurityProfile = "quick",
    redaction_tokens: Iterable[str] = (),
) -> dict[str, object]:
    repo = repo_root.resolve()
    redactions = tuple(token for token in redaction_tokens if token)
    results = [_run_git_status(repo, redactions), _run_command_check(
        repo,
        "security-check",
        ["bash", "scripts/security_check.sh"],
        redactions,
        timeout_seconds=30,
    )]
    if profile == "full":
        results.extend(_run_full_checks(repo, redactions))

    fail_count = sum(1 for result in results if result.status == "fail")
    warn_count = sum(1 for result in results if result.status == "warn")
    skipped_count = sum(1 for result in results if result.status == "skipped")
    return {
        "ok": fail_count == 0,
        "profile": profile,
        "results": [result.to_dict() for result in results],
        "fail_count": fail_count,
        "warn_count": warn_count,
        "skipped_count": skipped_count,
    }


def format_security_report(report: dict[str, object]) -> str:
    lines = [
        f"Security audit ({report.get('profile', 'unknown')}): "
        f"fail={report.get('fail_count', 0)} / warn={report.get('warn_count', 0)} / "
        f"skipped={report.get('skipped_count', 0)}"
    ]
    for item in report.get("results", []):
        if not isinstance(item, dict):
            continue
        lines.append(f"- {item.get('status', 'unknown')}: {item.get('name', 'unknown')} - {item.get('summary', '')}")
        details = str(item.get("details", "")).strip()
        if details:
            lines.append(_indent(details))
    return "\n".join(lines)


def _run_full_checks(repo: Path, redaction_tokens: tuple[str, ...]) -> list[SecurityCheckResult]:
    checks: list[SecurityCheckResult] = [
        _run_command_check(repo, "make test", ["make", "test"], redaction_tokens, timeout_seconds=120),
    ]
    tool_checks = (
        ("pip-audit", "pip-audit", ["-r", "requirements.txt"], 120),
        ("bandit", "bandit", ["-r", "knowledge_forward", "-x", "tests"], 120),
        (
            "shellcheck",
            "shellcheck",
            ["scripts/start.sh", "scripts/stop.sh", "scripts/status.sh", "scripts/restart.sh", "scripts/security_check.sh"],
            60,
        ),
        ("gitleaks", "gitleaks", ["detect", "--source", ".", "--redact", "--log-opts=--all"], 120),
    )
    for name, tool, args, timeout_seconds in tool_checks:
        command = _tool_command(repo, tool)
        if command is None:
            checks.append(SecurityCheckResult(name, "skipped", f"{tool} is not installed."))
            continue
        checks.append(
            _run_command_check(
                repo,
                name,
                [*command, *args],
                redaction_tokens,
                timeout_seconds=timeout_seconds,
            )
        )
    return checks


def _run_git_status(repo: Path, redaction_tokens: tuple[str, ...]) -> SecurityCheckResult:
    completed = _run_command(repo, ["git", "status", "--short", "--untracked-files=all"], timeout_seconds=15)
    output = _redact(completed.output, redaction_tokens)
    if completed.returncode != 0:
        return SecurityCheckResult("git status", "fail", "git status failed.", _truncate(output))
    if not output.strip():
        return SecurityCheckResult("git status", "pass", "worktree is clean.")
    changed_count = len([line for line in output.splitlines() if line.strip()])
    return SecurityCheckResult("git status", "warn", f"worktree has {changed_count} change(s).", _truncate(output))


def _run_command_check(
    repo: Path,
    name: str,
    command: list[str],
    redaction_tokens: tuple[str, ...],
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> SecurityCheckResult:
    completed = _run_command(repo, command, timeout_seconds=timeout_seconds)
    output = _redact(completed.output, redaction_tokens)
    if completed.timed_out:
        return SecurityCheckResult(name, "fail", f"timed out after {timeout_seconds}s.", _truncate(output))
    if completed.returncode == 0:
        return SecurityCheckResult(name, "pass", _summary(output, "passed."), _truncate(output))
    return SecurityCheckResult(name, "fail", _summary(output, f"failed with exit code {completed.returncode}."), _truncate(output))


@dataclass(frozen=True)
class _CompletedCommand:
    returncode: int
    output: str
    timed_out: bool = False


def _run_command(repo: Path, command: list[str], timeout_seconds: int) -> _CompletedCommand:
    try:
        completed = subprocess.run(  # nosec B603
            command,
            cwd=repo,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except FileNotFoundError:
        return _CompletedCommand(127, f"Command not found: {command[0]}")
    except subprocess.TimeoutExpired as exc:
        output = _decode_timeout_output(exc.stdout) + _decode_timeout_output(exc.stderr)
        return _CompletedCommand(124, output, timed_out=True)
    return _CompletedCommand(completed.returncode, (completed.stdout or "") + (completed.stderr or ""))


def _tool_command(repo: Path, tool: str) -> list[str] | None:
    local_tool = repo / ".venv" / "bin" / tool
    if local_tool.exists() and local_tool.is_file():
        return [str(local_tool)]
    found = shutil.which(tool)
    return [found] if found else None


def _decode_timeout_output(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _redact(text: str, redaction_tokens: tuple[str, ...]) -> str:
    redacted = ANSI_ESCAPE_RE.sub("", text)
    for token in redaction_tokens:
        redacted = redacted.replace(token, "[redacted]")
    path_patterns = (
        re.compile("/" + "Users" + r"/[^\s\"'<>]+"),
        re.compile("/" + "private" + r"/[^\s\"'<>]+"),
        re.compile(r"[A-Za-z]:\\[^\s\"'<>]+"),
    )
    for pattern in path_patterns:
        redacted = pattern.sub("[local path]", redacted)
    return redacted


def _summary(output: str, default: str) -> str:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if not lines:
        return default
    return _truncate(lines[-1], max_chars=220)


def _truncate(text: str, max_chars: int = MAX_DETAILS_CHARS) -> str:
    clean = text.strip()
    if len(clean) <= max_chars:
        return clean
    return clean[: max_chars - 24].rstrip() + "\n... [truncated]"


def _indent(text: str) -> str:
    return "\n".join(f"  {line}" for line in text.splitlines())


def _main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Run fixed KnowledgeForward security checks.")
    parser.add_argument("profile", nargs="?", default="quick", choices=("quick", "full"))
    args = parser.parse_args(argv)
    repo = Path(__file__).resolve().parents[1]
    report = run_security_checks(repo, profile=args.profile)
    print(format_security_report(report))
    return 1 if int(report["fail_count"]) else 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
