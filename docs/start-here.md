# KnowledgeForwardを使う前に

この文書は、KnowledgeForwardを使う前に「何をするソフトなのか」「安全面で何を確認すればよいのか」「最初にどう起動するのか」を見るための案内です。

公開 repo の入口は [README](../README.md) です。Codex や Claude などのコーディングエージェントに初回セットアップを任せる場合は [agent setup guide](agent-setup.md) を渡してください。

## まず安全面を確認したい場合

KnowledgeForwardはOSSです。使う前に不安がある場合は、次のファイルをCodex、Claude、ChatGPT、または詳しい人に渡して「危ない点がないか確認して」と聞いてください。

- `README.md`
- `docs/start-here.md`
- `SECURITY.md`

聞き方の例:

```text
このOSSを使う前に、安全面で気をつけることを確認してください。
特に、個人ノートが外部に送られないか、広すぎるフォルダを読まないか、tokenやDBがGitに入らないかを見てください。
```

KnowledgeForwardは、次の方針で作っています。

- private runtime の `config.yaml` に明示した Markdown フォルダだけを読みます。
- 外部 LLM API は使いません。
- 外部検索 API は使いません。
- telemetry は使いません。
- Mac 内の `127.0.0.1` に閉じて起動します。
- iPhone から使う場合は Tailscale Serve を使います。
- Tailscale Funnel でインターネット全体へ公開する前提ではありません。
- 実運用の `config.yaml`、DB、ログ、PID、個人ノートは KnowledgeForward の repo ディレクトリ外、または少なくとも Git 管理外に置く前提です。

ただし、OSSなので「絶対に安全」とは言えません。利用は自己責任です。不安が残る場合は、詳しい人やLLMに確認してから使ってください。

## これは何をするものか

KnowledgeForwardは、自分のMarkdownファイルを検索し、その検索結果を根拠としてローカルのOllamaに回答を作らせるツールです。

意図している使い方:

- 自分のメモやノートから、関連する情報を探す。
- 探した内容をもとに、要約や下書きを作る。
- Mac上で動くOllamaを使い、外部のAI APIへノートを送らない。

意図していない使い方:

- Mac全体やホームディレクトリ全体を読ませる。
- 個人ノート、token、DB、ログを Git 管理や共有場所へアップロードする。
- Tailscale Funnelなどでインターネット全体へ公開する。
- 法律、医療、金融などの重要判断を回答だけで決める。

## 初回利用の流れ

1. repo root で Python 仮想環境を作ります。

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

2. repo ディレクトリ外に private runtime を作ります。

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

3. private runtime の `config.yaml` で、読ませる Markdown フォルダを小さめに指定します。ホームディレクトリ全体、クラウド同期 root 全体、repo root は指定しないでください。

```yaml
allowed_sources:
  - name: user_notes
    path: "<ABSOLUTE_MARKDOWN_SOURCE_DIR>"
    type: obsidian
    enabled: true
    require_query_filter: true
    default_query_days: 30
```

`require_query_filter: true` は、検索時に日付 filter を要求するための安全設定です。全期間検索はユーザーが明示した場合だけにします。

4. Ollama モデルを用意し、起動します。

```bash
ollama pull llama3.2
KNOWLEDGE_FORWARD_HOME="$RUNTIME_HOME" ./knowledgeforward start
KNOWLEDGE_FORWARD_HOME="$RUNTIME_HOME" ./knowledgeforward status
```

Macでは `http://127.0.0.1:8765/` を開きます。iPhoneでは `status` の `iPhone URL` を開きます。Web UIの Token 欄には private runtime の `config.yaml` の `auth.token` を貼り付けます。

## private runtime

private runtime は、KnowledgeForward の repo と個人 runtime を分けるためのローカル専用ディレクトリです。実運用ではここに `config.yaml`、DB、ログ、PID、Ollama 管理ファイルを置きます。token、実パス、ログ全文、private runtime の `config.yaml` 全文を issue、PR、チャットに貼らないでください。

設定ファイルの優先順は次の通りです。

1. Python API などから渡された明示引数
2. `KNOWLEDGE_FORWARD_CONFIG`
3. `KNOWLEDGE_FORWARD_HOME/config.yaml`
4. 自動検出された private runtime の `config.yaml`
5. repo-local `config.yaml`

別名の config を使う場合は `KNOWLEDGE_FORWARD_CONFIG` を使えます。標準以外の runtime 場所を使う場合は、そのコマンドだけ `KNOWLEDGE_FORWARD_HOME` を付けて実行できます。

`KNOWLEDGE_FORWARD_HOME` と `KNOWLEDGE_FORWARD_CONFIG` が未設定で、private runtime も自動検出できない場合、互換用に repo-local `config.yaml`、`data/`、`tmp/` を使う legacy runtime へ fallback します。実運用では非推奨なので、警告が出た場合は private runtime へ移してください。

## 改造前に見るファイル

- `knowledge_forward/config.py`
- `knowledge_forward/source_safety.py`
- `knowledge_forward/api.py`
- `scripts/start.sh`
- `SECURITY.md`
- `CONTRIBUTING.md`

特に、読み込み対象フォルダの検証、token、ログ、DB、Tailscale公開範囲を変更する場合は、先に `SECURITY.md` の境界と矛盾しないか確認してください。

## 改造前チェック

変更前後で最低限次を実行してください。security 系コマンドは開発者・メンテナ向けの repo 監査です。Web UI の `/security` は token 認証後に同じ repo 監査を full 実行します。通常利用には不要ですが、起動中のローカル環境から確認できます。

```bash
./knowledgeforward test
./knowledgeforward security-check
./knowledgeforward security-audit
```

`security-audit full` はローカルに入っている監査ツールの状態に依存します。失敗した場合は、どのツールがなぜ失敗したかを切り分けてください。
