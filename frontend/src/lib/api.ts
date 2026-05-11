import {
  getStoredEmail,
  getStoredRefreshToken,
  getStoredToken,
  storeSession,
} from "@/lib/auth";

function resolveApiBaseUrl(): string {
  const raw = process.env.NEXT_PUBLIC_API_URL?.trim() ?? "";
  if (!raw) {
    return "http://localhost:8000";
  }
  if (!/^https?:\/\//i.test(raw)) {
    console.warn(
      `[NewsFoundry] NEXT_PUBLIC_API_URL doit être une URL absolue (ex. http://127.0.0.1:8000). ` +
        `Valeur reçue : ${JSON.stringify(raw)} — utilisation de http://localhost:8000.`,
    );
    return "http://localhost:8000";
  }
  return raw.replace(/\/+$/, "");
}

const API_BASE_URL = resolveApiBaseUrl();

type BackendHello = {
  message: string;
  app: string;
};

export type ChatDTO = {
  id: number;
  title: string;
  updated_at: string;
};

export type MessageDTO = {
  id: number;
  role: string;
  content: string;
  created_at: string;
};

export type PressReviewDTO = {
  id: number;
  chat_id: number;
  topic: string;
  content: string;
  created_at: string;
  chat_title?: string | null;
  review_title?: string | null;
  general_summary?: string | null;
  articles_breakdown?: { article_title: string; synthesis: string }[] | null;
};

export type LoginTokens = {
  accessToken: string;
  refreshToken: string;
};

async function networkFetch(
  input: string,
  init?: RequestInit,
): Promise<Response> {
  try {
    return await fetch(input, init);
  } catch (cause) {
    const reason = cause instanceof Error ? cause.message : String(cause);
    throw new Error(
      `Impossible de joindre l’API (${API_BASE_URL}). ` +
        `Démarrez le backend (port 8000) : cd backend puis uv run --env-file .env src/main.py. ` +
        `Détail : ${reason}`,
    );
  }
}

async function parseApiError(response: Response): Promise<string> {
  try {
    const data: unknown = await response.json();
    if (data && typeof data === "object" && "detail" in data) {
      const detail = (data as { detail: unknown }).detail;
      if (typeof detail === "string") {
        return detail;
      }
      if (Array.isArray(detail)) {
        return detail
          .map((item) =>
            item && typeof item === "object" && "msg" in item
              ? String((item as { msg: unknown }).msg)
              : JSON.stringify(item),
          )
          .join(", ");
      }
    }
    return JSON.stringify(data);
  } catch {
    return await response.text();
  }
}

function authHeaders(token: string): HeadersInit {
  return {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  };
}

