# KnowledgeForwardを使う前に

この文書は、KnowledgeForwardを使う前に「何をするソフトなのか」「安全面で何を確認すればよいのか」を見るための案内です。

READMEはCodex、Claude、またはファイル編集とコマンド実行ができるLLMに渡すための実行指示書です。自分で細かいコマンドを読むより、READMEをLLMに渡して作業してもらう前提で作っています。

## 詳しくない人へ

### まず安全面を確認したい場合

KnowledgeForwardはCodexで作成しているOSSです。使う前に不安がある場合は、次のファイルをCodex、Claude、ChatGPT、または詳しい人に渡して「危ない点がないか確認して」と聞いてください。

- `README.md`
- `docs/start-here.md`
- `SECURITY.md`

聞き方の例:

```text
このOSSを使う前に、安全面で気をつけることを確認してください。
特に、個人ノートが外部に送られないか、広すぎるフォルダを読まないか、tokenやDBがGitに入らないかを見てください。
```

KnowledgeForwardは、次の方針で作っています。

- ユーザーが `config.yaml` に明示したMarkdownフォルダだけを読みます。
- 外部LLM APIは使いません。
- 外部検索APIは使いません。
- telemetryは使いません。
- Mac内の `127.0.0.1` に閉じて起動します。
- iPhoneから使う場合はTailscale Serveを使います。
- Tailscale Funnelでインターネット全体へ公開する前提ではありません。
- `config.yaml`、DB、ログ、個人ノートをGitに入れない前提です。

ただし、OSSなので「絶対に安全」とは言えません。利用は自己責任です。不安が残る場合は、詳しい人やLLMに確認してから使ってください。

### これは何をするものか

KnowledgeForwardは、自分のMarkdownファイルを検索し、その検索結果を根拠としてローカルのOllamaに回答を作らせるツールです。

意図している使い方:

- 自分のメモやノートから、関連する情報を探す。
- 探した内容をもとに、要約や下書きを作る。
- Mac上で動くOllamaを使い、外部のAI APIへノートを送らない。

意図していない使い方:

- Mac全体やホームディレクトリ全体を読ませる。
- 個人ノート、token、DB、ログをGitHubへアップロードする。
- Tailscale Funnelなどでインターネット全体へ公開する。
- 法律、医療、金融などの重要判断を回答だけで決める。

### 使い始める方法

この文書だけでセットアップを進める必要はありません。READMEをCodexやClaudeなどに渡して、次のように依頼してください。

```text
このREADMEに従ってKnowledgeForwardを使い始められる状態にしてください。
私が指定したMarkdownフォルダだけを読ませてください。
token、実パス、ノート本文、ログ全文はチャットに貼らないでください。
```

LLMに作業してもらうときも、読ませるフォルダは小さめにしてください。ホームディレクトリ全体、クラウド同期root全体、repo rootは指定しないでください。

パスの例が必要な場合は、実パスを公開せずに `<ABSOLUTE_MARKDOWN_SOURCE_DIR>` のような置き方で相談してください。

### 免責

- KnowledgeForwardは無保証のOSSです。
- token、DB、ログ、個人ノートの管理は利用者自身の責任です。
- LLMの回答は間違うことがあります。
- 重要な判断は、回答だけに頼らず原文や専門家を確認してください。
- 法律、医療、金融などの判断にそのまま使わないでください。

## 詳しい人向け補足

### 構成

KnowledgeForwardは次の構成です。

- FastAPI: ローカルWeb/APIサーバー
- SQLite FTS5: Markdownチャンクの全文検索
- Ollama: localhostのローカルLLM
- Tailscale Serve: tailnet内のiPhone Safari向け公開

外部LLM API、外部検索API、telemetryはデフォルトで使いません。

### 主要コマンド

repo rootで `./knowledgeforward` を使います。

```bash
./knowledgeforward start
./knowledgeforward status
./knowledgeforward restart
./knowledgeforward stop
./knowledgeforward test
./knowledgeforward security-check
./knowledgeforward security-audit
```

`make` ターゲットも互換用に残していますが、主導線は `./knowledgeforward ...` です。

### 設定と安全境界

`config.yaml` はローカル設定ファイルで、Git管理しません。`allowed_sources` に明示されたフォルダだけを読みます。

実データ用sourceは次の形を基本にします。

```yaml
allowed_sources:
  - name: user_notes
    path: "<ABSOLUTE_MARKDOWN_SOURCE_DIR>"
    type: obsidian
    enabled: true
    require_query_filter: true
    default_query_days: 30
```

`require_query_filter: true` は、検索時に日付filterを要求するための安全設定です。全期間検索はユーザーが明示した場合だけにします。

### 改造前に見るファイル

- `knowledge_forward/config.py`
- `knowledge_forward/source_safety.py`
- `knowledge_forward/api.py`
- `scripts/start.sh`
- `SECURITY.md`
- `CONTRIBUTING.md`

特に、読み込み対象フォルダの検証、token、ログ、DB、Tailscale公開範囲を変更する場合は、先に `SECURITY.md` の境界と矛盾しないか確認してください。

### 改造前チェック

変更前後で最低限次を実行してください。

```bash
./knowledgeforward test
./knowledgeforward security-check
./knowledgeforward security-audit
```

`security-audit full` はローカルに入っている監査ツールの状態に依存します。失敗した場合は、どのツールがなぜ失敗したかを切り分けてください。
