import { useEffect, useState } from "react";
import { useInfiniteQuery, useMutation } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { Lightbox } from "../components/Lightbox";
import {
  PIN_LENGTH,
  SharedAccessError,
  isValidPinFormat,
  normalizePin,
  sharedErrorMessage,
  type SharedErrorDetail,
} from "../lib/shared";
import { getNextMediaOffset } from "../lib/format";
import type { AlbumDetail, AlbumMediaPage, MediaItem } from "../types/api";

const PAGE_SIZE = 30;

// The public share endpoints are called with `credentials: "omit"`: the shared
// viewer is unauthenticated, so no session cookie is sent and the flow can NEVER
// read authenticated app data — access is gated exclusively by the URL token +
// the typed PIN. The backend re-validates the token, PIN, expiry, and rate
// limiting on every call.
const PUBLIC_FETCH_INIT: RequestInit = {
  method: "GET",
  credentials: "omit",
  headers: { Accept: "application/json" },
};

async function readErrorDetail(response: Response): Promise<SharedErrorDetail | string | null> {
  try {
    const body: unknown = await response.json();
    if (body && typeof body === "object" && "detail" in body) {
      return (body as { detail: SharedErrorDetail | string }).detail;
    }
  } catch {
    // Non-JSON error body — fall through to the status-based message.
  }
  return null;
}

/**
 * Verify the token + PIN against the PUBLIC share endpoint and return the album
 * metadata. On failure the backend's structured error (wrong PIN, expiry, or
 * 429 lockout) is mapped to a user message via {@link sharedErrorMessage}.
 */
async function fetchSharedAlbum(token: string, pin: string): Promise<AlbumDetail> {
  const query = new URLSearchParams({ token, pin });
  const response = await fetch(`/be_album/shared?${query.toString()}`, PUBLIC_FETCH_INIT);
  if (!response.ok) {
    throw new SharedAccessError(
      sharedErrorMessage(response.status, await readErrorDetail(response)),
      response.status,
    );
  }
  return (await response.json()) as AlbumDetail;
}

/**
 * Load one page of the shared album's media from the PUBLIC images endpoint
 * (`/album/shared/images`), which re-checks the token + PIN server-side before
 * returning file listings. Media files themselves are served by the public
 * `/images` and `/thumbnails` static mounts.
 */
async function fetchSharedMedia(token: string, pin: string, offset: number): Promise<AlbumMediaPage> {
  const query = new URLSearchParams({
    token,
    pin,
    offset: String(offset),
    limit: String(PAGE_SIZE),
  });
  const response = await fetch(`/album/shared/images?${query.toString()}`, PUBLIC_FETCH_INIT);
  if (!response.ok) {
    throw new SharedAccessError(
      sharedErrorMessage(response.status, await readErrorDetail(response)),
      response.status,
    );
  }
  return (await response.json()) as AlbumMediaPage;
}

/**
 * PUBLIC shared-album page (Phase 3.7 strangler variant of
 * frontend/templates/shared_album.html + album_detail.html "mode partagé").
 *
 * Served at `/app/shared/:token` OUTSIDE the `RequireAuth` guard and the
 * authenticated `Layout` — it renders its own minimal shell so it never calls
 * `GET /be_auth/me` nor exposes the authenticated navigation/logout. The share
 * token lives only in the URL and the verified PIN only in React state (memory):
 * neither is persisted to localStorage/sessionStorage. First a PIN is entered;
 * once the backend accepts it, a RESTRICTED read-only gallery is shown with none
 * of the owner affordances (no back-to-albums, edit, upload, share, cover, or
 * associate actions) — only a "shared access" badge and the media viewer.
 *
 * The Jinja shared pages stay live during the migration; this is the additive
 * `/app` variant.
 */
