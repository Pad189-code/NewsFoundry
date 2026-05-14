"""Formatage des erreurs LLM pour l’UI (sans dépendre des agents ni de la base)."""

from __future__ import annotations

from pydantic_ai.exceptions import ModelAPIError, ModelHTTPError


def format_llm_exception(exc: BaseException, *, max_body: int = 1200) -> str:
    """Détail lisible (ModelHTTPError : status + corps API)."""
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


def hint_for_rate_limit_429(detail: str) -> str:
    """Court conseil utilisateur quand le corps d’erreur l’indique (ex. Mistral 3505)."""
    low = detail.lower()
    if "service_tier_capacity" in low or "3505" in detail:
        return (
            " Côté Mistral (capacité du palier / du modèle) : essayez un autre identifiant dans "
            "MISTRAL_MODEL (ex. open-mistral-nemo-latest), patientez, ou consultez paliers et facturation "
            "sur https://console.mistral.ai ."
        )
    return ""
