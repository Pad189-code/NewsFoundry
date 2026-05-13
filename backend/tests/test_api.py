from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

import routes as routes_module

from database import engine
from models import Chat
from services.review_agent import ArticleMentionOutput, PressReviewAgentOutput


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "ok"
    assert body["app"] == "newsfoundry-api"


def test_login_invalid(client: TestClient) -> None:
    response = client.post(
        "/login",
        json={"email": "nope@nope.com", "password": "wrong"},
    )
    assert response.status_code == 401


def test_login_legacy_auth_alias(client: TestClient) -> None:
    """``/auth/login`` reste un alias de ``/login`` pour compatibilité."""
    response = client.post(
        "/auth/login",
        json={"email": "test@test.com", "password": "test"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_and_refresh(client: TestClient) -> None:
    login = client.post(
        "/login",
        json={"email": "test@test.com", "password": "test"},
    )
    assert login.status_code == 200
    body = login.json()
    assert "access_token" in body
    assert "refresh_token" in body
    access = body["access_token"]
    refresh = body["refresh_token"]

    me = client.get("/me", headers={"Authorization": f"Bearer {access}"})
    assert me.status_code == 200
    assert me.json()["email"] == "test@test.com"

    refreshed = client.post(
        "/auth/refresh",
        json={"refresh_token": refresh},
    )
    assert refreshed.status_code == 200
    new_body = refreshed.json()
    assert new_body["access_token"] != access
    assert new_body["refresh_token"] != refresh

    me2 = client.get(
        "/me",
        headers={"Authorization": f"Bearer {new_body['access_token']}"},
    )
    assert me2.status_code == 200


def test_chats_flow(client: TestClient) -> None:
    login = client.post(
        "/login",
        json={"email": "test@test.com", "password": "test"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    chats = client.get("/chats", headers=headers)
    assert chats.status_code == 200
    assert chats.json() == []

    created = client.post(
        "/chats",
        headers=headers,
        json={"title": "Ma discussion test"},
    )
    assert created.status_code == 200
    cid = created.json()["id"]

    chats2 = client.get("/chats", headers=headers)
    assert len(chats2.json()) == 1

    detail = client.get(f"/chats/{cid}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["messages"] == []

    msgs_only = client.get(f"/chats/{cid}/messages", headers=headers)
    assert msgs_only.status_code == 200
    assert msgs_only.json() == []

    no_auth = client.get(f"/chats/{cid}")
    assert no_auth.status_code == 403

    deleted = client.delete(f"/chats/{cid}", headers=headers)
    assert deleted.status_code == 204
    assert client.get(f"/chats/{cid}", headers=headers).status_code == 404
    assert client.get("/chats", headers=headers).json() == []


def test_chat_message_returns_assistant_reply(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    import routes as routes_module

    async def fake_run(
        *,
        user_message: str,
        history_text: str,
        articles_context: str,
        worldnews_api_key: str,
        model: object = None,
        system_prompt: str | None = None,
    ) -> str:
        _ = (
            user_message,
            history_text,
            articles_context,
            worldnews_api_key,
            model,
            system_prompt,
        )
        return "Réponse test NewsFoundry"

    monkeypatch.setattr(routes_module, "run_agent_reply", fake_run)

    login = client.post(
        "/login",
        json={"email": "test@test.com", "password": "test"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    created = client.post("/chats", headers=headers, json={"title": "T"})
    cid = created.json()["id"]

    msg = client.post(
        f"/chats/{cid}/messages",
        headers=headers,
        json={"content": "Bonjour"},
    )
    assert msg.status_code == 200
    body = msg.json()
    assert body["role"] == "assistant"
    assert body["content"] == "Réponse test NewsFoundry"

    detail = client.get(f"/chats/{cid}", headers=headers)
    msgs = detail.json()["messages"]
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user"
    assert msgs[1]["role"] == "assistant"


def test_press_review_structured_persisted_and_list_all_reviews(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    import routes as routes_module

    async def fake_run(
        *,
        user_message: str,
        history_text: str,
        articles_context: str,
        worldnews_api_key: str,
        model: object = None,
        system_prompt: str | None = None,
    ) -> str:
        _ = (
            user_message,
            history_text,
            articles_context,
            worldnews_api_key,
            model,
            system_prompt,
        )
        return "Réponse courte"

    async def fake_structured(
        *,
        topic: str,
        transcript: str,
        articles_rag: str,
        model: object = None,
    ) -> PressReviewAgentOutput:
        _ = transcript, articles_rag, model
        return PressReviewAgentOutput(
            title=f"Revue structurée — {topic}",
            general_summary="Synthèse globale test.",
            articles_mentioned=[
                ArticleMentionOutput(article_title="Fil lunaire", synthesis="Détail test."),
            ],
        )

    monkeypatch.setattr(routes_module, "run_agent_reply", fake_run)
    monkeypatch.setattr(routes_module, "run_press_review_structured", fake_structured)

    login = client.post(
        "/login",
        json={"email": "test@test.com", "password": "test"},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    created = client.post("/chats", headers=headers, json={"title": "Lune"})
    cid = created.json()["id"]

    assert (
        client.post(
            f"/chats/{cid}/messages",
            headers=headers,
            json={"content": "Qui est allé sur la Lune ?"},
        ).status_code
        == 200
    )

    rev = client.post(
        f"/chats/{cid}/reviews",
        headers=headers,
        json={"topic": "Programme Apollo"},
    )
    assert rev.status_code == 200
    body = rev.json()
    assert body["chat_id"] == cid
    assert body["review_title"] == "Revue structurée — Programme Apollo"
    assert body["general_summary"] == "Synthèse globale test."
    assert body["articles_breakdown"] and body["articles_breakdown"][0]["article_title"] == "Fil lunaire"

    with Session(engine) as session:
        chat = session.get(Chat, cid)
        assert chat is not None
        assert chat.review_display_title == body["review_title"]

    all_rev = client.get("/reviews", headers=headers)
    assert all_rev.status_code == 200
    items = all_rev.json()
    assert any(r["chat_id"] == cid and r.get("chat_title") for r in items)


def test_create_chat_persists_system_prompt_with_top_news(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    async def fake_top(*, api_key: str, **kwargs: object) -> list[dict[str, str]]:
        _ = api_key
        return [{"title": "Une actu", "summary": "Resume court pour le test."}]

    monkeypatch.setattr(routes_module, "fetch_worldnews_top_news", fake_top)
    monkeypatch.setenv("WORLDNEWS_API_KEY", "dummy-key")

    login = client.post(
        "/login",
        json={"email": "test@test.com", "password": "test"},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    created = client.post("/chats", headers=headers, json={"title": "T"})
    assert created.status_code == 200
    cid = created.json()["id"]

    with Session(engine) as session:
        chat = session.get(Chat, cid)
        assert chat is not None
        assert chat.system_prompt_saved
        assert "Une actu" in chat.system_prompt_saved
        assert "Resume court" in chat.system_prompt_saved
        assert "top-news" in chat.system_prompt_saved.lower() or "WorldNewsAPI" in (
            chat.system_prompt_saved or ""
        )


def test_user_cannot_access_other_users_chat(
    client: TestClient,
    other_user_token: str,
) -> None:
    login = client.post(
        "/login",
        json={"email": "test@test.com", "password": "test"},
    )
    token_a = login.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    created = client.post("/chats", headers=headers_a, json={"title": "Privé"})
    cid = created.json()["id"]

    headers_b = {"Authorization": f"Bearer {other_user_token}"}

    assert client.get(f"/chats/{cid}", headers=headers_b).status_code == 404
    assert (
        client.post(
            f"/chats/{cid}/messages",
            headers=headers_b,
            json={"content": "hack"},
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/chats/{cid}/news/fetch",
            headers=headers_b,
            json={"text": "x"},
        ).status_code
        == 404
    )
