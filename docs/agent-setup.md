# Agent setup guide

この文書は、Codex、Claude、またはファイル編集とコマンド実行ができる LLM に渡し、ユーザーが KnowledgeForward を使い始められる状態まで作業させるための実行指示書です。

## 依頼文

あなたはローカル環境を扱えるコーディングエージェントです。このリポジトリで KnowledgeForward を初回利用できる状態にしてください。

最終ゴールは次です。

- private runtime が KnowledgeForward repo ディレクトリ外、または少なくとも Git 管理外に作成され、安全な token 入りの `config.yaml` が設定されている。
- ユーザーが指定した Markdown フォルダだけが `allowed_sources` に設定されている。
- Ollama の指定モデルがローカルに存在する。
- `./knowledgeforward start` が成功し、`./knowledgeforward status` で起動状態を確認できる。
- Mac ブラウザまたは Tailscale 経由の iPhone Safari で Web UI を開ける URL をユーザーに伝えられる。
- token、実 Vault パス、Markdown 本文、ログ本文を不要に表示しない。

作業はこの文書の順に進めてください。人間に CLI の説明をしないでください。必要な確認、編集、コマンド実行はあなたが行い、足りない情報だけを短くユーザーに聞いてください。

## プロジェクト概要

KnowledgeForward は、明示的に許可されたローカル Markdown フォルダだけを SQLite FTS5 で検索し、localhost の Ollama で根拠付き回答を生成する local-first なプライベート知識ワークフローです。

主な境界:

- 外部 LLM API は使わない。
- 外部検索 API は使わない。
- telemetry は使わない。
- サーバーは `127.0.0.1:8765` に bind する。
- iPhone から使う場合は Tailscale Serve を使い、Tailscale Funnel は使わない。
- 実運用の `config.yaml`、DB、ログ、PID、実ノートは KnowledgeForward repo ディレクトリ外、または少なくとも Git 管理外に置く。
- repo-local `config.yaml`、`data/`、`tmp/` は legacy repo-local runtime であり、実運用では使わない。

## 利用する専用コマンド

repo root で実行します。

```bash
./knowledgeforward help
./knowledgeforward start
./knowledgeforward status
./knowledgeforward restart
./knowledgeforward stop
./knowledgeforward init-runtime <path>
./knowledgeforward test
./knowledgeforward security-check
./knowledgeforward security-audit
./knowledgeforward security-audit full
```

互換用に `make` ターゲットもありますが、通常は使わず `./knowledgeforward ...` に統一してください。

## 作業前確認

1. repo root にいることを確認する。

```bash
pwd
test -f README.md
test -x ./knowledgeforward
```

2. 現在の差分を確認する。ユーザーの未コミット変更を勝手に戻さない。

```bash
git status --short
```

3. 必要コマンドを確認する。

```bash
python3 --version
ollama --version
tailscale status
```

Python は 3.11 以上が必要です。`ollama` または `tailscale` がない場合は、ユーザーにインストールまたはログインを依頼して停止してください。Tailscale CLI が `Failed to load preferences` を返す場合も、macOS 側の Tailscale 状態をユーザーに直してもらってから再開してください。

## 初回セットアップ手順

### 1. Python 仮想環境と依存関係

`.venv` がなければ作成し、依存関係を入れます。

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

既に `.venv` がある場合も、依存不足が疑われるなら次を実行します。

```bash
.venv/bin/python -m pip install -r requirements.txt
```

### 2. private runtime を作る

実運用では、KnowledgeForward repo ディレクトリ外に private runtime を作ります。例:

```bash
RUNTIME_HOME="$HOME/.knowledgeforward-local"
./knowledgeforward init-runtime "$RUNTIME_HOME"
```

`init-runtime` は次を作成します。既存ファイルは上書きしません。

- `config.yaml`
- `data/`
- `logs/`
- `run/`
- `.gitignore`
- `sample_vault/`

以後の `start`、`status`、`stop` で runtime が自動検出されない場合は、そのコマンドだけ同じ `KNOWLEDGE_FORWARD_HOME` を指定して実行します。ユーザーから明示依頼がない限り、`~/.zshrc` などの shell profile は編集しないでください。

repo root 直下の `config.yaml`、`data/`、`tmp/` を使う旧方式は互換用に残していますが、実運用では非推奨です。既に repo-local に実設定や DB がある場合も自動移行はしません。ユーザー確認のうえで、private runtime 側へ手動で移してください。

