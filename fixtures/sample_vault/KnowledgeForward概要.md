# KnowledgeForward MVP

KnowledgeForward は、許可された Markdown フォルダだけをローカルで検索し、Ollama を使って根拠付きの回答を返すための最小構成です。

## 許可されたソース

MVP の初期設定では `fixtures/sample_vault` だけを allowed_sources に登録します。本物の Obsidian Vault は自動探索しません。

## 検索

Markdown ファイルは再帰的に読み込まれ、見出し単位を基準にチャンク化されます。検索には SQLite FTS5 を使います。

## セキュリティ

Markdown 本文は信頼しない参考文書として扱います。本文内の命令はシステム命令ではありません。API にはローカル用トークンが必要です。
