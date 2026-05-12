from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import logging
from pathlib import Path
import re
import secrets
from threading import Lock
from typing import Any, Literal
import unicodedata

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from . import security_audit
from .config import AppConfig, ConfigError, load_config
from .indexer import ReindexRequiredError, SearchFilterError, SearchOutcome, SearchResult, SearchService
from .ollama import OllamaClient, OllamaError
from .rag import (
    SYSTEM_PROMPT,
    build_answer_context,
    build_retrieval_queries,
    build_user_prompt,
    strip_citation_markers,
    strip_markdown_formatting,
)
from .web import INDEX_HTML


MAX_SEARCH_PAGE_SIZE = 100
MAX_SEARCH_OFFSET = 5000
MIN_ASK_EVIDENCE_SCORE = 1.0
DEFAULT_SEARCH_PAGE_SIZE = 50
MAX_ASK_EVIDENCE_ITEMS = 30
MAX_ASK_EVIDENCE_CHARS = 18000
MIN_ASK_RETRIEVAL_LIMIT = 50
HTML_SECURITY_HEADERS = {
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "base-uri 'none'; "
        "form-action 'self'; "
        "frame-ancestors 'none'"
    ),
}


class QueryFiltersPayload(BaseModel):
    date_from: str | None = None
    date_to: str | None = None
    tags: list[str] | None = None
    path_prefix: str | None = None
    source_names: list[str] | None = None
    all_time: bool = False


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    offset: int = Field(default=0, ge=0, le=MAX_SEARCH_OFFSET)
    page_size: int | None = Field(default=None, ge=1, le=MAX_SEARCH_PAGE_SIZE)
    limit: int | None = Field(default=None, ge=1, le=MAX_SEARCH_PAGE_SIZE)
    filters: QueryFiltersPayload | None = None


class AskRequest(BaseModel):
    question: str = Field(min_length=1)
    limit: int | None = Field(default=None, ge=1)
    filters: QueryFiltersPayload | None = None


class SecurityCheckRequest(BaseModel):
    profile: Literal["quick", "full"] = "quick"


def create_app(config_path: str | Path | None = None) -> FastAPI:
    config = load_config(config_path or "config.yaml")
    search_service = SearchService(config)
    app = FastAPI(title="KnowledgeForward", version="0.1.0")
    app.state.config = config
    app.state.search_service = search_service
    app.state.ollama = OllamaClient(config.ollama)
    app.state.security_check_lock = Lock()

    @app.get("/", response_class=HTMLResponse)
    async def index() -> HTMLResponse:
        return HTMLResponse(INDEX_HTML, headers=HTML_SECURITY_HEADERS)

    @app.get("/health", dependencies=[Depends(require_auth)])
    async def health(request: Request) -> dict[str, Any]:
        cfg: AppConfig = request.app.state.config
        return {
            "ok": True,
            "enabled_sources": [source.name for source in cfg.allowed_sources if source.enabled],
            "ollama_base_url": cfg.ollama.base_url,
            "ollama_model": cfg.ollama.model,
        }

    @app.post("/reindex", dependencies=[Depends(require_auth)])
    async def reindex(request: Request) -> dict[str, Any]:
        return request.app.state.search_service.reindex()

    @app.get("/search", dependencies=[Depends(require_auth)])
    async def search_get(
        request: Request,
        q: str = Query(min_length=1),
        offset: int = Query(default=0, ge=0, le=MAX_SEARCH_OFFSET),
        page_size: int | None = Query(default=None, ge=1, le=MAX_SEARCH_PAGE_SIZE),
        limit: int | None = Query(default=None, ge=1, le=MAX_SEARCH_PAGE_SIZE),
        date_from: str | None = None,
        date_to: str | None = None,
        tags: list[str] | None = Query(default=None),
        path_prefix: str | None = None,
        source_names: list[str] | None = Query(default=None),
        all_time: bool = False,
    ) -> dict[str, Any]:
        filters = {
            "date_from": date_from,
            "date_to": date_to,
            "tags": tags,
            "path_prefix": path_prefix,
            "source_names": source_names,
            "all_time": all_time,
        }
        return _search_payload(request, q, offset, _resolve_page_size(page_size, limit), filters)

    @app.post("/search", dependencies=[Depends(require_auth)])
    async def search_post(request: Request, payload: SearchRequest) -> dict[str, Any]:
        return _search_payload(
            request,
            payload.query,
            payload.offset,
            _resolve_page_size(payload.page_size, payload.limit),
            _filters_dict(payload.filters),
        )

    @app.post("/ask", dependencies=[Depends(require_auth)])
    async def ask(request: Request, payload: AskRequest) -> JSONResponse:
        current_date = _today()
        try:
            evidence = _ask_evidence(
                request.app.state.search_service,
                payload.question,
                filters=_filters_dict(payload.filters),
                current_date=current_date,
            )
        except SearchFilterError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except ReindexRequiredError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        answer_context = build_answer_context(
            payload.question,
            current_date=current_date,
            retrieval_scope=evidence.outcome.applied_filters.to_dict(),
        )
        citations = [chunk.to_dict(include_content=False) for chunk in evidence.chunks]
        citation_metadata = evidence.to_metadata()
        if not evidence.chunks:
            return JSONResponse(
                {
                    "answer": "根拠となるMarkdownチャンクが見つからないため、分かりません。",
                    "citations": [],
                    "used_ollama": False,
                    "answer_context": answer_context.to_dict(),
                    "applied_filters": evidence.outcome.applied_filters.to_dict(),
                    "default_filter_applied": evidence.outcome.default_filter_applied,
                    **citation_metadata,
                }
            )

        user_prompt = build_user_prompt(payload.question, evidence.chunks, answer_context)
        try:
            raw_answer = request.app.state.ollama.chat(SYSTEM_PROMPT, user_prompt)
            answer = strip_citation_markers(strip_markdown_formatting(raw_answer))
        except OllamaError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

        return JSONResponse(
            {
                "answer": answer,
                "citations": citations,
                "used_ollama": True,
                "answer_context": answer_context.to_dict(),
                "applied_filters": evidence.outcome.applied_filters.to_dict(),
                "default_filter_applied": evidence.outcome.default_filter_applied,
                **citation_metadata,
            }
        )

    @app.post("/security/check", dependencies=[Depends(require_auth)])
    async def security_check(request: Request, payload: SecurityCheckRequest) -> dict[str, Any]:
        lock: Lock = request.app.state.security_check_lock
        if not lock.acquire(blocking=False):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Security check is already running.",
            )
        try:
            return await run_in_threadpool(
                security_audit.run_security_checks,
                _repo_root(),
                payload.profile,
                (request.app.state.config.auth.token,),
            )
        finally:
            lock.release()

    return app


