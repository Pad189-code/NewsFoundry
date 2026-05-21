"""RAG optionnel (LlamaIndex) pour la revue de presse : retrieval par rapport au sujet."""

from __future__ import annotations

import logging
import os
from services.review_llm import format_articles_rag_for_prompt

logger = logging.getLogger(__name__)


def _rag_disabled() -> bool:
    return os.getenv("NEWSFOUNDRY_DISABLE_RAG", "").lower() in ("1", "true", "yes")


def retrieve_review_context(
    topic: str,
    articles: list[tuple[str, str, str | None, str | None]],
) -> str:
    """
    Construit un bloc « sources » pour l’agent revue.

    Si LlamaIndex + embeddings sont disponibles, ne retient que les passages les plus
    pertinents pour ``topic``. Sinon, retombe sur la concaténation titre/résumé (legacy).
    """
    if not articles:
        return ""

    if _rag_disabled():
        return format_articles_rag_for_prompt(articles)

    try:
        return _retrieve_with_llama_index(topic.strip(), articles)
    except ImportError:
        logger.info("LlamaIndex non installé : fallback bloc articles complet.")
        return format_articles_rag_for_prompt(articles)
    except Exception:
        logger.warning("retrieve_review_context: échec RAG, fallback", exc_info=True)
        return format_articles_rag_for_prompt(articles)


def _retrieve_with_llama_index(
    topic: str,
    articles: list[tuple[str, str, str | None, str | None]],
) -> str:
    from llama_index.core import Document, Settings, VectorStoreIndex

    use_hf = os.getenv("USE_HF_EMBEDDINGS", "").lower() in ("1", "true", "yes")

    if use_hf:
        try:
            from llama_index.embeddings.huggingface import HuggingFaceEmbedding

            model_name = os.getenv(
                "HF_EMBEDDING_MODEL",
                "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            )
            Settings.embed_model = HuggingFaceEmbedding(model_name=model_name)
        except ImportError as exc:
            raise ImportError(
                "USE_HF_EMBEDDINGS activé : installez llama-index-embeddings-huggingface "
                "et sentence-transformers."
            ) from exc
    else:
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            return format_articles_rag_for_prompt(articles)
        from llama_index.embeddings.openai import OpenAIEmbedding

        Settings.embed_model = OpenAIEmbedding(
            api_key=api_key,
            model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
        )

    documents: list[Document] = []
    for title, summary, url, published in articles:
        date_line = f"Date de publication : {published}\n\n" if published else ""
        body = (
            f"{title}\n\n{date_line}{summary or '(Pas de résumé)'}\n\n"
            f"URL: {url or 'n/a'}"
        )
        documents.append(
            Document(
                text=body,
                metadata={"title": title, "url": url or "", "published": published or ""},
            )
        )

    index = VectorStoreIndex.from_documents(documents)
    k = min(8, max(2, len(documents)))
    retriever = index.as_retriever(similarity_top_k=k)
    nodes = retriever.retrieve(topic or "revue de presse")

    lines: list[str] = [
        "## Sources jugées les plus pertinentes pour cette thématique\n",
        f"_Requête retrieval : « {topic} »._\n",
    ]
    seen_urls: set[str] = set()
    for i, ns in enumerate(nodes, start=1):
        node = ns.node
        meta = node.metadata or {}
        url = str(meta.get("url") or "").strip()
        if url and url in seen_urls:
            continue
        if url:
            seen_urls.add(url)
        title_meta = str(meta.get("title") or "").strip() or f"Source {i}"
        raw_text = str(getattr(node, "text", "") or "").strip()
        excerpt = raw_text[:3500]
        lines.append(f"### {i}. {title_meta}\n{excerpt}\n")

    if len(lines) <= 3:
        return format_articles_rag_for_prompt(articles)

    return "\n".join(lines)
