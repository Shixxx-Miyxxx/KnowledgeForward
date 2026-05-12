# KnowledgeForward

安全性や概要を自分で確認したい場合は、先に [KnowledgeForwardを使う前に](docs/start-here.md) を読んでください。

このREADMEは人間向けの操作マニュアルではありません。Codex、Claude、またはファイル編集とコマンド実行ができるLLMにこのREADMEを渡し、ユーザーがKnowledgeForwardを使い始められる状態まで作業させるための実行指示書です。

## LLMへの依頼文

あなたはローカル環境を扱えるコーディングエージェントです。このリポジトリでKnowledgeForwardを初回利用できる状態にしてください。

最終ゴールは次です。

- private runtimeが公開repo外に作成され、安全なtoken入りの `config.yaml` が設定されている。
- ユーザーが指定したMarkdownフォルダだけが `allowed_sources` に設定されている。
- Ollamaの指定モデルがローカルに存在する。
- `./knowledgeforward start` が成功し、`./knowledgeforward status` で起動状態を確認できる。
- MacブラウザまたはTailscale経由のiPhone SafariでWeb UIを開けるURLをユーザーに伝えられる。
- token、実Vaultパス、Markdown本文、ログ本文を不要に表示しない。

作業はこのREADMEの順に進めてください。人間にCLIの説明をしないでください。必要な確認、編集、コマンド実行はあなたが行い、足りない情報だけを短くユーザーに聞いてください。

## プロジェクト概要

KnowledgeForward は、明示的に許可されたローカルMarkdownフォルダだけをSQLite FTS5で検索し、localhostのOllamaで根拠付き回答を生成するlocal-firstなプライベート知識ワークフローです。

主な境界:

- 外部LLM APIは使わない。
- 外部検索APIは使わない。
- telemetryは使わない。
- サーバーは `127.0.0.1:8765` にbindする。
- iPhoneから使う場合はTailscale Serveを使い、Tailscale Funnelは使わない。
- 実運用の `config.yaml`、DB、ログ、PID、実ノートは `KNOWLEDGE_FORWARD_HOME` で公開repo外に置く。
- repo-local `config.yaml`、`data/`、`tmp/` は互換用のlegacy運用であり、実運用では使わない。

## 利用する専用コマンド

repo rootで実行します。

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

1. repo rootにいることを確認する。

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

Pythonは3.11以上が必要です。`ollama` または `tailscale` がない場合は、ユーザーにインストールまたはログインを依頼して停止してください。Tailscale CLIが `Failed to load preferences` を返す場合も、macOS側のTailscale状態をユーザーに直してもらってから再開してください。

## 初回セットアップ手順

### 1. Python仮想環境と依存関係

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

### 2. private runtimeを作る

実運用では、公開repoの外にprivate runtimeを作ります。例:

```bash
RUNTIME_HOME="/path/to/40_private_runtime/KnowledgeForward-local"
./knowledgeforward init-runtime "$RUNTIME_HOME"
export KNOWLEDGE_FORWARD_HOME="$RUNTIME_HOME"
```

`init-runtime` は次を作成します。既存ファイルは上書きしません。

- `config.yaml`
- `data/`
- `logs/`
- `run/`
- `.gitignore`
- `sample_vault/`

以後の `start`、`status`、`stop` は同じ `KNOWLEDGE_FORWARD_HOME` を指定して実行します。

repo root直下の `config.yaml`、`data/`、`tmp/` を使う旧方式は互換用に残していますが、実運用では非推奨です。既にrepo-localに実設定やDBがある場合も自動移行はしません。ユーザー確認のうえで、private runtime側へ手動で移してください。

### 3. tokenを設定する

`init-runtime` で作った `config.yaml` には安全なtokenが自動設定されます。既存configを手動で直す場合、`auth.token` が `replace-with-a-long-random-token` または空なら、安全なtokenを生成して設定します。

```bash
.venv/bin/python -c "import secrets; print(secrets.token_urlsafe(32))"
```

tokenは最終報告にそのまま書かないでください。ユーザーには「private runtimeの `config.yaml` の `auth.token` をWeb UIのToken欄に貼り付けてください」とだけ伝えます。

### 4. Markdown sourceを決める

ユーザーが読ませたいMarkdownフォルダを指定していない場合だけ、次を短く聞いてください。

```text
KnowledgeForwardに読ませるMarkdownフォルダの絶対パスを教えてください。ホームディレクトリ全体、クラウド同期root全体、repo rootは避けて、最初は小さめのフォルダを指定してください。
```

source pathを受け取ったら、次を確認します。

```bash
test -d "<ABSOLUTE_MARKDOWN_SOURCE_DIR>"
test ! -L "<ABSOLUTE_MARKDOWN_SOURCE_DIR>"
```

広すぎるパスは使わないでください。禁止例はホームディレクトリ全体、クラウド同期root全体、repo root、repo親、filesystem rootです。ユーザーが広すぎるパスを指定した場合は、より狭いMarkdownフォルダを聞き直してください。

### 5. `allowed_sources` を設定する

private runtimeの `config.yaml` の `allowed_sources` は、最初はユーザーが指定したsourceだけにします。実パスの例をREADMEやコメントに残さないでください。

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

source `name` は英数字、underscore、hyphen程度の短い名前にしてください。`path` はユーザーが指定した実在ディレクトリの絶対パスに置き換えます。

