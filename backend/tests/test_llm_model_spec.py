from __future__ import annotations

import pytest

from services.llm_model_spec import (
    normalize_gemini_model_id,
    normalize_provider_model_spec,
    resolve_chat_model_env_string,
    resolve_review_model_env_string,
)


def test_normalize_gemini_strips_prefix_and_latest() -> None:
    assert normalize_gemini_model_id("google-gla:gemini-1.5-flash-latest") == "gemini-1.5-flash"
    assert normalize_gemini_model_id("gemini-2.0-flash") == "gemini-2.0-flash"
    assert normalize_gemini_model_id("") == "gemini-1.5-flash"


def test_normalize_provider_model_spec() -> None:
    assert normalize_provider_model_spec("google-gla:gemini-1.5-flash-latest") == "google-gla:gemini-1.5-flash"
    assert normalize_provider_model_spec("openai:gpt-4o-mini-latest") == "openai:gpt-4o-mini"


def test_resolve_chat_prefers_gemini_model_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_MODEL", "google-gla:gemini-1.5-flash-latest")
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    assert resolve_chat_model_env_string() == "google-gla:gemini-1.5-flash"


def test_resolve_chat_defaults_to_gemini_when_only_google_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.setenv("GOOGLE_API_KEY", "x")
    assert resolve_chat_model_env_string() == "google-gla:gemini-1.5-flash"


def test_resolve_review_respects_openai_review_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEMINI_REVIEW_MODEL", raising=False)
    monkeypatch.setenv("OPENAI_REVIEW_MODEL", "gpt-4o-mini")
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    assert resolve_review_model_env_string() == "openai:gpt-4o-mini"
