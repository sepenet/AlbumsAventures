import { useEffect, useRef, useState } from "react";

import Uppy, { type UploadResult, type UppyFile } from "@uppy/core";
import Compressor from "@uppy/compressor";
import GoldenRetriever from "@uppy/golden-retriever";
import Tus from "@uppy/tus";
import French from "@uppy/locales/lib/fr_FR.js";

import { api } from "../lib/apiClient";
import {
  CHUNK_SIZE_FLOOR,
  EMPTY_COMPRESSION_METRIC,
  type CompressionMetric,
  buildUploadConfigQuery,
  clampChunkSize,
  computeCompressionMetric,
  readConnectionInfo,
  selectChunkSize,
} from "../lib/upload";
import type {
  ProcessingFile,
  ProcessingStatusResponse,
  ProcessingSummary,
  UploadConfig,
} from "../types/api";

// TUS metadata carries only the album id; no upload body is expected back.
type UploadMeta = { album_id: string };
type UploadBody = Record<string, never>;

// Aggressive early backoff then wider spacing — same schedule as the Phase 2
// Jinja upload page. The server also returns its own schedule via upload_config.
const TUS_RETRY_DELAYS = [0, 1000, 3000, 5000, 10000, 20000, 40000, 60000];
const TUS_ENDPOINT = "/be_resizer/tus/";

// Durable thumbnail-status polling cadence: every 3s, self-terminating once no
// file is pending/processing, with a ~2 min hard guard (40 ticks).
const POLL_INTERVAL_MS = 3000;
const POLL_MAX_TICKS = 40;

/** User-facing outcome of an upload batch (success/partial/failure). */
export interface UploadOutcome {
  status: "success" | "error";
  message: string;
  uploaded: number;
  errors: number;
  errorMessages: string[];
}

export interface UploaderState {
  uppy: Uppy<UploadMeta, UploadBody>;
  outcome: UploadOutcome | null;
  metrics: CompressionMetric;
  processingFiles: ProcessingFile[];
  processingSummary: ProcessingSummary | null;
}

/**
 * Construct the Uppy v5 instance with the full Phase 2 reliability stack:
 *   - TUS resumable transport to `/be_resizer/tus/` (cookie auth via
 *     `withCredentials`, `limit: 1`, `album_id` metadata),
 *   - client-side image compression before upload (#380),
 *   - GoldenRetriever resume-after-reload (IndexedDB; Service Worker storage is
 *     a Phase 4 PWA concern, so `serviceWorker: false`),
 *   - an adaptive chunk size seeded from the local connection, ALWAYS floored at
 *     256 KB; the server value is applied afterwards in the effect below.
 */
function buildUppy(albumId: number): Uppy<UploadMeta, UploadBody> {
  const chunkSize = selectChunkSize(readConnectionInfo());

  const uppy = new Uppy<UploadMeta, UploadBody>({
    id: "uppy-album-upload",
    autoProceed: false,
    allowMultipleUploadBatches: true,
    locale: French,
    restrictions: {
      // Ceiling aligned to the backend video limit (500 MB). Precise per-type
      // limits (image 30 MB / video 500 MB) are enforced server-side in the TUS
      // pre-creation hook (413 on exceed). ".avi" is filtered by extension
      // because the browser reports it as "video/x-msvideo", not "video/avi".
      maxFileSize: 500 * 1024 * 1024,
      allowedFileTypes: ["image/*", "video/mp4", ".avi", ".heic"],
    },
  });

  uppy.setMeta({ album_id: String(albumId) });

  uppy.use(Tus, {
    endpoint: TUS_ENDPOINT,
    chunkSize,
    retryDelays: TUS_RETRY_DELAYS,
    removeFingerprintOnSuccess: true,
    withCredentials: true,
    limit: 1,
  });

  // Client compression BEFORE upload (#380): the dominant reliability lever on
  // constrained mobile links. The server MAX_IMAGE_SIZE (30 MB) still applies.
  uppy.use(Compressor, { quality: 0.8, limit: 10 });

  // Resume after reload / tab crash / mobile app switch (#394). IndexedDB only;
  // the persistent server-side TUS offset lets the in-flight upload resume
  // instead of restarting.
  uppy.use(GoldenRetriever, { serviceWorker: false });

  return uppy;
}

/**
 * React hook owning the Uppy v5 upload lifecycle and the durable
 * post-processing status for one album. Returns a stable Uppy instance (for the
 * `@uppy/react` Dashboard) plus the reactive reliability state the page renders:
 * the compression metric (#380) and the per-file thumbnail status (UPL-01).
 */
