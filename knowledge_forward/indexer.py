from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, Mapping

from .config import AppConfig
from .markdown import chunk_markdown, iter_markdown_documents, normalize_tag


class SearchFilterError(ValueError):
    """Raised when query-time filters are invalid."""


class ReindexRequiredError(RuntimeError):
    """Raised when the SQLite schema predates the current metadata fields."""


@dataclass(frozen=True)
class QueryFilters:
    date_from: date | None = None
    date_to: date | None = None
    tags: tuple[str, ...] = ()
    path_prefix: str | None = None
    source_names: tuple[str, ...] = ()
    all_time: bool = False

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {}
        if self.date_from is not None:
            data["date_from"] = self.date_from.isoformat()
        if self.date_to is not None:
            data["date_to"] = self.date_to.isoformat()
        if self.tags:
            data["tags"] = list(self.tags)
        if self.path_prefix:
            data["path_prefix"] = self.path_prefix
        if self.source_names:
            data["source_names"] = list(self.source_names)
        if self.all_time:
            data["all_time"] = True
        return data


@dataclass(frozen=True)
class SearchOutcome:
    results: list["SearchResult"]
    applied_filters: QueryFilters
    default_filter_applied: bool
    total_count: int
    offset: int
    page_size: int

    @property
    def returned_count(self) -> int:
        return len(self.results)

    @property
    def has_more(self) -> bool:
        return self.offset + self.returned_count < self.total_count


@dataclass(frozen=True)
class SearchResult:
    id: int
    source_name: str
    relative_path: str
    title: str
    document_date: str | None
    heading: str
    chunk_index: int
    content: str
    score: float
    match_source: str = "fts"

    def to_dict(self, include_content: bool = True) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id,
            "source_name": self.source_name,
            "relative_path": self.relative_path,
            "title": self.title,
            "document_date": self.document_date,
            "heading": self.heading,
            "chunk_index": self.chunk_index,
            "score": self.score,
            "match_source": self.match_source,
            "snippet": _snippet(self.content),
        }
        if include_content:
            data["content"] = self.content
        return data


