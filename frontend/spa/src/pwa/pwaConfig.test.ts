import { describe, expect, it } from "vitest";

import { manifest, pwaOptions, runtimeCaching, workbox } from "./pwaConfig";

// These tests lock in the mandatory architect-council conditions on the Phase 4
// service worker. They assert the SOURCE config that `vite-plugin-pwa` compiles
// into the generated SW, so a regression (e.g. someone switching `/be_*` to a
// caching handler) fails the build via `npm run test`.

type Rule = (typeof runtimeCaching)[number];

function ruleFor(path: string): Rule | undefined {
  // Mirror Workbox's "first matching rule wins" semantics.
  return runtimeCaching.find((rule) => rule.urlPattern.test(path));
}

const CACHING_HANDLERS = ["CacheFirst", "StaleWhileRevalidate", "CacheOnly"];

describe("service-worker runtime caching — council conditions", () => {
  it("COUNCIL 1: bypasses the TUS resumable-upload stack (NetworkOnly, never cached)", () => {
    const rule = ruleFor("/be_resizer/tus/12345");
    expect(rule?.handler).toBe("NetworkOnly");
    // TUS must be matched by the resizer-specific rule declared first.
    expect(runtimeCaching[0]).toBe(rule);
  });

  it("COUNCIL 2: never CacheFirst/SWR-caches authenticated API responses", () => {
    for (const path of [
      "/be_auth/me",
      "/be_album/42",
      "/be_user/7",
      "/be_group/3",
      "/be_category/9",
      "/be_resizer/tus/abc",
    ]) {
      const rule = ruleFor(path);
      expect(rule, `no rule matched ${path}`).toBeDefined();
      expect(rule?.handler).toBe("NetworkOnly");
      expect(CACHING_HANDLERS).not.toContain(rule?.handler);
    }
  });

  it("COUNCIL 3: bounds every media/static cache with an LRU + max-age + quota purge", () => {
    const bounded = runtimeCaching.filter((rule) =>
      ["media-images", "media-thumbnails", "static-assets"].includes(
        rule.options.cacheName,
      ),
    );
    expect(bounded).toHaveLength(3);
    for (const rule of bounded) {
      expect(CACHING_HANDLERS).toContain(rule.handler);
      const expiration = (rule.options as { expiration?: Record<string, unknown> }).expiration;
      expect(expiration?.maxEntries).toBeGreaterThan(0);
      expect(expiration?.maxAgeSeconds).toBeGreaterThan(0);
      expect(expiration?.purgeOnQuotaError).toBe(true);
    }
  });

  it("COUNCIL 3: media/static rules match their routes but NOT /be_* or /app/assets", () => {
    expect(ruleFor("/images/full/x.jpg")?.options.cacheName).toBe("media-images");
    expect(ruleFor("/thumbnails/x.jpg")?.options.cacheName).toBe("media-thumbnails");
    expect(ruleFor("/static/logo.png")?.options.cacheName).toBe("static-assets");
    // /app/assets is served by the PRECACHE (revisioned), never a media rule.
    expect(ruleFor("/app/assets/index-abc123.js")).toBeUndefined();
  });

  it("COUNCIL 4: activates deterministically on deploy (skipWaiting + clientsClaim + cleanup)", () => {
    expect(workbox?.skipWaiting).toBe(true);
    expect(workbox?.clientsClaim).toBe(true);
    expect(workbox?.cleanupOutdatedCaches).toBe(true);
    expect(pwaOptions.registerType).toBe("autoUpdate");
  });

  it("COUNCIL 5: precaches the shell and scopes the offline fallback to /app only", () => {
    expect(workbox?.navigateFallback).toBe("index.html");
    expect(workbox?.navigateFallbackAllowlist?.some((re) => re.test("/app/albums/1"))).toBe(true);
    // The fallback must never serve the shell for API / upload / media routes.
    for (const denied of ["/be_auth/me", "/be_resizer/tus/1", "/images/x.jpg"]) {
      expect(workbox?.navigateFallbackDenylist?.some((re) => re.test(denied))).toBe(true);
    }
  });

  it("COUNCIL 6: registers the SW via an EXTERNAL script (CSP script-src 'self' safe)", () => {
    // 'inline' would inject an inline <script>, violating the hardened SPA CSP.
    expect(pwaOptions.injectRegister).toBe("script");
  });
});

describe("web app manifest", () => {
  it("is installable and scoped to the /app SPA surface", () => {
    expect(manifest.name).toBe("AlbumsAventures");
    expect(manifest.short_name).toBe("AlbumsAventures");
    expect(manifest.description).toBe("Aventures planquées dans les cartes");
    expect(manifest.display).toBe("standalone");
    expect(manifest.start_url).toBe("/app/");
    expect(manifest.scope).toBe("/app/");
    expect(manifest.theme_color).toBe("#0ea5e9");
    expect(manifest.background_color).toBe("#ffffff");
  });

  it("ships 192, 512 and a maskable icon", () => {
    const sizes = manifest.icons?.map((icon) => `${icon.sizes}:${icon.purpose}`);
    expect(sizes).toContain("192x192:any");
    expect(sizes).toContain("512x512:any");
    expect(sizes).toContain("512x512:maskable");
  });
});
