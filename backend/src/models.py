from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import Column, JSON, Text
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str = Field()


class Chat(SQLModel, table=True):
    """Discussion : métadonnées + historique complet des messages en JSON."""

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    title: str = Field(default="Discussion")
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    messages_json: list[Any] = Field(
        default_factory=list,
        sa_column=Column(JSON),
    )
    # Prompt système figé à l’ouverture de la discussion (base NewsFoundry + brève top-news).
    system_prompt_saved: Optional[str] = Field(default=None, sa_column=Column(Text))
    # Dernière revue de presse générée (aperçu pour l’UI sans requête jointe).
    review_display_title: Optional[str] = None
    review_general_summary: Optional[str] = Field(default=None, sa_column=Column(Text))
    review_articles_json: Optional[list[Any]] = Field(default=None, sa_column=Column(JSON))


class Article(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    chat_id: int = Field(foreign_key="chat.id", index=True)
    title: str
    url: str
    source: Optional[str] = None
    summary: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)


class PressReview(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    chat_id: int = Field(foreign_key="chat.id", index=True)
    topic: str
    content: str
    created_at: datetime = Field(default_factory=utcnow)
    # Sortie structurée de l’agent revue (titre éditorial, synthèse, points par article).
    review_title: Optional[str] = None
    general_summary: Optional[str] = Field(default=None, sa_column=Column(Text))
    articles_breakdown_json: Optional[list[Any]] = Field(default=None, sa_column=Column(JSON))
