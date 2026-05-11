from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

from pydantic_ai import Agent, RunContext
from pydantic_ai.exceptions import ModelAPIError, ModelHTTPError
from pydantic_ai.models import Model

from services.news import format_news_tool_result

logger = logging.getLogger(__name__)


def _format_llm_exception(exc: BaseException, *, max_body: int = 1200) -> str:
    """Détail lisible pour l’UI et les logs (ModelHTTPError inclut status + corps API Google/OpenAI)."""
    if isinstance(exc, ModelHTTPError):
        body = exc.body
        if body is None:
            body_s = ""
        elif isinstance(body, (bytes, bytearray)):
            body_s = body.decode("utf-8", errors="replace")
        else:
            body_s = str(body)
        body_s = " ".join(body_s.split())
        if len(body_s) > max_body:
            body_s = body_s[: max_body - 3] + "..."
        core = f"HTTP {exc.status_code}, modèle « {exc.model_name} »"
        if body_s:
            return f"{core}, réponse API : {body_s}"
        return core
    if isinstance(exc, ModelAPIError):
        return f"{exc.__class__.__name__} ({exc.model_name}): {exc.message}"
    return f"{exc.__class__.__name__}: {exc}"

def _credentials_ready(model: str | Model | None) -> bool:
    """OpenAI (openai:…) vs Google Gemini (google-gla:… / google-vertex:…)."""
    if isinstance(model, Model):
        return True
    spec = model if isinstance(model, str) else os.getenv("OPENAI_MODEL", "openai:gpt-4o-mini")
    sl = str(spec).lower()
    if sl.startswith("google-gla:") or sl.startswith("google-vertex:"):
        return bool(os.getenv("GOOGLE_API_KEY", "").strip())
    return bool(os.getenv("OPENAI_API_KEY", "").strip())


def _missing_key_hint(model: str | Model | None) -> str:
    if isinstance(model, Model):
        return "OPENAI_API_KEY ou GOOGLE_API_KEY"
    spec = model if isinstance(model, str) else os.getenv("OPENAI_MODEL", "openai:gpt-4o-mini")
    sl = str(spec).lower()
    if sl.startswith("google-gla:") or sl.startswith("google-vertex:"):
        return "GOOGLE_API_KEY (Google AI Studio / Vertex)"
    return "OPENAI_API_KEY"


SYSTEM_PROMPT_BASE = """Tu es un assistant spécialisé dans la revue de presse pour NewsFoundry.
Tu aides l'utilisateur à affiner sa veille : reformule, propose des angles, et si besoin appelle l'outil
pour chercher des articles récents. Réponds en français, de façon claire et professionnelle.
Tu peux t'appuyer sur le bloc « Dernières actualités » ci-dessous (titres et résumés issus de l'API)
pour répondre aux questions sur l'actualité du jour lorsque c'est pertinent."""


@dataclass
class ChatDeps:
    worldnews_api_key: str


def build_chat_agent(
    model: str | Model | None = None,
    system_prompt: str | None = None,
) -> Agent[ChatDeps, str]:
    resolved: str | Model | Any = (
        model if model is not None else os.getenv("OPENAI_MODEL", "openai:gpt-4o-mini")
    )
    sp = system_prompt if system_prompt is not None else SYSTEM_PROMPT_BASE
    agent = Agent(
        resolved,
        deps_type=ChatDeps,
        system_prompt=sp,
    )

    @agent.tool
    async def rechercher_actualites(ctx: RunContext[ChatDeps], sujet: str) -> str:
        """Recherche des articles d'actualité récents sur un sujet donné (API WorldNews)."""
        key = ctx.deps.worldnews_api_key
        if not key:
            return (
                "La clé WorldNewsAPI n'est pas configurée sur le serveur. "
                "Demandez à l'administrateur d'ajouter WORLDNEWS_API_KEY."
            )
        return await format_news_tool_result(key, sujet)

    return agent


async def run_agent_reply(
    *,
    user_message: str,
    history_text: str,
    articles_context: str,
    worldnews_api_key: str,
    model: str | Model | None = None,
    system_prompt: str | None = None,
) -> str:
    deps = ChatDeps(worldnews_api_key=worldnews_api_key)
    prompt_parts = []
    if articles_context.strip():
        prompt_parts.append("Articles déjà chargés pour cette discussion:\n" + articles_context.strip())
    if history_text.strip():
        prompt_parts.append("Historique récent:\n" + history_text.strip())
    prompt_parts.append("Message utilisateur:\n" + user_message.strip())
    full_prompt = "\n\n".join(prompt_parts)

    if not _credentials_ready(model):
        return (
            f"Impossible d'appeler le modèle d'IA (configurez {_missing_key_hint(model)} pour le modèle "
            f"défini dans OPENAI_MODEL, puis redémarrez le backend). "
            "En attendant, voici un extrait du contexte articles disponible:\n\n"
            + articles_context[:1200]
        )

    try:
        # build_chat_agent() instancie le client du fournisseur (OpenAI, Google, etc.).
        agent = build_chat_agent(model=model, system_prompt=system_prompt)
        result = await agent.run(full_prompt, deps=deps)
        return str(result.output).strip()
    except Exception as exc:  # noqa: BLE001
        logger.warning("run_agent_reply: échec appel modèle", exc_info=True)
        detail = _format_llm_exception(exc)
        return (
            "Impossible d'appeler le modèle d'IA (vérifiez "
            f"{_missing_key_hint(model)} et la valeur de OPENAI_MODEL — chaîne « fournisseur:modèle », "
            "ex. google-gla:gemini-2.0-flash). "
            f"Détail technique : {detail}. "
            "En attendant, voici un extrait du contexte articles disponible:\n\n"
            + articles_context[:1200]
        )
