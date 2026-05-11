export const AUTH_TOKEN_KEY = "newsfoundry_token";
export const AUTH_REFRESH_KEY = "newsfoundry_refresh";
export const AUTH_EMAIL_KEY = "newsfoundry_email";

export function getStoredToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }

  return window.localStorage.getItem(AUTH_TOKEN_KEY);
}

export function getStoredRefreshToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }

  return window.localStorage.getItem(AUTH_REFRESH_KEY);
}

export function isAuthenticated(): boolean {
  return Boolean(getStoredToken());
}

export function storeSession(
  email: string,
  accessToken: string,
  refreshToken?: string | null,
): void {
  window.localStorage.setItem(AUTH_EMAIL_KEY, email);
  window.localStorage.setItem(AUTH_TOKEN_KEY, accessToken);
  if (refreshToken) {
    window.localStorage.setItem(AUTH_REFRESH_KEY, refreshToken);
  } else {
    window.localStorage.removeItem(AUTH_REFRESH_KEY);
  }
}

export function clearSession(): void {
  window.localStorage.removeItem(AUTH_EMAIL_KEY);
  window.localStorage.removeItem(AUTH_TOKEN_KEY);
  window.localStorage.removeItem(AUTH_REFRESH_KEY);
}

export function getStoredEmail(): string | null {
  if (typeof window === "undefined") {
    return null;
  }

  return window.localStorage.getItem(AUTH_EMAIL_KEY);
}
