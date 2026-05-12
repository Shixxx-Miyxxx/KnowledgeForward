from datetime import date
from pathlib import Path

import pytest

from knowledge_forward.config import ConfigError, load_config


def test_default_token_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KNOWLEDGE_FORWARD_AUTH_TOKEN", raising=False)
    vault = tmp_path / "vault"
    vault.mkdir()
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        f"""
auth:
  token: replace-with-a-long-random-token
database:
  path: {tmp_path / "index.sqlite3"}
allowed_sources:
  - name: vault
    path: {vault}
    type: obsidian
    enabled: true
""",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="sample placeholder"):
        load_config(config_path)


def test_knowledgeforward_auth_token_overrides_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        f"""
auth:
  token: replace-with-a-long-random-token
database:
  path: {tmp_path / "index.sqlite3"}
allowed_sources:
  - name: vault
    path: {vault}
    type: obsidian
    enabled: true
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("KNOWLEDGE_FORWARD_AUTH_TOKEN", "safe-test-token")

    config = load_config(config_path)

    assert config.auth.token == "safe-test-token"


def test_load_config_defaults_to_current_config_yaml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KNOWLEDGE_FORWARD_CONFIG", raising=False)
    monkeypatch.delenv("KNOWLEDGE_FORWARD_HOME", raising=False)
    monkeypatch.chdir(tmp_path)
    vault = tmp_path / "vault"
    vault.mkdir()
    (tmp_path / "config.yaml").write_text(
        f"""
auth:
  token: test-token
database:
  path: ./index.sqlite3
allowed_sources:
  - name: vault
    path: {vault}
    type: obsidian
    enabled: true
""",
        encoding="utf-8",
    )

    config = load_config()

    assert config.config_path == tmp_path / "config.yaml"
    assert config.database.path == tmp_path / "index.sqlite3"


def test_knowledge_forward_config_env_selects_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    vault = runtime / "vault"
    vault.mkdir()
    config_path = runtime / "private.yaml"
    config_path.write_text(
        f"""
auth:
  token: test-token
database:
  path: ./data/index.sqlite3
allowed_sources:
  - name: vault
    path: {vault}
    type: obsidian
    enabled: true
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("KNOWLEDGE_FORWARD_CONFIG", str(config_path))
    monkeypatch.delenv("KNOWLEDGE_FORWARD_HOME", raising=False)

    config = load_config()

    assert config.config_path == config_path
    assert config.database.path == runtime / "data" / "index.sqlite3"


def test_knowledge_forward_home_env_selects_home_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = tmp_path / "runtime"
    vault = runtime / "vault"
    vault.mkdir(parents=True)
    config_path = runtime / "config.yaml"
    config_path.write_text(
        f"""
auth:
  token: test-token
database:
  path: ./data/index.sqlite3
allowed_sources:
  - name: vault
    path: {vault}
    type: obsidian
    enabled: true
""",
        encoding="utf-8",
    )
    monkeypatch.delenv("KNOWLEDGE_FORWARD_CONFIG", raising=False)
    monkeypatch.setenv("KNOWLEDGE_FORWARD_HOME", str(runtime))

    config = load_config()

    assert config.config_path == config_path
    assert config.database.path == runtime / "data" / "index.sqlite3"


def test_explicit_config_argument_overrides_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_runtime = tmp_path / "env"
    explicit_runtime = tmp_path / "explicit"
    env_vault = env_runtime / "vault"
    explicit_vault = explicit_runtime / "vault"
    env_vault.mkdir(parents=True)
    explicit_vault.mkdir(parents=True)
    env_config = env_runtime / "config.yaml"
    explicit_config = explicit_runtime / "config.yaml"
    env_config.write_text(
        f"""
auth:
  token: env-token
allowed_sources:
  - name: env
    path: {env_vault}
    type: obsidian
    enabled: true
""",
        encoding="utf-8",
    )
    explicit_config.write_text(
        f"""
auth:
  token: explicit-token
allowed_sources:
  - name: explicit
    path: {explicit_vault}
    type: obsidian
    enabled: true
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("KNOWLEDGE_FORWARD_CONFIG", str(env_config))

    config = load_config(explicit_config)

    assert config.config_path == explicit_config
    assert config.auth.token == "explicit-token"
    assert config.allowed_sources[0].name == "explicit"


def test_rejects_non_local_ollama_base_url(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        f"""
auth:
  token: test-token
database:
  path: {tmp_path / "index.sqlite3"}
ollama:
  base_url: https://example.com
allowed_sources:
  - name: vault
    path: {vault}
    type: obsidian
    enabled: true
""",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="ollama.base_url"):
        load_config(config_path)


def test_rejects_allowed_source_path_traversal(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    outside = tmp_path / "outside"
    vault.mkdir()
    outside.mkdir()
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
auth:
  token: test-token
allowed_sources:
  - name: outside
    path: ./vault/../outside
    type: obsidian
    enabled: true
""",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="path traversal"):
        load_config(config_path)


def test_loads_allowed_source_date_range(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        f"""
auth:
  token: test-token
database:
  path: {tmp_path / "index.sqlite3"}
allowed_sources:
  - name: vault
    path: {vault}
    type: obsidian
    enabled: true
    date_from: "2026-04-01"
    date_to: "2026-05-01"
""",
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.allowed_sources[0].date_from == date(2026, 4, 1)
    assert config.allowed_sources[0].date_to == date(2026, 5, 1)
    assert config.allowed_sources[0].require_query_filter is False
    assert config.allowed_sources[0].default_query_days == 30


def test_loads_query_filter_source_defaults(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        f"""
auth:
  token: test-token
database:
  path: {tmp_path / "index.sqlite3"}
allowed_sources:
  - name: vault
    path: {vault}
    type: obsidian
    enabled: true
    require_query_filter: true
""",
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.allowed_sources[0].require_query_filter is True
    assert config.allowed_sources[0].default_query_days == 30
    assert config.ollama.timeout_seconds == 180


def test_rejects_invalid_default_query_days(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        f"""
auth:
  token: test-token
allowed_sources:
  - name: vault
    path: {vault}
    type: obsidian
    enabled: true
    require_query_filter: true
    default_query_days: 0
""",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="default_query_days"):
        load_config(config_path)


def test_rejects_query_filter_source_with_index_time_date_range(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        f"""
auth:
  token: test-token
allowed_sources:
  - name: vault
    path: {vault}
    type: obsidian
    enabled: true
    require_query_filter: true
    date_from: "2026-05-01"
""",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="require_query_filter"):
        load_config(config_path)


def test_rejects_allowed_source_date_range_when_from_after_to(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        f"""
auth:
  token: test-token
allowed_sources:
  - name: vault
    path: {vault}
    type: obsidian
    enabled: true
    date_from: "2026-05-02"
    date_to: "2026-05-01"
""",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="date_from"):
        load_config(config_path)


def test_config_yaml_is_gitignored() -> None:
    gitignore = Path(".gitignore").read_text(encoding="utf-8").splitlines()

    assert "config.yaml" in gitignore
