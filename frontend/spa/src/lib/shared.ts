// Pure helpers for the PUBLIC shared-album flow (Phase 3.7).
//
// The shared viewer is NOT a logged-in user: access is gated only by a share
// token (JWT, 1 h expiry) carried in the URL and a 6-char PIN typed into the
// page. These helpers hold the client-side PIN-format check and the mapping of
// the backend's structured error payloads to French user messages. They are
// intentionally free of any DOM/`fetch` dependency so they can be unit-tested
// in isolation. The backend remains the source of truth for token validity,
// PIN verification, expiry, and rate limiting — nothing here weakens that.

/** PIN length enforced by the backend (`be_auth.generate_pin`, 6 chars). */
export const PIN_LENGTH = 6;

/**
 * True when `pin` is exactly {@link PIN_LENGTH} alphanumeric characters.
 * Mirrors the backend validation (`len(pin) == 6 and pin.isalnum()` in
 * `be_album.create_share_token`) so an obviously malformed PIN is rejected
 * client-side before a network round-trip; the server re-validates regardless.
 */
export function isValidPinFormat(pin: string): boolean {
  return /^[A-Za-z0-9]{6}$/.test(pin);
}

/**
 * Normalize a PIN the way the backend does before comparison: trim surrounding
 * whitespace and upper-case it (`verify_share_token` compares against the
 * stored upper-cased hash).
 */
export function normalizePin(pin: string): string {
  return pin.trim().toUpperCase();
}

/** Structured `detail` object the share endpoints return on error. */
export interface SharedErrorDetail {
  error?: string;
  message?: string;
  attempts_remaining?: number;
  retry_after_seconds?: number;
}

/**
 * Map a backend share error (HTTP status + structured `detail`) to a French
 * user message. Mirrors the mapping the Jinja `shared_album_verify` route uses,
 * so the SPA and the server-rendered page surface identical wording — including
 * the rate-limit lockout message (HTTP 429 `too_many_attempts`), which the
 * durable limiter emits after too many wrong PINs.
 */
export function sharedErrorMessage(
  status: number,
  detail: SharedErrorDetail | string | null,
): string {
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }

  const payload: SharedErrorDetail = detail && typeof detail === "object" ? detail : {};

  switch (payload.error) {
    case "invalid_pin": {
      const remaining = payload.attempts_remaining ?? 0;
      return remaining > 0
        ? `Code PIN incorrect. ${remaining} tentative(s) restante(s).`
        : "Accès bloqué temporairement.";
    }
    case "too_many_attempts":
      // Surface the backend's lockout wording (includes the retry delay).
      return payload.message ?? "Trop de tentatives échouées. Réessayez plus tard.";
    case "token_expired":
      return "Ce lien de partage a expiré ou n'est plus valide.";
    default:
      // HTTP 429 is the durable rate limiter's lockout status: surface a
      // lockout message even if the structured `error` code is absent.
      if (status === 429) {
        return payload.message ?? "Trop de tentatives échouées. Réessayez plus tard.";
      }
      return payload.message ?? "Erreur lors de la vérification du code PIN.";
  }
}

/**
 * Error thrown by the shared-album fetch helpers, carrying the already-mapped
 * user message and the originating HTTP status. Kept out of the shared
 * `apiClient` (whose `ApiError` only understands string `detail`s and whose
 * 401 handling redirects to /login — neither fits the public share flow).
 */
export class SharedAccessError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "SharedAccessError";
    this.status = status;
  }
}
