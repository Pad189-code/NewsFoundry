from __future__ import annotations

import asyncio

import httpx
import pytest

from services.news import (
    format_worldnews_http_error,
    sanitize_worldnews_error_detail,
    search_news_for_chat_tool,
)


def test_sanitize_worldnews_error_detail_masks_api_key() -> None:
    raw = (
        "HTTPStatusError: 402 for url "
        "'https://api.worldnewsapi.com/search-news?api-key=secret123&text=ours'"
    )
    assert "secret123" not in sanitize_worldnews_error_detail(raw)
    assert "api-key=***" in sanitize_worldnews_error_detail(raw)


def test_format_worldnews_http_error_402() -> None:
    request = httpx.Request("GET", "https://api.worldnewsapi.com/search-news")
    response = httpx.Response(402, request=request)
    exc = httpx.HTTPStatusError("Payment Required", request=request, response=response)
    msg = format_worldnews_http_error(exc)
    assert "402" in msg
    assert "WORLDNEWS_API_KEY" in msg
    assert "worldnewsapi.com" in msg


def test_search_news_for_chat_tool_returns_message_on_402(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fail_fetch(**_kwargs: object) -> list:
        request = httpx.Request("GET", "https://api.worldnewsapi.com/search-news")
        response = httpx.Response(402, request=request)
        raise httpx.HTTPStatusError("Payment Required", request=request, response=response)

    import services.news as news_mod

    monkeypatch.setattr(news_mod, "fetch_worldnews_articles", fail_fetch)

    async def _run() -> tuple[str, list]:
        return await search_news_for_chat_tool("key", "ours du Japon")

    text, items = asyncio.run(_run())
    assert items == []
    assert "402" in text
    assert "World News API" in text
