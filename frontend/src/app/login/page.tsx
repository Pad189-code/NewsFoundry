"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { loginRequest } from "@/lib/api";
import { isAuthenticated, storeSession } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("test@test.com");
  const [password, setPassword] = useState("test");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const alreadyConnected = useMemo(() => isAuthenticated(), []);

  useEffect(() => {
    if (alreadyConnected) {
      router.replace("/chats");
    }
  }, [alreadyConnected, router]);

  if (alreadyConnected) return null;

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      const tokens = await loginRequest(email.trim(), password);
      storeSession(
        email.trim(),
        tokens.accessToken,
        tokens.refreshToken,
      );
      router.push("/chats");
    } catch (requestError) {
      const message =
        requestError instanceof Error
          ? requestError.message
          : "Erreur inconnue";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="bg-login-grid flex min-h-screen items-center justify-center p-6">
      <main className="w-full max-w-[448px] rounded-xl border border-slate-200 bg-white px-7 py-8 shadow-lg">
        <h1 className="text-center text-lg font-semibold tracking-wide text-[#803cda]">
          NEWSFOUNDRY
        </h1>
        <p className="mt-2 text-center text-[11px] text-slate-500">
          Connectez-vous pour acceder a votre assistant d&apos;actualites IA
        </p>

        <form className="mt-5 space-y-4" onSubmit={onSubmit} noValidate>
          <div>
            <label
              htmlFor="login-email"
              className="mb-1 block text-sm font-medium text-slate-700"
            >
              Adresse email
            </label>
            <input
              id="login-email"
              name="email"
              autoComplete="email"
              enterKeyHint="next"
              aria-invalid={error ? true : undefined}
              aria-describedby={error ? "login-error" : undefined}
              className="w-full rounded-md border border-slate-200 bg-slate-100 px-3 py-2 text-[#898989] outline-none ring-0 focus:border-[#803cda]"
              type="email"
              placeholder="votre.email@exemple.com"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </div>
          <div>
            <label
              htmlFor="login-password"
              className="mb-1 block text-sm font-medium text-slate-700"
            >
              Mot de passe
            </label>
            <input
              id="login-password"
              name="password"
              autoComplete="current-password"
              enterKeyHint="done"
              aria-invalid={error ? true : undefined}
              aria-describedby={error ? "login-error" : undefined}
              className="w-full rounded-md border border-slate-200 bg-slate-100 px-3 py-2 text-[#898989] outline-none ring-0 focus:border-[#803cda]"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </div>

          {error ? (
            <p
              id="login-error"
              role="alert"
              aria-live="polite"
              className="rounded-md border border-red-200 bg-red-50 p-2 text-sm text-red-700"
            >
              {error}
            </p>
          ) : null}

          <button
            type="submit"
            disabled={isLoading}
            aria-busy={isLoading}
            className="w-full rounded-md bg-[#282833] px-4 py-2 text-sm font-medium text-[#898989] hover:bg-[#1f1f29] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isLoading ? "Connexion..." : "Se connecter"}
          </button>
        </form>
      </main>
    </div>
  );
}
