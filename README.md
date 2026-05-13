# KnowledgeForward

KnowledgeForward は、明示的に許可したローカル Markdown フォルダだけを SQLite FTS5 で検索し、localhost の Ollama で根拠付き回答を生成する local-first なプライベート知識ワークフローです。

安全性や利用前の確認事項を先に見たい場合は [KnowledgeForwardを使う前に](docs/start-here.md) を読んでください。Codex などのコーディングエージェントに初回セットアップを任せる場合は [agent setup guide](docs/agent-setup.md) を渡してください。

## 概要

KnowledgeForward が行うこと:

- ユーザーが `config.yaml` に明示した Markdown フォルダだけを読む。
- Markdown をチャンク化して SQLite に保存し、全文検索する。
- 検索結果を根拠として Ollama のローカルモデルに回答を作らせる。
- Mac では `127.0.0.1:8765`、iPhone では Tailscale Serve 経由で Web UI を使えるようにする。

KnowledgeForward がデフォルトで行わないこと:

- 外部 LLM API を使う。
- 外部検索 API を使う。
- telemetry を送る。
- Tailscale Funnel などでインターネット全体へ公開する。
- ホームディレクトリ全体やクラウド同期 root 全体を自動探索する。

## 要件

- macOS
- Python 3.11 以上
- Ollama
- iPhone から使う場合は Tailscale CLI とログイン済みの tailnet

Python 依存関係は repository-local の `.venv` に入れます。

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## 安全境界

実運用の `config.yaml`、DB、ログ、PID、実ノートは KnowledgeForward の repo ディレクトリ外、または少なくとも Git 管理外に置いてください。

```bash
RUNTIME_HOME="$HOME/.knowledgeforward-local"
./knowledgeforward init-runtime "$RUNTIME_HOME"
```

標準以外の場所に private runtime を作った場合は、そのコマンドだけ `KNOWLEDGE_FORWARD_HOME="$RUNTIME_HOME"` を付けて実行できます。`~/.zshrc` などへの永続設定は必須ではありません。

`init-runtime` は private runtime に次を作ります。既存ファイルは上書きしません。

- `config.yaml`
- `data/`
- `logs/`
- `run/`
- `.gitignore`
- `sample_vault/`

## 設定解決順

設定ファイルの優先順は次の通りです。

1. Python API などから渡された明示引数
2. `KNOWLEDGE_FORWARD_CONFIG`
3. `KNOWLEDGE_FORWARD_HOME/config.yaml`
4. 自動検出された private runtime の `config.yaml`
5. repo-local `config.yaml`

起動系スクリプトは `KNOWLEDGE_FORWARD_HOME`、`KNOWLEDGE_FORWARD_CONFIG`、または自動検出された private runtime から runtime path を解決し、PID、ログ、Ollama 管理ファイルを private runtime 側の `run/` と `logs/` に置きます。`KNOWLEDGE_FORWARD_HOME` と `KNOWLEDGE_FORWARD_CONFIG` を併用した場合、config は `KNOWLEDGE_FORWARD_CONFIG` を使い、runtime home は `KNOWLEDGE_FORWARD_HOME` を使います。

## 最短セットアップ

1. private runtime を作ります。

```bash
RUNTIME_HOME="$HOME/.knowledgeforward-local"
./knowledgeforward init-runtime "$RUNTIME_HOME"
```

2. private runtime の `config.yaml` を編集し、実データ用 source をユーザーが選んだ小さめの Markdown フォルダにします。ホームディレクトリ全体、クラウド同期 root 全体、repo root は指定しないでください。

```yaml
allowed_sources:
  - name: user_notes
    path: "<ABSOLUTE_MARKDOWN_SOURCE_DIR>"
    type: obsidian
    enabled: true
    require_query_filter: true
    default_query_days: 30
```

3. 設定した Ollama モデルを用意します。初期値は `llama3.2` です。

```bash
ollama pull llama3.2
```

4. 起動します。

```bash
KNOWLEDGE_FORWARD_HOME="$RUNTIME_HOME" ./knowledgeforward start
KNOWLEDGE_FORWARD_HOME="$RUNTIME_HOME" ./knowledgeforward status
```

Mac では `http://127.0.0.1:8765/` を開きます。iPhone では `status` の `iPhone URL` を開きます。Web UI の Token 欄には private runtime の `config.yaml` にある `auth.token` を貼り付けます。token、実パス、ログ全文、private runtime の `config.yaml` 全文を issue、PR、チャットに貼らないでください。

## 主要コマンド

repo root で実行します。

```bash
./knowledgeforward help
./knowledgeforward start
./knowledgeforward status
./knowledgeforward restart
./knowledgeforward stop
./knowledgeforward init-runtime <path>
./knowledgeforward test
```

`make` ターゲットも互換用に残していますが、通常は `./knowledgeforward ...` を使います。

## トラブル対応

private runtime の `config.yaml` がない:

```bash
./knowledgeforward init-runtime "$RUNTIME_HOME"
```

`uvicorn` または `yaml` がない:

```bash
.venv/bin/python -m pip install -r requirements.txt
```

`auth.token is still an insecure placeholder`:

```bash
.venv/bin/python -c "import secrets; print(secrets.token_urlsafe(32))"
```

生成した token を private runtime の `config.yaml` の `auth.token` に設定します。issue、PR、チャットには貼らないでください。

`Configured Ollama model was not found`:

```bash
ollama pull <MODEL_NAME>
```

`allowed_sources contains unsupported enabled source`:

source path が広すぎる、存在しない、symlink、`require_query_filter` 不足、または `default_query_days` 範囲外です。狭い実在 Markdown フォルダに変更し、実データでは `require_query_filter: true` と `default_query_days: 30` を使ってください。

`/ask` が「分かりません」だけ返す:

- 先に `/reindex` を実行する。
- query filter が狭すぎないか確認する。
- 日付 metadata がない Markdown の場合は、Web UI で全期間検索を明示する。
- `/diagnostics <query>` で検索前段のヒットを確認する。

repo-local runtime 警告が出る:

`KNOWLEDGE_FORWARD_HOME` と `KNOWLEDGE_FORWARD_CONFIG` が未設定で、private runtime も自動検出できない場合、互換用に repo root 直下の `config.yaml` と `tmp/` を使おうとします。この legacy repo-local runtime は実運用では非推奨です。`./knowledgeforward init-runtime "$HOME/.knowledgeforward-local"` で private runtime を作り、必要なコマンドに `KNOWLEDGE_FORWARD_HOME="$HOME/.knowledgeforward-local"` を付けて実行してください。

## 開発

変更前後で最低限次を実行してください。security 系コマンドは開発者・メンテナ向けの repo 監査です。Web UI の `/security` は token 認証後に同じ repo 監査を full 実行します。通常利用には不要ですが、起動中のローカル環境から確認できます。

```bash
./knowledgeforward test
./knowledgeforward security-check
./knowledgeforward security-audit
```

詳しくは [CONTRIBUTING.md](CONTRIBUTING.md) と [SECURITY.md](SECURITY.md) を確認してください。