async def require_auth(request: Request) -> None:
    expected_token = request.app.state.config.auth.token
    authorization = request.headers.get("authorization", "")
    header_token = request.headers.get("x-knowledgeforward-token", "")
    bearer_token = authorization.removeprefix("Bearer ").strip() if authorization.startswith("Bearer ") else ""
    actual_token = header_token.strip() or bearer_token
    if not secrets.compare_digest(actual_token, expected_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid KnowledgeForward token.",
        )


def _search_payload(
    request: Request,
    query: str,
    offset: int,
    page_size: int,
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        outcome = request.app.state.search_service.search_with_filters(
            query,
            limit=page_size,
            filters=filters,
            offset=offset,
            page_size=page_size,
        )
    except SearchFilterError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ReindexRequiredError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return {
        "query": query,
        "results": [result.to_dict(include_content=False) for result in outcome.results],
        "total_count": outcome.total_count,
        "returned_count": outcome.returned_count,
        "offset": outcome.offset,
        "page_size": outcome.page_size,
        "has_more": outcome.has_more,
        "applied_filters": outcome.applied_filters.to_dict(),
        "default_filter_applied": outcome.default_filter_applied,
    }


def _resolve_page_size(page_size: int | None, limit: int | None) -> int:
    resolved = page_size or limit or DEFAULT_SEARCH_PAGE_SIZE
    if resolved > MAX_SEARCH_PAGE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"page_size must be less than or equal to {MAX_SEARCH_PAGE_SIZE}.",
        )
    return resolved


def _filters_dict(filters: QueryFiltersPayload | None) -> dict[str, Any] | None:
    if filters is None:
        return None
    return {
        "date_from": filters.date_from,
        "date_to": filters.date_to,
        "tags": filters.tags,
        "path_prefix": filters.path_prefix,
        "source_names": filters.source_names,
        "all_time": filters.all_time,
    }


@dataclass(frozen=True)
class AskEvidence:
    outcome: SearchOutcome
    chunks: list[SearchResult]
    matched_count: int
    limit_reason: str | None

    def to_metadata(self) -> dict[str, Any]:
        returned_count = len(self.chunks)
        return {
            "citations_matched_count": self.matched_count,
            "citations_returned_count": returned_count,
            "citations_limited": self.matched_count > returned_count,
            "citation_limit_reason": self.limit_reason if self.matched_count > returned_count else None,
        }


