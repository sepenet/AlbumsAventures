// Pure, DOM-free helpers for the album create/edit forms.
//
// Kept framework-free (like `lib/admin.ts`, `lib/shared.ts`) so every transform,
// validation rule, and submit-orchestration path is unit-testable in the node
// vitest environment without a DOM. The React pages (`AlbumCreatePage`,
// `AlbumEditPage`) are thin views over these functions.
//
// Field parity mirrors the retired Jinja forms (album_form.html / album_edit.html):
// participants/tags are entered comma-separated in the UI ("Web" form) but stored
// pipe-separated in the DB ("DB" form).

import type { AlbumDetail } from "../types/api";

export const TITLE_MAX = 50;
export const TEXT_MAX = 512;
export const CATEGORY_NAME_MIN = 3;
export const CATEGORY_NAME_MAX = 128;

/** Controlled form state (all strings — `category_id` is the `<select>` value). */
export interface AlbumFormValues {
  title: string;
  description: string;
  category_id: string;
  date: string;
  participants: string;
  location: string;
  tags: string;
}

/** Payload sent to `POST create_album/` (AlbumCreate) / `PATCH update_album/{id}` (AlbumUpdate). */
export interface AlbumWritePayload {
  title: string;
  description: string | null;
  category_id: number;
  date: string;
  participants: string | null;
  location: string | null;
  tags: string | null;
  image_cover: string | null;
}

/** Web (comma) -> DB (pipe): "Jean, Marie" -> "Jean|Marie". Empty -> "". */
export function toDbList(web: string): string {
  return web
    .split(",")
    .map((part) => part.trim())
    .filter(Boolean)
    .join("|");
}

/** DB (pipe) -> Web (comma): "Jean|Marie" -> "Jean, Marie". null/empty -> "". */
export function toWebList(db: string | null | undefined): string {
  if (!db) return "";
  return db
    .split("|")
    .map((part) => part.trim())
    .filter(Boolean)
    .join(", ");
}

/** Empty/whitespace string -> null (so optional text fields clear to NULL server-side). */
function orNull(value: string): string | null {
  const trimmed = value.trim();
  return trimmed === "" ? null : trimmed;
}

/** Blank starting values, `date` defaulting to today (YYYY-MM-DD). */
export function emptyAlbumForm(today: string = new Date().toISOString().split("T")[0]): AlbumFormValues {
  return {
    title: "",
    description: "",
    category_id: "",
    date: today,
    participants: "",
    location: "",
    tags: "",
  };
}

/** Prefill form state from an album read (`GET get_album_by_id/{id}`), DB->Web. */
export function toFormValues(album: AlbumDetail): AlbumFormValues {
  return {
    title: album.title ?? "",
    description: album.description ?? "",
    category_id: String(album.category_id),
    date: album.date,
    participants: toWebList(album.participants),
    location: album.location ?? "",
    tags: toWebList(album.tags),
  };
}

/** Build the create/update payload: pipe-join lists, empty text -> null. */
export function toWritePayload(values: AlbumFormValues): AlbumWritePayload {
  return {
    title: values.title.trim(),
    description: orNull(values.description),
    category_id: Number(values.category_id),
    date: values.date,
    participants: toDbList(values.participants) || null,
    location: orNull(values.location),
    tags: toDbList(values.tags) || null,
    image_cover: null,
  };
}

export type AlbumFieldError =
  | "title"
  | "category_id"
  | "date"
  | "participants"
  | "location"
  | "tags";

export type AlbumFormErrors = Partial<Record<AlbumFieldError, string>>;

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

