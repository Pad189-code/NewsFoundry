from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

WORLDNEWS_SEARCH_URL = "https://api.worldnewsapi.com/search-news"
WORLDNEWS_TOP_NEWS_URL = "https://api.worldnewsapi.com/top-news"


def parse_worldnews_publish_date(raw: Any) -> datetime | None:
    """Parse ``publish_date`` renvoyé par WorldNewsAPI (ex. « 2024-04-06 22:44:18 »)."""
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
    s = str(raw).strip()
    if not s:
        return None
    for fmt, length in (("%Y-%m-%d %H:%M:%S", 19), ("%Y-%m-%d", 10)):
        try:
            chunk = s[:length]
            dt = datetime.strptime(chunk, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def sort_articles_by_recency(articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Articles les plus récents en premier (selon ``published_at``)."""

    def _ts(item: dict[str, Any]) -> float:
        pub = item.get("published_at")
        if isinstance(pub, datetime):
            return pub.timestamp()
        return 0.0

    return sorted(articles, key=_ts, reverse=True)


def _search_date_window(*, days_back: int | None = None) -> tuple[str, str]:
    days = days_back if days_back is not None else int(
        os.getenv("WORLDNEWS_DAYS_BACK", "14")
    )
    days = max(1, min(days, 31))
    now = datetime.now(timezone.utc)
    earliest = (now - timedelta(days=days)).strftime("%Y-%m-%d")
    latest = now.strftime("%Y-%m-%d")
    return earliest, latest


def _normalize_article_raw(raw: dict[str, Any]) -> dict[str, Any]:
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
    published_at = parse_worldnews_publish_date(
        raw.get("publish_date") or raw.get("published_at") or raw.get("date")
    )
    return {
        "title": title,
        "url": url,
        "summary": summary,
        "source": source,
        "published_at": published_at,
    }


async def fetch_worldnews_articles(
    *,
    api_key: str,
    text: str,
    number: int = 10,
    language: str = "fr",
) -> list[dict[str, Any]]:
    if not api_key:
        return []

    earliest, latest = _search_date_window()
    params = {
        "api-key": api_key,
        "text": text,
        "number": number,
        "language": language,
        "sort": "publish-time",
        "earliest-publish-date": earliest,
        "latest-publish-date": latest,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(WORLDNEWS_SEARCH_URL, params=params)
        response.raise_for_status()
        data = response.json()

    items = data.get("news") or data.get("articles") or []
    normalized = [_normalize_article_raw(raw) for raw in items if isinstance(raw, dict)]
    return sort_articles_by_recency(normalized)


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
        published_at = parse_worldnews_publish_date(raw.get("publish_date"))
        normalized.append(
            {"title": title, "summary": summary, "published_at": published_at}
        )
    return sort_articles_by_recency(normalized)


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
        pub = raw.get("published_at")
        date_hint = ""
        if isinstance(pub, datetime):
            date_hint = f" ({pub.strftime('%d/%m/%Y')})"
        if title or summary:
            lines.append(f"- {title}{date_hint}\n  Résumé: {summary}")
    return "\n".join(lines)


def worldnews_api_key() -> str:
    return os.getenv("WORLDNEWS_API_KEY", "").strip()


def _format_publish_label(published_at: Any) -> str:
    if isinstance(published_at, datetime):
        return published_at.strftime("%d/%m/%Y %H:%M")
    return "date inconnue"


def _format_news_tool_lines(articles: list[dict[str, Any]]) -> str:
    lines = []
    for a in articles:
        lines.append(
            f"- {a['title']}\n"
            f"  Publié le : {_format_publish_label(a.get('published_at'))}\n"
            f"  Source: {a.get('source') or 'n/a'}\n"
            f"  {str(a.get('summary') or '')[:400]}\n  URL: {a.get('url')}"
        )
    return "\n".join(lines)


async def search_news_for_chat_tool(
    api_key: str,
    sujet: str,
) -> tuple[str, list[dict[str, Any]]]:
    """Une requête search-news : texte pour le LLM + liste normalisée pour la persistance."""
    articles = await fetch_worldnews_articles(api_key=api_key, text=sujet, number=8)
    if not articles:
        return (
            "Aucun article trouvé pour ce sujet (ou clé API absente / erreur réseau).",
            [],
        )
    return _format_news_tool_lines(articles), articles


async def format_news_tool_result(api_key: str, sujet: str) -> str:
    text, _articles = await search_news_for_chat_tool(api_key, sujet)
    return text


def format_breaking_news_welcome(items: list[dict[str, Any]]) -> str:
    """Message d’accueil assistant (actualités récentes en puces Markdown)."""
    if not items:
        return (
            "Bonjour ! Je suis votre assistant revue de presse NewsFoundry. "
            "Posez-moi une question sur l'actualité ou affinez un sujet ; "
            "vous pourrez ensuite générer une revue de presse structurée."
        )
    lines = [
        "Voici un point sur **l'actualité récente** :",
        "",
    ]
    for raw in items[:8]:
        title = str(raw.get("title") or "").strip()
        summary = str(raw.get("summary") or "").strip()
        if len(summary) > 220:
            summary = summary[:220] + "…"
        pub = raw.get("published_at")
        date_hint = ""
        if isinstance(pub, datetime):
            date_hint = f" ({pub.strftime('%d/%m/%Y')})"
        if not title:
            continue
        line = f"- **{title}**{date_hint}"
        if summary:
            line += f" : {summary}"
        lines.append(line)
    lines.extend(
        [
            "",
            "Vous pouvez préciser un angle (ex. santé, économie, international) "
            "et je chercherai des articles complémentaires en ligne.",
            "",
            "Souhaitez-vous que je génère une **revue de presse détaillée** ? "
            "Utilisez le bouton « Générer une revue de presse » en haut à droite.",
        ]
    )
    return "\n".join(lines)
