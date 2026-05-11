from __future__ import annotations

import os
from typing import Any

import httpx

WORLDNEWS_SEARCH_URL = "https://api.worldnewsapi.com/search-news"
WORLDNEWS_TOP_NEWS_URL = "https://api.worldnewsapi.com/top-news"


async def fetch_worldnews_articles(
    *,
    api_key: str,
    text: str,
    number: int = 10,
    language: str = "fr",
) -> list[dict[str, Any]]:
    if not api_key:
        return []

    params = {
        "api-key": api_key,
        "text": text,
        "number": number,
        "language": language,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(WORLDNEWS_SEARCH_URL, params=params)
        response.raise_for_status()
        data = response.json()

    items = data.get("news") or data.get("articles") or []
    normalized: list[dict[str, Any]] = []
    for raw in items:
        title = raw.get("title") or "Sans titre"
        url = raw.get("url") or raw.get("link") or ""
        summary = raw.get("summary") or raw.get("text") or ""
        if isinstance(summary, str) and len(summary) > 2000:
            summary = summary[:2000] + "…"
        source = None
        src = raw.get("source")
        if isinstance(src, str):
            source = src
        elif isinstance(src, dict):
            source = src.get("name") or src.get("title")
        normalized.append(
            {
                "title": title,
                "url": url,
                "summary": summary,
                "source": source,
            }
        )
    return normalized


def _top_news_summary_only(raw: dict[str, Any], *, text_fallback_max: int = 320) -> str:
    """Résumé API uniquement ; si absent, extrait court du champ text (jamais l'article entier)."""
    summary = raw.get("summary")
    if isinstance(summary, str) and summary.strip():
        return summary.strip()
    text = raw.get("text") or ""
    if not isinstance(text, str) or not text.strip():
        return ""
    text = text.strip()
    if len(text) <= text_fallback_max:
        return text
    return text[:text_fallback_max] + "…"


async def fetch_worldnews_top_news(
    *,
    api_key: str,
    source_country: str | None = None,
    language: str | None = None,
    max_clusters: int = 12,
) -> list[dict[str, Any]]:
    """Appelle GET https://api.worldnewsapi.com/top-news (un article par cluster : titre + résumé)."""
    if not api_key:
        return []

    country = (source_country or os.getenv("WORLDNEWS_SOURCE_COUNTRY", "fr")).strip().lower()
    lang = (language or os.getenv("WORLDNEWS_LANGUAGE", "fr")).strip().lower()

    params: dict[str, Any] = {
        "api-key": api_key,
        "source-country": country,
        "language": lang,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(WORLDNEWS_TOP_NEWS_URL, params=params)
        response.raise_for_status()
        data = response.json()

    clusters = data.get("top_news") or []
    normalized: list[dict[str, Any]] = []
    for cluster in clusters[:max_clusters]:
        if not isinstance(cluster, dict):
            continue
        news_list = cluster.get("news") or []
        if not news_list or not isinstance(news_list[0], dict):
            continue
        raw = news_list[0]
        title = raw.get("title") or "Sans titre"
        summary = _top_news_summary_only(raw)
        normalized.append({"title": title, "summary": summary})
    return normalized


def format_top_news_for_system_prompt(
    items: list[dict[str, Any]],
    *,
    max_items: int = 10,
    summary_max: int = 280,
) -> str:
    """Titres + résumés courts uniquement (pas le corps complet des articles)."""
    lines: list[str] = []
    for raw in items[:max_items]:
        title = str(raw.get("title") or "").strip()
        summary = str(raw.get("summary") or "").strip()
        if len(summary) > summary_max:
            summary = summary[:summary_max] + "…"
        if title or summary:
            lines.append(f"- {title}\n  Résumé: {summary}")
    return "\n".join(lines)


def worldnews_api_key() -> str:
    return os.getenv("WORLDNEWS_API_KEY", "").strip()


async def format_news_tool_result(api_key: str, sujet: str) -> str:
    articles = await fetch_worldnews_articles(api_key=api_key, text=sujet, number=8)
    if not articles:
        return "Aucun article trouvé pour ce sujet (ou clé API absente / erreur réseau)."
    lines = []
    for a in articles:
        lines.append(
            f"- {a['title']}\n  Source: {a.get('source') or 'n/a'}\n  {str(a.get('summary') or '')[:400]}\n  URL: {a.get('url')}"
        )
    return "\n".join(lines)
