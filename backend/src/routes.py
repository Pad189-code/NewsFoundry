from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func
from models import Article, Chat, PressReview, User
from sqlmodel import Session, desc, select

from auth_tokens import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    get_current_user,
    verify_password,
)
from database import get_session
from rate_limit import limiter
from schemas import (
    ArticlePublic,
    ChatCreate,
    ChatDetailPublic,
    ChatListPublic,
    LoginRequest,
    MessageCreate,
    MessagePublic,
    NewsFetchRequest,
    PressReviewCreate,
    PressReviewPublic,
    RefreshRequest,
    TokenResponse,
    UserPublic,
)
from services.chat_agent import SYSTEM_PROMPT_BASE, run_agent_reply
from services.news import (
    fetch_worldnews_articles,
    fetch_worldnews_top_news,
    format_top_news_for_system_prompt,
    worldnews_api_key,
)
from services.review_agent import format_review_markdown, run_press_review_structured
from services.review_llm import format_articles_rag_for_prompt

router = APIRouter()


def _press_review_to_public(
    review: PressReview,
    *,
    chat_title: str | None = None,
) -> PressReviewPublic:
    raw_bd = review.articles_breakdown_json
    breakdown: list[dict] | None
    if raw_bd is None:
        breakdown = None
    elif isinstance(raw_bd, list):
        breakdown = [x for x in raw_bd if isinstance(x, dict)]
    else:
        breakdown = None
    return PressReviewPublic(
        id=int(review.id),  # type: ignore[arg-type]
        chat_id=int(review.chat_id),
        topic=review.topic,
        content=review.content,
        created_at=review.created_at,
        chat_title=chat_title,
        review_title=review.review_title,
        general_summary=review.general_summary,
        articles_breakdown=breakdown,
    )


def _coerce_messages_list(raw: object) -> list[dict]:
    if not raw:
        return []
    if isinstance(raw, list):
        return [m for m in raw if isinstance(m, dict)]
    return []


def _next_message_id(messages: list[dict]) -> int:
    best = 0
    for m in messages:
        try:
            mid = int(m.get("id", 0))
            if mid > best:
                best = mid
        except (TypeError, ValueError):
            continue
    return best + 1


def _message_dict_to_public(m: dict) -> MessagePublic:
    ca = m.get("created_at")
    if isinstance(ca, str):
        raw = ca.replace("Z", "+00:00")
        dt = datetime.fromisoformat(raw)
    else:
        dt = datetime.now(timezone.utc)
    return MessagePublic(
        id=int(m["id"]),
        role=str(m["role"]),
        content=str(m["content"]),
        created_at=dt,
    )


def _messages_as_text(messages: list[dict], limit: int = 30) -> str:
    tail = messages[-limit:] if len(messages) > limit else messages
    parts: list[str] = []
    for m in tail:
        parts.append(f"{str(m.get('role', '')).upper()}: {m.get('content', '')}")
    return "\n".join(parts)


@limiter.limit("10/minute")
@router.post("/auth/login", response_model=TokenResponse)
def login(
    request: Request,
    login_data: LoginRequest,
    session: Session = Depends(get_session),
) -> TokenResponse:
    email_norm = login_data.email.strip().lower()
    statement = select(User).where(func.lower(User.email) == email_norm)
    user = session.exec(statement).first()
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants invalides",
        )
    if user.id is None:
        raise HTTPException(status_code=500, detail="Utilisateur invalide")
    access = create_access_token(user.id)
    refresh = create_refresh_token(user.id)
    return TokenResponse(access_token=access, refresh_token=refresh)


@limiter.limit("30/minute")
@router.post("/auth/refresh", response_model=TokenResponse)
def refresh_tokens(
    request: Request,
    refresh_data: RefreshRequest,
    session: Session = Depends(get_session),
) -> TokenResponse:
    user_id = decode_refresh_token(refresh_data.refresh_token.strip())
    user = session.get(User, user_id)
    if not user or user.id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur introuvable",
        )
    access = create_access_token(user.id)
    new_refresh = create_refresh_token(user.id)
    return TokenResponse(access_token=access, refresh_token=new_refresh)


@router.get("/me", response_model=UserPublic)
def read_me(current: User = Depends(get_current_user)) -> UserPublic:
    return UserPublic.model_validate(current)


def _chat_or_404(session: Session, user_id: int, chat_id: int) -> Chat:
    chat = session.get(Chat, chat_id)
    if not chat or chat.user_id != user_id:
        raise HTTPException(status_code=404, detail="Discussion introuvable")
    return chat


