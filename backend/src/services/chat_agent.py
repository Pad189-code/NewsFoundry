from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Any

import httpx
from pydantic_ai import Agent, RunContext
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.models import Model

from services.article_tool_persist import persist_fetched_articles_for_chat
from services.llm import build_native_gemini_model
from services.llm_exception_format import format_llm_exception, hint_for_rate_limit_429
from services.news import format_worldnews_http_error, sanitize_worldnews_error_detail
from services.llm_model_spec import effective_chat_model_spec, resolve_chat_model_env_string
from services.news import search_news_for_chat_tool

logger = logging.getLogger(__name__)


def _string_model_spec(model: str | Model | None) -> str | None:
    """Spec ``fournisseur:modèle`` pour les contrôles de clé ; ``None`` si instance ``Model``."""
    if isinstance(model, Model):
        return None
    if isinstance(model, str):
        return effective_chat_model_spec(model)
    return resolve_chat_model_env_string()


def _credentials_ready(model: str | Model | None) -> bool:
    """Clés présentes selon le fournisseur (OpenAI, Google Gemini, Mistral)."""
    if isinstance(model, Model):
        return True
    spec = _string_model_spec(model)
    assert spec is not None
    sl = spec.lower()
    if sl.startswith("google-gla:") or sl.startswith("google-vertex:"):
        return bool(os.getenv("GOOGLE_API_KEY", "").strip())
    if sl.startswith("mistral:"):
        return bool(os.getenv("MISTRAL_API_KEY", "").strip())
    return bool(os.getenv("OPENAI_API_KEY", "").strip())


