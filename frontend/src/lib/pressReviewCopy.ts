import type { PressReviewDTO } from "@/lib/api";

function formatFrDateTime(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("fr-FR", {
      weekday: "long",
      day: "numeric",
      month: "long",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "";
  }
}

/** Retire la syntaxe Markdown courante pour un collage propre dans Word / Google Docs. */
function markdownToPlainText(md: string): string {
  return md
    .replace(/^#{1,6}\s+/gm, "")
    .replace(/\*\*(.+?)\*\*/g, "$1")
    .replace(/\*(.+?)\*/g, "$1")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/\[(.+?)\]\([^)]+\)/g, "$1")
    .trim();
}

function buildBodyFromStructured(review: PressReviewDTO): string {
  const parts: string[] = [];

  if (review.general_summary?.trim()) {
    parts.push("Synthèse générale", "", review.general_summary.trim(), "");
  }

  if (review.articles_breakdown?.length) {
    parts.push("Points par source ou thème", "");
    for (const article of review.articles_breakdown) {
      const dateSuffix = article.publication_date
        ? ` — publié le ${article.publication_date}`
        : "";
      parts.push(`${article.article_title}${dateSuffix}`, "", article.synthesis.trim(), "");
    }
  }

  return parts.join("\n").trim();
}

/** Texte complet de la revue, prêt à coller dans un autre document. */
export function formatPressReviewForClipboard(review: PressReviewDTO): string {
  const title = (review.review_title || review.topic).trim();
  const header: string[] = [title, formatFrDateTime(review.created_at)];

  if (review.chat_title) {
    header.push(`Discussion : ${review.chat_title}`);
  }

  const rawBody = review.content?.trim() || buildBodyFromStructured(review);
  const body = rawBody ? markdownToPlainText(rawBody) : "";

  return body ? `${header.join("\n")}\n\n${body}` : header.join("\n");
}

export async function copyTextToClipboard(text: string): Promise<boolean> {
  const value = text.trim();
  if (!value) {
    return false;
  }

  try {
    if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(value);
      return true;
    }
  } catch {
    /* repli ci-dessous */
  }

  if (typeof document === "undefined") {
    return false;
  }

  const textarea = document.createElement("textarea");
  textarea.value = value;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.left = "-9999px";
  textarea.style.top = "0";
  document.body.appendChild(textarea);
  textarea.focus();
  textarea.select();
  textarea.setSelectionRange(0, value.length);

  let ok = false;
  try {
    ok = document.execCommand("copy");
  } finally {
    document.body.removeChild(textarea);
  }

  return ok;
}
