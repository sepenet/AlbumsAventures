// Pure, dependency-free upload helpers (adaptive chunk sizing + compression
// metric + byte formatting). Kept DOM-free so the chunk-floor and
// compression-metric logic can be unit-tested in the node Vitest environment
// without a browser — mirroring `lib/format.ts`.
//
// These preserve the exact Phase 2 upload-reliability rules that previously
// lived inline in the Jinja upload page:
//   - a HARD 256 KB chunk floor (production incident 2026-04-27: 2 MB PATCH
//     chunks were silently dropped between Edge Android and the reverse proxy),
//   - an 8 MB ceiling,
//   - the client compression payload-reduction metric (#380).
// The server remains authoritative via `GET /be_resizer/upload_config`, which
// never returns a chunk below the floor; `clampChunkSize` re-guards it anyway.

/** Hard minimum TUS chunk size. Never upload below this, ever. */
export const CHUNK_SIZE_FLOOR = 256 * 1024;

/** Maximum TUS chunk size (fewer round-trips on good links). */
export const CHUNK_SIZE_CEILING = 8 * 1024 * 1024;

/**
 * Subset of the browser `NetworkInformation` API (`navigator.connection`) that
 * the adaptive sizing reads. Passed in explicitly (rather than read from
 * `navigator`) so `selectChunkSize` stays pure and testable.
 */
export interface ConnectionInfo {
  effectiveType?: string;
  downlink?: number;
  saveData?: boolean;
}

/** A single file's pre/post-compression byte sizes, for the metric. */
export interface CompressionSample {
  originalBytes: number;
  sentBytes: number;
}

/** Aggregate compression metric surfaced to the user (#380). */
export interface CompressionMetric {
  originalBytes: number;
  sentBytes: number;
  compressedSavedBytes: number;
}

/** Neutral starting metric (nothing uploaded yet). */
export const EMPTY_COMPRESSION_METRIC: CompressionMetric = {
  originalBytes: 0,
  sentBytes: 0,
  compressedSavedBytes: 0,
};

/**
 * Clamp any chunk-size candidate into [floor, ceiling]. A non-finite or
 * non-positive input falls back to the floor. Applied both to the locally
 * computed value and to the server-authoritative value (defense in depth).
 */
export function clampChunkSize(value: number): number {
  if (!Number.isFinite(value) || value <= 0) {
    return CHUNK_SIZE_FLOOR;
  }
  return Math.max(CHUNK_SIZE_FLOOR, Math.min(Math.floor(value), CHUNK_SIZE_CEILING));
}

/**
 * Compute an adaptive TUS chunk size from Network Information hints: a small
 * chunk on a constrained mobile link, a larger one on a good link. The 256 KB
 * floor is ALWAYS enforced (via {@link clampChunkSize}); `saveData` or an
 * absent connection object collapses to the floor. Synchronous so it can feed
 * the Tus plugin's `chunkSize` at construction; the server aligns it afterwards.
 */
export function selectChunkSize(conn?: ConnectionInfo | null): number {
  if (!conn || conn.saveData) {
    return CHUNK_SIZE_FLOOR;
  }
  const byEffectiveType: Record<string, number> = {
    "slow-2g": CHUNK_SIZE_FLOOR,
    "2g": CHUNK_SIZE_FLOOR,
    "3g": 512 * 1024,
    "4g": 2 * 1024 * 1024,
    "5g": 4 * 1024 * 1024,
  };
  let size = byEffectiveType[(conn.effectiveType ?? "").toLowerCase()] ?? CHUNK_SIZE_FLOOR;
  if (typeof conn.downlink === "number" && conn.downlink > 0) {
    // ~0.5 MB per Mbps of downlink, keeping the larger of type/bandwidth.
    size = Math.max(size, Math.floor(conn.downlink * 512 * 1024));
  }
  return clampChunkSize(size);
}

/**
 * Aggregate the per-file original vs. sent byte sizes into the compression
 * metric (#380). `compressedSavedBytes` never goes negative (compression only
 * ever removes bytes; a larger "sent" would just report zero savings).
 */
export function computeCompressionMetric(samples: CompressionSample[]): CompressionMetric {
  let originalBytes = 0;
  let sentBytes = 0;
  for (const sample of samples) {
    originalBytes += Math.max(0, sample.originalBytes || 0);
    sentBytes += Math.max(0, sample.sentBytes || 0);
  }
  return {
    originalBytes,
    sentBytes,
    compressedSavedBytes: Math.max(0, originalBytes - sentBytes),
  };
}

/** Human-readable French byte formatting for the metric UI. */
export function formatBytes(octets: number): string {
  const n = Number(octets) || 0;
  if (n < 1024) return `${n} o`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} Ko`;
  if (n < 1024 * 1024 * 1024) return `${(n / (1024 * 1024)).toFixed(1)} Mo`;
  return `${(n / (1024 * 1024 * 1024)).toFixed(2)} Go`;
}

/**
 * Read the browser Network Information hints, if available. Guarded so the
 * module stays importable in the node test environment (the reference is only
 * evaluated when this is actually called in a browser). Returns `null` when the
 * API is unavailable, which {@link selectChunkSize} treats as the floor.
 */
export function readConnectionInfo(): ConnectionInfo | null {
  if (typeof navigator === "undefined") {
    return null;
  }
  const nav = navigator as Navigator & {
    connection?: ConnectionInfo;
    mozConnection?: ConnectionInfo;
    webkitConnection?: ConnectionInfo;
  };
  const conn = nav.connection ?? nav.mozConnection ?? nav.webkitConnection;
  if (!conn) {
    return null;
  }
  return {
    effectiveType: conn.effectiveType,
    downlink: conn.downlink,
    saveData: conn.saveData,
  };
}

/**
 * Build the `GET /be_resizer/upload_config` query string from connection hints,
 * mirroring the server's expected params (`effective_type`, `downlink`,
 * `save_data`). Pure, so it is unit-testable.
 */
export function buildUploadConfigQuery(conn: ConnectionInfo | null): string {
  const params = new URLSearchParams();
  if (conn?.effectiveType) {
    params.set("effective_type", conn.effectiveType);
  }
  if (typeof conn?.downlink === "number") {
    params.set("downlink", String(conn.downlink));
  }
  if (conn?.saveData) {
    params.set("save_data", "true");
  }
  return params.toString();
}
