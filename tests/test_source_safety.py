from pathlib import Path

from knowledge_forward.config import load_config
from knowledge_forward.source_safety import (
    MAX_DEFAULT_QUERY_DAYS,
    safe_source_status_lines,
    validate_startup_allowed_sources,
)


def test_startup_allows_query_filtered_knowledge_source(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    source = tmp_path / "external" / "Knowledge" / "01_data"
    source.mkdir(parents=True)
    config = load_config(
        _write_config(
            tmp_path,
            source,
            """
    require_query_filter: true
    default_query_days: 30
""",
        )
    )

    errors, query_filtered_sources = validate_startup_allowed_sources(config, repo)

    assert errors == ()
    assert len(query_filtered_sources) == 1
    assert query_filtered_sources[0].name == "vault"
    assert query_filtered_sources[0].default_query_days == 30


def test_startup_rejects_non_test_source_without_query_filter(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    source = tmp_path / "external" / "Knowledge" / "01_data"
    source.mkdir(parents=True)
    config = load_config(_write_config(tmp_path, source))

    errors, query_filtered_sources = validate_startup_allowed_sources(config, repo)

    assert query_filtered_sources == ()
    assert errors
    assert "require_query_filter=true" in errors[0]


def test_startup_rejects_default_query_days_over_limit(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    source = tmp_path / "external" / "Knowledge" / "01_data"
    source.mkdir(parents=True)
    config = load_config(
        _write_config(
            tmp_path,
            source,
            """
    require_query_filter: true
    default_query_days: 365
""",
        )
    )

    errors, query_filtered_sources = validate_startup_allowed_sources(config, repo, max_default_query_days=90)

    assert query_filtered_sources == ()
    assert errors
    assert "default_query_days" in errors[0]
    assert str(MAX_DEFAULT_QUERY_DAYS) == "365"


def test_startup_allows_test_source_without_query_filter(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    source = repo / "tmp" / "private_test_vault"
    source.mkdir(parents=True)
    config = load_config(_write_config(tmp_path, source))

    errors, query_filtered_sources = validate_startup_allowed_sources(config, repo)

    assert errors == ()
    assert query_filtered_sources == ()


def test_startup_rejects_repo_root_even_with_query_filter(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    config = load_config(
        _write_config(
            tmp_path,
            repo,
            """
    require_query_filter: true
    default_query_days: 30
""",
        )
    )

    errors, query_filtered_sources = validate_startup_allowed_sources(config, repo)

    assert query_filtered_sources == ()
    assert errors
    assert "too broad" in errors[0]


def test_startup_rejects_home_child_root(tmp_path: Path, monkeypatch) -> None:
    repo = _make_repo(tmp_path)
    fake_home = tmp_path / "home"
    source = fake_home / "Documents"
    source.mkdir(parents=True)
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    config = load_config(
        _write_config(
            tmp_path,
            source,
            """
    require_query_filter: true
    default_query_days: 30
""",
        )
    )

    errors, query_filtered_sources = validate_startup_allowed_sources(config, repo)

    assert query_filtered_sources == ()
    assert errors
    assert "too broad" in errors[0]


def test_safe_source_status_lines_do_not_include_paths(tmp_path: Path) -> None:
    source = tmp_path / "external" / "Knowledge" / "01_data"
    source.mkdir(parents=True)
    config = load_config(
        _write_config(
            tmp_path,
            source,
            """
    require_query_filter: true
    default_query_days: 30
""",
        )
    )

    lines = safe_source_status_lines(config)

    assert lines == ("vault\tenabled=true\tquery_filter=required\tdefault_query_days=30",)
    assert str(source) not in lines[0]


def _make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    return repo


def _write_config(tmp_path: Path, source: Path, extra_source_lines: str = "") -> Path:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        f"""
auth:
  token: test-token
database:
  path: {tmp_path / "index.sqlite3"}
allowed_sources:
  - name: vault
    path: {source}
    type: obsidian
    enabled: true
{extra_source_lines}
""",
        encoding="utf-8",
    )
    return config_path
