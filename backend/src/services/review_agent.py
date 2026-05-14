"""Agent PydanticAI dédié à la revue de presse (sans outils, sortie structurée)."""

from __future__ import annotations

import logging
import os

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.models import Model

from services.llm import build_native_gemini_model
from services.llm_exception_format import format_llm_exception, hint_for_rate_limit_429
from services.llm_model_spec import effective_review_model_spec, resolve_review_model_env_string

logger = logging.getLogger(__name__)


class ArticleMentionOutput(BaseModel):
    """Synthèse d’un article ou d’un fil thématique mentionné dans la discussion."""

    article_title: str = Field(description="Titre court ou thème de la source / du point abordé")
    synthesis: str = Field(description="Synthèse en 2 à 5 phrases, en français, factuelle")


class PressReviewAgentOutput(BaseModel):
    """Sortie structurée persistée en base (titre + synthèse + points par article)."""

    title: str = Field(description="Titre éditorial de la revue de presse (une ligne)")
    general_summary: str = Field(
        description="Synthèse générale de la discussion sur le thème demandé, en français"
    )
    articles_mentioned: list[ArticleMentionOutput] = Field(
        default_factory=list,
        description="Un élément par article ou angle distinct abordé dans le chat ou les sources",
    )


REVIEW_AGENT_SYSTEM = """Tu es un rédacteur en chef spécialisé en revue de presse pour NewsFoundry.
Ta tâche : produire une synthèse structurée à partir PRINCIPALEMENT de l’historique de discussion fourni.
Des extraits d’articles peuvent compléter le contexte : ne les cite que s’ils apparaissent dans l’historique ou dans le bloc sources.
Ignore totalement les messages d’erreur technique (ex. « Impossible d’appeler le modèle », OPENAI_API_KEY, ModelHTTPError) : ne les résume pas et ne les cite pas.
Aucun outil n’est disponible. Ne fabrique pas de faits absents du matériel fourni.
Réponds strictement via le schéma de sortie imposé (titre, synthèse générale, liste de points par article/thème)."""


# Réponses assistant de repli (chat) à exclure de la matière première de la revue
_ASSISTANT_NOISE_MARKERS: tuple[str, ...] = (
    "Impossible d'appeler le modèle d'IA",
    "Impossible d'appeler le modèle",
    "OPENAI_API_KEY",
    "ModelHTTPError",
    "OpenAIError",
)


def sanitize_transcript_for_review(transcript: str) -> str:
    """Retire les tours assistant purement techniques pour ne pas polluer la revue."""
    lines_out: list[str] = []
    for raw in transcript.splitlines():
        line = raw.rstrip()
        if not line:
            lines_out.append("")
            continue
        role, sep, rest = line.partition(":")
        if not sep:
            lines_out.append(raw)
            continue
        role_u = role.strip().upper()
        body = rest.lstrip()
        if role_u == "ASSISTANT" and any(m in body for m in _ASSISTANT_NOISE_MARKERS):
            continue
        lines_out.append(raw)
    text = "\n".join(lines_out).strip()
    if text:
        return text
    # Si tout était du bruit : ne garder au minimum que les questions utilisateur
    user_only: list[str] = []
    for raw in transcript.splitlines():
        if raw.strip().upper().startswith("USER:"):
            user_only.append(raw.strip())
    return "\n".join(user_only).strip() or transcript.strip()


def _string_review_spec(model: str | Model | None) -> str | None:
    if isinstance(model, Model):
        return None
    if isinstance(model, str):
        return effective_review_model_spec(model)
    return resolve_review_model_env_string()


def _review_llm_ready(model: str | Model | None) -> bool:
    if isinstance(model, Model):
        return True
    spec = _string_review_spec(model)
    assert spec is not None
    sl = spec.lower()
    if sl.startswith("google-gla:") or sl.startswith("google-vertex:"):
        return bool(os.getenv("GOOGLE_API_KEY", "").strip())
    if sl.startswith("mistral:"):
        return bool(os.getenv("MISTRAL_API_KEY", "").strip())
    return bool(os.getenv("OPENAI_API_KEY", "").strip())


def build_press_review_agent(model: str | Model | None = None) -> Agent[None, PressReviewAgentOutput]:
    if isinstance(model, Model):
        resolved: str | Model = model
    elif isinstance(model, str):
        resolved = build_native_gemini_model(effective_review_model_spec(model))
    else:
        resolved = build_native_gemini_model(resolve_review_model_env_string())
    return Agent(
        resolved,
        output_type=PressReviewAgentOutput,
        system_prompt=REVIEW_AGENT_SYSTEM,
    )


