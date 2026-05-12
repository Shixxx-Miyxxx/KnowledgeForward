from pathlib import Path

from knowledge_forward.config import load_config
from knowledge_forward.runtime import init_runtime, resolve_runtime_paths


def test_resolve_runtime_paths_uses_external_config_parent(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    runtime = tmp_path / "runtime"
    repo.mkdir()
    runtime.mkdir()
    config_path = runtime / "private.yaml"
    monkeypatch.setenv("KNOWLEDGE_FORWARD_CONFIG", str(config_path))
    monkeypatch.delenv("KNOWLEDGE_FORWARD_HOME", raising=False)

    paths = resolve_runtime_paths(repo)

    assert paths.config_path == config_path
    assert paths.runtime_home == runtime
    assert paths.log_file == runtime / "logs" / "knowledgeforward.log"
    assert paths.pid_file == runtime / "run" / "knowledgeforward.pid"
    assert paths.is_external is True


def test_resolve_runtime_paths_uses_home_for_config_and_logs(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    runtime = tmp_path / "runtime"
    repo.mkdir()
    monkeypatch.delenv("KNOWLEDGE_FORWARD_CONFIG", raising=False)
    monkeypatch.setenv("KNOWLEDGE_FORWARD_HOME", str(runtime))

    paths = resolve_runtime_paths(repo)

    assert paths.config_path == runtime / "config.yaml"
    assert paths.runtime_home == runtime
    assert paths.log_file == runtime / "logs" / "knowledgeforward.log"
    assert paths.pid_file == runtime / "run" / "knowledgeforward.pid"
    assert paths.is_external is True


def test_resolve_runtime_paths_preserves_legacy_repo_tmp(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.delenv("KNOWLEDGE_FORWARD_CONFIG", raising=False)
    monkeypatch.delenv("KNOWLEDGE_FORWARD_HOME", raising=False)
    monkeypatch.chdir(repo)

    paths = resolve_runtime_paths(repo)

    assert paths.config_path == repo / "config.yaml"
    assert paths.runtime_home == repo / "tmp"
    assert paths.log_file == repo / "tmp" / "logs" / "knowledgeforward.log"
    assert paths.pid_file == repo / "tmp" / "run" / "knowledgeforward.pid"
    assert paths.is_external is False


def test_init_runtime_creates_private_runtime_without_overwriting(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    runtime = tmp_path / "KnowledgeForward-local"

    result = init_runtime(runtime, repo)

    assert result.config_path == runtime / "config.yaml"
    assert (runtime / "data").is_dir()
    assert (runtime / "logs").is_dir()
    assert (runtime / "run").is_dir()
    assert (runtime / ".gitignore").read_text(encoding="utf-8").splitlines() == [
        "config.yaml",
        "data/",
        "logs/",
        "run/",
        ".DS_Store",
    ]
    assert (runtime / "sample_vault" / "note.md").exists()
    config = load_config(runtime / "config.yaml")
    assert config.auth.token not in {"change-me-local-token", "replace-with-a-long-random-token"}
    assert config.database.path == runtime / "data" / "knowledgeforward.sqlite3"
    assert config.allowed_sources[0].name == "sample_vault"
    assert config.allowed_sources[0].path == runtime / "sample_vault"
    assert config.allowed_sources[0].require_query_filter is True

    original_config = (runtime / "config.yaml").read_text(encoding="utf-8")
    second = init_runtime(runtime, repo)

    assert (runtime / "config.yaml").read_text(encoding="utf-8") == original_config
    assert runtime / "config.yaml" in second.skipped
    assert runtime / "sample_vault" in second.skipped


def test_init_runtime_rejects_target_inside_public_repo(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    target = repo / "private_runtime"

    try:
        init_runtime(target, repo)
    except ValueError as exc:
        assert "outside the KnowledgeForward repository directory" in str(exc)
    else:
        raise AssertionError("init_runtime should reject repo-internal targets")


def _make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    sample = repo / "fixtures" / "sample_vault"
    sample.mkdir(parents=True)
    (sample / "note.md").write_text("# Sample\n\nSynthetic sample.", encoding="utf-8")
    return repo
