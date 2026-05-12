# KnowledgeForward

KnowledgeForward は、許可したローカル Markdown フォルダだけを SQLite FTS5 で検索し、localhost の Ollama で根拠付き回答や下書きを生成する local-first なプライベート知識ワークフローです。

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

## セットアップ

Python 3.11 以上を想定しています。

```bash
cd /path/to/KnowledgeForward
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp config.example.yaml config.yaml
```

Ollama のモデルは KnowledgeForward から自動 pull しません。事前にユーザー側で準備してください。

```bash
ollama pull llama3.2
```

日常利用では `make start` が Ollama の応答を確認し、未起動なら `ollama serve` を起動します。別のモデルを使う場合はコピー後の `config.yaml` の `ollama.model` を変更します。一時的に差し替える場合は `KNOWLEDGE_FORWARD_OLLAMA_MODEL` も使えます。`ollama.hide_thinking: true` のときは Ollama に `think: false` を渡し、`message.thinking` や本文内の `<think>...</think>` をユーザーへ返しません。

## 設定

`config.example.yaml` をコピーして `config.yaml` を作成します。`config.yaml` は本物のトークンや個人パスを含む前提のローカル設定ファイルなので、Git管理しません。

初期状態の `config.example.yaml` はサンプルVaultだけを参照します。

```yaml
allowed_sources:
  - name: sample_vault
    path: ./fixtures/sample_vault
    type: obsidian
    enabled: true
```

本物の Obsidian Vault は自動探索しません。後で使う場合は、ユーザーが `allowed_sources` に手動で追加してください。allowlist にないフォルダは読みません。

年月日ツリーで管理しているVaultでは、`Knowledge/01_data` のような年月日rootを一度インデックス対象にできます。DBには全期間の本文チャンク、相対パス、日付、タグなどのmetadataが入ります。`data/` と `data/knowledgeforward.sqlite3` は絶対にGit管理しないでください。

```yaml
allowed_sources:
  - name: knowledge_01_data
    path: "/path/to/Knowledge/01_data"
    type: obsidian
    enabled: true
    require_query_filter: true
    default_query_days: 30
```

`require_query_filter: true` の source は、`/search` と `/ask` のたびに query-time filter が適用されます。filters がない場合や、tag/sourceだけで全期間に広がり得る場合は、`default_query_days` による直近N日フィルタを自動適用します。未指定時は30日で、1〜365の範囲だけを許可します。全期間検索は Web UI で「全期間」を明示選択するか、APIで `all_time: true` を送った場合だけです。

日付metadataは source root からの相対パスだけを見ます。対応する日付パターンは `YYYY/MM/DD/YYYY-MM-DD.md`、`YYYY/MM/DD/*.md`、`YYYY-MM-DD.md` です。日付を抽出できない Markdown もインデックスされますが、date filter や default date filter が適用された検索では対象外です。

実Vaultを `make start` で使う場合、`scripts/start.sh` は `./tmp/private_test_vault` と `./fixtures/sample_vault` 以外の enabled source について、`type: obsidian`、`require_query_filter: true`、安全範囲の `default_query_days`、存在する非symlink directory、広すぎないrootだけを許可します。Obsidian VaultやiCloud Drive root、ホームディレクトリ、repo root、repo親、filesystem rootのような広いrootは拒否します。Vaultの自動探索は行いません。

`auth.token` はAPI用トークンです。`config.example.yaml` の `replace-with-a-long-random-token` はプレースホルダで、そのままでは起動できません。実運用前に必ず推測されにくい値へ変更してください。

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

生成した値を `config.yaml` の `auth.token` に設定します。環境変数 `KNOWLEDGE_FORWARD_AUTH_TOKEN` を設定すると `config.yaml` より優先されます。

## 日常利用の起動

日常利用では、Ollama、KnowledgeForward、Tailscale Serve を別々に手動起動せず、repo root から `make` ターゲットを使います。

運用確認が終わるまでは、`allowed_sources` は `./tmp/private_test_vault` のみ、または `./fixtures/sample_vault` と `./tmp/private_test_vault` のみにしてください。本物の Obsidian Vault、iCloud Drive、親/兄弟ディレクトリ、ホームディレクトリ全体はまだ追加しません。

```bash
make start
```

`make start` は次を確認してから KnowledgeForward を起動します。

- `.venv` と `requirements.txt` の依存
- `config.yaml` が存在し、Git管理外であること
- `auth.token` がサンプルのプレースホルダではないこと
- `allowed_sources` がテスト用Vault、または query-time filter 必須の安全なsourceであること
- Ollama が `http://127.0.0.1:11434` で応答すること。未起動なら `ollama serve` を起動すること
- `config.yaml` の `ollama.model` が Ollama に存在すること
- Tailscale CLI と `tailscale status` が使えること

KnowledgeForward は常に `127.0.0.1:8765` に bind します。`0.0.0.0` bind は使いません。

