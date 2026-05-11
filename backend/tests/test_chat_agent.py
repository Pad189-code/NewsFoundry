from __future__ import annotations

import asyncio

import pytest
from pydantic_ai.models.test import TestModel

from services.chat_agent import build_chat_agent, run_agent_reply


def test_run_agent_reply_with_pydantic_ai_test_model() -> None:
    """Utilitaire TestModel de PydanticAI : pas d'appel réseau, sortie contrôlée."""

    async def _run() -> str:
        model = TestModel(custom_output_text="OK agent NewsFoundry")
        return await run_agent_reply(
            user_message="Hello",
            history_text="",
            articles_context="",
            worldnews_api_key="",
            model=model,
        )

    assert asyncio.run(_run()) == "OK agent NewsFoundry"


def test_build_chat_agent_registers_news_tool() -> None:
    model = TestModel(custom_output_text="done", call_tools=[])
    agent = build_chat_agent(model=model)
    names = [t.name for t in agent.toolsets[0].tools.values()]  # type: ignore[attr-defined]
    assert "rechercher_actualites" in names


def test_run_agent_reply_without_openai_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sans OPENAI_API_KEY, l'échec survient à la construction du client : ne doit pas remonter en 500 API."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    async def _run() -> str:
        return await run_agent_reply(
            user_message="Bonjour",
            history_text="",
            articles_context="Contexte article de secours.",
            worldnews_api_key="",
        )

    out = asyncio.run(_run())
    assert "OPENAI_API_KEY" in out or "Impossible" in out
    assert "Contexte article" in out
