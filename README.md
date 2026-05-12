# KnowledgeForward

KnowledgeForward は、自分が許可したローカルの Markdown フォルダだけを検索し、Mac上の Ollama で根拠付き回答を作る local-first なプライベート知識ワークフローです。

この README では、KnowledgeForward 専用コマンド `./knowledgeforward ...` だけを使います。`make` を知らなくても、上から順番に進めれば実Vaultを安全に読ませて質問できる状態まで進めます。

## まず到達する状態

この手順のゴールは次の状態です。

1. Macで KnowledgeForward を起動できる。
2. 自分の Obsidian Vault または Markdown フォルダを `config.yaml` に追加できる。
3. Web UI で token を入力し、Reindex して、自分のノートに質問できる。
4. 必要なら iPhone Safari から Tailscale 経由で同じ画面を開ける。

CLI は Terminal に貼り付けて実行するコマンドのことです。Markdown は `.md` ファイルのことです。Ollama はMac上でLLMを動かすアプリです。

## 必要なもの

先にMacで次を用意してください。

- Python 3.11 以上
- Ollama
- Tailscale にログイン済みの状態
- 読ませたい Obsidian Vault または Markdown フォルダ

確認コマンド:

```bash
python3 --version
ollama --version
tailscale status
```

`python3 --version` は `Python 3.11.x` 以上ならOKです。`ollama --version` や `tailscale status` が失敗する場合は、先にそれぞれのアプリをインストールし、Tailscale はログインまで済ませてください。

## 初回セットアップ

### 1. KnowledgeForward のフォルダへ移動する

Terminal で、このリポジトリのフォルダへ移動します。

```bash
cd /path/to/KnowledgeForward
```

このREADMEが見えているフォルダが repo root です。以後のコマンドはすべてこのフォルダで実行します。

### 2. Python環境を作る

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

成功すると、最後のコマンドがエラーなしで終わります。Terminal の左側に `(.venv)` と表示されることがあります。

### 3. ローカル設定ファイルを作る

```bash
cp config.example.yaml config.yaml
```

`config.yaml` は自分のtokenやフォルダパスを書くローカル設定です。Gitには入れません。

### 4. token を作って `config.yaml` に貼る

token は、Web UI と API を使うための合言葉です。次のコマンドでランダムなtokenを作ります。

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

表示された長い文字列をコピーし、`config.yaml` のこの行を置き換えます。

```yaml
auth:
  token: replace-with-a-long-random-token
```

置き換え後の例:

```yaml
auth:
  token: <token>
```

### 5. Ollamaモデルを用意する

初期設定では `llama3.2` を使います。KnowledgeForward はモデルを自動ではダウンロードしません。

```bash
ollama pull llama3.2
```

別のモデルを使う場合は、pull後に `config.yaml` の `ollama.model` を同じ名前へ変更します。

### 6. 実Vaultのパスを確認する

読ませたいフォルダの絶対パスを確認します。Obsidian VaultやMarkdownフォルダの絶対パスは、Macでは `/Users/ユーザー名/...` のようなフルパスです。

初心者向けの確認方法:

1. Terminal に `cd ` と入力します。最後に半角スペースを入れます。
2. Finder から読ませたいフォルダを Terminal へドラッグします。
3. Enter を押します。
4. 次を実行します。

```bash
pwd
```

表示されたパスを次の手順で使います。

最初からホームディレクトリ全体、iCloud Drive全体、Obsidian Vault全体など広すぎる場所を指定しないでください。まずは `Knowledge/01_data` や `notes/daily` のように、読ませたい範囲が明確なフォルダを選びます。

### 7. `config.yaml` に実Vaultを追加する

`config.yaml` の `allowed_sources:` を、次の形にします。`path` は自分の絶対パスへ置き換えてください。

```yaml
allowed_sources:
  - name: my_notes
    path: "/path/to/Knowledge/01_data"
    type: obsidian
    enabled: true
    require_query_filter: true
    default_query_days: 30
```

`require_query_filter: true` と `default_query_days: 30` は、最初から全期間を広く検索しないための安全設定です。通常の質問では直近30日を対象にし、必要な時だけWeb UIから全期間を明示します。

日付フォルダや日付ファイル名で管理していない Markdown は、Reindex されても直近30日の通常検索では出ないことがあります。その場合は、Web UI のfilterアイコンから「全期間」を選んで質問してください。