export function SharedAlbumPage() {
  const { token } = useParams<{ token: string }>();

  // Apply the shared dark-mode preference so the standalone shell matches the
  // rest of the app, without pulling in the authenticated Layout.
  useEffect(() => {
    document.documentElement.classList.toggle("dark", localStorage.getItem("darkMode") === "true");
  }, []);

  const [pinInput, setPinInput] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  // The verified PIN is held in memory only, alongside the album it unlocked.
  const [verified, setVerified] = useState<{ album: AlbumDetail; pin: string } | null>(null);

  const verifyMutation = useMutation({
    mutationFn: (pin: string) => fetchSharedAlbum(token as string, pin),
    onSuccess: (album, pin) => {
      setVerified({ album, pin });
      setFormError(null);
    },
    onError: (error) => {
      setFormError(
        error instanceof SharedAccessError
          ? error.message
          : "Erreur de connexion. Veuillez réessayer.",
      );
    },
  });

  if (!token) {
    return (
      <SharedShell>
        <ErrorCard message="Lien de partage invalide." />
      </SharedShell>
    );
  }

  if (verified) {
    return <SharedAlbumDetail token={token} pin={verified.pin} album={verified.album} />;
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const pin = normalizePin(pinInput);
    if (!isValidPinFormat(pin)) {
      setFormError(
        `Le code PIN doit contenir exactement ${PIN_LENGTH} caractères alphanumériques.`,
      );
      return;
    }
    setFormError(null);
    verifyMutation.mutate(pin);
  }

  return (
    <SharedShell>
      <div className="mx-auto max-w-lg py-6">
        <div className="rounded-lg bg-white p-6 shadow-md dark:bg-gray-800">
          <div className="mb-6 text-center">
            <svg
              className="mx-auto h-12 w-12 text-green-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z"
              />
            </svg>
            <h1 className="mt-4 text-xl font-bold text-gray-900 dark:text-gray-100">Album partagé</h1>
            <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
              Saisissez le code PIN pour accéder à cet album.
            </p>
          </div>

          {formError ? (
            <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 dark:border-red-800 dark:bg-red-900/30">
              <p className="text-sm text-red-700 dark:text-red-300">{formError}</p>
            </div>
          ) : null}

          <form onSubmit={handleSubmit}>
            <label
              htmlFor="shared-pin"
              className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300"
            >
              Code PIN ({PIN_LENGTH} caractères)
            </label>
            <input
              id="shared-pin"
              name="pin"
              type="text"
              maxLength={PIN_LENGTH}
              placeholder="ABC123"
              autoComplete="off"
              required
              value={pinInput}
              onChange={(event) => setPinInput(event.target.value.toUpperCase())}
              className="w-full rounded-lg border border-gray-300 bg-white px-4 py-3 text-center font-mono text-2xl uppercase tracking-[0.5em] text-gray-900 focus:border-green-500 focus:ring-2 focus:ring-green-500 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
            />
            <button
              type="submit"
              disabled={verifyMutation.isPending}
              className="mt-4 w-full rounded-lg bg-green-600 px-4 py-3 font-medium text-white transition-colors hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {verifyMutation.isPending ? "Vérification…" : "Accéder à l'album"}
            </button>
          </form>
        </div>
      </div>
    </SharedShell>
  );
}

/**
 * RESTRICTED read-only gallery shown after a correct PIN. It deliberately omits
 * every owner affordance present on the authenticated album detail page — there
 * is NO back-to-albums link, edit, upload, share, cover-selection, or associate
 * action — because this is a public, temporary view. A "shared access" badge is
 * always visible; videos show a play overlay and images open the shared
 * Lightbox (reused from Phase 3.3).
 */