export function useUploader(albumId: number): UploaderState {
  const [uppy] = useState(() => buildUppy(albumId));
  const [outcome, setOutcome] = useState<UploadOutcome | null>(null);
  const [metrics, setMetrics] = useState<CompressionMetric>(EMPTY_COMPRESSION_METRIC);
  const [processingFiles, setProcessingFiles] = useState<ProcessingFile[]>([]);
  const [processingSummary, setProcessingSummary] = useState<ProcessingSummary | null>(null);

  // Keep the latest album id reachable from the (once-registered) listeners
  // without re-running the effect or re-building Uppy.
  const albumIdRef = useRef(albumId);
  albumIdRef.current = albumId;

  // Keep TUS metadata correct if the route param ever changes without a remount.
  useEffect(() => {
    uppy.setMeta({ album_id: String(albumId) });
  }, [uppy, albumId]);

  useEffect(() => {
    // Original sizes captured at file-added (pre-compression) to measure #380.
    const originalSizes: Record<string, number> = {};
    let pollTimer: ReturnType<typeof setInterval> | null = null;
    let pollTicks = 0;
    let cancelled = false;

    const stopPolling = () => {
      if (pollTimer) {
        clearInterval(pollTimer);
        pollTimer = null;
      }
    };

    // Durable thumbnail-status polling (UPL-01): the backend generates
    // thumbnails in a bounded worker pool AFTER the TUS 204, so a failure would
    // otherwise be invisible. Self-terminates when nothing is in flight.
    const poll = async () => {
      pollTicks += 1;
      try {
        const data = await api.get<ProcessingStatusResponse>(
          `/be_resizer/processing_status/${albumIdRef.current}`,
        );
        if (cancelled) return;
        setProcessingFiles(data.files ?? []);
        setProcessingSummary(data.summary ?? null);
        const inFlight = (data.summary?.pending ?? 0) + (data.summary?.processing ?? 0);
        if (inFlight === 0) {
          stopPolling();
          return;
        }
      } catch {
        // Transient network error: retry on the next tick.
      }
      if (pollTicks >= POLL_MAX_TICKS) {
        stopPolling();
      }
    };

    const startPolling = () => {
      pollTicks = 0;
      stopPolling();
      void poll();
      pollTimer = setInterval(() => void poll(), POLL_INTERVAL_MS);
    };

    const onFileAdded = (file: UppyFile<UploadMeta, UploadBody>) => {
      originalSizes[file.id] = file.size ?? 0;
    };

    const onComplete = (result: UploadResult<UploadMeta, UploadBody>) => {
      const successful = result.successful ?? [];
      const failed = result.failed ?? [];

      setMetrics(
        computeCompressionMetric(
          successful.map((file) => ({
            originalBytes: originalSizes[file.id] ?? file.size ?? 0,
            sentBytes: file.size ?? 0,
          })),
        ),
      );

      if (failed.length > 0) {
        setOutcome({
          status: successful.length > 0 ? "success" : "error",
          message: successful.length > 0 ? "Upload terminé avec des erreurs" : "Échec de l'upload",
          uploaded: successful.length,
          errors: failed.length,
          errorMessages: failed.map((file) => `${file.name}: ${file.error ?? "Erreur inconnue"}`),
        });
      } else if (successful.length > 0) {
        setOutcome({
          status: "success",
          message: `${successful.length} fichier(s) uploadé(s) avec succès`,
          uploaded: successful.length,
          errors: 0,
          errorMessages: [],
        });
      }

      if (successful.length > 0) {
        startPolling();
      }
    };

    const onError = (error: { name: string; message: string; details?: string }) => {
      setOutcome({
        status: "error",
        message: `Erreur lors de l'upload: ${error.message}`,
        uploaded: 0,
        errors: 0,
        errorMessages: [],
      });
    };

    uppy.on("file-added", onFileAdded);
    uppy.on("complete", onComplete);
    uppy.on("error", onError);

    // Align the chunk size to the server-authoritative value (best-effort,
    // async): never blocks the Dashboard/Tus, always re-clamped to the 256 KB
    // floor even on the server value.
    void (async () => {
      try {
        const query = buildUploadConfigQuery(readConnectionInfo());
        const cfg = await api.get<UploadConfig>(
          query ? `/be_resizer/upload_config?${query}` : "/be_resizer/upload_config",
        );
        if (cancelled) return;
        const serverChunk = clampChunkSize(cfg.chunk_size ?? CHUNK_SIZE_FLOOR);
        uppy.getPlugin<Tus<UploadMeta, UploadBody>>("Tus")?.setOptions({ chunkSize: serverChunk });
      } catch {
        // Server unreachable: the client value (already floored) stays in place.
      }
    })();

    return () => {
      cancelled = true;
      stopPolling();
      // Removes all listeners and tears down the plugins/IndexedDB handles.
      uppy.destroy();
    };
  }, [uppy]);

  return { uppy, outcome, metrics, processingFiles, processingSummary };
}
