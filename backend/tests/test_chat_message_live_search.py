"""POST /chats/{id}/messages déclenche une recherche presse avant la réponse agent."""

from __future__ import annotations

from fastapi.testclient import TestClient
import pytest


def test_append_message_triggers_live_search(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    import routes as routes_module

    calls: list[str] = []

    async def fake_live(chat_id: int, user_message: str) -> tuple[str, list]:
        _ = chat_id
        calls.append(user_message)
        return (
            "- **Titre presse** (01/05/2026)\n  Résumé.\n  URL: https://ex.test",
            [{"title": "Titre presse", "url": "https://ex.test"}],
        )

    async def fake_run(**kwargs: object) -> str:
        ctx = str(kwargs.get("articles_context", ""))
        assert "Titre presse" in ctx
        assert "santé" in ctx.lower() or "sante" in ctx.lower()
        return "Réponse basée sur la presse."

    monkeypatch.setattr(routes_module, "search_press_articles_for_message", fake_live)
    monkeypatch.setattr(routes_module, "run_agent_reply", fake_run)

    login = client.post(
        "/login",
        json={"email": "test@test.com", "password": "test"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    created = client.post("/chats", headers=headers, json={"title": "Veille"})
    cid = created.json()["id"]

    r = client.post(
        f"/chats/{cid}/messages",
        headers=headers,
        json={
            "content": "Je suis particulièrement curieux des applications dans le domaine de la santé",
        },
    )
    assert r.status_code == 200
    assert r.json()["content"] == "Réponse basée sur la presse."
    assert len(calls) == 1
    assert "santé" in calls[0]