async def _ensure_chat_system_prompt_saved(session: Session, chat: Chat) -> None:
    """Figée par discussion : base + brève top-news (titres + résumés), ou base seule si pas de clé / erreur."""
    if chat.system_prompt_saved:
        return
    key = worldnews_api_key()
    if not key:
        chat.system_prompt_saved = SYSTEM_PROMPT_BASE
    else:
        try:
            items = await fetch_worldnews_top_news(api_key=key)
            block = format_top_news_for_system_prompt(items)
            if block.strip():
                chat.system_prompt_saved = (
                    f"{SYSTEM_PROMPT_BASE}\n\n"
                    "### Dernières actualités (WorldNewsAPI top-news)\n"
                    f"{block}"
                )
            else:
                chat.system_prompt_saved = SYSTEM_PROMPT_BASE
        except Exception:
            chat.system_prompt_saved = SYSTEM_PROMPT_BASE
    session.add(chat)
    session.commit()
    session.refresh(chat)


def _articles_as_text(session: Session, chat_id: int) -> str:
    statement = select(Article).where(Article.chat_id == chat_id)
    rows = session.exec(statement).all()
    parts: list[str] = []
    for a in rows:
        parts.append(
            f"- {a.title} ({a.source or 'source inconnue'})\n  {a.summary or ''}\n  {a.url}"
        )
    return "\n".join(parts)


@router.get("/chats", response_model=list[ChatListPublic])
def list_chats(
    session: Session = Depends(get_session),
    current: User = Depends(get_current_user),
) -> list[Chat]:
    statement = (
        select(Chat)
        .where(Chat.user_id == current.id)
        .order_by(desc(Chat.updated_at))
    )
    return list(session.exec(statement).all())


@router.post("/chats", response_model=ChatListPublic)
async def create_chat(
    payload: ChatCreate,
    session: Session = Depends(get_session),
    current: User = Depends(get_current_user),
) -> Chat:
    now = datetime.now(timezone.utc)
    title = payload.title or f"Discussion du {now.strftime('%d/%m/%Y')}"
    chat = Chat(
        user_id=current.id,
        title=title,
        created_at=now,
        updated_at=now,
        messages_json=[],
    )
    session.add(chat)
    session.commit()
    session.refresh(chat)
    await _ensure_chat_system_prompt_saved(session, chat)
    session.refresh(chat)
    return chat


@router.get("/chats/{chat_id}", response_model=ChatDetailPublic)
def get_chat(
    chat_id: int,
    session: Session = Depends(get_session),
    current: User = Depends(get_current_user),
) -> ChatDetailPublic:
    chat = _chat_or_404(session, current.id, chat_id)
    raw = _coerce_messages_list(chat.messages_json)
    messages = [_message_dict_to_public(m) for m in raw]
    return ChatDetailPublic(
        id=chat.id,  # type: ignore[arg-type]
        title=chat.title,
        updated_at=chat.updated_at,
        messages=messages,
    )


@router.get("/chats/{chat_id}/messages", response_model=list[MessagePublic])
def list_chat_messages(
    chat_id: int,
    session: Session = Depends(get_session),
    current: User = Depends(get_current_user),
) -> list[MessagePublic]:
    """Même historique que GET /chats/{id} → messages (évite un 405 si un client fait GET sur ce chemin)."""
    chat = _chat_or_404(session, current.id, chat_id)
    raw = _coerce_messages_list(chat.messages_json)
    return [_message_dict_to_public(m) for m in raw]


