"""Routes breaking news et bootstrap d’accueil chat."""

from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from services.news import format_breaking_news_welcome


def test_format_breaking_news_welcome_includes_titles() -> None:
    text = format_breaking_news_welcome(
        [{"title": "Actu A", "summary": "Résumé court.", "published_at": None}]
    )
    assert "Actu A" in text
    assert "revue de presse" in text.lower()


def test_get_breaking_news_requires_key(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.delenv("WORLDNEWS_API_KEY", raising=False)
    login = client.post(
        "/login",
        json={"email": "test@test.com", "password": "test"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    r = client.get("/news/breaking", headers=headers)
    assert r.status_code == 503


def test_bootstrap_welcome_empty_chat(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    import routes as routes_module

    async def fake_top(*, api_key: str, **kwargs: object) -> list[dict]:
        _ = api_key, kwargs
        return [{"title": "Titre test", "summary": "Synthèse.", "published_at": None}]

    async def fake_search(*, api_key: str, text: str, **kwargs: object) -> list[dict]:
        _ = api_key, text, kwargs
        return []

    monkeypatch.setattr(routes_module, "fetch_worldnews_top_news", fake_top)
    monkeypatch.setattr(routes_module, "fetch_worldnews_articles", fake_search)
    monkeypatch.setenv("WORLDNEWS_API_KEY", "dummy")

    login = client.post(
        "/login",
        json={"email": "test@test.com", "password": "test"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    created = client.post("/chats", headers=headers, json={"title": "Boot"})
    cid = created.json()["id"]

    boot = client.post(f"/chats/{cid}/bootstrap-welcome", headers=headers)
    assert boot.status_code == 200
    body = boot.json()
    assert body["role"] == "assistant"
    assert "Titre test" in body["content"]

    detail = client.get(f"/chats/{cid}", headers=headers)
    assert len(detail.json()["messages"]) == 1
