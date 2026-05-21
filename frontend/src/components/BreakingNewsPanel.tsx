"use client";

import type { BreakingNewsDTO } from "@/lib/api";

type BreakingNewsPanelProps = {
  items: BreakingNewsDTO[];
  loading: boolean;
  error: string | null;
  onSelectSuggestion: (text: string) => void;
};

function formatPubLabel(iso: string | null | undefined): string {
  if (!iso) {
    return "";
  }
  try {
    return new Date(iso).toLocaleDateString("fr-FR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    });
  } catch {
    return "";
  }
}

export function BreakingNewsPanel({
  items,
  loading,
  error,
  onSelectSuggestion,
}: BreakingNewsPanelProps) {
  if (loading) {
    return (
      <p className="mt-6 text-xs text-slate-500" aria-live="polite">
        Chargement des dernières actualités…
      </p>
    );
  }

  if (error) {
    return (
      <p className="mt-6 text-xs text-amber-700" role="status">
        {error}
      </p>
    );
  }

  if (items.length === 0) {
    return null;
  }

  return (
    <div className="mt-8 text-left">
      <p className="text-xs font-semibold text-slate-700">
        Dernières actualités — cliquez pour explorer
      </p>
      <ul className="mt-3 max-h-48 space-y-2 overflow-y-auto text-left">
        {items.slice(0, 6).map((item) => {
          const date = formatPubLabel(
            item.published_at as string | null | undefined,
          );
          const suggestion = item.summary
            ? `Parlez-moi de : ${item.title}`
            : `Quelles sont les dernières nouvelles sur : ${item.title} ?`;
          return (
            <li key={item.title}>
              <button
                type="button"
                onClick={() => onSelectSuggestion(suggestion)}
                className="w-full rounded-lg border border-slate-200 bg-slate-50/80 px-3 py-2 text-left text-xs text-slate-600 transition hover:border-[#803cda]/40 hover:bg-white"
              >
                <span className="font-medium text-slate-800">{item.title}</span>
                {date ? (
                  <span className="text-slate-400"> — {date}</span>
                ) : null}
                {item.summary ? (
                  <span className="mt-0.5 block line-clamp-2 text-slate-500">
                    {item.summary}
                  </span>
                ) : null}
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
