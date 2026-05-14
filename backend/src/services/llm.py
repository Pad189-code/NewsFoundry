"""Construction des modèles PydanticAI (Google Gemini, Mistral, chaîne OpenAI).

``GoogleModel`` + ``GoogleProvider`` s’appuient sur le SDK ``google-genai``.
``MistralModel`` + ``MistralProvider`` sur le SDK ``mistralai`` (clé ``MISTRAL_API_KEY``).

Pour OpenAI, on renvoie la spec normalisée ``openai:…`` : PydanticAI utilise alors la clé ``OPENAI_API_KEY``.
"""

from __future__ import annotations

import os

from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.mistral import MistralModel
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.providers.mistral import MistralProvider

from services.llm_model_spec import normalize_provider_model_spec

# Alias intentionnel : nom historique « Gemini » → implémentation actuelle ``GoogleModel``.
GeminiModel = GoogleModel


def _google_api_key() -> str | None:
    key = (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or "").strip()
    return key or None


def _mistral_api_key() -> str | None:
    return os.getenv("MISTRAL_API_KEY", "").strip() or None


def build_native_gemini_model(normalized_spec: str) -> str | GoogleModel | MistralModel:
    """À partir d’une spec normalisée (``mistral:…``, ``google-gla:…``, ``openai:…``), retourne un modèle ou la chaîne OpenAI."""
    spec = normalize_provider_model_spec(normalized_spec)
    low = spec.lower()
    if low.startswith("mistral:"):
        model_id = spec.split(":", 1)[1].strip()
        return MistralModel(model_id, provider=MistralProvider(api_key=_mistral_api_key()))
    if low.startswith("google-gla:"):
        model_id = spec.split(":", 1)[1].strip()
        return GeminiModel(model_id, provider=GoogleProvider(api_key=_google_api_key()))
    if low.startswith("google-vertex:"):
        model_id = spec.split(":", 1)[1].strip()
        return GeminiModel(model_id, provider=GoogleProvider(vertexai=True))
    return spec
