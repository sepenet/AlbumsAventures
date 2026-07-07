import { describe, expect, it } from "vitest";

import { isValidPinFormat, normalizePin, sharedErrorMessage } from "./shared";

describe("isValidPinFormat", () => {
  it("accepts exactly 6 alphanumeric characters", () => {
    expect(isValidPinFormat("ABC123")).toBe(true);
    expect(isValidPinFormat("abcdef")).toBe(true);
    expect(isValidPinFormat("000000")).toBe(true);
  });

  it("rejects the wrong length", () => {
    expect(isValidPinFormat("ABC12")).toBe(false);
    expect(isValidPinFormat("ABC1234")).toBe(false);
    expect(isValidPinFormat("")).toBe(false);
  });

  it("rejects non-alphanumeric characters", () => {
    expect(isValidPinFormat("ABC-12")).toBe(false);
    expect(isValidPinFormat("ABC 12")).toBe(false);
    expect(isValidPinFormat("ABC!23")).toBe(false);
  });
});

describe("normalizePin", () => {
  it("trims and upper-cases like the backend", () => {
    expect(normalizePin("  abc123 ")).toBe("ABC123");
    expect(normalizePin("aBcDeF")).toBe("ABCDEF");
  });
});

describe("sharedErrorMessage", () => {
  it("surfaces a string detail verbatim", () => {
    expect(sharedErrorMessage(400, "Lien invalide")).toBe("Lien invalide");
  });

  it("reports remaining attempts on a wrong PIN", () => {
    expect(
      sharedErrorMessage(403, { error: "invalid_pin", attempts_remaining: 3 }),
    ).toBe("Code PIN incorrect. 3 tentative(s) restante(s).");
  });

  it("reports a lockout when no attempts remain", () => {
    expect(
      sharedErrorMessage(403, { error: "invalid_pin", attempts_remaining: 0 }),
    ).toBe("Accès bloqué temporairement.");
  });

  it("surfaces the backend rate-limit lockout message (429)", () => {
    const message = "Trop de tentatives échouées. Réessayez dans 12 minute(s).";
    expect(sharedErrorMessage(429, { error: "too_many_attempts", message })).toBe(message);
  });

  it("treats HTTP 429 as a lockout even without an error code", () => {
    expect(sharedErrorMessage(429, null)).toBe(
      "Trop de tentatives échouées. Réessayez plus tard.",
    );
  });

  it("reports an expired share link", () => {
    expect(sharedErrorMessage(403, { error: "token_expired" })).toBe(
      "Ce lien de partage a expiré ou n'est plus valide.",
    );
  });

  it("falls back for unknown or missing detail", () => {
    expect(sharedErrorMessage(500, null)).toBe("Erreur lors de la vérification du code PIN.");
    expect(sharedErrorMessage(500, { error: "boom", message: "Oups" })).toBe("Oups");
  });
});