class SearchService:
    def __init__(self, config: AppConfig):
        self.config = config

    def reindex(self) -> dict[str, Any]:
        self.config.database.path.parent.mkdir(parents=True, exist_ok=True)
        documents_count = 0
        chunks_count = 0
        warnings: list[str] = []

        with self._connect() as conn:
            _reset_schema(conn)
            _create_schema(conn)

            for source in self.config.allowed_sources:
                if source.enabled and not source.path.exists():
                    warnings.append(f"Allowed source does not exist: {source.name}")

            for document in iter_markdown_documents(self.config):
                document_date = document.document_date.isoformat() if document.document_date else None
                tags_json = _tags_json(document.tags)
                cursor = conn.execute(
                    """
                    INSERT INTO documents (
                        source_name, absolute_path, relative_path, title, document_date, tags_json,
                        mtime_ns, size, sha256, indexed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        document.source_name,
                        str(document.path),
                        document.relative_path,
                        document.title,
                        document_date,
                        tags_json,
                        document.mtime_ns,
                        document.size,
                        document.sha256,
                        _utc_now(),
                    ),
                )
                document_id = int(cursor.lastrowid)
                documents_count += 1

                for chunk in chunk_markdown(
                    document.content,
                    max_chars=self.config.indexing.chunk_max_chars,
                    overlap_chars=self.config.indexing.chunk_overlap_chars,
                ):
                    chunk_cursor = conn.execute(
                        """
                        INSERT INTO chunks (
                            document_id, source_name, relative_path, title,
                            document_date, tags_json, heading, chunk_index, content
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            document_id,
                            document.source_name,
                            document.relative_path,
                            document.title,
                            document_date,
                            tags_json,
                            chunk.heading,
                            chunk.chunk_index,
                            chunk.content,
                        ),
                    )
                    chunk_id = int(chunk_cursor.lastrowid)
                    conn.execute(
                        """
                        INSERT INTO chunks_fts(rowid, content, heading, relative_path, source_name)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            chunk_id,
                            chunk.content,
                            chunk.heading,
                            document.relative_path,
                            document.source_name,
                        ),
                    )
                    chunks_count += 1
                    for tag in document.tags:
                        conn.execute(
                            "INSERT INTO chunk_tags(chunk_id, tag) VALUES (?, ?)",
                            (chunk_id, tag),
                        )

        return {"documents": documents_count, "chunks": chunks_count, "warnings": warnings}

    def search(
        self,
        query: str,
        limit: int = 10,
        filters: QueryFilters | Mapping[str, Any] | None = None,
    ) -> list[SearchResult]:
        return self.search_with_filters(query, limit=limit, filters=filters).results

    def search_with_filters(
        self,
        query: str,
        limit: int = 10,
        filters: QueryFilters | Mapping[str, Any] | None = None,
        offset: int = 0,
        page_size: int | None = None,
    ) -> SearchOutcome:
        page_size = limit if page_size is None else page_size
        if offset < 0:
            raise SearchFilterError("offset must be greater than or equal to 0.")
        if page_size < 1:
            raise SearchFilterError("page_size must be greater than or equal to 1.")

        clean_query = query.strip()
        applied_filters, default_filter_applied = self._apply_default_filters(_normalize_query_filters(filters))
        if not clean_query:
            return SearchOutcome([], applied_filters, default_filter_applied, total_count=0, offset=offset, page_size=page_size)

        with self._connect() as conn:
            try:
                _create_schema(conn)
            except sqlite3.OperationalError as exc:
                raise ReindexRequiredError("SQLite schema changed; run /reindex before searching.") from exc
            _ensure_query_schema(conn)
            filter_clause = _build_sql_filters(applied_filters)
            fts_results = _search_fts(conn, clean_query, filter_clause)
            fallback_results = _search_lexical(
                conn,
                clean_query,
                filter_clause,
            )

        merged: dict[int, SearchResult] = {}
        for result in fts_results:
            merged[result.id] = result
        for result in fallback_results:
            existing = merged.get(result.id)
            if existing is None:
                merged[result.id] = result
            else:
                merged[result.id] = SearchResult(
                    id=existing.id,
                    source_name=existing.source_name,
                    relative_path=existing.relative_path,
                    title=existing.title,
                    document_date=existing.document_date,
                    heading=existing.heading,
                    chunk_index=existing.chunk_index,
                    content=existing.content,
                    score=existing.score + result.score,
                    match_source="fts+fallback",
                )

        ranked_results = sorted(merged.values(), key=lambda item: (-item.score, item.relative_path, item.chunk_index))
        total_count = len(ranked_results)
        results = ranked_results[offset : offset + page_size]
        return SearchOutcome(
            results,
            applied_filters,
            default_filter_applied,
            total_count=total_count,
            offset=offset,
            page_size=page_size,
        )

    def _apply_default_filters(self, filters: QueryFilters) -> tuple[QueryFilters, bool]:
        enabled_by_name = {source.name: source for source in self.config.allowed_sources if source.enabled}
        unknown_sources = tuple(name for name in filters.source_names if name not in enabled_by_name)
        if unknown_sources:
            raise SearchFilterError("filters.source_names contains an unknown or disabled source.")

        if filters.all_time or filters.date_from is not None or filters.date_to is not None or filters.path_prefix:
            return filters, False

        if filters.source_names:
            targeted_sources = tuple(enabled_by_name[name] for name in filters.source_names if name in enabled_by_name)
        else:
            targeted_sources = tuple(enabled_by_name.values())

        required_sources = [source for source in targeted_sources if source.require_query_filter]
        if not required_sources:
            return filters, False

        default_days = min(source.default_query_days for source in required_sources)
        today = _today()
        date_from = today - timedelta(days=default_days - 1)
        return (
            QueryFilters(
                date_from=date_from,
                date_to=today,
                tags=filters.tags,
                path_prefix=filters.path_prefix,
                source_names=filters.source_names,
                all_time=False,
            ),
            True,
        )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.config.database.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY,
            source_name TEXT NOT NULL,
            absolute_path TEXT NOT NULL,
            relative_path TEXT NOT NULL,
            title TEXT NOT NULL,
            document_date TEXT,
            tags_json TEXT NOT NULL DEFAULT '[]',
            mtime_ns INTEGER NOT NULL,
            size INTEGER NOT NULL,
            sha256 TEXT NOT NULL,
            indexed_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY,
            document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            source_name TEXT NOT NULL,
            relative_path TEXT NOT NULL,
            title TEXT NOT NULL,
            document_date TEXT,
            tags_json TEXT NOT NULL DEFAULT '[]',
            heading TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            content TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS chunk_tags (
            chunk_id INTEGER NOT NULL REFERENCES chunks(id) ON DELETE CASCADE,
            tag TEXT NOT NULL,
            PRIMARY KEY (chunk_id, tag)
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts
        USING fts5(content, heading, relative_path, source_name);

        CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);
        CREATE INDEX IF NOT EXISTS idx_chunks_source_path ON chunks(source_name, relative_path);
        CREATE INDEX IF NOT EXISTS idx_chunks_document_date ON chunks(document_date);
        CREATE INDEX IF NOT EXISTS idx_chunk_tags_tag ON chunk_tags(tag);
        """
    )


