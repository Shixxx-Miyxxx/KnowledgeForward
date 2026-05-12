from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable

import yaml

from .config import AppConfig, SourceConfig


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
ROOT_DATED_MARKDOWN_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})\.md$", re.IGNORECASE)
DATE_TREE_PART_RE = (
    re.compile(r"^\d{4}$"),
    re.compile(r"^\d{2}$"),
    re.compile(r"^\d{2}$"),
)
REQUIRED_EXCLUDED_DIRS = frozenset({"attachments"})
TAG_RE = re.compile(r"(?<![\w/])#([\w\u3040-\u30ff\u3400-\u9fffー/-]+)", re.UNICODE)
FENCE_RE = re.compile(r"(?ms)^(```|~~~).*?^\1\s*$")


@dataclass(frozen=True)
class MarkdownDocument:
    source_name: str
    path: Path
    relative_path: str
    title: str
    document_date: date | None
    tags: tuple[str, ...]
    content: str
    size: int
    mtime_ns: int
    sha256: str


@dataclass(frozen=True)
class MarkdownChunk:
    heading: str
    chunk_index: int
    content: str


def iter_markdown_documents(config: AppConfig) -> Iterable[MarkdownDocument]:
    for source in config.allowed_sources:
        if not source.enabled or not source.path.exists():
            continue
        yield from _iter_source_documents(source, config)


def chunk_markdown(content: str, max_chars: int, overlap_chars: int) -> list[MarkdownChunk]:
    chunks: list[MarkdownChunk] = []
    for heading, section_text in _split_sections(content):
        normalized = _normalize_text(section_text)
        if not normalized:
            continue
        for piece in _split_text(normalized, max_chars=max_chars, overlap_chars=overlap_chars):
            chunks.append(MarkdownChunk(heading=heading, chunk_index=len(chunks), content=piece))
    return chunks


def _iter_source_documents(source: SourceConfig, config: AppConfig) -> Iterable[MarkdownDocument]:
    source_root = source.path.resolve()
    excluded_dirs = set(config.indexing.excluded_dirs) | REQUIRED_EXCLUDED_DIRS
    extensions = set(config.indexing.markdown_extensions)
    has_date_filter = (
        not source.require_query_filter and (source.date_from is not None or source.date_to is not None)
    )

    for path in sorted(source_root.rglob("*")):
        if not path.is_file():
            continue
        if not _is_path_inside(path.resolve(), source_root):
            continue
        relative = path.relative_to(source_root)
        if _has_excluded_part(relative, excluded_dirs):
            continue
        if path.suffix.lower() not in extensions:
            continue
        if has_date_filter and not _matches_source_date_filter(relative, source):
            continue
        stat = path.stat()
        if stat.st_size > config.indexing.max_file_bytes:
            continue
        content = _read_markdown_text(path)
        if content is None:
            continue
        yield MarkdownDocument(
            source_name=source.name,
            path=path.resolve(),
            relative_path=relative.as_posix(),
            title=_extract_title(content, path),
            document_date=extract_document_date(relative),
            tags=extract_markdown_tags(content),
            content=content,
            size=stat.st_size,
            mtime_ns=stat.st_mtime_ns,
            sha256=hashlib.sha256(content.encode("utf-8")).hexdigest(),
        )


def _has_excluded_part(relative: Path, excluded_dirs: set[str]) -> bool:
    for part in relative.parts[:-1]:
        if part in excluded_dirs or part.startswith("."):
            return True
    return relative.name == ".DS_Store"


def _matches_source_date_filter(relative: Path, source: SourceConfig) -> bool:
    document_date = extract_document_date(relative)
    if document_date is None:
        return False
    if source.date_from is not None and document_date < source.date_from:
        return False
    if source.date_to is not None and document_date > source.date_to:
        return False
    return True


