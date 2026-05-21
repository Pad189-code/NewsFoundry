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
  bootstrapChatWelcome,
  createChat,
  createPressReview,
  deleteChat,
  fetchBreakingNews,
  getBreakingNewsPreview,
  listAllPressReviews,
  listChats,
  listMessages,
  listReviews,
  sendMessage,
  listArticles,
  type ArticleDTO,
  type BreakingNewsDTO,
  type ChatDTO,
  type MessageDTO,
  type PressReviewDTO,
} from "@/lib/api";
import { BreakingNewsPanel } from "@/components/BreakingNewsPanel";
import { ChatMessageBubble } from "@/components/ChatMessageBubble";
import { ChatMarkdown } from "@/components/ChatMarkdown";
import { PressReviewModal } from "@/components/PressReviewModal";
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
  const [reviewTopic, setReviewTopic] = useState("");
  const [reviewModalOpen, setReviewModalOpen] = useState(false);
  const [loadedArticles, setLoadedArticles] = useState<ArticleDTO[]>([]);
  const [breakingNews, setBreakingNews] = useState<BreakingNewsDTO[]>([]);
  const [breakingNewsLoading, setBreakingNewsLoading] = useState(false);
  const [breakingNewsError, setBreakingNewsError] = useState<string | null>(
    null,
  );
  const [allPressReviews, setAllPressReviews] = useState<PressReviewDTO[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const autoNewsAttempted = useRef<Set<number>>(new Set());
  const welcomeBootstrapped = useRef<Set<number>>(new Set());
  const messagesEndRef = useRef<HTMLDivElement>(null);

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

  const loadConversationData = useCallback(
    async (conversationId: number) => {
      if (!isAuthenticated()) {
        return;
      }
      setBusy(true);
      setError(null);
      try {
        let msgs = await listMessages(conversationId);

        if (
          msgs.length === 0 &&
          !welcomeBootstrapped.current.has(conversationId)
        ) {
          welcomeBootstrapped.current.add(conversationId);
          autoNewsAttempted.current.add(conversationId);
          try {
            await bootstrapChatWelcome(conversationId);
            msgs = await listMessages(conversationId);
          } catch {
            try {
              await fetchBreakingNews(conversationId, "actualites");
            } catch {
              /* WORLDNEWS_API_KEY optionnelle */
            }
          }
        }

        setMessages(msgs);
        setViewMode(msgs.length === 0 ? "home" : "chat");

        const revs = await listReviews(conversationId);
        setReviews(revs);
        try {
          setLoadedArticles(await listArticles(conversationId));
        } catch {
          setLoadedArticles([]);
        }
      } catch (requestError) {
        setError(
          requestError instanceof Error
            ? requestError.message
            : "Erreur de chargement",
        );
      } finally {
        setBusy(false);
      }
    },
    [],
  );

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
    if (!authState.authenticated) {
      return;
    }
    let cancelled = false;
    void (async () => {
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

  useEffect(() => {
    if (
      !authState.authenticated ||
      currentTab !== "chat" ||
      currentViewMode !== "home"
    ) {
      return;
    }
    let cancelled = false;
    void (async () => {
      setBreakingNewsLoading(true);
      setBreakingNewsError(null);
      try {
        const items = await getBreakingNewsPreview();
        if (!cancelled) {
          setBreakingNews(items);
        }
      } catch (requestError) {
        if (!cancelled) {
          setBreakingNews([]);
          const msg =
            requestError instanceof Error
              ? requestError.message
              : "Actualités indisponibles";
          if (!msg.includes("503") && !msg.includes("WORLDNEWS")) {
            setBreakingNewsError(msg);
          } else {
            setBreakingNewsError(
              "Clé World News API non configurée — les suggestions d'actualité sont limitées.",
            );
          }
        }
      } finally {
        if (!cancelled) {
          setBreakingNewsLoading(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [authState.authenticated, currentTab, currentViewMode]);

  useEffect(() => {
    if (!authState.authenticated || selectedConversationId === null) {
      return;
    }
    const conversationId = selectedConversationId;
    queueMicrotask(() => {
      void loadConversationData(conversationId);
    });
  }, [authState.authenticated, selectedConversationId, loadConversationData]);

  useEffect(() => {
    if (isReviewRoute || activeTab !== "chat" || viewMode !== "chat") {
      return;
    }
    messagesEndRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "end",
    });
  }, [messages, isReviewRoute, activeTab, viewMode]);

  function handleLogout() {
    clearSession();
    router.push("/login");
  }

  async function handleSubmitPrompt() {
    if (!prompt.trim() || selectedConversationId === null) {
      if (!prompt.trim()) {
        return;
      }
      setError("Sélectionnez une discussion dans la colonne de gauche.");
      return;
    }
    if (!isAuthenticated()) {
      return;
    }
    const keepReviewTab = searchParams.get("tab") === "review";
    setBusy(true);
    setError(null);
    try {
      await sendMessage(selectedConversationId, prompt.trim());
      setPrompt("");
      await loadConversationData(selectedConversationId);
      if (reviewModalOpen && selectedConversationId !== null) {
        try {
          setLoadedArticles(await listArticles(selectedConversationId));
        } catch {
          /* ignore */
        }
      }
      const items = await listChats();
      setChats(items);
      setViewMode("chat");
      if (keepReviewTab) {
        router.push("/chats?tab=review");
        setActiveTab("review");
      } else {
        router.push("/chats");
        setActiveTab("chat");
      }
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
      welcomeBootstrapped.current.delete(chatId);
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
      welcomeBootstrapped.current.delete(created.id);
      autoNewsAttempted.current.delete(created.id);
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

  async function openReviewModal() {
    if (selectedConversationId === null) {
      return;
    }
    setReviewTopic("");
    setReviewModalOpen(true);
    setError(null);
    try {
      setLoadedArticles(await listArticles(selectedConversationId));
    } catch {
      setLoadedArticles([]);
    }
  }

  async function handleGenerateReview() {
    if (!reviewTopic.trim()) {
      return;
    }
    if (selectedConversationId === null) {
      setError(
        "Sélectionnez une discussion dans la colonne de gauche avant de générer une revue.",
      );
      return;
    }
    if (messages.length === 0 && loadedArticles.length === 0) {
      setError(
        "Chargez des articles via le chat (posez des questions sur l’actualité) avant de créer une revue.",
      );
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
      await createPressReview(chatId, topic);
      setReviewTopic("");
      setReviewModalOpen(false);
      const revs = await listReviews(chatId);
      setReviews(revs);
      try {
        setAllPressReviews(await listAllPressReviews());
      } catch {
        /* ignore */
      }
      router.push("/chats?tab=review");
      setActiveTab("review");
      setViewMode("chat");
    } catch (requestError) {
      const msg =
        requestError instanceof Error
          ? requestError.message
          : "Generation impossible";
      setError(
        msg.includes("Aucun message") || msg.includes("Aucun article")
          ? `${msg} Continuez la discussion pour enrichir le contexte, puis réessayez.`
          : msg,
      );
    } finally {
      setBusy(false);
    }
  }

  const selectedChat = chats.find((c) => c.id === selectedConversationId);
  const displayReviews = (
    allPressReviews.length > 0 ? allPressReviews : reviews
  ).sort(
    (a, b) =>
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  );

  function handleSuggestionClick(text: string) {
    setPrompt(text);
    if (viewMode === "home") {
      setViewMode("chat");
    }
  }

  async function handleCopyReview(content: string) {
    try {
      await navigator.clipboard.writeText(content);
    } catch {
      setError("Copie impossible dans le presse-papiers.");
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
    <div className="flex h-svh min-h-0 flex-col bg-slate-100 p-4 md:p-6">
      <main className="mx-auto flex min-h-0 w-full max-w-[1440px] flex-1 flex-col overflow-hidden rounded-md border border-slate-200 bg-white shadow-sm">
        <div className="grid min-h-0 flex-1 grid-cols-1 md:grid-cols-[minmax(0,280px)_minmax(0,1fr)] md:gap-0">
          <aside className="flex min-h-0 max-h-[36svh] flex-col border-slate-200 bg-white md:max-h-none md:border-r">
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
            <ul className="min-h-0 flex-1 space-y-1 overflow-y-auto overflow-x-hidden overscroll-contain px-3 py-4">
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
              className="m-4 shrink-0 rounded-md border border-slate-300 px-3 py-2 text-sm text-[#898989] hover:bg-slate-100"
              onClick={handleLogout}
            >
              Se deconnecter
            </button>
          </aside>

          <section className="flex min-h-0 flex-col overflow-hidden bg-[#f4f4fb] md:min-h-0">
            <header className="shrink-0 border-b border-slate-200 bg-white px-4 py-3 md:px-6 md:py-4">
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
                      setActiveTab("review");
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

            {currentTab === "chat" && currentViewMode === "chat" ? (
              <div className="shrink-0 border-b border-slate-200 bg-white px-4 py-3 md:px-6">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => {
                          router.push("/chats");
                          setActiveTab("chat");
                          setViewMode("home");
                        }}
                        className="text-slate-500 hover:text-slate-800"
                        aria-label="Retour"
                      >
                        ←
                      </button>
                      <h2 className="truncate text-sm font-semibold text-slate-900">
                        {selectedChat?.title ?? "Nouvelle discussion"}
                      </h2>
                    </div>
                    <p className="mt-0.5 pl-6 text-xs text-slate-500">
                      Conversation active
                    </p>
                  </div>
                  <button
                    type="button"
                    disabled={busy || selectedConversationId === null}
                    onClick={() => void openReviewModal()}
                    className="inline-flex items-center gap-2 rounded-md bg-[#803cda] px-4 py-2 text-xs font-medium text-white shadow-sm hover:bg-[#6f2fc3] disabled:opacity-50"
                  >
                    <span aria-hidden className="text-base leading-none">
                      📄
                    </span>
                    Générer une revue de presse
                  </button>
                </div>
              </div>
            ) : null}

            <div className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden overscroll-contain">
            {currentTab === "chat" && currentViewMode === "home" ? (
              <div className="flex min-h-full items-center justify-center p-6 md:p-8">
                <div className="w-full max-w-[620px] rounded-xl bg-white px-8 py-12 text-center shadow-sm md:px-12 md:py-14">
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
                    Posez-moi des questions sur l&apos;actualité récente ou
                    demandez-moi de générer une revue de presse sur un sujet
                    spécifique.
                  </p>
                  <BreakingNewsPanel
                    items={breakingNews}
                    loading={breakingNewsLoading}
                    error={breakingNewsError}
                    onSelectSuggestion={handleSuggestionClick}
                  />
                  <p className="mt-6 text-xs font-semibold text-slate-600">
                    Exemples :
                  </p>
                  <ul className="mt-2 space-y-1 text-xs text-slate-500">
                    <li>
                      &quot;Quelles sont les dernières nouvelles en politique
                      ?&quot;
                    </li>
                    <li>
                      &quot;Génère une revue de presse sur la technologie&quot;
                    </li>
                    <li>
                      &quot;Résume l&apos;actualité économique de la
                      semaine&quot;
                    </li>
                  </ul>
                </div>
              </div>
            ) : null}

            {currentTab === "chat" && currentViewMode === "chat" ? (
              <div className="p-4 md:p-8">
                <div className="mx-auto max-w-4xl space-y-6 pb-4">
                  {messages.map((m) => (
                    <ChatMessageBubble key={m.id} message={m} />
                  ))}
                  <div ref={messagesEndRef} className="h-px shrink-0" aria-hidden />
                </div>
              </div>
            ) : null}

            {currentTab === "review" ? (
              <div className="p-4 md:p-8">
                <div className="mx-auto max-w-4xl space-y-4 pb-6">
                  <h3 className="text-lg font-semibold text-slate-800">Revues de Presse</h3>
                  <p className="text-sm text-slate-500">
                    Consultez et gérez vos revues de presse générées par l&apos;IA.
                  </p>
                  {displayReviews.length === 0 ? (
                    <p className="rounded-lg border border-slate-200 bg-white p-6 text-center text-sm text-slate-500">
                      Aucune revue pour le moment. Depuis l&apos;onglet Chat,
                      ouvrez une discussion puis cliquez sur &quot;Générer une
                      revue de presse&quot;.
                    </p>
                  ) : null}
                  {displayReviews.map((review) => (
                    <article
                      key={review.id}
                      className="rounded-lg bg-white p-4 shadow-sm md:p-6"
                    >
                      <div className="mb-3 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                        <div className="min-w-0 flex-1">
                          <h4 className="text-sm font-semibold uppercase tracking-wide text-slate-800">
                            {review.review_title || review.topic}
                          </h4>
                          <p className="mt-1 flex items-center gap-1 text-xs text-slate-500">
                            <span aria-hidden>📅</span>
                            {formatFrDateTime(review.created_at)}
                          </p>
                          {review.chat_title ? (
                            <p className="mt-1 text-xs text-slate-400">
                              Discussion : {review.chat_title}
                            </p>
                          ) : null}
                        </div>
                        <button
                          type="button"
                          className="shrink-0 self-start rounded-md bg-[#282833] px-4 py-2 text-xs text-white hover:bg-[#1a1a24]"
                          onClick={() => void handleCopyReview(review.content)}
                        >
                          Copier
                        </button>
                      </div>
                      <div className="text-sm leading-relaxed text-slate-700 break-words">
                        <ChatMarkdown content={review.content} />
                      </div>
                    </article>
                  ))}
                </div>
              </div>
            ) : null}
            </div>

            <div className="shrink-0 border-t border-slate-200 bg-white p-4">
              <div className="flex gap-2">
                <input
                  value={prompt}
                  onChange={(event) => setPrompt(event.target.value)}
                  placeholder="Tapez votre message ici..."
                  disabled={busy || selectedConversationId === null}
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
                  disabled={busy || selectedConversationId === null}
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
                {busy
                  ? currentTab === "review"
                    ? " — operation en cours…"
                    : " — recherche d'articles et réponse en cours…"
                  : ""}
                {currentTab === "review" && !busy ? (
                  <span className="text-slate-400">
                    {" "}
                    — Les messages s&apos;ajoutent aussi depuis l&apos;onglet
                    revue.
                  </span>
                ) : null}
              </p>
            </div>
          </section>
        </div>
      </main>

      <PressReviewModal
        open={reviewModalOpen}
        topic={reviewTopic}
        busy={busy}
        canSubmit={selectedConversationId !== null}
        onTopicChange={setReviewTopic}
        onClose={() => setReviewModalOpen(false)}
        onSubmit={() => void handleGenerateReview()}
      />
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
