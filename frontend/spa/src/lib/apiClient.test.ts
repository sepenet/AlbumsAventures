import { describe, expect, it } from "vitest";

import { parseCsrfToken } from "./apiClient";

describe("parseCsrfToken", () => {
  it("extrait le token CSRF parmi plusieurs cookies", () => {
    expect(parseCsrfToken("access_token=abc; csrf_token=xyz123")).toBe("xyz123");
  });

  it("décode les valeurs url-encodées", () => {
    expect(parseCsrfToken("csrf_token=a%2Bb%3D")).toBe("a+b=");
  });

  it("retourne null quand le cookie CSRF est absent", () => {
    expect(parseCsrfToken("access_token=abc; other=1")).toBeNull();
  });

  it("gère une chaîne de cookies vide", () => {
    expect(parseCsrfToken("")).toBeNull();
  });
});