/** Field-level validation mirroring the Jinja/schema constraints. */
export function validateAlbumForm(values: AlbumFormValues): AlbumFormErrors {
  const errors: AlbumFormErrors = {};

  const title = values.title.trim();
  if (title.length === 0) {
    errors.title = "Le titre est obligatoire.";
  } else if (title.length > TITLE_MAX) {
    errors.title = `Le titre ne peut pas dépasser ${TITLE_MAX} caractères.`;
  }

  if (!values.category_id || Number.isNaN(Number(values.category_id))) {
    errors.category_id = "La catégorie est obligatoire.";
  }

  if (!values.date || !ISO_DATE.test(values.date)) {
    errors.date = "La date est obligatoire (AAAA-MM-JJ).";
  }

  if (values.participants.length > TEXT_MAX) {
    errors.participants = `Champ trop long (max ${TEXT_MAX} caractères).`;
  }
  if (values.location.length > TEXT_MAX) {
    errors.location = `Champ trop long (max ${TEXT_MAX} caractères).`;
  }
  if (values.tags.length > TEXT_MAX) {
    errors.tags = `Champ trop long (max ${TEXT_MAX} caractères).`;
  }

  return errors;
}

export function isAlbumFormValid(values: AlbumFormValues): boolean {
  return Object.keys(validateAlbumForm(values)).length === 0;
}

/** Category-create modal name validation (min 3 / max 128). Returns an error string or null. */
export function validateCategoryName(name: string): string | null {
  const trimmed = name.trim();
  if (trimmed.length < CATEGORY_NAME_MIN) {
    return `Le nom doit contenir au moins ${CATEGORY_NAME_MIN} caractères.`;
  }
  if (trimmed.length > CATEGORY_NAME_MAX) {
    return `Le nom ne peut pas dépasser ${CATEGORY_NAME_MAX} caractères.`;
  }
  return null;
}

// ---------------------------------------------------------------------------
// Submit orchestration (pure — accepts injected client callables).
// ---------------------------------------------------------------------------

export interface CreateAlbumDeps {
  createAlbum: (payload: AlbumWritePayload) => Promise<{ id: number }>;
  createFolder: (albumId: number) => Promise<unknown>;
  uploadCover: (albumId: number, cover: File) => Promise<unknown>;
}

export type CreateAlbumOutcome =
  | { status: "created"; albumId: number }
  // Album row exists but a post-create step failed: surface the id so the caller
  // routes to the EDIT page (orphan handling) instead of reporting a total failure.
  | { status: "partial"; albumId: number; failedStep: "folder" | "cover"; error: unknown };

/**
 * Create flow: `create_album` -> `create_album_folder/{id}` (POST) -> optional
 * `upload_cover/{id}`. If `create_album` itself throws, the error propagates (no
 * album was created, so the caller shows the error and stays on the form). If a
 * step AFTER creation fails, the album id is returned so the caller can route to
 * the edit page. Folder/cover steps are individually idempotent server-side.
 */
export async function runCreateAlbum(
  payload: AlbumWritePayload,
  cover: File | null,
  deps: CreateAlbumDeps,
): Promise<CreateAlbumOutcome> {
  const album = await deps.createAlbum(payload);

  try {
    await deps.createFolder(album.id);
  } catch (error) {
    return { status: "partial", albumId: album.id, failedStep: "folder", error };
  }

  if (cover) {
    try {
      await deps.uploadCover(album.id, cover);
    } catch (error) {
      return { status: "partial", albumId: album.id, failedStep: "cover", error };
    }
  }

  return { status: "created", albumId: album.id };
}

export interface UpdateAlbumDeps {
  updateAlbum: (albumId: number, payload: AlbumWritePayload) => Promise<unknown>;
  uploadCover: (albumId: number, cover: File) => Promise<unknown>;
}

export type UpdateAlbumOutcome =
  | { status: "saved" }
  | { status: "cover_failed"; error: unknown };

/**
 * Edit flow: `PATCH update_album/{id}` (dir rename preserved server-side) ->
 * optional `upload_cover/{id}`. An `update_album` failure propagates; a cover
 * failure is reported separately (the metadata edit already succeeded).
 */
export async function runUpdateAlbum(
  albumId: number,
  payload: AlbumWritePayload,
  cover: File | null,
  deps: UpdateAlbumDeps,
): Promise<UpdateAlbumOutcome> {
  await deps.updateAlbum(albumId, payload);

  if (cover) {
    try {
      await deps.uploadCover(albumId, cover);
    } catch (error) {
      return { status: "cover_failed", error };
    }
  }

  return { status: "saved" };
}