すでに Ollama が起動している場合、`make start` は既存の Ollama を使います。KnowledgeForward は `make stop` で Ollama サーバー自体を停止しません。

ログとPIDファイルはrepo内の次の場所に置きます。

```text
tmp/logs/knowledgeforward.log
tmp/run/knowledgeforward.pid
tmp/logs/ollama.log
tmp/run/ollama.pid
tmp/run/ollama.managed
```

`tmp/logs/ollama.log` は KnowledgeForward が `ollama serve` を起動した場合だけ使います。`tmp/run/ollama.pid` はその PID、`tmp/run/ollama.managed` は KnowledgeForward が起動したことを示す marker です。

状態確認は次を使います。

```bash
make status
```

Ollama が応答している場合、`make status` は `ollama ps` を使って現在ロード中のモデル名も表示します。

再起動は停止後に起動します。

```bash
make restart
```

停止は次を使います。

```bash
make stop
```

`make stop` は KnowledgeForward プロセスを止め、KnowledgeForward 用の Tailscale Serve 設定を削除します。その後、`config.yaml` の `ollama.model` を `ollama stop <model>` で unload します。これは keep_alive によりメモリ上に残るモデルを解放するための処理で、Ollama サーバー自体は停止しません。KnowledgeForwardログ、token、Markdown本文は表示しません。

モデルをメモリ上に残したい場合は、次のように unload をスキップできます。

```bash
KNOWLEDGE_FORWARD_SKIP_MODEL_UNLOAD=1 make stop
```

手動で unload する場合は次を使います。

```bash
ollama stop qwen3:8b
ollama ps
```

ローカルMacで直接確認する場合は、起動後に次を開きます。

```text
http://127.0.0.1:8765/
```

現在のWeb UIでは、token未保存時だけ起動時にToken入力popupを表示します。token保存済みなら起動時に自動でReindexします。tokenはブラウザセッション内だけに保存します。通常入力は `/ask` に送られます。下部入力欄左のfilterアイコンでfilter設定を開きます。入力欄で `/` を打つとcommand候補を表示します。手動でReindexする場合は `/reindex`、検索診断をする場合は `/diagnostics <query>`、セキュリティ診断のfull実行は `/security` を入力します。

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

`/search` は通常検索UIではなく診断用です。`page_size` と `offset` でページングし、レスポンスに `total_count`、`returned_count`、`offset`、`page_size`、`has_more`、`applied_filters`、`default_filter_applied` を返します。後方互換のため `limit` も受け取りますが、`page_size` 相当として扱います。検索結果一覧は本文全文 `content` を返さず、metadata と `snippet` を返します。

`/ask` は filter 後の上位チャンクだけを、信頼しない参考文書として Ollama に渡します。Markdown本文内の命令は、システム命令として扱いません。根拠が見つからない場合は Ollama を呼ばずに「分かりません」と返します。レスポンスには `applied_filters`、`default_filter_applied`、`used_ollama`、filter後に使われた citations が含まれます。citations は `source_name`、`relative_path`、`document_date`、`heading`、`chunk_index`、`match_source`、`score` を返し、内部絶対パスは返しません。

## Tailscale経由でiPhoneから使う

KnowledgeForward は `127.0.0.1:8765` に閉じたまま起動し、Tailscale Serve で tailnet 内だけに公開します。Tailscale Funnel は使いません。

`make start` は KnowledgeForward 起動後に次の永続Serve設定を行います。

```bash
tailscale serve --bg localhost:8765
```

この設定は tailnet 内向けです。インターネット公開用の Funnel コマンドは実行しません。

iPhone から開く手順:

1. Macで `make start` を実行します。
2. Macで `make status` を実行します。
3. `iPhone URL` に表示された Tailscale Serve URL を iPhone Safari で開きます。
4. Web UI の Token 入力popupに `config.yaml` の `auth.token` を入力します。
5. token はURLに含めません。

注意:

- Tailscale 公開時もAPIトークン認証を必ず使ってください。
- `auth.token` はプレースホルダのままにしないでください。
- 信頼できないネットワークやLANへ直接公開しないでください。
- macOS ファイアウォールや Tailscale ACL で到達元を制限してください。
- Tailscale Funnel は今回の用途では不要です。インターネットへ外部公開せず、tailnet 内だけで使ってください。
- KnowledgeForward は外部LLM APIや外部検索APIを使わず、Ollama localhost への接続だけを前提にしています。

## 実データ投入前の手順

実データを読ませる前に、対象範囲を小さく保って段階的に確認してください。

1. まず `fixtures/sample_vault` だけで `/reindex`、`/search`、`/ask` を確認する
2. 次に、個人情報を含まない小さなテストVaultを作り、`allowed_sources` に追加して確認する
3. その後、Obsidian Vault の小さな期間を `date_from` / `date_to` filter 付きで確認する
4. `Knowledge/01_data` rootを追加する場合は、`require_query_filter: true` と `default_query_days: 30` を設定する
5. `/reindex` 後に `/search` と `/ask` が filter 後の citations だけを返すことを確認する
6. 全期間検索は必要な時だけ明示的に選ぶ
7. Obsidian Vault の場所は自動探索しない
8. ユーザーが `config.yaml` に明示したパスだけを読む

