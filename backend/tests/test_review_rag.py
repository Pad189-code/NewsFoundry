"""RAG revue : fallback sans clé API et désactivation explicite."""

from __future__ import annotations

import pytest

from services.review_llm import format_articles_rag_for_prompt
from services.review_rag import retrieve_review_context


def test_retrieve_review_context_empty() -> None:
    assert retrieve_review_context("sujet", []) == ""


def test_retrieve_review_context_disabled_matches_legacy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEWSFOUNDRY_DISABLE_RAG", "1")
    arts = [("Titre A", "Résumé A", "https://a.example")]
    legacy = format_articles_rag_for_prompt(arts)
    assert retrieve_review_context("technologie", arts) == legacy


def test_retrieve_review_context_no_openai_key_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NEWSFOUNDRY_DISABLE_RAG", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("USE_HF_EMBEDDINGS", raising=False)
    arts = [("Titre B", "Synthèse", "https://b.example")]
    assert retrieve_review_context("emploi", arts) == format_articles_rag_for_prompt(arts)
