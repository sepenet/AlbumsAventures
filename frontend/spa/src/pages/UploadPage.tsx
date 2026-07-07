import { useMutation, useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import Dashboard from "@uppy/react/dashboard";
import "@uppy/core/css/style.min.css";
import "@uppy/dashboard/css/style.min.css";

import { useUploader } from "../hooks/useUploader";
import { api } from "../lib/apiClient";
import { formatBytes } from "../lib/upload";
import type { AlbumDetail, ProcessingFile } from "../types/api";

const PROCESSING_LABELS: Record<ProcessingFile["status"], string> = {
  success: "Vignette prête",
  processing: "En cours…",
  pending: "En attente…",
  skipped: "Ignoré",
  failed: "Échec",
};

const PROCESSING_CLASSES: Record<ProcessingFile["status"], string> = {
  success: "text-green-600 dark:text-green-400",
  processing: "text-amber-600 dark:text-amber-400",
  pending: "text-amber-600 dark:text-amber-400",
  skipped: "text-gray-500 dark:text-gray-400",
  failed: "text-red-600 dark:text-red-400",
};

async function fetchAlbum(albumId: number): Promise<AlbumDetail> {
  return api.get<AlbumDetail>(`/be_album/get_album_by_id/${albumId}`);
}

export function UploadPage() {
  const params = useParams<{ albumId: string }>();
  const albumId = Number(params.albumId);

  const albumQuery = useQuery({
    queryKey: ["album", albumId],
    queryFn: () => fetchAlbum(albumId),
    enabled: Number.isFinite(albumId),
  });

  const { uppy, outcome, metrics, processingFiles, processingSummary } = useUploader(albumId);

  // Regenerate thumbnails — real superuser action wired to the existing
  // endpoint (unchanged backend), for files whose thumbnail failed.
  const regenerate = useMutation({
    mutationFn: () => api.get(`/be_resizer/create_thumbnails/${albumId}`),
  });

  const dashboardTheme =
    typeof document !== "undefined" && document.documentElement.classList.contains("dark")
      ? "dark"
      : "light";

  const hasFailedThumbnail = processingFiles.some((file) => file.status === "failed");

  return (
    <div className="mx-auto max-w-4xl py-6">
      {/* Header */}
      <div className="mb-8">
        <Link
          to={`/albums/${albumId}`}
          className="mb-4 inline-flex items-center gap-2 text-sky-600 transition-colors hover:text-sky-700 dark:text-sky-400 dark:hover:text-sky-300"
        >
          <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          Retour à l'album
        </Link>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Ajouter des photos</h1>
        {albumQuery.data ? (
          <p className="mt-1 text-gray-600 dark:text-gray-400">
            Album : <span className="font-medium">{albumQuery.data.title}</span>
          </p>
        ) : null}
      </div>

      {/* Upload result banner */}
      {outcome ? (
        <div
          className={`mb-6 rounded-lg border p-4 ${
            outcome.status === "success"
              ? "border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-900/20"
              : "border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-900/20"
          }`}
        >
          <p
            className={`font-medium ${
              outcome.status === "success"
                ? "text-green-700 dark:text-green-300"
                : "text-red-700 dark:text-red-300"
            }`}
          >
            {outcome.message}
          </p>
          <ul
            className={`mt-2 text-sm ${
              outcome.status === "success"
                ? "text-green-600 dark:text-green-400"
                : "text-red-600 dark:text-red-400"
            }`}
          >
            {outcome.uploaded > 0 ? <li>✓ {outcome.uploaded} fichier(s) uploadé(s)</li> : null}
            {outcome.errors > 0 ? <li>✗ {outcome.errors} erreur(s)</li> : null}
          </ul>
          {outcome.errorMessages.length > 0 ? (
            <ul className="mt-2 text-sm text-red-600 dark:text-red-400">
              {outcome.errorMessages.map((message) => (
                <li key={message}>• {message}</li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}

      {/* Uppy Dashboard (v5, ESM — bundled by Vite, same-origin, no CDN) */}
      <div className="rounded-xl bg-white p-6 shadow-lg dark:bg-gray-800">
        <Dashboard
          uppy={uppy}
          proudlyDisplayPoweredByUppy={false}
          theme={dashboardTheme}
          note="Images (max 30 Mo) et vidéos MP4/AVI (max 500 Mo)"
        />
      </div>

      {/* Client compression metric (#380): bytes saved before upload */}
      {metrics.compressedSavedBytes > 0 ? (
        <div className="mt-6 rounded-lg border border-sky-200 bg-sky-50 p-4 dark:border-sky-800 dark:bg-sky-900/20">
          <div className="flex items-center gap-3">
            <svg className="h-5 w-5 flex-shrink-0 text-sky-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            <p className="text-sm text-sky-700 dark:text-sky-300">
              Compression : <span className="font-semibold">{formatBytes(metrics.compressedSavedBytes)}</span>{" "}
              économisés ({formatBytes(metrics.originalBytes)} → {formatBytes(metrics.sentBytes)} envoyés).
            </p>
          </div>
        </div>
      ) : null}

      {/* Durable post-processing (thumbnails) status per file — UPL-01 */}
      {processingSummary ? (
        <div className="mt-6 rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
              Traitement des vignettes
            </h2>
            <div className="flex items-center gap-3 text-xs">
              <span className="text-green-600 dark:text-green-400">✓ {processingSummary.success}</span>
              <span className="text-amber-600 dark:text-amber-400">
                ⏳ {processingSummary.pending + processingSummary.processing}
              </span>
              <span className="text-gray-500 dark:text-gray-400">⤼ {processingSummary.skipped}</span>
              <span className="text-red-600 dark:text-red-400">✗ {processingSummary.failed}</span>
            </div>
          </div>
          <ul className="max-h-56 space-y-1 overflow-y-auto">
            {processingFiles.map((file) => (
              <li
                key={file.filename}
                className="flex items-center justify-between border-b border-gray-100 py-1 text-sm last:border-0 dark:border-gray-700"
              >
                <span className="truncate text-gray-700 dark:text-gray-300">{file.filename}</span>
                <span className={`ml-3 flex-shrink-0 text-xs font-medium ${PROCESSING_CLASSES[file.status]}`}>
                  {PROCESSING_LABELS[file.status] ?? file.status}
                </span>
              </li>
            ))}
          </ul>
          {hasFailedThumbnail ? (
            <p className="mt-2 text-xs text-red-600 dark:text-red-400">
              Certaines vignettes ont échoué — utilisez « Régénérer vignettes » ci-dessous.
            </p>
          ) : null}
        </div>
      ) : null}

      {/* Post-upload actions */}
      <div className="mt-6 flex flex-col gap-3 sm:flex-row">
        <Link
          to={`/albums/${albumId}`}
          className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-sky-600 px-6 py-3 font-medium text-white transition-colors hover:bg-sky-700"
        >
          <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
            />
          </svg>
          Voir l'album
        </Link>
        <button
          type="button"
          onClick={() => regenerate.mutate()}
          disabled={regenerate.isPending}
          className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-purple-600 px-6 py-3 font-medium text-white transition-colors hover:bg-purple-700 disabled:cursor-not-allowed disabled:bg-purple-400 sm:flex-none"
        >
          <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
          {regenerate.isPending ? "Génération…" : "Régénérer vignettes"}
        </button>
      </div>

      {regenerate.isError ? (
        <p className="mt-4 rounded-lg bg-red-100 px-4 py-2 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
          Échec de la régénération des vignettes.
        </p>
      ) : null}
    </div>
  );
}