function SharedAlbumDetail({
  token,
  pin,
  album,
}: {
  token: string;
  pin: string;
  album: AlbumDetail;
}) {
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);

  const mediaQuery = useInfiniteQuery({
    queryKey: ["shared-media", token, pin],
    queryFn: ({ pageParam }) => fetchSharedMedia(token, pin, pageParam),
    initialPageParam: 0,
    getNextPageParam: (_lastPage, allPages) => getNextMediaOffset(allPages),
  });

  const media = mediaQuery.data?.pages.flatMap((page) => page.items) ?? [];
  const totalImages = mediaQuery.data?.pages[0]?.total ?? 0;

  return (
    <SharedShell>
      <div className="py-2">
        <div className="mb-6 rounded-lg bg-white p-6 shadow-md dark:bg-gray-800">
          {/* Shared-access badge — the read-only public marker. */}
          <div className="mb-4 inline-flex items-center gap-2 rounded-full bg-amber-100 px-3 py-1 text-sm font-medium text-amber-800 dark:bg-amber-900/40 dark:text-amber-200">
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M13 10V3L4 14h7v7l9-11h-7z"
              />
            </svg>
            <span>Accès temporaire par lien de partage</span>
          </div>

          <h1 className="mb-3 text-2xl font-bold text-gray-900 dark:text-gray-100">{album.title}</h1>

          <div className="flex flex-wrap gap-4 text-sm text-gray-600 dark:text-gray-400">
            <span>{album.date}</span>
            {album.location ? <span>{album.location}</span> : null}
            <span>{totalImages} photo(s)</span>
          </div>

          {album.description ? (
            <p className="mt-4 text-gray-700 dark:text-gray-300">{album.description}</p>
          ) : null}
        </div>

        <SharedMediaGallery
          media={media}
          isPending={mediaQuery.isPending}
          isError={mediaQuery.isError}
          onRetry={() => mediaQuery.refetch()}
          onOpen={setLightboxIndex}
        />

        {mediaQuery.hasNextPage ? (
          <div className="flex justify-center py-6">
            <button
              type="button"
              onClick={() => mediaQuery.fetchNextPage()}
              disabled={mediaQuery.isFetchingNextPage}
              className="rounded-lg border border-gray-300 bg-white px-5 py-2 font-medium text-gray-700 transition-colors hover:bg-gray-100 disabled:opacity-60 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
            >
              {mediaQuery.isFetchingNextPage ? "Chargement…" : "Charger plus de photos"}
            </button>
          </div>
        ) : null}

        <Lightbox
          items={media}
          index={lightboxIndex}
          onClose={() => setLightboxIndex(null)}
          onNavigate={setLightboxIndex}
        />
      </div>
    </SharedShell>
  );
}

function SharedMediaGallery({
  media,
  isPending,
  isError,
  onRetry,
  onOpen,
}: {
  media: MediaItem[];
  isPending: boolean;
  isError: boolean;
  onRetry: () => void;
  onOpen: (index: number) => void;
}) {
  if (isPending) {
    return (
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-4">
        {Array.from({ length: 8 }).map((_, index) => (
          <div
            key={index}
            className="aspect-square animate-pulse rounded-lg bg-gray-200 dark:bg-gray-700"
          />
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <div className="py-12 text-center">
        <p className="text-red-600 dark:text-red-400">Impossible de charger les photos.</p>
        <button
          type="button"
          onClick={onRetry}
          className="mt-4 rounded-lg bg-sky-600 px-4 py-2 text-white transition-colors hover:bg-sky-700"
        >
          Réessayer
        </button>
      </div>
    );
  }

  if (media.length === 0) {
    return (
      <div className="rounded-lg bg-white py-12 text-center dark:bg-gray-800">
        <p className="text-gray-500 dark:text-gray-400">Aucun média dans cet album</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-4">
      {media.map((item, index) => (
        <button
          key={item.filename}
          type="button"
          onClick={() => onOpen(index)}
          className="group relative block aspect-square overflow-hidden rounded-lg bg-gray-100 dark:bg-gray-800"
        >
          <img
            src={item.thumbnail_url}
            alt={item.filename}
            loading="lazy"
            className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
          />
          {item.is_video ? (
            <span className="pointer-events-none absolute inset-0 flex items-center justify-center">
              <span className="flex h-14 w-14 items-center justify-center rounded-full bg-black/50 transition-colors group-hover:bg-black/70">
                <svg className="ml-1 h-7 w-7 text-white" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M8 5v14l11-7z" />
                </svg>
              </span>
            </span>
          ) : null}
        </button>
      ))}
    </div>
  );
}

/** Minimal standalone shell for the public share pages (no authenticated nav). */
function SharedShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 text-gray-900 transition-colors duration-300 dark:from-gray-900 dark:to-gray-800 dark:text-gray-100">
      <header className="border-b border-gray-200 bg-white shadow-sm dark:border-gray-700 dark:bg-gray-800">
        <div className="container mx-auto px-4 py-4">
          <span className="bg-gradient-to-r from-sky-500 to-blue-600 bg-clip-text text-xl font-bold text-transparent">
            Albums Aventures
          </span>
        </div>
      </header>
      <main className="container mx-auto px-4 py-6">{children}</main>
    </div>
  );
}

function ErrorCard({ message }: { message: string }) {
  return (
    <div className="mx-auto max-w-lg py-6">
      <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center dark:border-red-800 dark:bg-red-900/30">
        <p className="text-sm text-red-700 dark:text-red-300">{message}</p>
      </div>
    </div>
  );
}
