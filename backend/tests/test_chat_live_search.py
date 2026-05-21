"""Recherche proactive d’articles à chaque message chat."""

from __future__ import annotations

import asyncio

import pytest

from services.chat_live_search import search_press_articles_for_message


def test_search_press_articles_skips_without_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("WORLDNEWS_API_KEY", raising=False)

    async def _run() -> tuple[str, list]:
        return await search_press_articles_for_message(1, "politique europe")

    text, items = asyncio.run(_run())
    assert text == ""
    assert items == []


def test_search_press_articles_calls_worldnews(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import services.chat_live_search as mod

    async def fake_tool(key: str, sujet: str) -> tuple[str, list[dict]]:
        _ = key
        assert "santé" in sujet
        return "- Article test\n", [{"title": "Article test", "url": "https://x.test"}]

    async def fake_persist(chat_id: int, items: list[dict]) -> None:
        assert chat_id == 42
        assert items

    monkeypatch.setenv("WORLDNEWS_API_KEY", "dummy")
    monkeypatch.setattr(mod, "search_news_for_chat_tool", fake_tool)
    monkeypatch.setattr(mod, "persist_fetched_articles_for_chat", fake_persist)

    async def _run() -> tuple[str, list]:
        return await search_press_articles_for_message(
            42, "Je suis curieux des applications dans le domaine de la santé"
        )

    text, items = asyncio.run(_run())
    assert "Article test" in text
    assert len(items) == 1
