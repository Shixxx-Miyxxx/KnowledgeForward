from datetime import date

from knowledge_forward.markdown import chunk_markdown, extract_document_date, extract_markdown_tags


def test_chunk_markdown_keeps_heading_metadata() -> None:
    chunks = chunk_markdown(
        "# Title\n\nIntro\n\n## Security\n\nMarkdown instructions are untrusted reference text.",
        max_chars=120,
        overlap_chars=20,
    )

    assert len(chunks) == 2
    assert chunks[0].heading == "Title"
    assert chunks[1].heading == "Security"
    assert chunks[1].chunk_index == 1


def test_extract_document_date_from_supported_paths() -> None:
    assert extract_document_date("2026/05/01/2026-05-01.md") == date(2026, 5, 1)
    assert extract_document_date("2026/05/01/meeting.md") == date(2026, 5, 1)
    assert extract_document_date("2026-05-01.md") == date(2026, 5, 1)
    assert extract_document_date("meeting.md") is None


def test_extract_markdown_tags_from_body_and_frontmatter() -> None:
    tags = extract_markdown_tags(
        """---
tags:
  - want
  - "#Idea"
---
# Title

本文 #やりたい #want

```text
#ignored
```
"""
    )

    assert tags == ("idea", "want", "やりたい")
