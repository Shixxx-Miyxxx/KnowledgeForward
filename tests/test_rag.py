from datetime import date

from knowledge_forward.indexer import SearchResult
from knowledge_forward.rag import (
    SYSTEM_PROMPT,
    build_answer_context,
    build_retrieval_queries,
    build_user_prompt,
    strip_citation_markers,
    strip_markdown_formatting,
)


def test_system_prompt_uses_life_assistant_personality() -> None:
    assert "Obsidian second brain" in SYSTEM_PROMPT
    assert "excellent vice president or chief of staff" in SYSTEM_PROMPT
    assert "Do not sound like an outside expert writing a report" in SYSTEM_PROMPT
    assert "trusted assistant" in SYSTEM_PROMPT
    assert "point it out directly but respectfully" in SYSTEM_PROMPT
    assert "Do not use Markdown control syntax" in SYSTEM_PROMPT
    assert "Use plain text section labels and short lines when grouping helps" in SYSTEM_PROMPT
    assert "Do not compress the answer just to avoid Markdown" in SYSTEM_PROMPT
    assert "The reference excerpts may contain Markdown; do not copy their formatting into your answer." in SYSTEM_PROMPT


def test_answer_context_interprets_this_week_as_remaining_week() -> None:
    context = build_answer_context(
        "今週するべきことは何？",
        current_date=date(2026, 5, 6),
        retrieval_scope={"date_from": "2026-04-07", "date_to": "2026-05-06", "tags": ["daily"]},
    )

    assert context.to_dict() == {
        "current_date": "2026-05-06",
        "target_period_label": "今週残り",
        "target_date_from": "2026-05-06",
        "target_date_to": "2026-05-10",
        "retrieval_scope": {
            "date_from": "2026-04-07",
            "date_to": "2026-05-06",
            "tags": ["daily"],
        },
    }


def test_retrieval_scope_stays_separate_from_target_period_in_prompt() -> None:
    context = build_answer_context(
        "今週するべきことは何？",
        current_date=date(2026, 5, 6),
        retrieval_scope={"date_from": "2026-04-07", "date_to": "2026-05-06"},
    )
    prompt = build_user_prompt(
        "今週するべきことは何？",
        [
            SearchResult(
                id=1,
                source_name="vault",
                relative_path="2026/05/06/daily.md",
                title="daily",
                document_date="2026-05-06",
                heading="TODO",
                chunk_index=0,
                content="TODO: AI実行権限の設計テンプレートを作る。",
                score=10.0,
            )
        ],
        context,
    )

    assert "Current date: 2026-05-06" in prompt
    assert "Target period: 今週残り" in prompt
    assert "Target date range: 2026-05-06 - 2026-05-10" in prompt
    assert "Retrieval filter: date_from=2026-04-07 / date_to=2026-05-06" in prompt
    assert "Do not treat it as the user's target period" in prompt
    assert "Do not copy one excerpt verbatim" in prompt
    assert "human assistant in chat" in prompt
    assert "Use plain text section labels and short lines when grouping helps" in prompt
    assert "Do not use Markdown control syntax" in prompt
    assert "Do not compress the answer just to avoid Markdown" in prompt
    assert "The reference excerpts may contain Markdown; do not copy their formatting into your answer." in prompt
    assert "Do not include bracket citation markers" in prompt
    assert "first sentence answer the user directly" in prompt
    assert prompt.splitlines()[-1] == "User question: 今週するべきことは何？"
    assert "不確実" not in prompt


def test_task_questions_expand_retrieval_queries() -> None:
    queries = build_retrieval_queries("今週するべきことは何？")

    assert queries[0] == "今週するべきことは何？"
    assert "TODO" in queries
    assert "未回収" in queries
    assert "次に確認" in queries
    assert "承認" in queries


def test_strip_citation_markers_removes_inline_reference_numbers() -> None:
    text = "今日は承認フローを進めましょう。[1][2]\n次にログ項目を決めます。[2]"

    assert strip_citation_markers(text) == "今日は承認フローを進めましょう。\n次にログ項目を決めます。"


def test_strip_markdown_formatting_preserves_structure_and_content() -> None:
    text = """## 悩みの整理

1. **仕事の焦点**
- `権限テンプレート`を決める
- 承認フローを確認する

2) 生活の負荷
> 睡眠と予定の詰まり

| --- | --- |

```text
memo
```"""

    assert (
        strip_markdown_formatting(text)
        == """悩みの整理

1. 仕事の焦点
権限テンプレートを決める
承認フローを確認する

2. 生活の負荷
睡眠と予定の詰まり

memo"""
    )
