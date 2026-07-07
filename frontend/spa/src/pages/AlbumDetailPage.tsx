import { useState } from "react";
import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { Lightbox } from "../components/Lightbox";
import { useSession } from "../auth/useSession";
import { ApiError, api } from "../lib/apiClient";
import { formatMonthYear, formatParticipants, getNextMediaOffset } from "../lib/format";
import type { AlbumDetail, AlbumMediaPage, MediaItem } from "../types/api";

const PAGE_SIZE = 30;

// Sub-phase ownership for affordances whose native SPA flow is not yet built.
// Kept as constants so the TODO references stay discoverable in the source.
const SUBPHASE_SHARE = "3.7"; // shared-album / associate flow
const SUBPHASE_ALBUM_ADMIN = "3.6"; // album delete + admin actions

async function fetchAlbum(albumId: number): Promise<AlbumDetail> {
  // Calls `be_album` DIRECTLY (same-origin), bypassing the fe_router Jinja
  // page-render httpx loopback hop (C-8) — see the increment plan.
  return api.get<AlbumDetail>(`/be_album/get_album_by_id/${albumId}`);
}

async function fetchMediaPage(albumId: number, offset: number): Promise<AlbumMediaPage> {
  // The media listing is filesystem-derived and exposed by the existing
  // browser-facing JSON endpoint `/album/{id}/images` (thumbnails/originals are
  // served by the `/thumbnails` and `/images` static mounts). No be_album media
  // endpoint exists and the backend is unchanged this increment; full
  // fe_router retirement is Phase 3.8.
  return api.get<AlbumMediaPage>(`/album/${albumId}/images?offset=${offset}&limit=${PAGE_SIZE}`);
}

