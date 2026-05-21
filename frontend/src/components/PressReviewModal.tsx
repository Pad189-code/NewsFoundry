"use client";

type PressReviewModalProps = {
  open: boolean;
  topic: string;
  busy: boolean;
  canSubmit: boolean;
  onTopicChange: (value: string) => void;
  onClose: () => void;
  onSubmit: () => void;
};

export function PressReviewModal({
  open,
  topic,
  busy,
  canSubmit,
  onTopicChange,
  onClose,
  onSubmit,
}: PressReviewModalProps) {
  if (!open) {
    return null;
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="review-modal-title"
      onClick={() => !busy && onClose()}
    >
      <div
        className="relative flex w-[556px] max-w-[calc(100vw-2rem)] min-h-[370px] flex-col rounded-xl bg-white px-8 py-8 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          type="button"
          disabled={busy}
          className="absolute right-5 top-5 text-sm text-slate-500 hover:text-slate-800 disabled:opacity-50"
          onClick={onClose}
        >
          Fermer
        </button>
        <div className="flex flex-1 flex-col justify-center">
          <h2
            id="review-modal-title"
            className="text-center text-lg font-semibold text-slate-900"
          >
            Générer une revue de presse
          </h2>
          <p className="mt-2 text-center text-sm text-slate-500">
            Donner un titre à votre revue de presse
          </p>
          <label className="mt-8 block text-sm font-medium text-slate-800">
            Thème de la revue de presse
            <input
              value={topic}
              onChange={(event) => onTopicChange(event.target.value)}
              disabled={busy}
              autoFocus
              className="mt-2 w-full rounded-lg border-0 bg-slate-100 px-4 py-3 text-sm text-slate-800 outline-none ring-1 ring-slate-200 focus:bg-white focus:ring-[#803cda] disabled:opacity-60"
              onKeyDown={(event) => {
                if (event.key === "Enter" && topic.trim() && canSubmit) {
                  event.preventDefault();
                  onSubmit();
                }
              }}
            />
          </label>
          <button
            type="button"
            disabled={busy || !topic.trim() || !canSubmit}
            onClick={onSubmit}
            className="mt-8 w-full rounded-lg bg-[#23232f] px-4 py-3 text-sm font-medium text-white hover:bg-[#1a1a24] disabled:opacity-50"
          >
            {busy ? "Génération en cours…" : "Générer"}
          </button>
        </div>
      </div>
    </div>
  );
}
