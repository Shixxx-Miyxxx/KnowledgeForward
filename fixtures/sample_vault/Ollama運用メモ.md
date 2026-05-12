# Ollama 運用メモ

KnowledgeForward は localhost の Ollama API に接続します。既定の接続先は `http://127.0.0.1:11434` です。

## モデル

モデルはユーザーが事前に `ollama pull` などで準備します。KnowledgeForward はモデルを自動で pull しません。

## 回答

質問に対して、検索で見つかった Markdown チャンクを参考文書としてプロンプトに入れます。根拠が弱い場合は分からないと答える方針です。
