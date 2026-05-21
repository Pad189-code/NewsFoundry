"""Recherche proactive d’articles de presse à chaque message utilisateur (chat)."""

from __future__ import annotations

import logging

from services.article_tool_persist import persist_fetched_articles_for_chat
from services.news import search_news_for_chat_tool, worldnews_api_key

logger = logging.getLogger(__name__)

# Limite raisonnable pour la requête World News « text »
_MAX_QUERY_LEN = 400


async def search_press_articles_for_message(
    chat_id: int,
    user_message: str,
) -> tuple[str, list[dict]]:
    """
    Interroge World News API avec le texte saisi par l’utilisateur,
    persiste les articles en base et renvoie (texte outil, items normalisés).
    """
    key = worldnews_api_key()
    query = (user_message or "").strip()[:_MAX_QUERY_LEN]
    if not key or not query:
        return "", []

    try:
        tool_text, items = await search_news_for_chat_tool(key, query)
        if items:
            await persist_fetched_articles_for_chat(chat_id, items)
        return tool_text, items
    except Exception:
        logger.warning(
            "search_press_articles_for_message: échec chat_id=%s",
            chat_id,
            exc_info=True,
        )
        return "", []
