const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type BackendHello = {
  message: string;
};

export async function pingBackend(): Promise<BackendHello> {
  const response = await fetch(`${API_BASE_URL}/`, { cache: "no-store" });

  if (!response.ok) {
    throw new Error("Backend indisponible");
  }

  return (await response.json()) as BackendHello;
}

export async function loginWithSeedUser(
  email: string,
  password: string,
): Promise<string> {
  await pingBackend();

  // Temporary auth flow: backend currently has no /auth/login endpoint.
  if (email !== "test@test.com" || password !== "test") {
    throw new Error("Identifiants invalides");
  }

  return `dev-token-${Date.now()}`;
}
