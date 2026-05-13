"use client";

import Image from "next/image";
import {
  Suspense,
  useCallback,
  useEffect,
  useRef,
  useState,
  useSyncExternalStore,
  type MouseEvent,
} from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  createChat,
  createPressReview,
  deleteChat,
  fetchBreakingNews,
  listAllPressReviews,
  listChats,
  listMessages,
  listReviews,
  sendMessage,
  type ChatDTO,
  type MessageDTO,
  type PressReviewDTO,
} from "@/lib/api";
import { ChatMarkdown } from "@/components/ChatMarkdown";
import { clearSession, getStoredEmail, isAuthenticated } from "@/lib/auth";

type ViewMode = "home" | "chat" | "review";

type AuthSnapshot = {
  ready: boolean;
  authenticated: boolean;
  email: string;
};

const SERVER_AUTH_SNAPSHOT: AuthSnapshot = {
  ready: false,
  authenticated: false,
  email: "",
};

let clientAuthSnapshot: AuthSnapshot = {
  ready: true,
  authenticated: false,
  email: "",
};

function getClientAuthSnapshot(): AuthSnapshot {
  const nextSnapshot: AuthSnapshot = {
    ready: true,
    authenticated: isAuthenticated(),
    email: getStoredEmail() ?? "",
  };

  if (
    clientAuthSnapshot.authenticated !== nextSnapshot.authenticated ||
    clientAuthSnapshot.email !== nextSnapshot.email
  ) {
    clientAuthSnapshot = nextSnapshot;
  }

  return clientAuthSnapshot;
}