def _fallback_output(topic: str, transcript: str, articles_rag: str) -> PressReviewAgentOutput:
    """Repli sans LLM : reste structuré pour l’API et la base."""
    clean = sanitize_transcript_for_review(transcript)
    base = (clean or articles_rag.strip() or "(Aucun contenu exploitable.)")[:4000]
    mentions: list[ArticleMentionOutput] = []
    if articles_rag.strip():
        mentions.append(
            ArticleMentionOutput(
                article_title="Sources chargées",
                synthesis=articles_rag.strip()[:2500],
            )
        )
    if not mentions and base:
        mentions.append(
            ArticleMentionOutput(article_title="Discussion", synthesis=base[:2500])
        )
    return PressReviewAgentOutput(
        title=f"Revue de presse — {topic}",
        general_summary=base[:3000],
        articles_mentioned=mentions[:12],
    )


def format_review_markdown(out: PressReviewAgentOutput) -> str:
    lines = [f"# {out.title}\n", "## Synthèse générale\n\n", out.general_summary.strip(), "\n\n## Points par source ou thème\n"]
    for m in out.articles_mentioned:
        lines.append(f"\n### {m.article_title}\n\n{m.synthesis.strip()}\n")
    return "".join(lines)


def _quota_or_model_error_output(msg: str) -> PressReviewAgentOutput:
    return PressReviewAgentOutput(
        title="Revue de presse — indisponible",
        general_summary=msg,
        articles_mentioned=[],
    )


async def run_press_review_structured(
    *,
    topic: str,
    transcript: str,
    articles_rag: str,
    model: str | Model | None = None,
) -> PressReviewAgentOutput:
    """Appelle l’agent revue (sortie Pydantic) ; repli structuré si pas de clé ou erreur LLM."""
    if not _review_llm_ready(model):
        return _fallback_output(topic, transcript, articles_rag)

    clean_transcript = sanitize_transcript_for_review(transcript)
    user_block = (
        f"Thématique demandée pour la revue : {topic.strip()}\n\n"
        f"## Historique de la discussion (nettoyé)\n\n{clean_transcript[:120_000]}\n\n"
        f"## Extraits d’articles (contexte optionnel)\n\n{(articles_rag or '(Aucun article chargé.)').strip()[:80_000]}"
    )

    try:
        agent = build_press_review_agent(model=model)
        result = await agent.run(user_block)
        out = result.output
        if isinstance(out, PressReviewAgentOutput):
            return _polish_review_output(out)
        return _fallback_output(topic, transcript, articles_rag)
    except ModelHTTPError as exc:
        logger.warning("run_press_review_structured: erreur HTTP modèle", exc_info=True)
        if exc.status_code == 429:
            detail = format_llm_exception(exc, max_body=500)
            return _quota_or_model_error_output(
                "Limite de débit, quota ou capacité du fournisseur d’IA (HTTP 429). "
                "Réessayez plus tard ou vérifiez votre plan (Mistral La Plateforme, Google AI Studio, OpenAI)."
                f"{hint_for_rate_limit_429(detail)} "
                f"Indication technique : {detail}",
            )
        if exc.status_code == 404:
            return _quota_or_model_error_output("Modèle d'IA indisponible (vérifiez la config).")
        return _fallback_output(topic, transcript, articles_rag)
    except Exception:  # noqa: BLE001
        return _fallback_output(topic, transcript, articles_rag)


def _strip_noise_substrings(text: str) -> str:
    """Retire fragments d’erreurs API / config souvent recopiés dans un bloc de texte."""
    out = text
    for m in _ASSISTANT_NOISE_MARKERS:
        out = out.replace(m, "")
    for snippet in (
        "vérifiez OPENAI_API_KEY côté serveur.",
        "vérifiez OPENAI_API_KEY côté serveur",
        "En attendant, voici un extrait du contexte articles disponible:",
        "Détail technique:",
    ):
        out = out.replace(snippet, "")
    return " ".join(out.split()).strip()


def _polish_review_output(out: PressReviewAgentOutput) -> PressReviewAgentOutput:
    """Si le modèle a quand même recopié du bruit technique, le retirer des champs texte."""
    gs = _strip_noise_substrings(out.general_summary)
    if any(m in gs for m in _ASSISTANT_NOISE_MARKERS):
        gs = sanitize_transcript_for_review(gs)
    gs = _strip_noise_substrings(gs)
    if not gs:
        gs = (
            "Peu de contenu exploitable après filtrage des messages d’erreur technique. "
            "Rechargez une fois le modèle d’IA disponible, puis régénérez la revue."
        )
    title = out.title.strip()
    if any(m in title for m in _ASSISTANT_NOISE_MARKERS):
        title = _strip_noise_substrings(title) or title.split("—")[0].strip() or "Revue de presse"
    cleaned_mentions: list[ArticleMentionOutput] = []
    for m in out.articles_mentioned:
        syn = _strip_noise_substrings(m.synthesis)
        if any(x in syn for x in _ASSISTANT_NOISE_MARKERS):
            syn = sanitize_transcript_for_review(syn) or syn
        syn = _strip_noise_substrings(syn)
        if not syn:
            continue
        cleaned_mentions.append(ArticleMentionOutput(article_title=m.article_title, synthesis=syn))
    return PressReviewAgentOutput(
        title=title or out.title,
        general_summary=gs,
        articles_mentioned=cleaned_mentions or out.articles_mentioned,
    )