@router.post("/chats/{chat_id}/messages", response_model=MessagePublic)
async def append_message(
    chat_id: int,
    payload: MessageCreate,
    session: Session = Depends(get_session),
    current: User = Depends(get_current_user),
) -> MessagePublic:
    chat = _chat_or_404(session, current.id, chat_id)
    now = datetime.now(timezone.utc)
    msgs = _coerce_messages_list(chat.messages_json)

    uid = _next_message_id(msgs)
    user_entry = {
        "id": uid,
        "role": "user",
        "content": payload.content.strip(),
        "created_at": now.isoformat(),
    }
    msgs.append(user_entry)
    chat.messages_json = msgs
    session.add(chat)
    session.commit()
    session.refresh(chat)

    history = _messages_as_text(msgs, limit=25)
    articles_block = _articles_as_text(session, chat_id)

    await _ensure_chat_system_prompt_saved(session, chat)
    session.refresh(chat)

    assistant_text = await run_agent_reply(
        user_message=payload.content.strip(),
        history_text=history,
        articles_context=articles_block,
        worldnews_api_key=worldnews_api_key(),
        system_prompt=chat.system_prompt_saved,
    )

    aid = _next_message_id(_coerce_messages_list(chat.messages_json))
    assistant_entry = {
        "id": aid,
        "role": "assistant",
        "content": assistant_text,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    msgs = _coerce_messages_list(chat.messages_json)
    msgs.append(assistant_entry)
    chat.messages_json = msgs
    chat.updated_at = datetime.now(timezone.utc)
    if chat.title.startswith("Discussion du") and len(payload.content.strip()) > 3:
        short = payload.content.strip().replace("\n", " ")[:60]
        chat.title = short + ("…" if len(payload.content.strip()) > 60 else "")

    session.add(chat)
    session.commit()
    session.refresh(chat)
    return _message_dict_to_public(assistant_entry)


@router.post("/chats/{chat_id}/news/fetch", response_model=list[ArticlePublic])
async def fetch_news_for_chat(
    chat_id: int,
    payload: NewsFetchRequest,
    session: Session = Depends(get_session),
    current: User = Depends(get_current_user),
) -> list[Article]:
    chat = _chat_or_404(session, current.id, chat_id)
    key = worldnews_api_key()
    if not key:
        raise HTTPException(
            status_code=503,
            detail="WORLDNEWS_API_KEY manquante sur le serveur",
        )

    raw_items = await fetch_worldnews_articles(api_key=key, text=payload.text)
    existing = session.exec(
        select(Article.url).where(Article.chat_id == chat_id)
    ).all()
    existing_urls = set(existing)

    created: list[Article] = []
    for item in raw_items:
        url = item.get("url") or ""
        if not url or url in existing_urls:
            continue
        art = Article(
            chat_id=chat_id,
            title=item.get("title") or "Sans titre",
            url=url,
            source=item.get("source"),
            summary=item.get("summary"),
        )
        session.add(art)
        created.append(art)
        existing_urls.add(url)

    chat.updated_at = datetime.now(timezone.utc)
    session.add(chat)
    session.commit()
    for art in created:
        session.refresh(art)
    return created


@router.get("/chats/{chat_id}/articles", response_model=list[ArticlePublic])
def list_articles(
    chat_id: int,
    session: Session = Depends(get_session),
    current: User = Depends(get_current_user),
) -> list[Article]:
    _chat_or_404(session, current.id, chat_id)
    statement = (
        select(Article)
        .where(Article.chat_id == chat_id)
        .order_by(desc(Article.created_at))
    )
    return list(session.exec(statement).all())


@router.get("/reviews", response_model=list[PressReviewPublic])
def list_all_press_reviews(
    session: Session = Depends(get_session),
    current: User = Depends(get_current_user),
) -> list[PressReviewPublic]:
    """Toutes les revues de presse de l’utilisateur, toutes discussions confondues."""
    stmt = (
        select(PressReview, Chat.title)
        .join(Chat, PressReview.chat_id == Chat.id)
        .where(PressReview.user_id == current.id)
        .order_by(desc(PressReview.created_at))
    )
    rows = session.exec(stmt).all()
    out: list[PressReviewPublic] = []
    for row in rows:
        review, title = row
        out.append(_press_review_to_public(review, chat_title=str(title)))
    return out


@router.get("/chats/{chat_id}/reviews", response_model=list[PressReviewPublic])
def list_reviews(
    chat_id: int,
    session: Session = Depends(get_session),
    current: User = Depends(get_current_user),
) -> list[PressReviewPublic]:
    _chat_or_404(session, current.id, chat_id)
    statement = (
        select(PressReview)
        .where(PressReview.chat_id == chat_id)
        .order_by(desc(PressReview.created_at))
    )
    rows = list(session.exec(statement).all())
    return [_press_review_to_public(r) for r in rows]


@router.post("/chats/{chat_id}/reviews", response_model=PressReviewPublic)
async def create_review(
    chat_id: int,
    payload: PressReviewCreate,
    session: Session = Depends(get_session),
    current: User = Depends(get_current_user),
) -> PressReviewPublic:
    chat = _chat_or_404(session, current.id, chat_id)

    msgs = _coerce_messages_list(chat.messages_json)
    transcript = _messages_as_text(msgs, limit=120)

    statement = select(Article).where(Article.chat_id == chat_id)
    articles_rows = list(session.exec(statement).all())

    if not transcript.strip() and not articles_rows:
        raise HTTPException(
            status_code=400,
            detail="Aucun message dans la discussion ni article chargé. "
            "Échangez dans le chat ou chargez des articles (news/fetch), puis réessayez.",
        )

    articles_tuples = [(a.title, a.summary or "", a.url) for a in articles_rows]
    articles_rag = (
        format_articles_rag_for_prompt(articles_tuples) if articles_tuples else ""
    )

    structured = await run_press_review_structured(
        topic=payload.topic.strip(),
        transcript=transcript,
        articles_rag=articles_rag,
    )
    content = format_review_markdown(structured)
    breakdown = [m.model_dump() for m in structured.articles_mentioned]

    review = PressReview(
        user_id=current.id,
        chat_id=chat_id,
        topic=payload.topic.strip(),
        content=content,
        review_title=structured.title,
        general_summary=structured.general_summary,
        articles_breakdown_json=breakdown,
    )
    session.add(review)

    chat.review_display_title = structured.title
    chat.review_general_summary = structured.general_summary
    chat.review_articles_json = breakdown
    chat.updated_at = datetime.now(timezone.utc)
    session.add(chat)
    session.commit()
    session.refresh(review)
    return _press_review_to_public(review, chat_title=chat.title)