export function AlbumDetailPage() {
  const params = useParams<{ albumId: string }>();
  const albumId = Number(params.albumId);
  const { data: user } = useSession();
  const queryClient = useQueryClient();

  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);

  const albumQuery = useQuery({
    queryKey: ["album", albumId],
    queryFn: () => fetchAlbum(albumId),
    enabled: Number.isFinite(albumId),
  });

  const mediaQuery = useInfiniteQuery({
    queryKey: ["album-media", albumId],
    queryFn: ({ pageParam }) => fetchMediaPage(albumId, pageParam),
    initialPageParam: 0,
    getNextPageParam: (_lastPage, allPages) => getNextMediaOffset(allPages),
    enabled: Number.isFinite(albumId) && albumQuery.isSuccess,
  });

  // Regenerate thumbnails — a real superuser action wired to the existing
  // endpoint; on success the media cache is invalidated so new thumbnails show.
  // F-1: the endpoint is a state-changing POST (was a GET), so apiClient.post
  // automatically echoes the CSRF double-submit header; the server also enforces
  // superuser access, so a non-admin request is rejected 403 regardless of UI.
  const regenerateThumbnails = useMutation({
    mutationFn: () => api.post(`/be_resizer/create_thumbnails/${albumId}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["album-media", albumId] }),
  });

  const media = mediaQuery.data?.pages.flatMap((page) => page.items) ?? [];
  const totalImages = mediaQuery.data?.pages[0]?.total ?? 0;
  const isSuperuser = user?.is_superuser ?? false;

  // ---- Album-level loading / error states -------------------------------
  if (albumQuery.isPending && Number.isFinite(albumId)) {
    return <AlbumDetailSkeleton />;
  }

  if (albumQuery.isError) {
    const notFound = albumQuery.error instanceof ApiError && albumQuery.error.status === 404;
    return (
      <div className="py-12 text-center">
        <p className="text-red-600 dark:text-red-400">
          {notFound ? "Cet album est introuvable." : "Impossible de charger l'album."}
        </p>
        <div className="mt-4 flex justify-center gap-3">
          {!notFound ? (
            <button
              type="button"
              onClick={() => albumQuery.refetch()}
              className="rounded-lg bg-sky-600 px-4 py-2 text-white transition-colors hover:bg-sky-700"
            >
              Réessayer
            </button>
          ) : null}
          <Link
            to="/"
            className="rounded-lg border border-gray-300 px-4 py-2 text-gray-700 transition-colors hover:bg-gray-100 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
          >
            Retour aux albums
          </Link>
        </div>
      </div>
    );
  }

  const album = albumQuery.data as AlbumDetail;

  return (
    <div className="py-2">
      {/* Header : back link + album info + action affordances */}
      <div className="mb-6">
        <Link
          to="/"
          className="mb-4 inline-flex items-center gap-2 text-sky-600 transition-colors hover:text-sky-700 dark:text-sky-400 dark:hover:text-sky-300"
        >
          <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          <span>Retour aux albums</span>
        </Link>

        <div className="rounded-lg bg-white p-6 shadow-md dark:bg-gray-800">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div className="flex-1">
              <h1 className="mb-3 text-2xl font-bold text-gray-900 dark:text-gray-100">{album.title}</h1>

              <div className="flex flex-wrap gap-4 text-sm text-gray-600 dark:text-gray-400">
                <MetaItem
                  label={formatMonthYear(album.date) || album.date}
                  iconPath="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
                />
                {album.participants ? (
                  <MetaItem
                    label={formatParticipants(album.participants)}
                    iconPath="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"
                  />
                ) : null}
                {album.location ? (
                  <MetaItem
                    label={album.location}
                    iconPath="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"
                  />
                ) : null}
                <MetaItem
                  label={`${totalImages} photo(s)`}
                  iconPath="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                />
              </div>

              {album.tags ? (
                <div className="mt-3 flex flex-wrap gap-2">
                  {album.tags
                    .split(/[|,]/)
                    .map((tag) => tag.trim())
                    .filter(Boolean)
                    .map((tag) => (
                      <span
                        key={tag}
                        className="rounded-full bg-sky-100 px-3 py-1 text-xs font-medium text-sky-800 dark:bg-sky-900/40 dark:text-sky-200"
                      >
                        {tag}
                      </span>
                    ))}
                </div>
              ) : null}

              {album.description ? (
                <p className="mt-4 text-gray-700 dark:text-gray-300">{album.description}</p>
              ) : null}
            </div>

            {/* Action affordances — gated on the cookie-session is_superuser
                (Phase 1 #485). Upload is available to every authenticated user. */}
            <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
              {isSuperuser ? (
                <>
                  {/* Edit — links to the existing (still-Jinja) edit page; native
                      SPA edit lands in a later admin increment. */}
                  <a
                    href={`/album/${album.id}/edit`}
                    className="inline-flex items-center gap-2 rounded-lg bg-amber-500 px-4 py-2 font-medium text-white shadow-md transition-colors hover:bg-amber-600"
                  >
                    <ActionIcon path="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                    Modifier
                  </a>

                  {/* Share / associate — TODO(sub-phase 3.7): native shared-album
                      + associate flow. Links to the existing Jinja detail page
                      where the working associate/share modal lives. */}
                  <a
                    href={`/album/${album.id}`}
                    title={`Partage natif à venir (sous-phase ${SUBPHASE_SHARE})`}
                    className="inline-flex items-center gap-2 rounded-lg bg-sky-600 px-4 py-2 font-medium text-white shadow-md transition-colors hover:bg-sky-700"
                  >
                    <ActionIcon path="M17 20h5v-1a4 4 0 00-3-3.87M9 20H4v-1a4 4 0 013-3.87M16 11a4 4 0 11-8 0 4 4 0 018 0z" />
                    Partager
                  </a>

                  {/* Regenerate thumbnails — real action against the existing
                      endpoint, invalidates the media cache on success. */}
                  <button
                    type="button"
                    disabled={regenerateThumbnails.isPending}
                    onClick={() => {
                      if (window.confirm("Régénérer les miniatures de cet album ?")) {
                        regenerateThumbnails.mutate();
                      }
                    }}
                    className="inline-flex items-center gap-2 rounded-lg bg-purple-600 px-4 py-2 font-medium text-white shadow-md transition-colors hover:bg-purple-700 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <ActionIcon path="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    {regenerateThumbnails.isPending ? "Régénération…" : "Miniatures"}
                  </button>

                  {/* Delete — TODO(sub-phase 3.6): album deletion. No backend
                      album-delete endpoint exists yet and the backend is
                      unchanged this increment, so this is a stub. */}
                  <button
                    type="button"
                    title={`Suppression d'album à venir (sous-phase ${SUBPHASE_ALBUM_ADMIN})`}
                    onClick={() =>
                      window.alert(
                        `La suppression d'album arrivera dans la sous-phase ${SUBPHASE_ALBUM_ADMIN}.`,
                      )
                    }
                    className="inline-flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 font-medium text-white shadow-md transition-colors hover:bg-red-700"
                  >
                    <ActionIcon path="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    Supprimer
                  </button>
                </>
              ) : null}

              {/* Upload — every authenticated user; native SPA upload page
                  (Phase 3.4, Uppy v5) via the in-SPA router. */}
              <Link
                to={`/albums/${album.id}/upload`}
                className="inline-flex items-center gap-2 rounded-lg bg-green-600 px-4 py-2 font-medium text-white shadow-md transition-colors hover:bg-green-700"
              >
                <ActionIcon path="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                Ajouter des photos
              </Link>
            </div>
          </div>
        </div>
      </div>

      {regenerateThumbnails.isError ? (
        <p className="mb-4 rounded-lg bg-red-100 px-4 py-2 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
          Échec de la régénération des miniatures.
        </p>
      ) : null}

      {/* Media gallery */}
      <MediaGallery
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
  );
}

function MediaGallery({
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
        <svg
          className="mx-auto mb-4 h-16 w-16 text-gray-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
          />
        </svg>
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

function MetaItem({ label, iconPath }: { label: string; iconPath: string }) {
  return (
    <div className="flex items-center gap-1">
      <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={iconPath} />
      </svg>
      <span>{label}</span>
    </div>
  );
}

function ActionIcon({ path }: { path: string }) {
  return (
    <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={path} />
    </svg>
  );
}

function AlbumDetailSkeleton() {
  return (
    <div className="py-2">
      <div className="mb-6 rounded-lg bg-white p-6 shadow-md dark:bg-gray-800">
        <div className="mb-3 h-8 w-1/2 animate-pulse rounded bg-gray-200 dark:bg-gray-700" />
        <div className="h-4 w-1/3 animate-pulse rounded bg-gray-200 dark:bg-gray-700" />
      </div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-4">
        {Array.from({ length: 8 }).map((_, index) => (
          <div
            key={index}
            className="aspect-square animate-pulse rounded-lg bg-gray-200 dark:bg-gray-700"
          />
        ))}
      </div>
    </div>
  );
}
