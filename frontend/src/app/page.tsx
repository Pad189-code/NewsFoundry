import Link from "next/link";

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-slate-50 px-6 text-slate-900">
      <main className="w-full max-w-2xl rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="text-3xl font-semibold">NewsFoundry</h1>
        <p className="mt-3 text-slate-600">
          Socle frontend initial pour la revue de presse assistee par IA.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link
            href="/login"
            className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
          >
            Se connecter
          </Link>
          <Link
            href="/chats"
            className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium hover:bg-slate-100"
          >
            Ouvrir les discussions
          </Link>
        </div>
      </main>
    </div>
  );
}