async function tryRefreshAccessToken(): Promise<boolean> {
  const refresh = getStoredRefreshToken();
  const email = getStoredEmail();
  if (!refresh || !email) {
    return false;
  }
  const response = await networkFetch(`${API_BASE_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh }),
  });
  if (!response.ok) {
    return false;
  }
  const data = (await response.json()) as {
    access_token: string;
    refresh_token: string;
  };
  storeSession(email, data.access_token, data.refresh_token);
  return true;
}

async function withAuthRetry(
  run: (accessToken: string) => Promise<Response>,
): Promise<Response> {
  let access = getStoredToken();
  if (!access) {
    throw new Error("Non authentifie");
  }
  let response = await run(access);
  if (response.status === 401) {
    const refreshed = await tryRefreshAccessToken();
    if (refreshed) {
      access = getStoredToken();
      if (access) {
        response = await run(access);
      }
    }
  }
  return response;
}

export async function pingBackend(): Promise<BackendHello> {
  const response = await networkFetch(`${API_BASE_URL}/health`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(
      `L’API répond mais /health n’est pas OK (${response.status}). Vérifiez ${API_BASE_URL}.`,
    );
  }

  let data: unknown;
  try {
    data = await response.json();
  } catch {
    throw new Error(
      `La réponse de /health sur ${API_BASE_URL} n’est pas du JSON. ` +
        `Vérifiez qu’il s’agit bien du backend NewsFoundry (uv run --env-file .env src/main.py dans le dossier backend).`,
    );
  }

  if (!data || typeof data !== "object") {
    throw new Error(
      `Le service sur ${API_BASE_URL} n’est pas l’API NewsFoundry (réponse /health inattendue : ${JSON.stringify(data)}). ` +
        `Un autre programme occupe peut‑être le port 8000 — arrêtez‑le ou définissez NEXT_PUBLIC_API_URL vers la bonne URL, ` +
        `puis lancez ce backend : cd backend puis uv run --env-file .env src/main.py.`,
    );
  }

  const body = data as { message?: unknown; app?: unknown };
  if (body.message !== "ok" || body.app !== "newsfoundry-api") {
    throw new Error(
      `Sur ${API_BASE_URL}, /health ne correspond pas au backend NewsFoundry actuel (réponse : ${JSON.stringify(data)}). ` +
        `Cause fréquente : un ancien processus utilise encore le port (il expose /health mais pas /auth/login → 404 à la connexion). ` +
        `Sous Windows : netstat -ano | findstr :8000 puis taskkill /PID <pid> /F. Ensuite : cd backend puis uv run --env-file .env src/main.py.`,
    );
  }

  return data as BackendHello;
}

export async function loginRequest(
  email: string,
  password: string,
): Promise<LoginTokens> {
  await pingBackend();
  const response = await networkFetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (response.status === 429) {
    throw new Error(
      "Trop de tentatives de connexion. Patientez environ une minute puis réessayez.",
    );
  }
  if (!response.ok) {
    const detail = await parseApiError(response);
    if (response.status === 401) {
      throw new Error(
        `${detail} — compte démo : test@test.com / mot de passe : test`,
      );
    }
    if (response.status === 404) {
      throw new Error(
        `Route introuvable (404) sur ${API_BASE_URL}/auth/login — ` +
          `soit le backend NewsFoundry n’est pas à jour / pas démarré, soit NEXT_PUBLIC_API_URL pointe vers le mauvais serveur. ` +
          `Détail : ${detail}`,
      );
    }
    throw new Error(detail);
  }
  const data = (await response.json()) as {
    access_token: string;
    refresh_token: string;
  };
  return {
    accessToken: data.access_token,
    refreshToken: data.refresh_token,
  };
}

export async function listChats(): Promise<ChatDTO[]> {
  const response = await withAuthRetry((access) =>
    fetch(`${API_BASE_URL}/chats`, { headers: authHeaders(access) }),
  );
  if (!response.ok) {
    throw new Error(await parseApiError(response));
  }
  return (await response.json()) as ChatDTO[];
}

export async function createChat(title?: string): Promise<ChatDTO> {
  const response = await withAuthRetry((access) =>
    fetch(`${API_BASE_URL}/chats`, {
      method: "POST",
      headers: authHeaders(access),
      body: JSON.stringify({ title: title ?? null }),
    }),
  );
  if (!response.ok) {
    throw new Error(await parseApiError(response));
  }
  return (await response.json()) as ChatDTO;
}

export async function listMessages(chatId: number): Promise<MessageDTO[]> {
  const response = await withAuthRetry((access) =>
    fetch(`${API_BASE_URL}/chats/${chatId}`, { headers: authHeaders(access) }),
  );
  if (!response.ok) {
    throw new Error(await parseApiError(response));
  }
  const data = (await response.json()) as { messages: MessageDTO[] };
  return data.messages;
}

export async function sendMessage(
  chatId: number,
  content: string,
): Promise<MessageDTO> {
  const response = await withAuthRetry((access) =>
    fetch(`${API_BASE_URL}/chats/${chatId}/messages`, {
      method: "POST",
      headers: authHeaders(access),
      body: JSON.stringify({ content }),
    }),
  );
  if (!response.ok) {
    throw new Error(await parseApiError(response));
  }
  return (await response.json()) as MessageDTO;
}

export async function fetchBreakingNews(
  chatId: number,
  text = "actualites",
): Promise<void> {
  const response = await withAuthRetry((access) =>
    fetch(`${API_BASE_URL}/chats/${chatId}/news/fetch`, {
      method: "POST",
      headers: authHeaders(access),
      body: JSON.stringify({ text }),
    }),
  );
  if (!response.ok) {
    throw new Error(await parseApiError(response));
  }
}

export async function listReviews(chatId: number): Promise<PressReviewDTO[]> {
  const response = await withAuthRetry((access) =>
    fetch(`${API_BASE_URL}/chats/${chatId}/reviews`, {
      headers: authHeaders(access),
    }),
  );
  if (!response.ok) {
    throw new Error(await parseApiError(response));
  }
  return (await response.json()) as PressReviewDTO[];
}

/** Toutes les revues de l’utilisateur (toutes discussions). */
export async function listAllPressReviews(): Promise<PressReviewDTO[]> {
  const response = await withAuthRetry((access) =>
    fetch(`${API_BASE_URL}/reviews`, {
      headers: authHeaders(access),
    }),
  );
  if (!response.ok) {
    throw new Error(await parseApiError(response));
  }
  return (await response.json()) as PressReviewDTO[];
}

export async function createPressReview(
  chatId: number,
  topic: string,
): Promise<PressReviewDTO> {
  const response = await withAuthRetry((access) =>
    fetch(`${API_BASE_URL}/chats/${chatId}/reviews`, {
      method: "POST",
      headers: authHeaders(access),
      body: JSON.stringify({ topic }),
    }),
  );
  if (!response.ok) {
    throw new Error(await parseApiError(response));
  }
  return (await response.json()) as PressReviewDTO;
}