## テスト

```bash
source .venv/bin/activate
pytest
python -m compileall knowledge_forward tests
```

または次を使います。

```bash
make test
```

テストでは一時ディレクトリ内のダミーMarkdownと、Fake Ollama クライアントを使います。本物の Obsidian Vault や外部資料は読みません。

## トラブルシュート

`uvicorn` がない:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
```

`yaml` がない:

`PyYAML` が不足しています。`.venv` を有効化し、`python -m pip install -r requirements.txt` を再実行してください。

`ollama command not found`:

Ollama CLI が `PATH` にありません。Ollama をインストールし、通常の端末で次が通る状態にしてください。

```bash
ollama --version
```

`port 11434 already in use`:

`make start` は最初に `http://127.0.0.1:11434/api/tags` を確認します。応答があれば既存 Ollama として使います。ポートは使われているのに応答しない場合は、別プロセスや壊れた Ollama が残っている可能性があります。KnowledgeForward は port 11434 のプロセスを無条件に kill しないので、通常の端末で手動確認してください。

Ollama model not found:

`config.yaml` の `ollama.model` が Ollama に存在しません。KnowledgeForward はモデルを自動 pull しないため、事前にモデルを用意してください。

```bash
ollama pull <model-name>
```

別モデルを使う場合は `config.yaml` の `ollama.model` を変更します。

Ollama responds but KnowledgeForward cannot answer:

- `make status` で `Ollama model` が available になっているか確認します。
- `/ask` は検索根拠がない場合、Ollama を呼ばずに「分かりません」と返します。先に `Reindex` または `/reindex` を実行してください。
- Ollama は応答していてもモデルロードや生成で失敗する場合があります。KnowledgeForward が起動した Ollama なら `tmp/logs/ollama.log`、KnowledgeForward 本体は `tmp/logs/knowledgeforward.log` を確認してください。

Tailscale CLI がない:

MacにTailscaleをインストールし、`tailscale status` が通る状態にしてください。`make start` はTailscale CLIが使えない場合に停止します。

Tailscale CLI が `Failed to load preferences` を返す:

Tailscale for macOS 側の設定やログイン状態を確認してください。KnowledgeForward のスクリプトは、この状態を自動修復したり、macOS側のTailscale設定を変更したりしません。`tailscale status` が通常の端末から成功する状態になってから、`make start` を再実行してください。

`Serve is not enabled on your tailnet`:

Tailscale Serve が tailnet 側で未有効です。Tailscale CLI が表示する案内に従い、Tailscale管理画面で Serve / HTTPS certificates を有効化してください。KnowledgeForward 側では Funnel を使いません。

iPhoneからURLが開けない:

- iPhone が同じ tailnet にログインしているか確認します。
- Macで `make status` を実行し、`tailscale status` と `tailscale serve status` を確認します。
- `iPhone URL` が表示されない場合は、`tailscale serve status` の出力にある tailnet URL を使います。
- KnowledgeForward が `127.0.0.1:8765` で起動しているか確認します。

token認証で失敗する:

- token はURLに入れず、Web UI の Token 欄に入力します。
- 現在のWeb UIでは、token未保存時だけ Token 入力popupが開きます。
- `config.yaml` の `auth.token` がプレースホルダでないことを確認します。
- ブラウザに古いtokenが保存されている場合は、Token欄に現在のtokenを入れ直します。
- `make status` の authenticated `/health` が成功するか確認します。

## push前チェック

```bash
make security-check
```

固定されたセキュリティ診断は次でも実行できます。`PROFILE=full` を付けると、導入済みの監査ツールも実行します。未導入ツールはスキップします。

```bash
make security-audit
PROFILE=full make security-audit
```

push前には `make security-check` を実行してください。`config.yaml` は本物のトークンや個人パスを含むローカル設定なので、絶対にcommitしません。`data/` と `tmp/` も絶対にcommitしません。DBにはローカル絶対パスや本文チャンクが入るため、Git管理してはいけません。実tokenを誤ってpushした場合は、履歴削除だけでなくtokenローテーションも必要です。

ログにはMarkdown本文チャンク、token、`config.yaml` 全文、実Vaultパスを出さない方針です。`security-check` は `config.yaml`、`data/`、`tmp/`、SQLite DB、credentialらしい文字列、ローカル絶対パスの混入を検査します。

schema変更後や古いDBで検索エラーが出た場合は `/reindex` を実行してください。完全に作り直す場合は KnowledgeForward を止めてから `data/knowledgeforward.sqlite3` と `data/knowledgeforward.sqlite3-shm`、`data/knowledgeforward.sqlite3-wal` を削除し、再起動後に `/reindex` します。`data/` はGit管理外のままにしてください。

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