### 3. 設定解決順を理解する

設定ファイルの優先順は次の通りです。

1. Python API などから渡された明示引数
2. `KNOWLEDGE_FORWARD_CONFIG`
3. `KNOWLEDGE_FORWARD_HOME/config.yaml`
4. 自動検出された private runtime の `config.yaml`
5. repo-local `config.yaml`

別名の config ファイルを使う上級運用では `KNOWLEDGE_FORWARD_CONFIG` を使えます。標準以外の runtime 場所を使う場合は、そのコマンドだけ `KNOWLEDGE_FORWARD_HOME` を指定できます。`KNOWLEDGE_FORWARD_HOME` と `KNOWLEDGE_FORWARD_CONFIG` を併用すると、config は `KNOWLEDGE_FORWARD_CONFIG` を読み、PID、ログ、Ollama 管理ファイルは `KNOWLEDGE_FORWARD_HOME` の `run/` と `logs/` に置きます。

### 4. token を設定する

`init-runtime` で作った `config.yaml` には安全な token が自動設定されます。既存 config を手動で直す場合、`auth.token` が `replace-with-a-long-random-token` または空なら、安全な token を生成して設定します。

```bash
.venv/bin/python -c "import secrets; print(secrets.token_urlsafe(32))"
```

token は最終報告にそのまま書かないでください。ユーザーには「private runtime の `config.yaml` の `auth.token` を Web UI の Token 欄に貼り付けてください」とだけ伝えます。token、実パス、ログ全文、private runtime の `config.yaml` 全文を issue、PR、チャットに貼らないでください。

### 5. Markdown source を決める

ユーザーが読ませたい Markdown フォルダを指定していない場合だけ、次を短く聞いてください。

```text
KnowledgeForward に読ませる Markdown フォルダの絶対パスを教えてください。ホームディレクトリ全体、クラウド同期 root 全体、repo root は避けて、最初は小さめのフォルダを指定してください。
```

source path を受け取ったら、次を確認します。

```bash
test -d "<ABSOLUTE_MARKDOWN_SOURCE_DIR>"
test ! -L "<ABSOLUTE_MARKDOWN_SOURCE_DIR>"
```

広すぎるパスは使わないでください。禁止例はホームディレクトリ全体、クラウド同期 root 全体、repo root、repo 親、filesystem root です。ユーザーが広すぎるパスを指定した場合は、より狭い Markdown フォルダを聞き直してください。

### 6. `allowed_sources` を設定する

private runtime の `config.yaml` の `allowed_sources` は、最初はユーザーが指定した source だけにします。実パスの例を repo docs やコメントに残さないでください。

設定形:

```yaml
allowed_sources:
  - name: user_notes
    path: "<ABSOLUTE_MARKDOWN_SOURCE_DIR>"
    type: obsidian
    enabled: true
    require_query_filter: true
    default_query_days: 30
```

source `name` は英数字、underscore、hyphen 程度の短い名前にしてください。`path` はユーザーが指定した実在ディレクトリの絶対パスに置き換えます。

`require_query_filter: true` と `default_query_days: 30` は実データ用の安全設定です。日付を抽出できない Markdown も Reindex されますが、通常検索では直近日付 filter から外れることがあります。その場合は Web UI で全期間検索を明示して使います。

### 7. Ollama モデルを用意する

private runtime の `config.yaml` の `ollama.model` を読みます。初期値は `llama3.2` です。

モデルがローカルにない場合は pull します。

```bash
ollama pull llama3.2
```

別モデルに変更する場合は、必ず private runtime の `config.yaml` の `ollama.model` と pull するモデル名を一致させてください。

### 8. 起動する

```bash
KNOWLEDGE_FORWARD_HOME="$RUNTIME_HOME" ./knowledgeforward start
```

このコマンドは以下を検査します。

- `.venv` と Python 依存関係
- private runtime の `config.yaml` が存在すること
- `auth.token` がプレースホルダではないこと
- `allowed_sources` が安全な source であること
- Ollama が応答し、指定モデルが存在すること
- Tailscale CLI と `tailscale status` が使えること

成功条件は、最後に `Done. Run ./knowledgeforward status ...` が出ることです。

### 9. 状態確認

```bash
KNOWLEDGE_FORWARD_HOME="$RUNTIME_HOME" ./knowledgeforward status
```

最低限、次を確認します。

