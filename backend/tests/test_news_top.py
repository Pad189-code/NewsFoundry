"""Extraction top-news : titre + résumé court, pas le corps complet."""

from __future__ import annotations

from services.news import (
    _top_news_summary_only,
    format_top_news_for_system_prompt,
)


def test_top_news_prefers_summary_over_long_text() -> None:
    raw = {"summary": "  Résumé API  ", "text": "X" * 10_000}
    assert _top_news_summary_only(raw) == "Résumé API"


def test_top_news_text_fallback_is_truncated() -> None:
    raw = {"text": "A" * 500}
    s = _top_news_summary_only(raw)
    assert s.endswith("…")
    assert len(s) == 321


def test_format_top_news_truncates_summary_in_prompt_block() -> None:
    items = [
        {
            "title": "T",
            "summary": "S" * 400,
        }
    ]
    block = format_top_news_for_system_prompt(items, summary_max=50)
    assert "S" * 50 in block
    assert "…" in block
    assert len(block) < 200
