import { useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { ApiError, api } from "../lib/apiClient";
import {
  emptyAlbumForm,
  runCreateAlbum,
  toWritePayload,
  validateAlbumForm,
  validateCategoryName,
  type AlbumFormValues,
} from "../lib/albumForm";
import type { Album, Category } from "../types/api";

const cardClass =
  "rounded-xl border border-gray-200 bg-white shadow-lg dark:border-gray-700 dark:bg-gray-800";
const inputClass =
  "w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-gray-900 focus:border-transparent focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100";
const labelClass = "mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300";
const primaryBtn =
  "inline-flex items-center justify-center rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-sky-700 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:ring-offset-2 disabled:bg-sky-400";
const secondaryBtn =
  "inline-flex items-center justify-center rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm text-gray-700 transition-colors hover:bg-gray-100 disabled:opacity-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700";

function errorText(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback;
}

function FieldError({ message }: { message?: string }) {
  if (!message) return null;
  return <p className="mt-1 text-sm text-red-600 dark:text-red-400">{message}</p>;
}

/**
 * SPA-native album creation (`/app/album/new`, superuser-only). Replaces the
 * retired Jinja `album_form.html`. Flow: `POST create_album/` -> `POST
 * create_album_folder/{id}` -> optional `POST upload_cover/{id}` -> navigate to
 * /admin. On a post-create failure the created album id is surfaced and the user
 * is routed to the EDIT page (orphan handling) rather than reporting total
 * failure. The backend auto-links the new album to the canonical `all_albums`
 * group, so no client-side group link is replicated here.
 */
export function AlbumCreatePage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [values, setValues] = useState<AlbumFormValues>(() => emptyAlbumForm());
  const [showErrors, setShowErrors] = useState(false);
  const [cover, setCover] = useState<File | null>(null);
  const [coverPreview, setCoverPreview] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Category modal state (create-only affordance, parity with Jinja modal).
  const [modalOpen, setModalOpen] = useState(false);
  const [newCategoryName, setNewCategoryName] = useState("");
  const [categoryError, setCategoryError] = useState<string | null>(null);

  const categoriesQuery = useQuery<Category[]>({
    queryKey: ["categories"],
    queryFn: () => api.get<Category[]>("/be_category/get_all_categories/"),
  });
  const categories = useMemo(() => categoriesQuery.data ?? [], [categoriesQuery.data]);

  const errors = validateAlbumForm(values);

  function setField<K extends keyof AlbumFormValues>(key: K, value: AlbumFormValues[K]) {
    setValues((form) => ({ ...form, [key]: value }));
  }

  function handleCoverFile(file: File | null) {
    setCover(file);
    if (!file) {
      setCoverPreview(null);
      return;
    }
    const reader = new FileReader();
    reader.onload = () => setCoverPreview(typeof reader.result === "string" ? reader.result : null);
    reader.readAsDataURL(file);
  }

  const createCategory = useMutation({
    mutationFn: (name: string) => api.post<Category>("/be_category/create_category/", { category: name }),
    onSuccess: (created) => {
      queryClient.invalidateQueries({ queryKey: ["categories"] });
      setField("category_id", String(created.id));
      setModalOpen(false);
      setNewCategoryName("");
      setCategoryError(null);
    },
    onError: (error) => setCategoryError(errorText(error, "Erreur lors de la création de la catégorie")),
  });

  const submit = useMutation({
    mutationFn: () =>
      runCreateAlbum(toWritePayload(values), cover, {
        createAlbum: (payload) => api.post<Album>("/be_album/create_album/", payload),
        createFolder: (albumId) => api.postForm(`/be_album/create_album_folder/${albumId}`, new FormData()),
        uploadCover: (albumId, file) => {
          const fd = new FormData();
          fd.append("image_cover", file);
          return api.postForm(`/be_album/upload_cover/${albumId}`, fd);
        },
      }),
    onSuccess: (outcome) => {
      queryClient.invalidateQueries({ queryKey: ["albums"] });
      if (outcome.status === "created") {
        navigate("/admin");
      } else {
        // Orphan handling: the album row exists but a post-create step failed —
        // route to the edit page with the created id so it can be completed.
        setSubmitError(
          `L'album a été créé (n°${outcome.albumId}) mais une étape (${
            outcome.failedStep === "folder" ? "dossier" : "couverture"
          }) a échoué. Vous pouvez la terminer depuis la page d'édition.`,
        );
        navigate(`/album/${outcome.albumId}/edit`);
      }
    },
    onError: (error) => setSubmitError(errorText(error, "Erreur lors de la création de l'album")),
  });

  function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setSubmitError(null);
    setShowErrors(true);
    if (Object.keys(validateAlbumForm(values)).length > 0) return;
    submit.reset();
    submit.mutate();
  }

  function confirmCreateCategory() {
    const validationError = validateCategoryName(newCategoryName);
    if (validationError) {
      setCategoryError(validationError);
      return;
    }
    createCategory.reset();
    createCategory.mutate(newCategoryName.trim());
  }

  return (
    <div className="mx-auto max-w-2xl py-4">
      <h1 className="mb-6 text-2xl font-bold text-gray-900 dark:text-gray-100">Créer un album</h1>

      <form onSubmit={onSubmit} className={`${cardClass} space-y-5 p-6`} noValidate>
        {submitError ? (
          <p role="alert" className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300">
            {submitError}
          </p>
        ) : null}

        <div>
          <label htmlFor="album-title" className={labelClass}>
            Titre <span className="text-red-500">*</span>
          </label>
          <input
            id="album-title"
            type="text"
            maxLength={50}
            value={values.title}
            onChange={(event) => setField("title", event.target.value)}
            className={inputClass}
          />
          {showErrors ? <FieldError message={errors.title} /> : null}
        </div>

        <div>
          <label htmlFor="album-description" className={labelClass}>
            Description
          </label>
          <textarea
            id="album-description"
            rows={3}
            value={values.description}
            onChange={(event) => setField("description", event.target.value)}
            className={inputClass}
          />
        </div>

        <div>
          <label htmlFor="album-category" className={labelClass}>
            Catégorie <span className="text-red-500">*</span>
          </label>
          <div className="flex gap-2">
            <select
              id="album-category"
              value={values.category_id}
              onChange={(event) => setField("category_id", event.target.value)}
              className={inputClass}
            >
              <option value="" disabled>
                {categoriesQuery.isPending ? "Chargement…" : "Sélectionner une catégorie"}
              </option>
              {categories.map((category) => (
                <option key={category.id} value={String(category.id)}>
                  {category.category}
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={() => {
                setCategoryError(null);
                setModalOpen(true);
              }}
              className={secondaryBtn}
            >
              + Catégorie
            </button>
          </div>
          {showErrors ? <FieldError message={errors.category_id} /> : null}
        </div>

        <div>
          <label htmlFor="album-date" className={labelClass}>
            Date <span className="text-red-500">*</span>
          </label>
          <input
            id="album-date"
            type="date"
            value={values.date}
            onChange={(event) => setField("date", event.target.value)}
            className={inputClass}
          />
          {showErrors ? <FieldError message={errors.date} /> : null}
        </div>

        <div>
          <label htmlFor="album-participants" className={labelClass}>
            Participants (séparés par des virgules)
          </label>
          <input
            id="album-participants"
            type="text"
            maxLength={512}
            value={values.participants}
            onChange={(event) => setField("participants", event.target.value)}
            className={inputClass}
          />
          {showErrors ? <FieldError message={errors.participants} /> : null}
        </div>

        <div>
          <label htmlFor="album-location" className={labelClass}>
            Lieu
          </label>
          <input
            id="album-location"
            type="text"
            maxLength={512}
            value={values.location}
            onChange={(event) => setField("location", event.target.value)}
            className={inputClass}
          />
          {showErrors ? <FieldError message={errors.location} /> : null}
        </div>

        <div>
          <label htmlFor="album-tags" className={labelClass}>
            Tags (séparés par des virgules)
          </label>
          <input
            id="album-tags"
            type="text"
            maxLength={512}
            value={values.tags}
            onChange={(event) => setField("tags", event.target.value)}
            className={inputClass}
          />
          {showErrors ? <FieldError message={errors.tags} /> : null}
        </div>

        <div>
          <label className={labelClass}>Image de couverture (optionnel)</label>
          <div
            onDragOver={(event) => {
              event.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(event) => {
              event.preventDefault();
              setDragOver(false);
              handleCoverFile(event.dataTransfer.files?.[0] ?? null);
            }}
            className={`flex flex-col items-center gap-3 rounded-lg border-2 border-dashed p-4 text-center ${
              dragOver ? "border-sky-500 bg-sky-50 dark:bg-sky-900/20" : "border-gray-300 dark:border-gray-600"
            }`}
          >
            {coverPreview ? (
              <img src={coverPreview} alt="Aperçu de la couverture" className="max-h-48 rounded-lg object-contain" />
            ) : (
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Glissez-déposez une image ou cliquez pour choisir un fichier.
              </p>
            )}
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={(event) => handleCoverFile(event.target.files?.[0] ?? null)}
              className="hidden"
            />
            <div className="flex gap-2">
              <button type="button" onClick={() => fileInputRef.current?.click()} className={secondaryBtn}>
                Choisir une image
              </button>
              {cover ? (
                <button
                  type="button"
                  onClick={() => {
                    handleCoverFile(null);
                    if (fileInputRef.current) fileInputRef.current.value = "";
                  }}
                  className={secondaryBtn}
                >
                  Retirer
                </button>
              ) : null}
            </div>
          </div>
        </div>

        <div className="flex justify-end gap-3 border-t border-gray-200 pt-4 dark:border-gray-700">
          <button type="button" onClick={() => navigate("/admin")} className={secondaryBtn}>
            Annuler
          </button>
          <button type="submit" disabled={submit.isPending} className={primaryBtn}>
            {submit.isPending ? "Création…" : "Créer l'album"}
          </button>
        </div>
      </form>

      {modalOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className={`${cardClass} w-full max-w-md space-y-4 p-6`} role="dialog" aria-modal="true">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Nouvelle catégorie</h2>
            <div>
              <label htmlFor="new-category" className={labelClass}>
                Nom de la catégorie
              </label>
              <input
                id="new-category"
                type="text"
                value={newCategoryName}
                onChange={(event) => setNewCategoryName(event.target.value)}
                className={inputClass}
              />
              {categoryError ? <FieldError message={categoryError} /> : null}
            </div>
            <div className="flex justify-end gap-3">
              <button
                type="button"
                onClick={() => {
                  setModalOpen(false);
                  setCategoryError(null);
                }}
                className={secondaryBtn}
              >
                Annuler
              </button>
              <button
                type="button"
                onClick={confirmCreateCategory}
                disabled={createCategory.isPending}
                className={primaryBtn}
              >
                {createCategory.isPending ? "Création…" : "Créer"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
