"use client";

import Image from "next/image";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { clearSession, getStoredEmail, isAuthenticated } from "@/lib/auth";

const MOCK_CHATS = [
  { id: "1", title: "Discussion du", updatedAt: "10/12/2026" },
  { id: "2", title: "Discussion du", updatedAt: "10/12/2026" },
  { id: "3", title: "Discussion du", updatedAt: "10/12/2026" },
  { id: "4", title: "Discussion du", updatedAt: "10/12/2026" },
  { id: "5", title: "Discussion du", updatedAt: "10/12/2026" },
  { id: "6", title: "Discussion du", updatedAt: "10/12/2026" },
  { id: "7", title: "Discussion du", updatedAt: "10/12/2026" },
];

const MOCK_REVIEWS = [
  {
    id: "r1",
    title: "ACTUALITES POLITIQUES - SEMAINE 39",
    date: "mardi 30 septembre 2025 a 09:00",
  },
  {
    id: "r2",
    title: "ACTUALITES POLITIQUES - SEMAINE 39",
    date: "mardi 30 septembre 2025 a 09:00",
  },
];

type ViewMode = "home" | "chat" | "review";

export default function ChatsPage() {
  const router = useRouter();
  const [prompt, setPrompt] = useState("");
  const [isReviewModalOpen, setIsReviewModalOpen] = useState(false);
  const [reviewTopic, setReviewTopic] = useState("");
  const [viewMode, setViewMode] = useState<ViewMode>("home");
  const [activeTab, setActiveTab] = useState<"chat" | "review">("chat");
  const authenticated = isAuthenticated();
  const email = getStoredEmail();

  useEffect(() => {
    if (!authenticated) {
      router.replace("/login");
    }
  }, [authenticated, router]);

  function handleLogout() {
    clearSession();
    router.push("/login");
  }

  function handleSubmitPrompt() {
    if (!prompt.trim()) {
      return;
    }
    setViewMode("chat");
    setActiveTab("chat");
    setPrompt("");
  }

  function handleGenerateReview() {
    setIsReviewModalOpen(true);
  }

  if (!authenticated) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <p className="text-slate-600">Chargement...</p>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-100 p-6">
      <main className="h-[992px] w-full max-w-[1440px] overflow-hidden rounded-md border border-slate-200 bg-white shadow-sm">
        <div className="grid h-full grid-cols-[300px_1fr]">
          <aside className="flex h-full flex-col border-r border-slate-200 bg-white">
            <div className="border-b border-slate-200 px-5 py-5">
              <h1 className="text-xs font-medium text-[#803cda]">NEWSFOUNDRY</h1>
            </div>
            <ul className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
              {MOCK_CHATS.map((chat) => (
                <li
                  key={chat.id}
                  className="rounded-md border border-slate-200 p-3 hover:bg-slate-50 cursor-pointer"
                  onClick={() => {
                    setViewMode("chat");
                    setActiveTab("chat");
                  }}
                >
                  <p className="text-sm font-medium text-slate-900">{chat.title}</p>
                  <p className="text-xs text-slate-500">{chat.updatedAt}</p>
                </li>
              ))}
            </ul>
            <button
              className="m-4 rounded-md border border-slate-300 px-3 py-2 text-sm hover:bg-slate-100"
              onClick={handleLogout}
            >
              Se deconnecter
            </button>
          </aside>

          <section className="flex h-full flex-col bg-[#f4f4fb]">
            <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-4">
              <div className="flex items-center gap-2">
                <button
                  onClick={() => {
                    setActiveTab("chat");
                    setViewMode("home");
                  }}
                  className={`rounded-md px-3 py-1.5 text-xs ${
                    activeTab === "chat"
                      ? "bg-[#803cda] text-white"
                      : "border border-slate-300 bg-white text-slate-700"
                  }`}
                >
                  Chat
                </button>
                <button
                  onClick={() => {
                    setActiveTab("review");
                    setViewMode("review");
                  }}
                  className={`rounded-md px-3 py-1.5 text-xs ${
                    activeTab === "review"
                      ? "bg-[#803cda] text-white"
                      : "border border-slate-300 bg-white text-slate-700"
                  }`}
                >
                  Revue de presse
                </button>
              </div>
              {activeTab === "chat" ? (
                <button
                  className="rounded-md bg-[#803cda] px-4 py-2 text-sm font-medium text-white hover:bg-[#6f2fc3]"
                  onClick={handleGenerateReview}
                >
                  Generer une revue de presse
                </button>
              ) : null}
            </header>

            {activeTab === "chat" && viewMode === "home" ? (
              <div className="flex flex-1 items-center justify-center p-8">
                <div className="w-full max-w-[620px] rounded-xl bg-white px-12 py-14 text-center shadow-sm">
                  <div className="flex justify-center">
                    <Image
                      src="/Robo.png"
                      alt="Robot NewsFoundry"
                      width={76}
                      height={76}
                      priority
                    />
                  </div>
                  <h3 className="mt-4 text-4 font-semibold text-[#803cda]">
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

            {activeTab === "chat" && viewMode === "chat" ? (
              <div className="flex-1 overflow-y-auto p-8">
                <div className="mx-auto max-w-4xl space-y-6">
                  <div className="ml-auto w-[420px] rounded-md bg-[#23232f] p-4 text-sm text-white">
                    Peux-tu me donner les dernieres actualites politiques ?
                  </div>
                  <div className="w-[560px] rounded-md bg-white p-4 text-sm text-slate-700">
                    Voici un resume des dernieres nouvelles politiques :
                    <br />- Le gouvernement a annonce de nouvelles mesures
                    economiques
                    <br />- Debat sur la reforme des retraites au Parlement
                    <br />- Visite diplomatique prevue la semaine prochaine
                  </div>
                  <div className="ml-auto w-[420px] rounded-md bg-[#23232f] p-4 text-sm text-white">
                    Je suis curieux des applications dans la sante et l&apos;education.
                  </div>
                </div>
              </div>
            ) : null}

            {activeTab === "review" ? (
              <div className="flex-1 overflow-y-auto p-8">
                <div className="mx-auto max-w-4xl space-y-4">
                  <h3 className="text-3 font-semibold text-slate-800">Revues de Presse</h3>
                  <p className="text-sm text-slate-500">
                    Consultez et gerez vos revues de presse generees par l&apos;IA
                  </p>
                  {MOCK_REVIEWS.map((review) => (
                    <article
                      key={review.id}
                      className="rounded-lg bg-white p-6 shadow-sm"
                    >
                      <div className="mb-3 flex items-center justify-between">
                        <div>
                          <h4 className="text-sm font-semibold text-slate-800">
                            {review.title}
                          </h4>
                          <p className="text-xs text-slate-500">{review.date}</p>
                        </div>
                        <button className="rounded-md bg-[#282833] px-4 py-2 text-xs text-white">
                          Copier
                        </button>
                      </div>
                      <p className="text-sm leading-6 text-slate-700">
                        **REVUE DE PRESSE POLITIQUE - 30 Septembre 2025**
                        <br />
                        **Synthese hebdomadaire des principales actualites
                        politiques**
                        <br />
                        - **Reforme economique** : Le gouvernement a presente son
                        plan de relance.
                        <br />- **Relations internationales** : Preparation du
                        sommet europeen.
                        <br />- **Politique interieure** : Debats parlementaires
                        sur la reforme du systeme de sante.
                      </p>
                    </article>
                  ))}
                </div>
              </div>
            ) : null}

            <div className="border-t border-slate-200 bg-white p-4">
              <div className="flex gap-2">
                <input
                  value={prompt}
                  onChange={(event) => setPrompt(event.target.value)}
                  placeholder="Tapez votre message ici..."
                  className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-[#803cda]"
                />
                <button
                  onClick={handleSubmitPrompt}
                  className="rounded-md bg-[#803cda] px-4 py-2 text-sm font-medium text-white hover:bg-[#6f2fc3]"
                >
                  Envoyer
                </button>
              </div>
              <p className="mt-2 text-xs text-slate-500">
                Connecte en tant que {email}
              </p>
            </div>
          </section>
        </div>
      </main>

      {isReviewModalOpen ? (
        <div className="fixed inset-0 z-10 flex items-center justify-center bg-black/30 p-6">
          <div className="h-[370px] w-[556px] rounded-xl bg-white p-8 shadow-xl">
            <div className="flex items-start justify-between">
              <h3 className="text-lg font-semibold text-slate-900">
                Generer une revue de presse
              </h3>
              <button
                onClick={() => setIsReviewModalOpen(false)}
                className="text-sm text-slate-500 hover:text-slate-800"
              >
                Fermer
              </button>
            </div>
            <p className="mt-2 text-sm text-slate-500">
              Donner un titre a votre revue de presse
            </p>

            <label className="mt-8 block text-sm font-medium text-slate-700">
              Theme de la revue de presse
            </label>
            <input
              value={reviewTopic}
              onChange={(event) => setReviewTopic(event.target.value)}
              className="mt-2 w-full rounded-md border border-slate-200 bg-slate-100 px-3 py-2 text-sm outline-none focus:border-[#803cda]"
            />
            <button
              onClick={() => setIsReviewModalOpen(false)}
              className="mt-6 w-full rounded-md bg-[#282833] px-4 py-2 text-sm font-medium text-white hover:bg-[#1f1f29]"
            >
              Generer
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