@dataclass(frozen=True)
class _ScoredResult:
    result: SearchResult
    selection_score: float


@dataclass(frozen=True)
class _SelectionFeatures:
    normalized: str
    words: set[str]
    japanese_trigrams: set[str]


_ASK_WORD_RE = re.compile(r"[a-z0-9][a-z0-9_-]+")
_ASK_JAPANESE_RE = re.compile(r"[\u3040-\u30ff\u3400-\u9fffー]+")
_ASK_RECENCY_HINTS = ("最近", "直近", "今日", "昨日", "今週", "今月", "今年")


def _ask_evidence(
    search_service: SearchService,
    question: str,
    filters: dict[str, Any] | None,
    current_date: date,
) -> AskEvidence:
    queries = build_retrieval_queries(question)
    outcomes = [
        search_service.search_with_filters(query, limit=MIN_ASK_RETRIEVAL_LIMIT, filters=filters)
        for query in queries
        if query.strip()
    ]
    if not outcomes:
        outcome = search_service.search_with_filters(question, limit=MIN_ASK_RETRIEVAL_LIMIT, filters=filters)
        return AskEvidence(outcome=outcome, chunks=[], matched_count=0, limit_reason=None)

    merged: dict[int, SearchResult] = {}
    for result in (item for outcome in outcomes for item in outcome.results):
        if result.score < MIN_ASK_EVIDENCE_SCORE:
            continue
        existing = merged.get(result.id)
        if existing is None:
            merged[result.id] = result
        else:
            merged[result.id] = _combine_results(existing, result)

    scored = _score_evidence(
        list(merged.values()),
        question=question,
        outcome=outcomes[0],
        current_date=current_date,
    )
    grouped = _group_evidence(scored)
    chunks, limit_reason = _limit_evidence(grouped)
    return AskEvidence(outcome=outcomes[0], chunks=chunks, matched_count=len(grouped), limit_reason=limit_reason)


def _score_evidence(
    results: list[SearchResult],
    question: str,
    outcome: SearchOutcome,
    current_date: date,
) -> list[_ScoredResult]:
    question_features = _selection_features(question)
    return [
        _ScoredResult(
            result=result,
            selection_score=_selection_score(question, question_features, result, outcome, current_date),
        )
        for result in results
    ]


def _selection_score(
    question: str,
    question_features: _SelectionFeatures,
    result: SearchResult,
    outcome: SearchOutcome,
    current_date: date,
) -> float:
    boost = _metadata_boost(question_features, result) + _date_boost(question, result, outcome, current_date)
    return result.score * (1.0 + min(0.25, boost))


def _metadata_boost(question_features: _SelectionFeatures, result: SearchResult) -> float:
    boost = 0.0
    if _metadata_matches(question_features, result.heading):
        boost += 0.08
    if _metadata_matches(question_features, result.title):
        boost += 0.06
    return min(0.14, boost)


def _metadata_matches(question_features: _SelectionFeatures, text: str) -> bool:
    text_features = _selection_features(text)
    if question_features.words & text_features.words:
        return True
    return len(question_features.japanese_trigrams & text_features.japanese_trigrams) >= 2


def _date_boost(question: str, result: SearchResult, outcome: SearchOutcome, current_date: date) -> float:
    document_date = _parse_document_date(result.document_date)
    if document_date is None:
        return 0.0

    filters = outcome.applied_filters
    if not filters.all_time and (filters.date_from is not None or filters.date_to is not None):
        date_to = filters.date_to or current_date
        if filters.date_from is not None:
            span = (date_to - filters.date_from).days
            if span <= 0:
                return 0.12
            position = (document_date - filters.date_from).days / span
            return 0.12 * max(0.0, min(1.0, position))
        days_from_to = max(0, (date_to - document_date).days)
        return 0.12 * max(0.0, 1.0 - min(days_from_to, 365) / 365)

    if filters.all_time and _is_recency_question(question):
        age_days = max(0, (current_date - document_date).days)
        return 0.10 * max(0.0, 1.0 - min(age_days, 365) / 365)

    return 0.0


def _selection_features(text: str) -> _SelectionFeatures:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    normalized = re.sub(r"\s+", " ", normalized).strip()
    words = {word for word in _ASK_WORD_RE.findall(normalized) if len(word) >= 2}
    japanese_trigrams: set[str] = set()
    for sequence in _ASK_JAPANESE_RE.findall(normalized):
        japanese_trigrams.update(_ngrams(sequence, 3))
    return _SelectionFeatures(normalized=normalized, words=words, japanese_trigrams=japanese_trigrams)