function formatFrDate(iso: string): string {
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

function ChatsPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [prompt, setPrompt] = useState("");
  const [viewMode, setViewMode] = useState<ViewMode>("home");
  const [activeTab, setActiveTab] = useState<"chat" | "review">("chat");
  const [chats, setChats] = useState<ChatDTO[]>([]);
  const [selectedConversationId, setSelectedConversationId] = useState<
    number | null
  >(null);
  const [messages, setMessages] = useState<MessageDTO[]>([]);
  const [reviews, setReviews] = useState<PressReviewDTO[]>([]);
  const [allPressReviews, setAllPressReviews] = useState<PressReviewDTO[]>([]);
  const [reviewTopic, setReviewTopic] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const autoNewsAttempted = useRef<Set<number>>(new Set());

  const authState = useSyncExternalStore(
    () => () => undefined,
    getClientAuthSnapshot,
    () => SERVER_AUTH_SNAPSHOT,
  );
  const isReviewRoute = searchParams.get("tab") === "review";
  const currentTab = isReviewRoute ? "review" : activeTab;
  const currentViewMode = isReviewRoute ? "review" : viewMode;

  useEffect(() => {
    if (authState.ready && !authState.authenticated) {
      router.replace("/login");
    }
  }, [authState.authenticated, authState.ready, router]);

  useEffect(() => {
    if (!authState.authenticated || !isAuthenticated()) {
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const all = await listAllPressReviews();
        if (!cancelled) {
          setAllPressReviews(all);
        }
      } catch {
        if (!cancelled) {
          setAllPressReviews([]);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [authState.authenticated]);

  const loadConversationData = useCallback(async (conversationId: number) => {
    if (!isAuthenticated()) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const msgs = await listMessages(conversationId);
      setMessages(msgs);
      setViewMode(msgs.length === 0 ? "home" : "chat");

      if (
        msgs.length === 0 &&
        !autoNewsAttempted.current.has(conversationId)
      ) {
        autoNewsAttempted.current.add(conversationId);
        try {
          await fetchBreakingNews(conversationId, "actualites");
        } catch {
          /* WORLDNEWS_API_KEY optionnelle */
        }
      }

      const revs = await listReviews(conversationId);
      setReviews(revs);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Erreur de chargement",
      );
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    if (!authState.authenticated) {
      return;
    }
    if (!isAuthenticated()) {
      return;
    }

    let cancelled = false;
    (async () => {
      setBusy(true);
      setError(null);
      try {
        let items = await listChats();
        if (items.length === 0) {
          await createChat();
          items = await listChats();
        }
        if (cancelled) {
          return;
        }
        setChats(items);
        setSelectedConversationId((prev) => prev ?? items[0]?.id ?? null);
      } catch (requestError) {
        if (!cancelled) {
          setError(
            requestError instanceof Error
              ? requestError.message
              : "Erreur de chargement",
          );
        }
      } finally {
        if (!cancelled) {
          setBusy(false);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [authState.authenticated]);

  useEffect(() => {
    if (!authState.authenticated || selectedConversationId === null) {
      return;
    }
    const conversationId = selectedConversationId;
    queueMicrotask(() => {
      void loadConversationData(conversationId);
    });
  }, [authState.authenticated, selectedConversationId, loadConversationData]);

  function handleLogout() {
    clearSession();
    router.push("/login");
  }

  async function handleSubmitPrompt() {
    if (!prompt.trim() || selectedConversationId === null) {
      return;
    }
    if (!isAuthenticated()) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await sendMessage(selectedConversationId, prompt.trim());
      setPrompt("");
      await loadConversationData(selectedConversationId);
      const items = await listChats();
      setChats(items);
      setViewMode("chat");
      router.push("/chats");
      setActiveTab("chat");
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Envoi impossible",
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleDeleteConversation(
    chatId: number,
    event: MouseEvent,
  ) {
    event.stopPropagation();
    if (
      !window.confirm(
        "Supprimer cette discussion ? Les messages, articles et revues associés seront effacés de façon définitive.",
      )
    ) {
      return;
    }
    if (!isAuthenticated()) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await deleteChat(chatId);
      autoNewsAttempted.current.delete(chatId);
      let items = await listChats();
      if (items.length === 0) {
        await createChat();
        items = await listChats();
      }
      setChats(items);
      if (selectedConversationId === chatId) {
        setSelectedConversationId(items[0]?.id ?? null);
        setMessages([]);
        setReviews([]);
        setViewMode("home");
      }
      try {
        setAllPressReviews(await listAllPressReviews());
      } catch {
        setAllPressReviews([]);
      }
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Suppression impossible",
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleNewConversation() {
    if (!isAuthenticated()) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const created = await createChat();
      try {
        await fetchBreakingNews(created.id, "actualites");
      } catch {
        /* optionnel */
      }
      const items = await listChats();
      setChats(items);
      setSelectedConversationId(created.id);
      router.push("/chats");
      setActiveTab("chat");
      setViewMode("home");
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Creation impossible",
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleGenerateReview() {
    if (!reviewTopic.trim() || selectedConversationId === null) {
      return;
    }
    if (!isAuthenticated()) {
      return;
    }
    const topic = reviewTopic.trim();
    const chatId = selectedConversationId;
    setBusy(true);
    setError(null);
    try {
      try {
        await fetchBreakingNews(chatId, topic);
      } catch {
        /* Articles optionnels : la revue peut reposer sur l’historique du chat seul. */
      }
      await createPressReview(chatId, topic);
      setReviewTopic("");
      const revs = await listReviews(chatId);
      setReviews(revs);
      try {
        setAllPressReviews(await listAllPressReviews());
      } catch {
        /* ignore */
      }
    } catch (requestError) {
      const msg =
        requestError instanceof Error
          ? requestError.message
          : "Generation impossible";
      setError(
        msg.includes("Aucun article") || msg.includes("news/fetch")
          ? `${msg} Astuce : élargissez le thème ou vérifiez que WORLDNEWS_API_KEY est bien définie côté serveur.`
          : msg,
      );
    } finally {
      setBusy(false);
    }
  }

  if (!authState.ready || !authState.authenticated) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <p className="text-slate-600">Chargement...</p>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-100 p-6">
      <main className="min-h-[min(992px,100dvh)] max-h-[100dvh] w-full max-w-[1440px] overflow-hidden rounded-md border border-slate-200 bg-white shadow-sm md:h-[992px]">
        {/* Sur mobile : colonne discussions en haut (bouton visible). Sur md+ : barre 300px à gauche. */}
        <div className="grid h-full min-h-0 grid-cols-1 md:grid-cols-[300px_1fr]">
          <aside className="flex min-h-0 max-h-[40vh] flex-col border-slate-200 bg-white md:max-h-none md:border-r">
            <div className="shrink-0 border-b border-slate-200 px-5 py-4">
              <h1 className="text-xs font-medium text-[#803cda]">NEWSFOUNDRY</h1>
              <button
                type="button"
                disabled={busy}
                onClick={() => void handleNewConversation()}
                className="mt-3 w-full rounded-md bg-[#803cda] px-3 py-2.5 text-xs font-semibold text-white shadow-sm hover:bg-[#6f2fc3] disabled:opacity-50"
              >
                + Nouvelle discussion
              </button>
            </div>
            <ul className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
              {chats.map((chat) => (
                <li
                  key={chat.id}
                  className={`cursor-pointer rounded-md border p-3 hover:bg-slate-50 ${
                    selectedConversationId === chat.id
                      ? "border-[#803cda] bg-[#f4f4fb]"
                      : "border-slate-200"
                  }`}
                  onClick={() => {
                    setSelectedConversationId(chat.id);
                    router.push("/chats");
                    setActiveTab("chat");
                  }}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-slate-900">{chat.title}</p>
                      <p className="text-xs text-slate-500">
                        {formatFrDate(chat.updated_at)}
                      </p>
                    </div>
                    <button
                      type="button"
                      disabled={busy}
                      aria-label={`Supprimer la discussion ${chat.title}`}
                      className="shrink-0 rounded px-1.5 py-0.5 text-xs text-red-600 hover:bg-red-50 disabled:opacity-40"
                      onClick={(e) => void handleDeleteConversation(chat.id, e)}
                    >
                      Supprimer
                    </button>
                  </div>
                </li>
              ))}
            </ul>
            <button
              className="m-4 rounded-md border border-slate-300 px-3 py-2 text-sm text-[#898989] hover:bg-slate-100"
              onClick={handleLogout}
            >
              Se deconnecter
            </button>
          </aside>

          <section className="flex h-full flex-col bg-[#f4f4fb]">
            <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-4">
              <div className="flex flex-1 flex-col gap-1">
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      router.push("/chats");
                      setActiveTab("chat");
                      setViewMode("chat");
                    }}
                    className={`rounded-md px-3 py-1.5 text-xs ${
                      currentTab === "chat"
                        ? "bg-[#803cda] text-white"
                        : "border border-slate-300 bg-white text-[#898989]"
                    }`}
                  >
                    Chat
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      router.push("/chats?tab=review");
                    }}
                    className={`rounded-md px-3 py-1.5 text-xs ${
                      currentTab === "review"
                        ? "bg-[#803cda] text-white"
                        : "border border-slate-300 bg-white text-[#898989]"
                    }`}
                  >
                    Revue de presse
                  </button>
                </div>
                {busy ? (
                  <div
                    className="flex items-center gap-2 text-xs font-medium text-[#803cda]"
                    aria-live="polite"
                    aria-busy="true"
                  >
                    <span
                      className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-[#803cda] border-t-transparent"
                      aria-hidden
                    />
                    Traitement en cours…
                  </div>
                ) : null}
                {error ? (
                  <p className="text-xs text-red-600">{error}</p>
                ) : null}
              </div>
            </header>

            {currentTab === "chat" && currentViewMode === "home" ? (
              <div className="flex flex-1 items-center justify-center p-8">
                <div className="w-full max-w-[620px] rounded-xl bg-white px-12 py-14 text-center shadow-sm">
                  <div className="flex justify-center">
                    <Image
                      src="/Robo.png"
                      alt="Robot NewsFoundry"
                      width={76}
                      height={76}
                      className="h-auto w-[76px]"
                      priority
                    />
                  </div>
                  <h3 className="mt-4 text-lg font-semibold text-[#803cda]">
                    Assistant Revue de Presse IA
                  </h3>
                  <p className="mt-4 text-sm text-slate-500">
                    Posez-moi des questions sur l&apos;actualite recente ou
                    demandez-moi de generer une revue de presse.
                  </p>
                  <p className="mt-6 text-xs font-semibold text-slate-600">Exemples :</p>
                  <ul className="mt-2 space-y-1 text-xs text-slate-500">
                    <li>&quot;Quelles sont les dernieres nouvelles en politique ?&quot;</li>
                    <li>&quot;Genere une revue de presse sur la technologie&quot;</li>
                    <li>&quot;Resume l&apos;actualite economique de la semaine&quot;</li>
                  </ul>
                </div>
              </div>
            ) : null}

            {currentTab === "chat" && currentViewMode === "chat" ? (
              <div className="flex-1 overflow-y-auto p-8">
                <div className="mx-auto max-w-4xl space-y-6">
                  {messages.map((m) =>
                    m.role === "user" ? (
                      <div
                        key={m.id}
                        className="ml-auto max-w-[420px] rounded-md bg-[#23232f] p-4 text-sm text-white"
                      >
                        {m.content}
                      </div>
                    ) : (
                      <div
                        key={m.id}
                        className="max-w-[560px] rounded-md bg-white p-4 text-sm text-slate-700"
                      >
                        <ChatMarkdown content={m.content} />
                      </div>
                    ),
                  )}
                </div>
              </div>
            ) : null}

            {currentTab === "review" ? (
              <div className="flex-1 overflow-y-auto p-8">
                <div className="mx-auto max-w-4xl space-y-4">
                  <h3 className="text-lg font-semibold text-slate-800">Revues de Presse</h3>
                  <p className="text-sm text-slate-500">
                    Choisissez un sujet puis generez une revue a partir de l&apos;historique de la
                    discussion. Retrouvez ci-dessous toutes vos revues (toutes discussions).
                  </p>
                  <div className="flex flex-wrap items-end gap-2 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
                    <div className="min-w-[200px] flex-1">
                      <label className="block text-xs font-medium text-slate-600">
                        Sujet de la revue de presse
                      </label>
                      <input
                        value={reviewTopic}
                        onChange={(event) => setReviewTopic(event.target.value)}
                        placeholder="Ex. technologie et emploi"
                        className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-[#898989] outline-none focus:border-[#803cda]"
                      />
                    </div>
                    <button
                      type="button"
                      disabled={busy || !reviewTopic.trim()}
                      onClick={() => void handleGenerateReview()}
                      className="rounded-md bg-[#803cda] px-4 py-2 text-sm font-medium text-white hover:bg-[#6f2fc3] disabled:opacity-50"
                    >
                      Generer la revue de presse
                    </button>
                  </div>
                  <div className="rounded-lg border border-slate-200 bg-slate-50/80 p-4">
                    <h4 className="text-sm font-semibold text-slate-800">
                      Toutes vos revues (toutes discussions)
                    </h4>
                    <p className="mt-1 text-xs text-slate-500">
                      {allPressReviews.length === 0
                        ? "Aucune revue pour le moment."
                        : `${allPressReviews.length} revue(s).`}
                    </p>
                    <ul className="mt-3 max-h-[220px] space-y-2 overflow-y-auto text-xs">
                      {allPressReviews.map((r) => (
                        <li
                          key={`${r.chat_id}-${r.id}`}
                          className="rounded border border-slate-200 bg-white px-3 py-2 text-slate-700"
                        >
                          <span className="font-medium text-[#803cda]">
                            {r.review_title || r.topic}
                          </span>
                          {r.chat_title ? (
                            <span className="text-slate-500"> — {r.chat_title}</span>
                          ) : null}
                          {r.general_summary ? (
                            <p className="mt-1 line-clamp-2 text-slate-600">{r.general_summary}</p>
                          ) : null}
                        </li>
                      ))}
                    </ul>
                  </div>
                  {reviews.map((review) => (
                    <article
                      key={review.id}
                      className="rounded-lg bg-white p-6 shadow-sm"
                    >
                      <div className="mb-3 flex items-center justify-between gap-2">
                        <div>
                          <h4 className="text-sm font-semibold text-slate-800">
                            {review.review_title || review.topic}
                          </h4>
                          <p className="text-xs text-slate-500">
                            Sujet : {review.topic} — {formatFrDate(review.created_at)}
                          </p>
                          {review.general_summary ? (
                            <p className="mt-2 text-xs leading-relaxed text-slate-600">
                              {review.general_summary}
                            </p>
                          ) : null}
                        </div>
                        <button
                          type="button"
                          className="shrink-0 rounded-md bg-[#282833] px-4 py-2 text-xs text-[#898989]"
                          onClick={() =>
                            void navigator.clipboard.writeText(review.content)
                          }
                        >
                          Copier
                        </button>
                      </div>
                      <p className="text-sm leading-6 text-slate-700 whitespace-pre-wrap">
                        {review.content}
                      </p>
                    </article>
                  ))}
                </div>
              </div>
            ) : null}

            {currentTab === "chat" ? (
              <div className="border-t border-slate-200 bg-white p-4">
                <div className="flex gap-2">
                  <input
                    value={prompt}
                    onChange={(event) => setPrompt(event.target.value)}
                    placeholder="Tapez votre message ici..."
                    disabled={busy}
                    className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm text-[#898989] outline-none focus:border-[#803cda] disabled:bg-slate-50"
                    onKeyDown={(event) => {
                      if (event.key === "Enter" && !event.shiftKey) {
                        event.preventDefault();
                        void handleSubmitPrompt();
                      }
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => void handleSubmitPrompt()}
                    disabled={busy}
                    className="rounded-md disabled:opacity-40"
                    aria-label="Envoyer"
                  >
                    <Image
                      src="/EnvoiR.png"
                      alt="Envoyer"
                      width={40}
                      height={40}
                      className="h-10 w-auto"
                    />
                  </button>
                </div>
                <p className="mt-2 text-xs text-slate-500">
                  Connecte en tant que {authState.email}
                  {busy ? " — envoi en cours…" : ""}
                </p>
              </div>
            ) : (
              <div className="border-t border-slate-200 bg-white px-4 py-3">
                <p className="text-xs text-slate-500">
                  Connecte en tant que {authState.email}
                  {busy ? " — operation en cours…" : ""}
                </p>
              </div>
            )}
          </section>
        </div>
      </main>
    </div>
  );
}

export default function ChatsPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-slate-50">
          <p className="text-slate-600">Chargement…</p>
        </div>
      }
    >
      <ChatsPageContent />
    </Suspense>
  );
}