def extract_document_date(relative: str | Path) -> date | None:
    relative_path = Path(relative)
    parts = relative_path.parts
    is_date_tree_path = len(parts) >= 4 and all(
        pattern.match(part) for pattern, part in zip(DATE_TREE_PART_RE, parts[:3])
    )
    if is_date_tree_path:
        return _date_or_none(parts[0], parts[1], parts[2])

    if len(parts) == 1:
        match = ROOT_DATED_MARKDOWN_RE.match(parts[0])
        if match:
            return _date_or_none(*match.groups())

    return None


def extract_markdown_tags(content: str) -> tuple[str, ...]:
    tags: set[str] = set()
    tags.update(_extract_frontmatter_tags(content))
    text = _strip_frontmatter(content)
    text = FENCE_RE.sub("", text)
    for match in TAG_RE.finditer(text):
        normalized = normalize_tag(match.group(1))
        if normalized:
            tags.add(normalized)
    return tuple(sorted(tags))


def normalize_tag(value: str) -> str:
    tag = value.strip()
    while tag.startswith("#"):
        tag = tag[1:].strip()
    tag = unicodedata.normalize("NFKC", tag).casefold().strip()
    tag = tag.strip(" \t\r\n,.;:!?()[]{}<>\"'")
    return tag


def _extract_frontmatter_tags(content: str) -> set[str]:
    frontmatter = _frontmatter_text(content)
    if frontmatter is None:
        return set()
    try:
        parsed = yaml.safe_load(frontmatter) or {}
    except yaml.YAMLError:
        return set()
    if not isinstance(parsed, dict):
        return set()

    raw_tags = []
    for key in ("tags", "tag"):
        value = parsed.get(key)
        if value is None:
            continue
        if isinstance(value, list):
            raw_tags.extend(value)
        else:
            raw_tags.append(value)

    tags: set[str] = set()
    for item in raw_tags:
        if isinstance(item, str):
            parts = re.split(r"[\s,]+", item.strip())
        else:
            parts = [str(item)]
        for part in parts:
            normalized = normalize_tag(part)
            if normalized:
                tags.add(normalized)
    return tags


def _frontmatter_text(content: str) -> str | None:
    if not content.startswith("---"):
        return None
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return "\n".join(lines[1:index])
    return None


def _strip_frontmatter(content: str) -> str:
    if not content.startswith("---"):
        return content
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return content
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return "\n".join(lines[index + 1 :])
    return content


def _date_or_none(year: str, month: str, day: str) -> date | None:
    try:
        return date(int(year), int(month), int(day))
    except ValueError:
        return None


def _is_path_inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _read_markdown_text(path: Path) -> str | None:
    data = path.read_bytes()
    if b"\x00" in data:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _extract_title(content: str, path: Path) -> str:
    for line in content.splitlines():
        match = HEADING_RE.match(line)
        if match:
            return match.group(2).strip()
    return path.stem


def _split_sections(content: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    current_heading = "Document"
    current_lines: list[str] = []
    in_fence = False

    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
        match = None if in_fence else HEADING_RE.match(line)
        if match:
            if current_lines:
                sections.append((current_heading, "\n".join(current_lines).strip()))
                current_lines = []
            current_heading = match.group(2).strip()
            current_lines.append(line)
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_heading, "\n".join(current_lines).strip()))
    return sections


def _split_text(text: str, max_chars: int, overlap_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    pieces: list[str] = []
    current = ""

    for paragraph in paragraphs:
        next_text = paragraph if not current else f"{current}\n\n{paragraph}"
        if len(next_text) <= max_chars:
            current = next_text
            continue
        if current:
            pieces.extend(_split_long_text(current, max_chars, overlap_chars))
        current = paragraph

    if current:
        pieces.extend(_split_long_text(current, max_chars, overlap_chars))
    return pieces


def _split_long_text(text: str, max_chars: int, overlap_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    pieces = []
    start = 0
    while start < len(text):
        end = min(len(text), start + max_chars)
        pieces.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(0, end - overlap_chars)
    return [piece for piece in pieces if piece]


def _normalize_text(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", text).strip()
