export const API_URL = "/api";

export const tokenStorageKey = "accessToken";
export const mustChangePasswordKey = "mustChangePassword";

export function getToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(tokenStorageKey);
}

export function setToken(token: string | null) {
  if (typeof window === "undefined") {
    return;
  }
  if (token) {
    window.localStorage.setItem(tokenStorageKey, token);
  } else {
    window.localStorage.removeItem(tokenStorageKey);
  }
}

export function setMustChangePassword(value: boolean) {
  if (typeof window === "undefined") {
    return;
  }
  if (value) {
    window.localStorage.setItem(mustChangePasswordKey, "true");
  } else {
    window.localStorage.removeItem(mustChangePasswordKey);
  }
}

export function getMustChangePassword(): boolean {
  if (typeof window === "undefined") {
    return false;
  }
  return window.localStorage.getItem(mustChangePasswordKey) === "true";
}

export async function apiFetch(path: string, options: RequestInit = {}) {
  const token = getToken();
  const headers = new Headers(options.headers ?? {});
  const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;
  if (!isFormData && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    setToken(null);
    setMustChangePassword(false);
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
  }

  if (response.status === 403) {
    const data = await response.clone().json().catch(() => null);
    const errorCode = data?.error_code;
    if (errorCode === "ACCOUNT_BLOCKED") {
      if (typeof window !== "undefined") {
        window.location.href = "/blocked";
      }
    }
    if (errorCode === "MUST_CHANGE_PASSWORD") {
      setMustChangePassword(true);
      if (typeof window !== "undefined") {
        window.location.href = "/profile";
      }
    }
  }

  return response;
}
