from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import AppConfig, SourceConfig


MAX_DEFAULT_QUERY_DAYS = 365
MAX_DATE_LIMIT_DAYS = MAX_DEFAULT_QUERY_DAYS


@dataclass(frozen=True)
class QueryFilteredSource:
    name: str
    default_query_days: int

    @property
    def query_filter_status(self) -> str:
        return f"default_query_days={self.default_query_days}"


def validate_startup_allowed_sources(
    config: AppConfig,
    repo_root: Path,
    max_default_query_days: int = MAX_DEFAULT_QUERY_DAYS,
) -> tuple[tuple[str, ...], tuple[QueryFilteredSource, ...]]:
    repo = repo_root.resolve()
    allowed_test_roots = {
        (repo / "tmp" / "private_test_vault").resolve(),
        (repo / "fixtures" / "sample_vault").resolve(),
    }

    errors: list[str] = []
    query_filtered_sources: list[QueryFilteredSource] = []
    for source in config.allowed_sources:
        if not source.enabled:
            continue
        source_path = source.path.resolve()
        if source_path in allowed_test_roots:
            continue
        error = _query_filtered_source_error(source, repo, max_default_query_days)
        if error:
            errors.append(f"{source.name}: {error}")
        else:
            query_filtered_sources.append(
                QueryFilteredSource(
                    name=source.name,
                    default_query_days=source.default_query_days,
                )
            )

    return tuple(errors), tuple(query_filtered_sources)


def safe_source_status_lines(config: AppConfig) -> tuple[str, ...]:
    lines = []
    for source in config.allowed_sources:
        filter_status = "required" if source.require_query_filter else "optional"
        enabled_status = "true" if source.enabled else "false"
        lines.append(
            f"{source.name}\tenabled={enabled_status}\tquery_filter={filter_status}"
            f"\tdefault_query_days={source.default_query_days}"
        )
    return tuple(lines)


def _query_filtered_source_error(source: SourceConfig, repo: Path, max_default_query_days: int) -> str | None:
    if source.type != "obsidian":
        return "type must be obsidian"
    if not source.require_query_filter:
        return "require_query_filter=true is required for non-test sources"
    if source.default_query_days < 1 or source.default_query_days > max_default_query_days:
        return f"default_query_days must be from 1 to {max_default_query_days}"

    try:
        source_path = source.path.resolve()
    except OSError:
        return "path could not be resolved"
    if not source.path.exists():
        return "path must exist"
    if not source.path.is_dir():
        return "path must be a directory"
    if source.path.is_symlink():
        return "path must not be a symlink"
    if _is_disallowed_broad_path(source_path, repo):
        return "path is too broad for startup; choose the dated data root or a narrower directory"

    return None


def _is_disallowed_broad_path(path: Path, repo: Path) -> bool:
    home = Path.home().resolve()
    disallowed_roots = {home, repo, *repo.parents, *_cloud_storage_roots(home)}
    if path in disallowed_roots:
        return True
    if path.parent == home:
        return True
    if path.parent == repo.parent and path != repo:
        return True
    return False


def _cloud_storage_roots(home: Path) -> tuple[Path, ...]:
    mobile_documents = home / "Library" / ("Mobile " + "Documents")
    cloud_docs = mobile_documents / ("com~apple~" + "CloudDocs")
    provider_document_roots = tuple(
        path.resolve()
        for path in mobile_documents.glob("*/Documents")
        if path.exists()
    )
    provider_roots = tuple(path.resolve() for path in mobile_documents.glob("*") if path.exists())
    return (mobile_documents, cloud_docs, *provider_roots, *provider_document_roots)
