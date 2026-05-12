"""Construction des modèles PydanticAI pour Gemini (API Google native, pas le mode compat OpenAI).

``GoogleModel`` + ``GoogleProvider`` s’appuient sur le SDK ``google-genai`` (paquet ``google-genai``).
Aucune ``base_url`` n’est passée ici : le client officiel gère les endpoints.

Le symbole ``GeminiModel`` est un alias de ``GoogleModel`` pour garder un nom familier côté appel.
"""

from __future__ import annotations

import os

from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

from services.llm_model_spec import normalize_provider_model_spec

# Alias intentionnel : nom historique « Gemini » → implémentation actuelle ``GoogleModel``.
GeminiModel = GoogleModel


def _google_api_key() -> str | None:
    key = (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or "").strip()
    return key or None


def build_native_gemini_model(normalized_spec: str) -> str | GoogleModel:
    """À partir d’une spec déjà normalisée (``google-gla:…``, ``openai:…``), retourne un modèle ou la chaîne OpenAI."""
    spec = normalize_provider_model_spec(normalized_spec)
    low = spec.lower()
    if low.startswith("google-gla:"):
        model_id = spec.split(":", 1)[1].strip()
        return GeminiModel(model_id, provider=GoogleProvider(api_key=_google_api_key()))
    if low.startswith("google-vertex:"):
        model_id = spec.split(":", 1)[1].strip()
        return GeminiModel(model_id, provider=GoogleProvider(vertexai=True))
    return spec
