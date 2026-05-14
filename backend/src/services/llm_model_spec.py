"""Résolution et normalisation des identifiants de modèles (Mistral / Google Gemini / OpenAI) pour PydanticAI."""

from __future__ import annotations

import os

# Modèle Gemini recommandé pour la prod (évite les noms expérimentaux / endpoints instables).
DEFAULT_GEMINI_MODEL_ID = "gemini-1.5-flash"
# Modèle Mistral par défaut si seule ``MISTRAL_API_KEY`` est définie (voir doc Mistral pour les noms à jour).
DEFAULT_MISTRAL_MODEL_ID = "mistral-small-latest"


def strip_latest_suffix(model_id: str) -> str:
    """Retire un suffixe ``-latest`` (souvent source de 404 selon l'endpoint Google)."""
    s = model_id.strip()
    if s.lower().endswith("-latest"):
        return s[: -len("-latest")]
    return s


def normalize_gemini_model_id(raw: str) -> str:
    """Extrait l'ID Gemini depuis ``GEMINI_MODEL`` ou une spec ``google-gla:…``."""
    s = raw.strip()
    for prefix in ("google-gla:", "google-vertex:"):
        if s.lower().startswith(prefix):
            s = s[len(prefix) :].strip()
            break
    s = strip_latest_suffix(s)
    return s or DEFAULT_GEMINI_MODEL_ID


def normalize_mistral_model_id(raw: str) -> str:
    """Extrait l’ID modèle Mistral depuis ``MISTRAL_MODEL`` ou ``mistral:…``.

    Les noms Mistral côté API incluent souvent ``-latest`` : on ne retire pas ce suffixe
    (contrairement à Gemini), sinon l’API peut répondre 404 (ex. ``mistral-small`` invalide).
    """
    s = raw.strip()
    if s.lower().startswith("mistral:"):
        s = s[len("mistral:") :].strip()
    return s or DEFAULT_MISTRAL_MODEL_ID


def normalize_provider_model_spec(spec: str) -> str:
    """Normalise ``fournisseur:modèle`` (suffixe ``-latest``, préfixes redondants sur la partie modèle)."""
    s = spec.strip()
    if ":" not in s:
        return f"openai:{strip_latest_suffix(s)}"
    provider, mid = s.split(":", 1)
    p = provider.strip().lower()
    mid = mid.strip()
    if p in ("google-gla", "google-vertex"):
        mid = normalize_gemini_model_id(mid)
    elif p == "mistral":
        mid = normalize_mistral_model_id(mid)
    else:
        mid = strip_latest_suffix(mid)
    return f"{p}:{mid}"


def resolve_chat_model_env_string() -> str:
    """Chat : ``MISTRAL_MODEL``, ``GEMINI_MODEL``, ``OPENAI_MODEL``, puis défaut selon les clés."""
    mistral_m = os.getenv("MISTRAL_MODEL", "").strip()
    if mistral_m:
        return f"mistral:{normalize_mistral_model_id(mistral_m)}"
    gem = os.getenv("GEMINI_MODEL", "").strip()
    if gem:
        return f"google-gla:{normalize_gemini_model_id(gem)}"
    om = os.getenv("OPENAI_MODEL", "").strip()
    if om:
        return normalize_provider_model_spec(om)
    if os.getenv("GOOGLE_API_KEY", "").strip():
        return f"google-gla:{DEFAULT_GEMINI_MODEL_ID}"
    if os.getenv("MISTRAL_API_KEY", "").strip():
        return f"mistral:{DEFAULT_MISTRAL_MODEL_ID}"
    return "openai:gpt-4o-mini"


def resolve_review_model_env_string() -> str:
    """Revue : ``MISTRAL_REVIEW_MODEL``, ``GEMINI_REVIEW_MODEL``, ``OPENAI_REVIEW_MODEL``, puis alignement chat / défaut."""
    mistral_rev = os.getenv("MISTRAL_REVIEW_MODEL", "").strip()
    if mistral_rev:
        return f"mistral:{normalize_mistral_model_id(mistral_rev)}"
    gem_rev = os.getenv("GEMINI_REVIEW_MODEL", "").strip()
    if gem_rev:
        return f"google-gla:{normalize_gemini_model_id(gem_rev)}"
    explicit = os.environ.get("OPENAI_REVIEW_MODEL")
    if explicit is not None and explicit.strip():
        raw = explicit.strip()
        if ":" in raw:
            return normalize_provider_model_spec(raw)
        return normalize_provider_model_spec(f"openai:{raw}")
    mistral_m = os.getenv("MISTRAL_MODEL", "").strip()
    if mistral_m:
        return f"mistral:{normalize_mistral_model_id(mistral_m)}"
    gem = os.getenv("GEMINI_MODEL", "").strip()
    if gem:
        return f"google-gla:{normalize_gemini_model_id(gem)}"
    om = os.getenv("OPENAI_MODEL", "").strip()
    if om:
        return normalize_provider_model_spec(om)
    if os.getenv("GOOGLE_API_KEY", "").strip():
        return f"google-gla:{DEFAULT_GEMINI_MODEL_ID}"
    if os.getenv("MISTRAL_API_KEY", "").strip():
        return f"mistral:{DEFAULT_MISTRAL_MODEL_ID}"
    return "openai:gpt-4o-mini"


def effective_chat_model_spec(model: str | None) -> str:
    """Spec chaîne effective pour le chat (normalisation d'une valeur explicite)."""
    if model is None:
        return resolve_chat_model_env_string()
    return normalize_provider_model_spec(model)


def effective_review_model_spec(model: str | None) -> str:
    if model is None:
        return resolve_review_model_env_string()
    return normalize_provider_model_spec(model)