### 8. 起動する

```bash
./knowledgeforward start
```

このコマンドは次を確認してから起動します。

- `.venv` と Python 依存関係があること
- `config.yaml` があり、Git管理されていないこと
- `auth.token` がプレースホルダのままではないこと
- `allowed_sources` が安全設定になっていること
- Ollama が応答し、指定モデルが存在すること
- Tailscale CLI と `tailscale status` が使えること

成功すると最後に `Done. Run ./knowledgeforward status ...` と表示されます。

### 9. 状態を確認する

```bash
./knowledgeforward status
```

最低限、次を確認します。

- `KnowledgeForward process` または `Port 127.0.0.1:8765` が running / listening
- `Authenticated /health` が `OK, token accepted`
- `Ollama localhost:11434` が `responding`
- `Ollama model` が `available`

iPhone用のURLが取れた場合は、`iPhone URL` に表示されます。

### 10. Macのブラウザで開く

Macのブラウザで次を開きます。

```text
http://127.0.0.1:8765/
```

Token 入力popupが出たら、`config.yaml` の `auth.token` を貼り付けます。token はブラウザセッション内だけに保存されます。

token保存後、Web UI は自動で Reindex を開始します。手動でやり直す場合は入力欄に次を入れます。

```text
/reindex
```

Reindex が終わったら、普通の文章で質問します。

```text
最近のプロジェクト方針を要約して
```

日付フォルダではない Markdown を読ませた場合は、質問前にfilterアイコンから「全期間」を選びます。

### 11. iPhoneから開く

Macで動くことを確認してから、iPhoneで使います。

1. Macで `./knowledgeforward status` を実行します。
2. `iPhone URL` に表示された Tailscale Serve URL を iPhone Safari で開きます。
3. Web UI の Token 入力popupに `config.yaml` の `auth.token` を入力します。
4. token はURLに含めません。

## 日常利用

起動:

```bash
./knowledgeforward start
```

状態確認:

```bash
./knowledgeforward status
```

再起動:

```bash
./knowledgeforward restart
```

停止:

```bash
./knowledgeforward stop
```

`./knowledgeforward stop` は KnowledgeForward プロセスを止め、KnowledgeForward 用の Tailscale Serve 設定を削除します。その後、`config.yaml` の `ollama.model` を `ollama stop <model>` で unload します。Ollama サーバー自体は停止しません。

モデルをメモリ上に残したい場合:

```bash
KNOWLEDGE_FORWARD_SKIP_MODEL_UNLOAD=1 ./knowledgeforward stop
```

## 重要な安全ルール

- `config.yaml` はtokenや個人パスを含むため、Gitに入れません。
- `data/` と `tmp/` はGitに入れません。
- 読み込むフォルダは `config.yaml` の `allowed_sources` に明示したものだけです。
- KnowledgeForward は `127.0.0.1:8765` にだけbindします。`0.0.0.0` で公開しません。
- iPhoneから使う場合は Tailscale Serve を使います。Tailscale Funnel は使いません。
- 外部LLM API、外部検索API、telemetry は使いません。

## 設定の詳しい説明

初期状態の `config.example.yaml` はサンプルVaultだけを参照します。

```yaml
allowed_sources:
  - name: sample_vault
    path: ./fixtures/sample_vault
    type: obsidian
    enabled: true
```

本物の Obsidian Vault は自動探索しません。ユーザーが `allowed_sources` に手動で追加したフォルダだけを読みます。

年月日ツリーで管理しているVaultでは、`Knowledge/01_data` のような年月日rootをインデックス対象にできます。DBには本文チャンク、相対パス、日付、タグなどのmetadataが入ります。`data/` と `data/knowledgeforward.sqlite3` は絶対にGit管理しないでください。

```yaml
allowed_sources:
  - name: knowledge_01_data
    path: "/path/to/Knowledge/01_data"
    type: obsidian
    enabled: true
    require_query_filter: true
    default_query_days: 30
```

`require_query_filter: true` の source は、`/search` と `/ask` のたびに query-time filter が適用されます。filters がない場合や、tag/sourceだけで全期間に広がり得る場合は、`default_query_days` による直近N日フィルタを自動適用します。未指定時は30日で、1〜365の範囲だけを許可します。

