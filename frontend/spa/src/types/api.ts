// Shared API types mirroring the FastAPI `be_*` response schemas
// (backend/db/schemas.py). Kept intentionally narrow: only the fields the SPA
// consumes are typed.

/** Mirrors `schemas.UserAdmin` returned by `GET /be_auth/me`. */
export interface SessionUser {
  id: number;
  email: string;
  firstname: string;
  lastname: string;
  is_active: boolean;
  is_superuser: boolean;
}

/** Mirrors `schemas.Album_Category_WithCoverUrl` from `be_album`. */
export interface Album {
  id: number;
  title: string;
  description: string | null;
  category_id: number;
  /** ISO date string (YYYY-MM-DD). */
  date: string;
  participants: string | null;
  location: string | null;
  tags: string | null;
  image_cover: string | null;
  category: string;
  image_cover_url: string | null;
}

/** Mirrors `schemas.Category` from `be_category`. */
export interface Category {
  id: number;
  category: string;
}

/**
 * Mirrors `schemas.Album_Category` returned by
 * `GET /be_album/get_album_by_id/{album_id}` (album-detail view).
 *
 * Unlike {@link Album}, this schema does NOT include `image_cover_url` — the
 * detail page renders the media gallery rather than a single cover URL.
 */
export interface AlbumDetail {
  id: number;
  title: string;
  description: string | null;
  category_id: number;
  /** ISO date string (YYYY-MM-DD). */
  date: string;
  participants: string | null;
  location: string | null;
  tags: string | null;
  /** Cover filename (used for the "current cover" badge), not a URL. */
  image_cover: string | null;
  category: string;
}

/**
 * A single media file (image or video) as returned by the browser-facing
 * `GET /album/{album_id}/images` JSON endpoint. URLs point at the `/images`
 * and `/thumbnails` static mounts.
 */
export interface MediaItem {
  filename: string;
  thumbnail_url: string;
  full_url: string;
  is_video: boolean;
  has_thumbnail: boolean;
  width: number | null;
  height: number | null;
}

/** One paginated page of album media (`GET /album/{album_id}/images`). */
export interface AlbumMediaPage {
  items: MediaItem[];
  total: number;
  has_more: boolean;
}

/**
 * Server-authoritative upload configuration from
 * `GET /be_resizer/upload_config` (backend/routers/be_resizer.py). The server
 * computes `chunk_size` from the client's Network Information hints but never
 * returns a value below `chunk_size_floor` (256 KB) nor above
 * `chunk_size_ceiling` (8 MB), so the client can trust it while still clamping
 * defensively.
 */
export interface UploadConfig {
  chunk_size: number;
  chunk_size_floor: number;
  chunk_size_ceiling: number;
  retry_delays: number[];
  limit: number;
}

/**
 * Durable per-file thumbnail-processing status as returned in the `files` array
 * of `GET /be_resizer/processing_status/{album_id}`. Thumbnails are generated in
 * a bounded worker pool AFTER the TUS 204, so this endpoint surfaces whether a
 * given upload's thumbnail is pending, in progress, done, skipped, or failed.
 */
export interface ProcessingFile {
  filename: string;
  media_type: string | null;
  status: "pending" | "processing" | "success" | "failed" | "skipped";
  detail: string | null;
  updated_at: string | null;
}

/** Aggregate counts by status (`summary` of `processing_status`). */
export interface ProcessingSummary {
  pending: number;
  processing: number;
  success: number;
  failed: number;
  skipped: number;
}

/** Full response of `GET /be_resizer/processing_status/{album_id}`. */
export interface ProcessingStatusResponse {
  album_id: number;
  summary: ProcessingSummary;
  files: ProcessingFile[];
}

/** Mirrors `schemas.UserAdmin` in the admin user list (`GET /be_auth/admin/users`). */
export interface AdminUser {
  id: number;
  email: string;
  firstname: string;
  lastname: string;
  is_active: boolean;
  is_superuser: boolean;
}

/** Body of `PUT /be_auth/admin/users/{id}/rights` (`schemas.UserRightsUpdate`). */
export interface UserRightsUpdate {
  is_active?: boolean;
  is_superuser?: boolean;
}

/** Mirrors `schemas.Group` from `be_group`. */
export interface Group {
  id: number;
  name: string;
  description: string | null;
}

/** Compact user for admin dropdowns (`GET /be_group/get_all_users_simple/`). */
export interface SimpleUser {
  id: number;
  firstname: string;
  lastname: string;
}

/** Compact album for admin dropdowns (`GET /be_group/get_all_albums_simple/`). */
export interface SimpleAlbum {
  id: number;
  title: string;
  date: string;
  image_cover_url: string | null;
}

/**
 * A user as returned inside `get_group_details` (`users` array): includes the
 * membership fields the admin panel renders.
 */
export interface GroupMemberUser {
  id: number;
  firstname: string;
  lastname: string;
  email?: string;
}

/** An album as returned inside `get_group_details` (`albums` array). */
export interface GroupAlbum {
  id: number;
  title: string;
  date: string;
  image_cover: string | null;
  image_cover_url: string | null;
}

/** Full response of `GET /be_group/get_group_details/{group_id}`. */
export interface GroupDetails {
  group: Group;
  users: GroupMemberUser[];
  albums: GroupAlbum[];
}