- KnowledgeForward が `127.0.0.1:8765` で起動している。
- authenticated `/health` が成功している。
- Ollama が `127.0.0.1:11434` で応答している。
- `Ollama model` が available。
- `allowed_sources` にユーザー指定 source が表示される。

Tailscale Serve URL が取れた場合、`iPhone URL` に表示されます。

### 10. Web UI 利用開始

Mac 用 URL:

```text
http://127.0.0.1:8765/
```

ユーザーに伝える内容:

- Mac では上の URL を開く。
- iPhone では `./knowledgeforward status` の `iPhone URL` を開く。
- Token popup には private runtime の `config.yaml` の `auth.token` を貼り付ける。
- token 保存後、自動 Reindex が始まる。
- 手動 Reindex は入力欄に `/reindex`。
- 日付を持たない Markdown が検索に出ない場合は、filter アイコンから全期間検索を選ぶ。

token の実値、source の実パス、Markdown 本文はチャットに貼らないでください。

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

`.venv/bin/python -c "import secrets; print(secrets.token_urlsafe(32))"` で生成し、private runtime の `config.yaml` の `auth.token` を置き換えます。

`Configured Ollama model was not found`:

private runtime の `config.yaml` の `ollama.model` を読み、そのモデルを pull します。

```bash
ollama pull <MODEL_NAME>
```

`Tailscale CLI is not available` または `tailscale status failed`:

ユーザーに Tailscale のインストール、ログイン、macOS 側の状態修復を依頼してください。KnowledgeForward 側で Tailscale 設定を無理に修復しないでください。

`allowed_sources contains unsupported enabled source`:

source path が広すぎる、存在しない、symlink、`require_query_filter` 不足、または `default_query_days` 範囲外です。狭い実在 Markdown フォルダに変更し、次の設定に戻してください。

```yaml
require_query_filter: true
default_query_days: 30
```

`/ask` が「分かりません」だけ返す:

- 先に `/reindex` を実行する。
- query filter が狭すぎないか確認する。
- 日付 metadata がない Markdown の場合は、Web UI で全期間検索を選ぶ。
- `/diagnostics <query>` で検索前段のヒットを確認する。

古い DB や schema 変更で検索エラー:

まず `/reindex` を実行してください。完全に作り直す場合は、KnowledgeForward を止めてから private runtime の `data/knowledgeforward.sqlite3`、`data/knowledgeforward.sqlite3-shm`、`data/knowledgeforward.sqlite3-wal` を削除し、再起動後に `/reindex` します。private runtime は repo ディレクトリ外、または少なくとも Git 管理外に置いてください。

## 検証

セットアップ作業後、可能な範囲で次を実行します。security 系コマンドは開発者・メンテナ向けの repo 監査です。Web UI の `/security` は token 認証後に同じ repo 監査を full 実行します。通常利用には不要ですが、起動中のローカル環境から確認できます。

```bash
./knowledgeforward test
./knowledgeforward security-check
./knowledgeforward security-audit
```

`security-audit full` は任意です。ローカル監査ツールのインストール状態に依存するため、失敗した場合はツール名と理由だけを報告してください。

## 完了報告フォーマット

完了時は、ユーザーに次だけを短く報告してください。

- 起動できたか。
- Mac URL。
- iPhone URL が取れたか。
- Reindex が必要か、または完了したか。
- 残っているユーザー作業があればその 1 つだけ。

報告に含めないもの:

- token の実値
- source の実パス
- Markdown 本文
- `config.yaml` 全文
- ログ全文

## 開発者向けメモ

MVP の範囲:

- FastAPI ベースのローカル Web/API サーバー
- SQLite によるインデックス保存
- Markdown ファイルの再帰読み込み
- 見出し単位を基準にしたチャンク化
- SQLite FTS5 による全文検索
- Ollama `http://127.0.0.1:11434` との連携
- `/ask`、`/search`、`/reindex` API
- iPhone Safari から使いやすい最小 Web UI
- 回答への根拠ファイル、見出し、チャンク情報の表示
- pytest による最小テスト

未実装:

- PDF
- 画像 OCR
- コードリポジトリ解析
- Slack / Discord / Telegram 連携
- 外部 LLM API
- 外部検索 API
- クラウド DB 連携

インデックス対象外:

- `.git`
- `.obsidian`
- `node_modules`
- `attachments`
- `.venv` / `venv`
- `__pycache__`
- `.DS_Store`
- Markdown 以外の画像、添付ファイル、バイナリ