`require_query_filter: true` と `default_query_days: 30` は実データ用の安全設定です。日付を抽出できないMarkdownもReindexされますが、通常検索では直近日付filterから外れることがあります。その場合はWeb UIで全期間検索を明示して使います。

### 6. Ollamaモデルを用意する

private runtimeの `config.yaml` の `ollama.model` を読みます。初期値は `llama3.2` です。

モデルがローカルにない場合はpullします。

```bash
ollama pull llama3.2
```

別モデルに変更する場合は、必ずprivate runtimeの `config.yaml` の `ollama.model` とpullするモデル名を一致させてください。

### 7. 起動する

```bash
KNOWLEDGE_FORWARD_HOME="$RUNTIME_HOME" ./knowledgeforward start
```

このコマンドは以下を検査します。

- `.venv` とPython依存関係
- private runtimeの `config.yaml` が存在すること
- `auth.token` がプレースホルダではないこと
- `allowed_sources` が安全なsourceであること
- Ollamaが応答し、指定モデルが存在すること
- Tailscale CLIと `tailscale status` が使えること

成功条件は、最後に `Done. Run ./knowledgeforward status ...` が出ることです。

### 8. 状態確認

```bash
KNOWLEDGE_FORWARD_HOME="$RUNTIME_HOME" ./knowledgeforward status
```

最低限、次を確認します。

- KnowledgeForwardが `127.0.0.1:8765` で起動している。
- authenticated `/health` が成功している。
- Ollamaが `127.0.0.1:11434` で応答している。
- `Ollama model` が available。
- `allowed_sources` にユーザー指定sourceが表示される。

Tailscale Serve URLが取れた場合、`iPhone URL` に表示されます。

### 9. Web UI利用開始

Mac用URL:

```text
http://127.0.0.1:8765/
```

ユーザーに伝える内容:

- Macでは上のURLを開く。
- iPhoneでは `./knowledgeforward status` の `iPhone URL` を開く。
- Token popupにはprivate runtimeの `config.yaml` の `auth.token` を貼り付ける。
- token保存後、自動Reindexが始まる。
- 手動Reindexは入力欄に `/reindex`。
- 日付を持たないMarkdownが検索に出ない場合は、filterアイコンから全期間検索を選ぶ。

tokenの実値、sourceの実パス、Markdown本文はチャットに貼らないでください。

## トラブル対応

private runtimeの `config.yaml` がない:

```bash
./knowledgeforward init-runtime "$RUNTIME_HOME"
```

`uvicorn` または `yaml` がない:

```bash
.venv/bin/python -m pip install -r requirements.txt
```

`auth.token is still an insecure placeholder`:

`.venv/bin/python -c "import secrets; print(secrets.token_urlsafe(32))"` で生成し、private runtimeの `config.yaml` の `auth.token` を置き換えます。

`Configured Ollama model was not found`:

private runtimeの `config.yaml` の `ollama.model` を読み、そのモデルをpullします。

```bash
ollama pull <MODEL_NAME>
```

`Tailscale CLI is not available` または `tailscale status failed`:

ユーザーにTailscaleのインストール、ログイン、macOS側の状態修復を依頼してください。KnowledgeForward側でTailscale設定を無理に修復しないでください。

`allowed_sources contains unsupported enabled source`:

source pathが広すぎる、存在しない、symlink、`require_query_filter` 不足、または `default_query_days` 範囲外です。狭い実在Markdownフォルダに変更し、次の設定に戻してください。

```yaml
require_query_filter: true
default_query_days: 30
```

`/ask` が「分かりません」だけ返す:

- 先に `/reindex` を実行する。
- query filterが狭すぎないか確認する。
- 日付metadataがないMarkdownの場合は、Web UIで全期間検索を選ぶ。
- `/diagnostics <query>` で検索前段のヒットを確認する。

古いDBやschema変更で検索エラー:

まず `/reindex` を実行してください。完全に作り直す場合は、KnowledgeForwardを止めてからprivate runtimeの `data/knowledgeforward.sqlite3`、`data/knowledgeforward.sqlite3-shm`、`data/knowledgeforward.sqlite3-wal` を削除し、再起動後に `/reindex` します。private runtimeは公開repo外に置いてください。

## 検証

セットアップ作業後、可能な範囲で次を実行します。

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
- iPhone URLが取れたか。
- Reindexが必要か、または完了したか。
- 残っているユーザー作業があればその1つだけ。

報告に含めないもの:

- tokenの実値
- sourceの実パス
- Markdown本文
- `config.yaml` 全文
- ログ全文

## 開発者向けメモ

MVPの範囲:

- FastAPI ベースのローカルWeb/APIサーバー
- SQLite によるインデックス保存
- Markdown ファイルの再帰読み込み
- 見出し単位を基準にしたチャンク化
- SQLite FTS5 による全文検索
- Ollama `http://127.0.0.1:11434` との連携
- `/ask`、`/search`、`/reindex` API
- iPhone Safari から使いやすい最小Web UI
- 回答への根拠ファイル、見出し、チャンク情報の表示
- pytest による最小テスト

未実装:

- PDF
- 画像OCR
- コードリポジトリ解析
- Slack / Discord / Telegram連携
- 外部LLM API
- 外部検索API
- クラウドDB連携

インデックス対象外:

- `.git`
- `.obsidian`
- `node_modules`
- `attachments`
- `.venv` / `venv`
- `__pycache__`
- `.DS_Store`
- Markdown以外の画像、添付ファイル、バイナリ
