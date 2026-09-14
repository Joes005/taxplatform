import type { ApiEnvelope, TokenPair } from "@/types/api";
import { tokenStorage } from "@/lib/token-storage";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  code: string;
  status: number;
  fields?: Record<string, string[]>;

  constructor(message: string, code: string, status: number, fields?: Record<string, string[]>) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.fields = fields;
  }
}

let refreshPromise: Promise<boolean> | null = null;

async function refreshAccessToken(): Promise<boolean> {
  const refreshToken = tokenStorage.getRefreshToken();
  if (!refreshToken) return false;

  try {
    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!response.ok) return false;

    const body = (await response.json()) as ApiEnvelope<TokenPair>;
    if (!body.success) return false;

    tokenStorage.setTokens(body.data.access_token, body.data.refresh_token);
    return true;
  } catch {
    return false;
  }
}

interface RequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  skipAuth?: boolean;
  skipRetry?: boolean;
}

/**
 * Performs one fetch with the access token attached, transparently doing a
 * single silent-refresh-and-retry on a 401. Shared by the JSON request path
 * and the binary download path so both get the same session-expiry
 * handling without duplicating the refresh dance.
 */
async function fetchWithAuthRetry(
  path: string,
  init: RequestInit,
  { skipAuth = false, skipRetry = false }: { skipAuth?: boolean; skipRetry?: boolean } = {}
): Promise<Response> {
  const headers = new Headers(init.headers);

  if (!skipAuth) {
    const accessToken = tokenStorage.getAccessToken();
    if (accessToken) {
      headers.set("Authorization", `Bearer ${accessToken}`);
    }
  }

  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers });

  if (response.status === 401 && !skipAuth && !skipRetry) {
    if (!refreshPromise) {
      refreshPromise = refreshAccessToken().finally(() => {
        refreshPromise = null;
      });
    }
    const refreshed = await refreshPromise;
    if (refreshed) {
      return fetchWithAuthRetry(path, init, { skipAuth, skipRetry: true });
    }
    tokenStorage.clear();
    window.location.assign("/login");
    throw new ApiError("Session expired", "AUTHENTICATION_FAILED", 401);
  }

  return response;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, skipAuth, skipRetry, headers, ...rest } = options;

  const finalHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    ...(headers as Record<string, string>),
  };

  const response = await fetchWithAuthRetry(
    path,
    { ...rest, headers: finalHeaders, body: body !== undefined ? JSON.stringify(body) : undefined },
    { skipAuth, skipRetry }
  );

  const envelope = (await response.json().catch(() => null)) as ApiEnvelope<T> | null;

  if (!envelope) {
    throw new ApiError("Unexpected server response", "UNKNOWN_ERROR", response.status);
  }

  if (!envelope.success) {
    throw new ApiError(
      envelope.error.message,
      envelope.error.code,
      response.status,
      envelope.error.fields
    );
  }

  return envelope.data;
}

/** POSTs FormData (e.g. a file upload) — deliberately omits Content-Type so
 * the browser sets the multipart boundary itself. */
async function upload<T>(path: string, formData: FormData): Promise<T> {
  const response = await fetchWithAuthRetry(path, { method: "POST", body: formData });

  const envelope = (await response.json().catch(() => null)) as ApiEnvelope<T> | null;
  if (!envelope) {
    throw new ApiError("Unexpected server response", "UNKNOWN_ERROR", response.status);
  }
  if (!envelope.success) {
    throw new ApiError(
      envelope.error.message,
      envelope.error.code,
      response.status,
      envelope.error.fields
    );
  }
  return envelope.data;
}

/** GETs a binary file. On failure, the server still returns the standard
 * JSON error envelope, which is parsed and thrown just like `request`. */
async function downloadBlob(path: string): Promise<{ blob: Blob; filename: string | null }> {
  const response = await fetchWithAuthRetry(path, { method: "GET" });

  const contentType = response.headers.get("content-type") ?? "";
  if (!response.ok || contentType.includes("application/json")) {
    const envelope = (await response.json().catch(() => null)) as ApiEnvelope<unknown> | null;
    if (envelope && !envelope.success) {
      throw new ApiError(
        envelope.error.message,
        envelope.error.code,
        response.status,
        envelope.error.fields
      );
    }
    throw new ApiError("Could not download this file", "UNKNOWN_ERROR", response.status);
  }

  const disposition = response.headers.get("content-disposition") ?? "";
  const match = /filename="?([^"]+)"?/.exec(disposition);
  const filename = match ? match[1] : null;

  return { blob: await response.blob(), filename };
}

export const apiClient = {
  get: <T>(path: string, options?: RequestOptions) => request<T>(path, { ...options, method: "GET" }),
  post: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "POST", body }),
  patch: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "PATCH", body }),
  delete: <T>(path: string, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "DELETE" }),
  upload,
  downloadBlob,
};
