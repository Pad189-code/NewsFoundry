from __future__ import annotations

import pytest
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.mistral import MistralModel

from services.llm import GeminiModel, build_native_gemini_model


def test_gemini_model_alias_is_google_model() -> None:
    assert GeminiModel is GoogleModel


def test_build_native_openai_returns_string() -> None:
    assert build_native_gemini_model("openai:gpt-4o-mini") == "openai:gpt-4o-mini"


def test_build_native_google_gla_returns_google_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    m = build_native_gemini_model("google-gla:gemini-1.5-flash")
    assert isinstance(m, GoogleModel)
    assert m.model_name == "gemini-1.5-flash"


def test_build_native_mistral_returns_mistral_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MISTRAL_API_KEY", "sk-test")
    m = build_native_gemini_model("mistral:mistral-small-latest")
    assert isinstance(m, MistralModel)
    assert m.model_name == "mistral-small-latest"
