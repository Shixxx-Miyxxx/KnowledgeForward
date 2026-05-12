from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml


class ConfigError(ValueError):
    """Raised when config.yaml is missing required settings."""


INSECURE_AUTH_TOKENS = frozenset(
    {
        "change-me-local-token",
        "replace-with-a-long-random-token",
    }
)


@dataclass(frozen=True)
class ServerConfig:
    host: str = "127.0.0.1"
    port: int = 8765


@dataclass(frozen=True)
class AuthConfig:
    token: str


@dataclass(frozen=True)
class DatabaseConfig:
    path: Path


@dataclass(frozen=True)
class OllamaConfig:
    base_url: str = "http://127.0.0.1:11434"
    model: str = "llama3.2"
    timeout_seconds: int = 180
    temperature: float = 0.2
    hide_thinking: bool = True


@dataclass(frozen=True)
class IndexingConfig:
    max_file_bytes: int = 1_048_576
    chunk_max_chars: int = 1400
    chunk_overlap_chars: int = 160
    excluded_dirs: tuple[str, ...] = (
        ".git",
        ".obsidian",
        "node_modules",
        "attachments",
        ".venv",
        "venv",
        "__pycache__",
    )
    markdown_extensions: tuple[str, ...] = (".md", ".markdown")


@dataclass(frozen=True)
class SourceConfig:
    name: str
    path: Path
    type: str = "obsidian"
    enabled: bool = True
    date_from: date | None = None
    date_to: date | None = None
    require_query_filter: bool = False
    default_query_days: int = 30


@dataclass(frozen=True)
class AppConfig:
    config_path: Path
    server: ServerConfig
    auth: AuthConfig
    database: DatabaseConfig
    ollama: OllamaConfig
    indexing: IndexingConfig
    allowed_sources: tuple[SourceConfig, ...]


