// Auth API calls for the SPA auth pages (Phase 3.8), over the existing `be_*`
// FastAPI endpoints. Same-origin, cookie-only (PD-01): a successful login sets
// the existing HttpOnly session cookie server-side and this module stores NO
// token in JS. The 60-minute cookie session is kept as-is — there is no
// refresh-token endpoint (a 401 later surfaces via the auth guard, which
// redirects to the login page).

import { ApiError, api } from "./apiClient";
import type { SignupFormValues } from "./authValidation";

/**
 * Error raised by {@link login} carrying the backend's status + detail so the
 * page can show the exact message (e.g. wrong password → 400, unknown user →
 * 401). Unlike the shared apiClient — whose 401 handling means "session
 * expired, redirect to login" — the login page must render these inline.
 */
export class AuthError extends ApiError {
  constructor(status: number, message: string) {
    super(status, message);
    this.name = "AuthError";
  }
}

async function detailFromResponse(response: Response, fallback: string): Promise<string> {
  try {
    const body: unknown = await response.json();
    if (body && typeof body === "object" && "detail" in body) {
      const detail = (body as { detail: unknown }).detail;
      if (typeof detail === "string") return detail;
    }
  } catch {
    // Non-JSON error body — keep the fallback.
  }
  return fallback;
}

/**
 * Log in with the OAuth2 password form the backend expects
 * (`POST /be_auth/login`, form-encoded `username`/`password`). On success the
 * backend sets the HttpOnly `access_token` cookie; the browser stores it
 * automatically on this same-origin request. A dedicated `fetch` is used (not
 * the shared apiClient) so a 401 stays an inline error instead of triggering a
 * redirect.
 */
export async function login(email: string, password: string): Promise<void> {
  const body = new URLSearchParams({ username: email, password });
  const response = await fetch("/be_auth/login", {
    method: "POST",
    // Same-origin so the Set-Cookie from the backend is stored by the browser.
    credentials: "same-origin",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });

  if (!response.ok) {
    throw new AuthError(response.status, await detailFromResponse(response, "Identifiants invalides"));
  }
}

/** Response shape of the account-creation endpoint (a subset of UserAdmin). */
interface CreatedUser {
  id: number;
  email: string;
}

/**
 * Register a new account (`POST /be_auth/create/`). The server forces the new
 * account to `is_active=false` / `is_superuser=false` (SEC-03): a registration
 * awaits admin activation before it can log in — mirroring the Jinja signup
 * flow. A duplicate email surfaces as a 400 via the shared apiClient.
 */
export async function signup(values: SignupFormValues): Promise<CreatedUser> {
  return api.post<CreatedUser>("/be_auth/create/", {
    firstname: values.firstname,
    lastname: values.lastname,
    email: values.email,
    password: values.password,
    is_active: false,
    is_superuser: false,
  });
}

/** Neutral acknowledgement message returned by the forgot-password endpoint. */
interface MessageResponse {
  message: string;
}

/**
 * Request a password-reset link (`POST /be_auth/forgot-password`). The backend
 * always returns the same neutral message whether or not the email exists
 * (anti-enumeration) and sends the email out-of-band.
 */
export async function forgotPassword(email: string): Promise<MessageResponse> {
  return api.post<MessageResponse>("/be_auth/forgot-password", { email });
}

/**
 * Reset the password using the token from the reset link
 * (`POST /be_auth/reset-password`). An invalid/expired token surfaces as a 400.
 */
export async function resetPassword(token: string, newPassword: string): Promise<MessageResponse> {
  return api.post<MessageResponse>("/be_auth/reset-password", {
    token,
    new_password: newPassword,
  });
}