全期間検索は Web UI で「全期間」を明示選択するか、APIで `all_time: true` を送った場合だけです。

日付metadataは source root からの相対パスだけを見ます。対応する日付パターンは `YYYY/MM/DD/YYYY-MM-DD.md`、`YYYY/MM/DD/*.md`、`YYYY-MM-DD.md` です。日付を抽出できない Markdown もインデックスされますが、date filter や default date filter が適用された検索では対象外です。

実Vaultを `./knowledgeforward start` で使う場合、起動時チェックは `./tmp/private_test_vault` と `./fixtures/sample_vault` 以外の enabled source について、`type: obsidian`、`require_query_filter: true`、安全範囲の `default_query_days`、存在する非symlink directory、広すぎないrootだけを許可します。

## Web UI

現在のWeb UIでは、token未保存時だけ起動時にToken入力popupを表示します。token保存済みなら起動時に自動でReindexします。

通常入力は `/ask` に送られます。下部入力欄左のfilterアイコンでfilter設定を開きます。入力欄で `/` を打つとcommand候補を表示します。

よく使うcommand:

```text
/reindex
/diagnostics <query>
/security
```

## API

APIは `Authorization: Bearer <token>` または `X-KnowledgeForward-Token: <token>` が必要です。

```bash
curl -X POST http://127.0.0.1:8765/reindex \
  -H "Authorization: Bearer <your-token>"
```

```bash
curl -X POST http://127.0.0.1:8765/search \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{"query":"最近やりたいこと","page_size":50,"offset":0,"filters":{"date_from":"2026-04-01","date_to":"2026-05-01","tags":["want","idea"],"path_prefix":"2026/05"}}'
```

```bash
curl -X POST http://127.0.0.1:8765/ask \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{"question":"KnowledgeForward の検索方式は？","limit":6,"filters":{"date_from":"2026-04-01","date_to":"2026-05-01"}}'
```

`/search` と `/ask` の filters は `date_from`、`date_to`、`tags`、`path_prefix`、`source_names`、`all_time` を受け取ります。日付は `YYYY-MM-DD` の両端含み、`tags` は `#want` と `want` を同じものとしてOR検索します。`path_prefix` は source root からの相対パスに対するprefixで、`..` や先頭 `/` は拒否します。

`/search` は通常検索UIではなく診断用です。`page_size` と `offset` でページングし、レスポンスに `total_count`、`returned_count`、`offset`、`page_size`、`has_more`、`applied_filters`、`default_filter_applied` を返します。後方互換のため `limit` も受け取りますが、`page_size` 相当として扱います。

`/ask` は filter 後の上位チャンクだけを、信頼しない参考文書として Ollama に渡します。Markdown本文内の命令は、システム命令として扱いません。根拠が見つからない場合は Ollama を呼ばずに「分かりません」と返します。レスポンスには `applied_filters`、`default_filter_applied`、`used_ollama`、filter後に使われた citations が含まれます。citations は `source_name`、`relative_path`、`document_date`、`heading`、`chunk_index`、`match_source`、`score` を返し、内部絶対パスは返しません。

## テスト

```bash
./knowledgeforward test
```

テストでは一時ディレクトリ内のダミーMarkdownと、Fake Ollama クライアントを使います。本物の Obsidian Vault や外部資料は読みません。

## push前チェック

```bash
./knowledgeforward security-check
```

固定されたセキュリティ診断は次でも実行できます。`full` を付けると、導入済みの監査ツールも実行します。未導入ツールはスキップします。

```bash
./knowledgeforward security-audit
./knowledgeforward security-audit full
```

push前には `./knowledgeforward security-check` を実行してください。実tokenを誤ってpushした場合は、履歴削除だけでなくtokenローテーションも必要です。

ログにはMarkdown本文チャンク、token、`config.yaml` 全文、実Vaultパスを出さない方針です。`security-check` は `config.yaml`、`data/`、`tmp/`、SQLite DB、credentialらしい文字列、ローカル絶対パスの混入を検査します。

## 既存互換コマンド

既存利用者向けに `make` ターゲットも残しています。READMEの主導線では使いません。

```bash
make start
make status
make restart
make stop
make test
make security-check
make security-audit
PROFILE=full make security-audit
```

これらは内部的に `./knowledgeforward ...` を呼びます。