def _reset_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DROP TABLE IF EXISTS chunks_fts;
        DROP TABLE IF EXISTS chunk_tags;
        DROP TABLE IF EXISTS chunks;
        DROP TABLE IF EXISTS documents;
        """
    )


def _ensure_query_schema(conn: sqlite3.Connection) -> None:
    tables = {
        str(row["name"])
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table', 'virtual')"
        ).fetchall()
    }
    if not {"documents", "chunks", "chunk_tags", "chunks_fts"}.issubset(tables):
        raise ReindexRequiredError("SQLite schema changed; run /reindex before searching.")

    chunk_columns = {str(row["name"]) for row in conn.execute("PRAGMA table_info(chunks)").fetchall()}
    document_columns = {str(row["name"]) for row in conn.execute("PRAGMA table_info(documents)").fetchall()}
    if not {"document_date", "tags_json"}.issubset(chunk_columns) or not {
        "document_date",
        "tags_json",
    }.issubset(document_columns):
        raise ReindexRequiredError("SQLite schema changed; run /reindex before searching.")


@dataclass(frozen=True)
class _SqlFilterClause:
    where_sql: str
    params: tuple[Any, ...]


def _normalize_query_filters(filters: QueryFilters | Mapping[str, Any] | None) -> QueryFilters:
    if filters is None:
        return QueryFilters()
    if isinstance(filters, QueryFilters):
        normalized = filters
    elif isinstance(filters, Mapping):
        normalized = QueryFilters(
            date_from=_parse_filter_date(filters.get("date_from"), "filters.date_from"),
            date_to=_parse_filter_date(filters.get("date_to"), "filters.date_to"),
            tags=_normalize_filter_tags(filters.get("tags")),
            path_prefix=_normalize_path_prefix(filters.get("path_prefix")),
            source_names=_normalize_source_names(filters.get("source_names")),
            all_time=_parse_filter_bool(filters.get("all_time", False), "filters.all_time"),
        )
    else:
        raise SearchFilterError("filters must be an object.")

    if normalized.date_from and normalized.date_to and normalized.date_from > normalized.date_to:
        raise SearchFilterError("filters.date_from must be earlier than or equal to filters.date_to.")
    if normalized.all_time and (normalized.date_from is not None or normalized.date_to is not None):
        raise SearchFilterError("filters.all_time=true cannot be combined with date_from/date_to.")
    return normalized


def _parse_filter_date(value: Any, label: str) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        raise SearchFilterError(f"{label} must be a YYYY-MM-DD string.")
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise SearchFilterError(f"{label} must be a YYYY-MM-DD string.") from exc


def _parse_filter_bool(value: Any, label: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized in {"true", "yes", "1", "on"}:
            return True
        if normalized in {"false", "no", "0", "off", ""}:
            return False
    if value is None:
        return False
    raise SearchFilterError(f"{label} must be true or false.")


def _normalize_filter_tags(value: Any) -> tuple[str, ...]:
    if value is None or value == "":
        return ()
    raw_items: list[str] = []
    if isinstance(value, str):
        raw_items = re.split(r"[\s,]+", value.strip())
    elif isinstance(value, list | tuple):
        raw_items = [str(item) for item in value]
    else:
        raise SearchFilterError("filters.tags must be an array or string.")
    tags = sorted({normalized for item in raw_items if (normalized := normalize_tag(item))})
    return tuple(tags)


def _normalize_source_names(value: Any) -> tuple[str, ...]:
    if value is None or value == "":
        return ()
    if isinstance(value, str):
        names = re.split(r"[\s,]+", value.strip())
    elif isinstance(value, list | tuple):
        names = [str(item).strip() for item in value]
    else:
        raise SearchFilterError("filters.source_names must be an array or string.")
    normalized = tuple(dict.fromkeys(name for name in names if name))
    return normalized


def _normalize_path_prefix(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise SearchFilterError("filters.path_prefix must be a string.")
    prefix = value.strip()
    if not prefix:
        return None
    if prefix.startswith("/") or "\\" in prefix or "\x00" in prefix:
        raise SearchFilterError("filters.path_prefix must be a relative path prefix.")
    parts = Path(prefix).parts
    if any(part == ".." for part in parts):
        raise SearchFilterError("filters.path_prefix must not contain path traversal.")
    return prefix


def _build_sql_filters(filters: QueryFilters) -> _SqlFilterClause:
    clauses: list[str] = []
    params: list[Any] = []

    if filters.date_from is not None:
        clauses.append("c.document_date >= ?")
        params.append(filters.date_from.isoformat())
    if filters.date_to is not None:
        clauses.append("c.document_date <= ?")
        params.append(filters.date_to.isoformat())
    if filters.path_prefix:
        clauses.append("substr(c.relative_path, 1, ?) = ?")
        params.extend([len(filters.path_prefix), filters.path_prefix])
    if filters.source_names:
        placeholders = ", ".join("?" for _ in filters.source_names)
        clauses.append(f"c.source_name IN ({placeholders})")
        params.extend(filters.source_names)
    if filters.tags:
        placeholders = ", ".join("?" for _ in filters.tags)
        clauses.append(_tag_filter_sql(placeholders))
        params.extend(filters.tags)

    return _SqlFilterClause(" AND ".join(clauses), tuple(params))


def _tag_filter_sql(placeholders: str) -> str:
    return "EXISTS (SELECT 1 FROM chunk_tags ct WHERE ct.chunk_id = c.id AND ct.tag IN (" + placeholders + "))"  # nosec


def _tags_json(tags: tuple[str, ...]) -> str:
    return json.dumps(list(tags), ensure_ascii=False, separators=(",", ":"))


def _today() -> date:
    return date.today()


def _search_fts(conn: sqlite3.Connection, query: str, filters: _SqlFilterClause) -> list[SearchResult]:
    fts_query = _to_fts_query(query)
    extra_where = f" AND {filters.where_sql}" if filters.where_sql else ""
    try:
        sql = """
            SELECT
                c.id,
                c.source_name,
                c.relative_path,
                c.title,
                c.document_date,
                c.heading,
                c.chunk_index,
                c.content,
                bm25(chunks_fts) AS rank
            FROM chunks_fts
            JOIN chunks c ON c.id = chunks_fts.rowid
            WHERE chunks_fts MATCH ?
        """
        sql += extra_where  # nosec B608
        sql += " ORDER BY rank"
        rows = conn.execute(
            sql,
            (fts_query, *filters.params),
        ).fetchall()
    except sqlite3.OperationalError:
        rows = []

    if not rows:
        sql = """
            SELECT
                c.id,
                c.source_name,
                c.relative_path,
                c.title,
                c.document_date,
                c.heading,
                c.chunk_index,
                c.content,
                0.0 AS rank
            FROM chunks c
            WHERE (c.content LIKE ? OR c.heading LIKE ? OR c.relative_path LIKE ?)
        """
        sql += extra_where  # nosec B608
        rows = conn.execute(
            sql,
            (f"%{query}%", f"%{query}%", f"%{query}%", *filters.params),
        ).fetchall()

    return [
        SearchResult(
            id=int(row["id"]),
            source_name=str(row["source_name"]),
            relative_path=str(row["relative_path"]),
            title=str(row["title"]),
            document_date=row["document_date"] if row["document_date"] is not None else None,
            heading=str(row["heading"]),
            chunk_index=int(row["chunk_index"]),
            content=str(row["content"]),
            score=max(1.0, -float(row["rank"])),
            match_source="fts",
        )
        for row in rows
    ]


def _search_lexical(
    conn: sqlite3.Connection,
    query: str,
    filters: _SqlFilterClause,
) -> list[SearchResult]:
    query_features = _features(query)
    if not query_features.tokens:
        return []

    where_sql = f"WHERE {filters.where_sql}" if filters.where_sql else ""
    sql = """
        SELECT
            c.id,
            c.source_name,
            c.relative_path,
            c.title,
            c.document_date,
            c.heading,
            c.chunk_index,
            c.content
        FROM chunks c
    """
    sql += where_sql  # nosec B608
    rows = conn.execute(
        sql,
        filters.params,
    ).fetchall()
    results: list[SearchResult] = []
    for row in rows:
        score = _lexical_score(query, query_features, row)
        if score < 8.0:
            continue
        results.append(
            SearchResult(
                id=int(row["id"]),
                source_name=str(row["source_name"]),
                relative_path=str(row["relative_path"]),
                title=str(row["title"]),
                document_date=row["document_date"] if row["document_date"] is not None else None,
                heading=str(row["heading"]),
                chunk_index=int(row["chunk_index"]),
                content=str(row["content"]),
                score=score,
                match_source="fallback",
            )
        )
    return sorted(results, key=lambda item: (-item.score, item.relative_path, item.chunk_index))


def _to_fts_query(query: str) -> str:
    terms = re.findall(r"[\w\u3040-\u30ff\u3400-\u9fff]+", query, flags=re.UNICODE)
    if not terms:
        terms = [query]
    quoted = [f'"{term.replace(chr(34), chr(34) + chr(34))}"' for term in terms[:8]]
    return " OR ".join(quoted)


@dataclass(frozen=True)
class _TextFeatures:
    normalized: str
    tokens: set[str]
    tags: set[str]
    words: set[str]


_ALNUM_RE = re.compile(r"[a-z0-9][a-z0-9_-]*")
_JAPANESE_RE = re.compile(r"[\u3040-\u30ff\u3400-\u9fffー]+")
_TAG_RE = re.compile(r"#[a-z0-9_\-\u3040-\u30ff\u3400-\u9fffー]+")
_RECENCY_HINTS = ("最近", "直近", "過去", "今日", "昨日", "日記", "daily")
_DATED_PATH_RE = re.compile(r"(?:^|/)\d{4}-\d{2}-\d{2}\.md$", re.IGNORECASE)
_KNOWN_PHRASES = (
    "やりたいこと",
    "気になっていること",
    "未回収の課題",
    "次に確認すべき課題",
    "注意点",
    "確認項目",
    "ローカルrag",
    "tailscale",
    "knowledgeforward",
    "reference",
)


def _features(text: str) -> _TextFeatures:
    normalized = _normalize_search_text(text)
    words = set(_ALNUM_RE.findall(normalized))
    tokens = set(words)
    for sequence in _JAPANESE_RE.findall(normalized):
        tokens.update(_ngrams(sequence, 2))
        tokens.update(_ngrams(sequence, 3))
    tags = set(_TAG_RE.findall(normalized))
    tokens.update(tags)
    return _TextFeatures(normalized=normalized, tokens=tokens, tags=tags, words=words)


def _lexical_score(query: str, query_features: _TextFeatures, row: sqlite3.Row) -> float:
    heading_features = _features(str(row["heading"]))
    title_features = _features(str(row["title"]))
    path_features = _features(str(row["relative_path"]).replace("/", " "))
    content_features = _features(str(row["content"]))
    source_features = _features(str(row["source_name"]))

    score = 0.0
    score += 1.0 * len(query_features.tokens & content_features.tokens)
    score += 3.0 * len(query_features.tokens & heading_features.tokens)
    score += 2.5 * len(query_features.tokens & title_features.tokens)
    score += 2.5 * len(query_features.tokens & path_features.tokens)
    score += 1.0 * len(query_features.tokens & source_features.tokens)
    score += 4.0 * len(query_features.words & path_features.words)
    score += 3.0 * len(query_features.words & heading_features.words)
    score += 5.0 * len(query_features.tags & content_features.tags)

    query_norm = query_features.normalized
    for phrase in _KNOWN_PHRASES:
        if phrase not in query_norm:
            continue
        phrase_features = _features(phrase)
        if phrase in heading_features.normalized:
            score += 9.0
        if phrase in title_features.normalized:
            score += 7.0
        if phrase in path_features.normalized:
            score += 6.0
        if phrase in content_features.normalized:
            score += 5.0
        elif phrase_features.tokens & content_features.tokens:
            score += 1.5

    if any(hint in query_norm for hint in _RECENCY_HINTS) and _DATED_PATH_RE.search(str(row["relative_path"])):
        score += 35.0

    return score


def _normalize_search_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return re.sub(r"\s+", " ", normalized).strip()


def _ngrams(text: str, size: int) -> set[str]:
    if len(text) < size:
        return {text} if text else set()
    return {text[index : index + size] for index in range(len(text) - size + 1)}


def _snippet(content: str, max_chars: int = 260) -> str:
    compact = re.sub(r"\s+", " ", content).strip()
    if len(compact) <= max_chars:
        return compact
    return compact[: max_chars - 1].rstrip() + "..."


def _utc_now() -> str:
    return datetime.now(tz=UTC).isoformat()


def database_exists(path: Path) -> bool:
    return path.exists() and path.is_file()