def load_config(config_path: str | Path = "config.yaml") -> AppConfig:
    path = Path(config_path).expanduser().resolve()
    if not path.exists():
        raise ConfigError("Config file not found.")

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ConfigError("config.yaml must contain a mapping at the top level.")

    base_dir = path.parent
    server_raw = _mapping(raw.get("server", {}), "server")
    auth_raw = _mapping(raw.get("auth", {}), "auth")
    database_raw = _mapping(raw.get("database", {}), "database")
    ollama_raw = _mapping(raw.get("ollama", {}), "ollama")
    indexing_raw = _mapping(raw.get("indexing", {}), "indexing")
    ollama_base_url = os.environ.get("KNOWLEDGE_FORWARD_OLLAMA_BASE_URL") or str(
        ollama_raw.get("base_url", "http://127.0.0.1:11434")
    )
    ollama_model = os.environ.get("KNOWLEDGE_FORWARD_OLLAMA_MODEL") or str(ollama_raw.get("model", "llama3.2"))

    env_token = os.environ.get("KNOWLEDGE_FORWARD_AUTH_TOKEN")
    token = str(env_token or auth_raw.get("token", "")).strip()
    if not token:
        raise ConfigError("auth.token is required. Set it in config.yaml or KNOWLEDGE_FORWARD_AUTH_TOKEN.")
    if token in INSECURE_AUTH_TOKENS:
        raise ConfigError(
            "auth.token is still set to the sample placeholder. "
            "Set KNOWLEDGE_FORWARD_AUTH_TOKEN or replace auth.token in config.yaml before starting KnowledgeForward."
        )

    database_path = _resolve_config_path(base_dir, str(database_raw.get("path", "./data/knowledgeforward.sqlite3")))
    ollama_base_url = _validate_ollama_base_url(ollama_base_url)

    sources = []
    for item in raw.get("allowed_sources", []):
        source_raw = _mapping(item, "allowed_sources[]")
        name = str(source_raw.get("name", "")).strip()
        source_path = str(source_raw.get("path", "")).strip()
        if not name or not source_path:
            raise ConfigError("Each allowed_sources item requires name and path.")
        date_from = _parse_optional_date(source_raw.get("date_from"), "allowed_sources.date_from")
        date_to = _parse_optional_date(source_raw.get("date_to"), "allowed_sources.date_to")
        if date_from and date_to and date_from > date_to:
            raise ConfigError("allowed_sources.date_from must be earlier than or equal to date_to.")
        require_query_filter = _parse_bool(
            source_raw.get("require_query_filter", False),
            "allowed_sources.require_query_filter",
        )
        default_query_days = _parse_default_query_days(source_raw.get("default_query_days", 30))
        if require_query_filter and (date_from is not None or date_to is not None):
            raise ConfigError(
                "allowed_sources with require_query_filter=true must not also set date_from/date_to; "
                "use /search or /ask filters instead."
            )
        sources.append(
            SourceConfig(
                name=name,
                path=_resolve_source_path(base_dir, source_path),
                type=str(source_raw.get("type", "obsidian")),
                enabled=_parse_bool(source_raw.get("enabled", True), "allowed_sources.enabled"),
                date_from=date_from,
                date_to=date_to,
                require_query_filter=require_query_filter,
                default_query_days=default_query_days,
            )
        )

    if not sources:
        raise ConfigError("At least one allowed_sources entry is required.")

    return AppConfig(
        config_path=path,
        server=ServerConfig(
            host=str(server_raw.get("host", "127.0.0.1")),
            port=int(server_raw.get("port", 8765)),
        ),
        auth=AuthConfig(token=token),
        database=DatabaseConfig(path=database_path),
        ollama=OllamaConfig(
            base_url=ollama_base_url.rstrip("/"),
            model=ollama_model,
            timeout_seconds=int(ollama_raw.get("timeout_seconds", 180)),
            temperature=float(ollama_raw.get("temperature", 0.2)),
            hide_thinking=bool(ollama_raw.get("hide_thinking", True)),
        ),
        indexing=IndexingConfig(
            max_file_bytes=int(indexing_raw.get("max_file_bytes", 1_048_576)),
            chunk_max_chars=int(indexing_raw.get("chunk_max_chars", 1400)),
            chunk_overlap_chars=int(indexing_raw.get("chunk_overlap_chars", 160)),
            excluded_dirs=tuple(indexing_raw.get("excluded_dirs", IndexingConfig.excluded_dirs)),
            markdown_extensions=tuple(
                ext.lower() for ext in indexing_raw.get("markdown_extensions", IndexingConfig.markdown_extensions)
            ),
        ),
        allowed_sources=tuple(sources),
    )


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigError(f"{label} must be a mapping.")
    return value


def _resolve_config_path(base_dir: Path, value: str) -> Path:
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = base_dir / candidate
    return candidate.resolve()


def _parse_optional_date(value: Any, label: str) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise ConfigError(f"{label} must be a YYYY-MM-DD string.")
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ConfigError(f"{label} must be a YYYY-MM-DD string.") from exc


def _parse_bool(value: Any, label: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized in {"true", "yes", "1", "on"}:
            return True
        if normalized in {"false", "no", "0", "off"}:
            return False
    raise ConfigError(f"{label} must be true or false.")


def _parse_default_query_days(value: Any) -> int:
    try:
        days = int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError("allowed_sources.default_query_days must be an integer from 1 to 365.") from exc
    if days < 1 or days > 365:
        raise ConfigError("allowed_sources.default_query_days must be from 1 to 365.")
    return days


def _resolve_source_path(base_dir: Path, value: str) -> Path:
    candidate = Path(value)
    if value.startswith("~"):
        raise ConfigError("allowed_sources.path must be explicit; '~' expansion is not allowed.")
    if any(part == ".." for part in candidate.parts):
        raise ConfigError("allowed_sources.path must not contain '..' path traversal.")
    if not candidate.is_absolute():
        candidate = base_dir / candidate
    if candidate.exists() and candidate.is_symlink():
        raise ConfigError("allowed_sources.path must not be a symlink.")
    return candidate.resolve()


def _validate_ollama_base_url(value: str) -> str:
    parsed = urlparse(value)
    allowed_hosts = {"127.0.0.1", "localhost", "::1"}
    if parsed.scheme != "http" or parsed.hostname not in allowed_hosts or parsed.port != 11434:
        raise ConfigError("ollama.base_url must be http://127.0.0.1:11434 or another localhost:11434 form.")
    return value.rstrip("/")