## トラブルシュート

`uvicorn` がない:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
```

`yaml` がない:

`PyYAML` が不足しています。`.venv` を有効化し、`python -m pip install -r requirements.txt` を再実行してください。

`ollama command not found`:

Ollama CLI が `PATH` にありません。Ollama をインストールし、通常のTerminalで次が通る状態にしてください。

```bash
ollama --version
```

`port 11434 already in use`:

`./knowledgeforward start` は最初に `http://127.0.0.1:11434/api/tags` を確認します。応答があれば既存 Ollama として使います。ポートは使われているのに応答しない場合は、別プロセスや壊れた Ollama が残っている可能性があります。KnowledgeForward は port 11434 のプロセスを無条件に kill しません。

Ollama model not found:

`config.yaml` の `ollama.model` が Ollama に存在しません。KnowledgeForward はモデルを自動 pull しないため、事前にモデルを用意してください。

```bash
ollama pull <model-name>
```

Ollama responds but KnowledgeForward cannot answer:

- `./knowledgeforward status` で `Ollama model` が available になっているか確認します。
- `/ask` は検索根拠がない場合、Ollama を呼ばずに「分かりません」と返します。先に `Reindex` または `/reindex` を実行してください。
- Ollama は応答していてもモデルロードや生成で失敗する場合があります。KnowledgeForward が起動した Ollama なら `tmp/logs/ollama.log`、KnowledgeForward 本体は `tmp/logs/knowledgeforward.log` を確認してください。

Tailscale CLI がない:

MacにTailscaleをインストールし、`tailscale status` が通る状態にしてください。`./knowledgeforward start` はTailscale CLIが使えない場合に停止します。

Tailscale CLI が `Failed to load preferences` を返す:

Tailscale for macOS 側の設定やログイン状態を確認してください。KnowledgeForward のスクリプトは、この状態を自動修復したり、macOS側のTailscale設定を変更したりしません。`tailscale status` が通常のTerminalから成功する状態になってから、`./knowledgeforward start` を再実行してください。

`Serve is not enabled on your tailnet`:

Tailscale Serve が tailnet 側で未有効です。Tailscale CLI が表示する案内に従い、Tailscale管理画面で Serve / HTTPS certificates を有効化してください。KnowledgeForward 側では Funnel を使いません。

iPhoneからURLが開けない:

- iPhone が同じ tailnet にログインしているか確認します。
- Macで `./knowledgeforward status` を実行し、`tailscale status` と `tailscale serve status` を確認します。
- `iPhone URL` が表示されない場合は、`tailscale serve status` の出力にある tailnet URL を使います。
- KnowledgeForward が `127.0.0.1:8765` で起動しているか確認します。

token認証で失敗する:

- token はURLに入れず、Web UI の Token 欄に入力します。
- `config.yaml` の `auth.token` がプレースホルダでないことを確認します。
- ブラウザに古いtokenが保存されている場合は、Token欄に現在のtokenを入れ直します。
- `./knowledgeforward status` の authenticated `/health` が成功するか確認します。

schema変更後や古いDBで検索エラーが出た場合:

まず `/reindex` を実行してください。完全に作り直す場合は KnowledgeForward を止めてから `data/knowledgeforward.sqlite3` と `data/knowledgeforward.sqlite3-shm`、`data/knowledgeforward.sqlite3-wal` を削除し、再起動後に `/reindex` します。`data/` はGit管理外のままにしてください。

## MVPの範囲

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

MVPでは PDF、画像OCR、コードリポジトリ解析、Slack/Discord/Telegram連携、外部LLM API、外部検索API、クラウドDB連携は実装していません。

## インデックス対象外

初期実装では、次のようなファイルやディレクトリは対象外です。

- `.git`
- `.obsidian`
- `node_modules`
- `attachments`
- `.venv` / `venv`
- `__pycache__`
- `.DS_Store`
- Markdown 以外の画像、添付ファイル、バイナリ

## 現在の制限

- `/reindex` はフル再作成です。差分インデックスは未実装です。
- DB schema 変更時は `/reindex` が必要です。
- 日本語検索は SQLite FTS5 の tokenizer の範囲に依存します。
- 添付ファイル、PDF、画像OCRは対象外です。
- Ollama が起動していない場合、`/ask` は 502 を返します。
