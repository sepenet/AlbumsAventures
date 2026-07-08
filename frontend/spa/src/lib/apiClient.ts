/**
 * Typed, same-origin API client over the existing `be_*` FastAPI endpoints.
 *
 * Auth model (unchanged from the server-rendered app):
 *   - The browser holds an HttpOnly session cookie and sends it automatically
 *     on same-origin requests, so this client stores NO token in
 *     localStorage/sessionStorage.
 *   - Mutations additionally echo the CSRF double-submit token: the
 *     `csrf_token` cookie is JS-readable (set with httponly=false server-side,
 *     see utils/csrf.py) and its value is sent back in the `X-CSRF-Token`
 *     header, which the CORS/security layer already allows (utils/security.py).
 *
 * All requests are same-origin (the SPA is served by FastAPI under /app), so
 * no CORS relaxation is involved. A 401 surfaces as `UnauthorizedError` so the
 * auth guard can redirect to the server-rendered /login page.
 */

const CSRF_COOKIE_NAME = "csrf_token";
const CSRF_HEADER_NAME = "X-CSRF-Token";
const MUTATING_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export class UnauthorizedError extends ApiError {
  constructor(message = "Non authentifié") {
    super(401, message);
    this.name = "UnauthorizedError";
  }
}

/**
 * Pure helper: extract the CSRF token from a `Cookie`-header-style string.
 * Exported so it can be unit-tested without a DOM.
 */
export function parseCsrfToken(cookieString: string): string | null {
  for (const part of cookieString.split(";")) {
    const trimmed = part.trim();
    if (!trimmed) continue;
    const eq = trimmed.indexOf("=");
    const name = eq === -1 ? trimmed : trimmed.slice(0, eq);
    if (name === CSRF_COOKIE_NAME) {
      const rawValue = eq === -1 ? "" : trimmed.slice(eq + 1);
      return decodeURIComponent(rawValue);
    }
  }
  return null;
}

function csrfHeader(): Record<string, string> {
  const token = typeof document !== "undefined" ? parseCsrfToken(document.cookie) : null;
  return token ? { [CSRF_HEADER_NAME]: token } : {};
}

function extractDetail(body: unknown, fallback: string): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
  }
  return fallback;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method ?? "GET").toUpperCase();
  const headers = new Headers(init.headers);

  if (MUTATING_METHODS.has(method)) {
    for (const [key, value] of Object.entries(csrfHeader())) {
      headers.set(key, value);
    }
  }

  const response = await fetch(path, {
    ...init,
    method,
    // Same-origin: the session cookie rides along automatically. `same-origin`
    // keeps credentials scoped to this origin without opting into cross-origin
    // credential sharing.
    credentials: "same-origin",
    headers,
  });

  if (response.status === 401) {
    throw new UnauthorizedError();
  }

  if (!response.ok) {
    let detail = response.statusText;
    try {
      detail = extractDetail(await response.json(), detail);
    } catch {
      // Response body was not JSON; keep the status text.
    }
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export const api = {
  get: <T>(path: string): Promise<T> => request<T>(path),
  post: <T>(path: string, body?: unknown): Promise<T> =>
    request<T>(path, {
      method: "POST",
      headers: body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    }),
  patch: <T>(path: string, body?: unknown): Promise<T> =>
    request<T>(path, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  put: <T>(path: string, body?: unknown): Promise<T> =>
    request<T>(path, {
      method: "PUT",
      headers: body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    }),
  del: <T>(path: string): Promise<T> => request<T>(path, { method: "DELETE" }),
  /**
   * Multipart POST helper for file uploads (e.g. album cover). Sends a
   * `FormData` body: NO explicit `Content-Type` is set so the browser adds the
   * multipart boundary itself. Like the other mutations it rides the same-origin
   * session cookie and echoes the `X-CSRF-Token` header via the shared `request`.
   */
  postForm: <T>(path: string, formData: FormData): Promise<T> =>
    request<T>(path, { method: "POST", body: formData }),
};
