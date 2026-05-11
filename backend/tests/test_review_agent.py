from __future__ import annotations

import asyncio

import pytest
from pydantic_ai.models.test import TestModel

from services.review_agent import (
    ArticleMentionOutput,
    PressReviewAgentOutput,
    build_press_review_agent,
    format_review_markdown,
    run_press_review_structured,
    sanitize_transcript_for_review,
)


def test_sanitize_transcript_removes_assistant_error_lines() -> None:
    raw = """USER: Qui va sur la Lune ?
ASSISTANT: Impossible d'appeler le modèle d'IA (vérifiez OPENAI_API_KEY côté serveur). Détail technique: ModelHTTPError.
USER: Merci"""
    clean = sanitize_transcript_for_review(raw)
    assert "Impossible" not in clean
    assert "ModelHTTPError" not in clean
    assert "Qui va sur la Lune" in clean
    assert "Merci" in clean


def test_format_review_markdown() -> None:
    out = PressReviewAgentOutput(
        title="T",
        general_summary="G",
        articles_mentioned=[
            ArticleMentionOutput(article_title="A1", synthesis="S1"),
        ],
    )
    md = format_review_markdown(out)
    assert "# T" in md
    assert "Synthèse générale" in md
    assert "A1" in md


def test_run_press_review_structured_with_test_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    model = TestModel(
        call_tools=[],
        custom_output_args={
            "title": "Revue test",
            "general_summary": "Une synthèse.",
            "articles_mentioned": [
                {"article_title": "Actu X", "synthesis": "Détail court."},
            ],
        },
    )

    async def _run() -> PressReviewAgentOutput:
        return await run_press_review_structured(
            topic="espace",
            transcript="USER: Bonjour\nASSISTANT: Salut",
            articles_rag="",
            model=model,
        )

    out = asyncio.run(_run())
    assert out.title == "Revue test"
    assert out.general_summary == "Une synthèse."
    assert len(out.articles_mentioned) == 1
    assert out.articles_mentioned[0].article_title == "Actu X"


def test_build_press_review_agent_accepts_test_model() -> None:
    model = TestModel(
        call_tools=[],
        custom_output_args={
            "title": "x",
            "general_summary": "y",
            "articles_mentioned": [],
        },
    )
    agent = build_press_review_agent(model=model)
    assert agent is not None
