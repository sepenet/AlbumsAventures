import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { useSession } from "../auth/useSession";
import { ApiError, api } from "../lib/apiClient";
import { formatMonthYear, formatParticipants } from "../lib/format";
import type { Album, Category } from "../types/api";

async function fetchAlbums(userId: number): Promise<Album[]> {
  try {
    return await api.get<Album[]>(`/be_album/get_albums_by_user/${userId}`);
  } catch (error) {
    // `be_album` returns 404 when the user has no accessible albums — treat it
    // as an empty grid rather than an error.
    if (error instanceof ApiError && error.status === 404) {
      return [];
    }
    throw error;
  }
}

export function AlbumGridPage() {
  const { data: user } = useSession();
  const userId = user?.id;

  // Calls `be_album` DIRECTLY (same-origin), bypassing the fe_router httpx
  // loopback hop the Jinja2 page uses.
  const albumsQuery = useQuery({
    queryKey: ["albums", userId],
    queryFn: () => fetchAlbums(userId as number),
    enabled: userId !== undefined,
  });

  const categoriesQuery = useQuery({
    queryKey: ["categories"],
    queryFn: () => api.get<Category[]>("/be_category/get_all_categories/"),
  });

  const [query, setQuery] = useState("");
  const [selectedCategories, setSelectedCategories] = useState<number[]>([]);

  const albums = useMemo(() => albumsQuery.data ?? [], [albumsQuery.data]);
  const categories = categoriesQuery.data ?? [];

  const filteredAlbums = useMemo(() => {
    let list = albums;

    if (selectedCategories.length > 0) {
      list = list.filter((album) => selectedCategories.includes(album.category_id));
    }

    const trimmed = query.trim().toLowerCase();
    if (trimmed) {
      list = list.filter((album) =>
        [album.title, album.participants, album.location, album.tags, album.date, formatMonthYear(album.date)]
          .filter((value): value is string => Boolean(value))
          .some((value) => value.toLowerCase().includes(trimmed)),
      );
    }

    return [...list].sort(
      (a, b) =>
        new Date(b.date || "1900-01-01").getTime() - new Date(a.date || "1900-01-01").getTime(),
    );
  }, [albums, query, selectedCategories]);

  function toggleCategory(categoryId: number) {
    setSelectedCategories((current) =>
      current.includes(categoryId)
        ? current.filter((id) => id !== categoryId)
        : [...current, categoryId],
    );
  }

  if (albumsQuery.isPending && userId !== undefined) {
    return <p className="py-12 text-center text-gray-500 dark:text-gray-400">Chargement des albums…</p>;
  }

  if (albumsQuery.isError) {
    return (
      <div className="py-12 text-center">
        <p className="text-red-600 dark:text-red-400">
          Impossible de charger les albums. Veuillez réessayer.
        </p>
        <button
          type="button"
          onClick={() => albumsQuery.refetch()}
          className="mt-4 rounded-lg bg-sky-600 px-4 py-2 text-white transition-colors hover:bg-sky-700"
        >
          Réessayer
        </button>
      </div>
    );
  }

  return (
    <div className="py-2">
      {/* Category filter chips */}
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => setSelectedCategories([])}
          className={`rounded-lg border px-4 py-2 text-sm font-medium transition-colors ${
            selectedCategories.length === 0
              ? "border-sky-600 bg-sky-600 text-white"
              : "border-gray-300 bg-white text-gray-700 hover:bg-gray-100 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
          }`}
        >
          Toutes
        </button>
        {categories.map((category) => {
          const active = selectedCategories.includes(category.id);
          return (
            <button
              key={category.id}
              type="button"
              onClick={() => toggleCategory(category.id)}
              className={`rounded-lg border px-4 py-2 text-sm font-medium transition-colors ${
                active
                  ? "border-sky-600 bg-sky-600 text-white"
                  : "border-gray-300 bg-white text-gray-700 hover:bg-gray-100 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
              }`}
            >
              {category.category}
            </button>
          );
        })}
      </div>

      {/* Search + create */}
      <div className="mb-6 flex flex-col gap-4 sm:flex-row">
        <div className="relative flex-grow">
          <input
            type="text"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Rechercher par titre, date, participants, lieu, tags..."
            className="w-full rounded-lg border border-gray-300 bg-white px-4 py-3 text-gray-900 placeholder-gray-400 transition duration-200 focus:border-transparent focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
          />
        </div>
        {user?.is_superuser ? (
          <a
            href="/album/new"
            className="inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg bg-sky-600 px-5 py-3 font-medium text-white transition-colors hover:bg-sky-700 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:ring-offset-2"
          >
            <span className="hidden sm:inline">Créer un album</span>
            <span className="sm:hidden">Créer</span>
          </a>
        ) : null}
      </div>

      {/* Responsive grid: 4 cols PC/tablet, 1 col mobile (GUIDELINES_UI.md) */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        {filteredAlbums.map((album) => (
          <div
            key={album.id}
            className="flex flex-col overflow-hidden rounded-lg bg-white shadow-md dark:bg-gray-800"
          >
            <Link to={`/albums/${album.id}`} className="relative block aspect-square overflow-hidden">
              {album.image_cover_url ? (
                <img
                  src={album.image_cover_url}
                  alt={album.title}
                  loading="lazy"
                  className="h-full w-full object-cover transition-transform duration-300 hover:scale-105"
                />
              ) : (
                <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-sky-400 to-blue-500">
                  <svg
                    className="h-12 w-12 text-white/50"
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
                </div>
              )}
            </Link>

            <div className="flex flex-grow flex-col p-3">
              <Link to={`/albums/${album.id}`} className="block">
                <h3 className="truncate font-semibold text-gray-900 transition-colors hover:text-sky-600 dark:text-gray-100 dark:hover:text-sky-400">
                  {album.title}
                </h3>
              </Link>
              <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">{formatMonthYear(album.date)}</p>
              <p className="mt-1 truncate text-sm text-gray-600 dark:text-gray-400">
                {formatParticipants(album.participants)}
              </p>
            </div>
          </div>
        ))}
      </div>

      {filteredAlbums.length === 0 ? (
        <div className="py-12 text-center">
          <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100">Aucun album trouvé</h3>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            {query ? "Essayez une autre recherche." : "Vous n'avez pas encore d'albums accessibles."}
          </p>
        </div>
      ) : null}
    </div>
  );
}
