from __future__ import annotations

import os
from typing import Iterable

from openai import AsyncOpenAI


def format_articles_rag_for_prompt(
    articles: Iterable[tuple[str, str, str | None, str | None]],
) -> str:
    """Bloc texte articles pour le prompt revue (réutilisé par la route)."""
    return _rag_block(articles)


def _rag_block(articles: Iterable[tuple[str, str, str | None, str | None]]) -> str:
    lines = []
    for title, summary, url, published in articles:
        date_line = (
            f"Date de publication : {published}\n"
            if published
            else ""
        )
        lines.append(f"## {title}\n{date_line}{summary or ''}\nLien: {url or 'n/a'}\n")
    return "\n".join(lines)


def _fallback_review(topic: str, rag: str) -> str:
    return (
        f"# Revue de presse — {topic}\n\n"
        f"_Génération locale (OPENAI_API_KEY non configurée)._\n\n"
        f"## Synthèse à partir des sources chargées\n\n"
        f"{rag[:6000]}\n\n"
        "---\n"
        "Pour une rédaction IA complète, configurez OPENAI_API_KEY sur le backend."
    )


async def generate_press_review(
    *,
    topic: str,
    articles: list[tuple[str, str, str | None, str | None]],
    transcript: str,
) -> str:
    rag = _rag_block(articles)
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return _fallback_review(topic, rag)

    model = os.getenv("OPENAI_REVIEW_MODEL", "gpt-4o-mini")
    client = AsyncOpenAI(api_key=api_key)
    system = (
        "Tu es un journaliste senior. Rédige une revue de presse structurée en français "
        "à partir UNIQUEMENT des sources fournies (RAG). Cite les faits de façon neutre. "
        "Utilise des sections Markdown (##, listes). Ne fabrique pas de sources absentes. "
        "Privilégie les articles les plus récents et indique leur date de publication."
    )
    user = (
        f"Thématique demandée: {topic}\n\n"
        f"## Sources (articles, du plus récent au plus ancien)\n{rag}\n\n"
        f"## Échanges avec l'utilisateur (contexte)\n{transcript[:8000]}\n"
    )

    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.4,
    )
    choice = response.choices[0].message.content
    return (choice or "").strip() or _fallback_review(topic, rag)
