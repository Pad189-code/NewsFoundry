"""Persistance des articles issus des appels World News (outil ou équivalent)."""

from __future__ import annotations

from sqlmodel import Session, select

from database import engine
from models import Article, Chat, User
from services.article_tool_persist import persist_fetched_articles_for_chat


def test_persist_creates_articles_and_merges_loaded_urls() -> None:
    with Session(engine) as session:
        u = User(email="persist@test.com", hashed_password="x")
        session.add(u)
        session.commit()
        session.refresh(u)
        chat = Chat(user_id=u.id, title="C")
        session.add(chat)
        session.commit()
        session.refresh(chat)
        cid = int(chat.id or 0)

    items = [
        {
            "title": "Fil un",
            "url": "https://news.example/a",
            "summary": "Résumé",
            "source": "Src",
        },
        {
            "title": "Fil deux",
            "url": "https://news.example/b",
            "summary": "Autre",
            "source": "Src",
        },
    ]
    persist_fetched_articles_for_chat(cid, items)

    with Session(engine) as session:
        chat2 = session.get(Chat, cid)
        assert chat2 is not None
        assert "https://news.example/a" in (chat2.loaded_articles or [])
        assert "https://news.example/b" in (chat2.loaded_articles or [])
        rows = list(session.exec(select(Article).where(Article.chat_id == cid)).all())
        urls = {a.url for a in rows}
        assert urls == {"https://news.example/a", "https://news.example/b"}