def _ngrams(text: str, size: int) -> set[str]:
    if len(text) < size:
        return set()
    return {text[index : index + size] for index in range(len(text) - size + 1)}


def _is_recency_question(question: str) -> bool:
    normalized = unicodedata.normalize("NFKC", question).casefold()
    return any(hint in normalized for hint in _ASK_RECENCY_HINTS)


def _parse_document_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _group_evidence(scored_results: list[_ScoredResult]) -> list[_ScoredResult]:
    by_location: dict[tuple[str, str, str], list[_ScoredResult]] = {}
    for scored in scored_results:
        result = scored.result
        by_location.setdefault((result.source_name, result.relative_path, result.heading), []).append(scored)

    groups: list[_ScoredResult] = []
    for items in by_location.values():
        ordered = sorted(items, key=lambda item: item.result.chunk_index)
        run: list[_ScoredResult] = []
        for item in ordered:
            if run and item.result.chunk_index != run[-1].result.chunk_index + 1:
                groups.extend(_split_evidence_run(run))
                run = []
            run.append(item)
        if run:
            groups.extend(_split_evidence_run(run))

    return sorted(
        groups,
        key=lambda item: (-item.selection_score, item.result.relative_path, item.result.chunk_index),
    )


def _split_evidence_run(run: list[_ScoredResult]) -> list[_ScoredResult]:
    return [_combine_evidence_group(run[index : index + 3]) for index in range(0, len(run), 3)]


def _combine_evidence_group(items: list[_ScoredResult]) -> _ScoredResult:
    ordered = sorted(items, key=lambda item: item.result.chunk_index)
    first = ordered[0].result
    result = SearchResult(
        id=first.id,
        source_name=first.source_name,
        relative_path=first.relative_path,
        title=first.title,
        document_date=first.document_date,
        heading=first.heading,
        chunk_index=first.chunk_index,
        content=_join_group_content([item.result.content for item in ordered]),
        score=max(item.result.score for item in ordered),
        match_source=_combine_match_sources([item.result.match_source for item in ordered]),
    )
    return _ScoredResult(
        result=result,
        selection_score=max(item.selection_score for item in ordered),
    )


def _join_group_content(contents: list[str]) -> str:
    if not contents:
        return ""
    combined = contents[0].strip()
    for content in contents[1:]:
        combined = _append_group_content(combined, content.strip())
    return combined


def _append_group_content(left: str, right: str) -> str:
    max_overlap = min(240, len(left), len(right))
    for size in range(max_overlap, 39, -1):
        if left[-size:] == right[:size]:
            return f"{left.rstrip()}\n\n{right[size:].lstrip()}".strip()
    return f"{left.rstrip()}\n\n{right.lstrip()}".strip()


def _combine_match_sources(match_sources: list[str]) -> str:
    unique = set(match_sources)
    if "fts+fallback" in unique or {"fts", "fallback"}.issubset(unique):
        return "fts+fallback"
    return match_sources[0] if match_sources else "fts"


def _limit_evidence(results: list[_ScoredResult]) -> tuple[list[SearchResult], str | None]:
    selected: list[SearchResult] = []
    total_chars = 0
    for scored in results:
        result = scored.result
        if len(selected) >= MAX_ASK_EVIDENCE_ITEMS:
            return selected, "max_evidence_items"

        next_chars = total_chars + len(result.content)
        if selected and next_chars > MAX_ASK_EVIDENCE_CHARS:
            return selected, "max_evidence_chars"

        selected.append(result)
        total_chars = next_chars

    return selected, None


def _combine_results(existing: SearchResult, result: SearchResult) -> SearchResult:
    return SearchResult(
        id=existing.id,
        source_name=existing.source_name,
        relative_path=existing.relative_path,
        title=existing.title,
        document_date=existing.document_date,
        heading=existing.heading,
        chunk_index=existing.chunk_index,
        content=existing.content,
        score=existing.score + result.score,
        match_source=existing.match_source,
    )


def _today() -> date:
    return date.today()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


try:
    app = create_app()
except ConfigError as exc:
    logging.getLogger(__name__).error("KnowledgeForward configuration error.")
    app = FastAPI(title="KnowledgeForward", version="0.1.0")

    @app.get("/")
    async def config_error() -> JSONResponse:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)