def _is_worldnews_exception(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        try:
            host = (exc.request.url.host or "").lower()
        except Exception:  # noqa: BLE001
            host = ""
        if "worldnewsapi" in host:
            return True
    low = str(exc).lower()
    return "worldnewsapi.com" in low or "worldnewsapi" in low or "world news api" in low


def _worldnews_failure_reply(
    *,
    exc: httpx.HTTPStatusError,
    articles_context: str,
) -> str:
    detail = format_worldnews_http_error(exc)
    return (
        "Impossible de rechercher des articles en ligne (World News API). "
        f"{detail} "
        "Le modèle d'IA (MISTRAL_API_KEY, etc.) n'est pas en cause si seule cette erreur apparaît. "
        "En attendant, voici un extrait du contexte articles disponible:\n\n"
        + articles_context[:1200]
    )


def _missing_key_hint(model: str | Model | None) -> str:
    if isinstance(model, Model):
        return "OPENAI_API_KEY, GOOGLE_API_KEY ou MISTRAL_API_KEY"
    spec = _string_model_spec(model)
    assert spec is not None
    sl = spec.lower()
    if sl.startswith("google-gla:") or sl.startswith("google-vertex:"):
        return "GOOGLE_API_KEY (Google AI Studio / Vertex)"
    if sl.startswith("mistral:"):
        return "MISTRAL_API_KEY (console Mistral)"
    return "OPENAI_API_KEY"


SYSTEM_PROMPT_BASE = """Tu es un assistant spécialisé dans la revue de presse pour NewsFoundry.
À chaque message utilisateur, des articles de presse récents sont recherchés en ligne (World News API)
et fournis dans le contexte (« Articles de presse trouvés en ligne pour votre demande »).
Tu DOIS t'appuyer en priorité sur ces sources pour répondre : cite les faits, titres et dates quand ils
sont disponibles. Si le contexte est insuffisant, appelle l'outil rechercher_actualites avec une requête
affinée (mots-clés précis tirés du message utilisateur).
Réponds en français, de façon claire et professionnelle (listes à puces possibles).
Ne invente pas d'articles absents du contexte ni de l'outil."""


@dataclass
class ChatDeps:
    worldnews_api_key: str
    # Si défini, persistance des résultats outil → Article + chat.loaded_articles
    chat_id: int | None = None


def build_chat_agent(
    model: str | Model | None = None,
    system_prompt: str | None = None,
) -> Agent[ChatDeps, str]:
    resolved: str | Model | Any
    if isinstance(model, Model):
        resolved = model
    elif isinstance(model, str):
        resolved = build_native_gemini_model(effective_chat_model_spec(model))
    else:
        resolved = build_native_gemini_model(resolve_chat_model_env_string())
    sp = system_prompt if system_prompt is not None else SYSTEM_PROMPT_BASE
    agent = Agent(
        resolved,
        deps_type=ChatDeps,
        system_prompt=sp,
    )

    @agent.tool
    async def rechercher_actualites(ctx: RunContext[ChatDeps], sujet: str) -> str:
        """
        Recherche des articles d'actualité récents sur un sujet (requête texte World News API).
        Utilise cet outil pour compléter ou préciser la veille si le bloc d'articles déjà fourni
        ne couvre pas l'angle demandé par l'utilisateur.
        """
        key = ctx.deps.worldnews_api_key
        if not key:
            return (
                "La clé WorldNewsAPI n'est pas configurée sur le serveur. "
                "Demandez à l'administrateur d'ajouter WORLDNEWS_API_KEY."
            )
        text, items = await search_news_for_chat_tool(key, sujet)
        cid = ctx.deps.chat_id
        if cid is not None and items:
            await asyncio.to_thread(persist_fetched_articles_for_chat, cid, items)
        return text

    return agent


async def run_agent_reply(
    *,
    user_message: str,
    history_text: str,
    articles_context: str,
    worldnews_api_key: str,
    chat_id: int | None = None,
    model: str | Model | None = None,
    system_prompt: str | None = None,
) -> str:
    deps = ChatDeps(worldnews_api_key=worldnews_api_key, chat_id=chat_id)
    prompt_parts = []
    if articles_context.strip():
        prompt_parts.append("Articles déjà chargés pour cette discussion:\n" + articles_context.strip())
    if history_text.strip():
        prompt_parts.append("Historique récent:\n" + history_text.strip())
    prompt_parts.append(
        "Consigne: répondez en vous appuyant sur les articles de presse du contexte "
        "(recherche en ligne déjà effectuée pour le message ci-dessous). "
        "Appelez rechercher_actualites uniquement si vous avez besoin d'articles "
        "complémentaires sur un sous-thème précis.\n"
    )
    prompt_parts.append("Message utilisateur:\n" + user_message.strip())
    full_prompt = "\n\n".join(prompt_parts)

    if not _credentials_ready(model):
        return (
            f"Impossible d'appeler le modèle d'IA (configurez {_missing_key_hint(model)} pour le modèle "
            f"défini (MISTRAL_MODEL, GEMINI_MODEL ou OPENAI_MODEL), puis redémarrez le backend). "
            "En attendant, voici un extrait du contexte articles disponible:\n\n"
            + articles_context[:1200]
        )

    try:
        # build_chat_agent() instancie le client du fournisseur (OpenAI, Google, etc.).
        agent = build_chat_agent(model=model, system_prompt=system_prompt)
        result = await agent.run(full_prompt, deps=deps)
        return str(result.output).strip()
    except ModelHTTPError as exc:
        logger.warning("run_agent_reply: erreur HTTP modèle", exc_info=True)
        if exc.status_code == 429:
            detail = format_llm_exception(exc, max_body=500)
            return (
                "Limite de débit, quota ou capacité du fournisseur d’IA (HTTP 429). "
                "Réessayez plus tard, espacez les messages, ou vérifiez votre plan "
                "(Mistral La Plateforme, Google AI Studio, OpenAI)."
                f"{hint_for_rate_limit_429(detail)} "
                f"Indication technique : {detail}"
            )
        if exc.status_code == 404:
            return "Modèle d'IA indisponible (vérifiez la config)."
        detail = format_llm_exception(exc)
        return (
            "Impossible d'appeler le modèle d'IA (vérifiez "
            f"{_missing_key_hint(model)} et MISTRAL_MODEL / GEMINI_MODEL / OPENAI_MODEL — ex. mistral:mistral-small-latest, "
            "google-gla:gemini-1.5-flash, openai:gpt-4o-mini). "
            f"Détail technique : {detail}. "
            "En attendant, voici un extrait du contexte articles disponible:\n\n"
            + articles_context[:1200]
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("run_agent_reply: échec appel agent", exc_info=True)
        detail = sanitize_worldnews_error_detail(format_llm_exception(exc))
        if isinstance(exc, httpx.HTTPStatusError) and _is_worldnews_exception(exc):
            return _worldnews_failure_reply(exc=exc, articles_context=articles_context)
        return (
            "Impossible d'appeler le modèle d'IA (vérifiez "
            f"{_missing_key_hint(model)} et MISTRAL_MODEL / GEMINI_MODEL / OPENAI_MODEL — ex. mistral:mistral-small-latest, "
            "google-gla:gemini-1.5-flash, openai:gpt-4o-mini). "
            f"Détail technique : {detail}. "
            "En attendant, voici un extrait du contexte articles disponible:\n\n"
            + articles_context[:1200]
        )
