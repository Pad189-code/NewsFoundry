"""Persistance des articles issus de World News API (outil chat ou route fetch)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlmodel import Session, select

from database import engine
from models import Article, Chat

logger = logging.getLogger(__name__)


def _normalize_loaded(raw: object | None) -> list[str]:
    if not raw:
        return []
    if isinstance(raw, list):
        return [str(u).strip() for u in raw if str(u).strip()]
    return []


def persist_fetched_articles_for_chat(chat_id: int, items: list[dict[str, Any]]) -> None:
    """Crée les lignes Article manquantes et fusionne les URLs dans chat.loaded_articles."""
    if not items:
        return
    with Session(engine) as session:
        chat = session.get(Chat, chat_id)
        if chat is None:
            logger.warning("persist_fetched_articles_for_chat: chat %s introuvable", chat_id)
            return

        urls_loaded = _normalize_loaded(chat.loaded_articles)
        existing_stmt = select(Article.url).where(Article.chat_id == chat_id)
        existing = set(session.exec(existing_stmt).all())

        added = False
        for item in items:
            url = (item.get("url") or "").strip()
            if not url:
                continue
            if url not in urls_loaded:
                urls_loaded.append(url)
            if url not in existing:
                session.add(
                    Article(
                        chat_id=chat_id,
                        title=item.get("title") or "Sans titre",
                        url=url,
                        source=item.get("source"),
                        summary=item.get("summary"),
                    )
                )
                existing.add(url)
                added = True

        chat.loaded_articles = urls_loaded
        chat.updated_at = datetime.now(timezone.utc)
        session.add(chat)
        session.commit()
        if added:
            logger.debug(
                "persist_fetched_articles_for_chat: chat=%s urls_total=%s",
                chat_id,
                len(urls_loaded),
            )
