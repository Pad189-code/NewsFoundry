from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=10)


class LoginRequest(BaseModel):
    email: str
    password: str


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str


class ChatCreate(BaseModel):
    title: Optional[str] = None


class ChatListPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    updated_at: datetime


class ChatDetailPublic(BaseModel):
    """Historique complet pour affichage côté client."""

    id: int
    title: str
    updated_at: datetime
    messages: list["MessagePublic"]


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=8000)


class MessagePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: str
    created_at: datetime


class NewsFetchRequest(BaseModel):
    text: str = "actualites"


class BreakingNewsItemPublic(BaseModel):
    title: str
    summary: str
    published_at: Optional[datetime] = None


class ArticlePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    url: str
    source: Optional[str] = None
    summary: Optional[str] = None
    published_at: Optional[datetime] = None


class PressReviewCreate(BaseModel):
    topic: str = Field(min_length=1, max_length=500)


class PressReviewPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    chat_id: int
    topic: str
    content: str
    created_at: datetime
    chat_title: Optional[str] = None
    review_title: Optional[str] = None
    general_summary: Optional[str] = None
    articles_breakdown: Optional[list[dict[str, Any]]] = None
