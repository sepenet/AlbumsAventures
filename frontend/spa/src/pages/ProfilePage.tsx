import { useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { useSession } from "../auth/useSession";
import { ApiError, api } from "../lib/apiClient";
import {
  isValid,
  validatePasswordForm,
  validateProfileForm,
  type PasswordErrors,
  type PasswordFormValues,
  type ProfileErrors,
  type ProfileFormValues,
} from "../lib/profileValidation";

const EMPTY_PASSWORD: PasswordFormValues = {
  current_password: "",
  new_password: "",
  confirm_password: "",
};

const inputClass =
  "w-full rounded-lg border border-gray-300 bg-white px-4 py-2 text-gray-900 focus:border-transparent focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100";

const labelClass = "mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300";

const fieldErrorClass = "mt-1 text-sm text-red-600 dark:text-red-400";

/**
 * React profile page (Phase 3.5 strangler variant of frontend/templates/profile.html).
 *
 * Serves the `/app/profile` route. Prefills the "informations personnelles"
 * form from the cookie-backed session (`GET /be_auth/me`, via useSession) and
 * exposes the same two sections as the Jinja page: profile update and password
 * change. Both mutations go through the shared apiClient, which sends the
 * HttpOnly session cookie same-origin and echoes the CSRF double-submit token
 * on PUT — no token is stored in JS. Client-side validation (including the
 * password-mismatch check) mirrors the Jinja page; the server re-validates.
 *
 * The Jinja `/profile` page stays live during the migration; this is the
 * additive `/app` variant.
 */
export function ProfilePage() {
  const { data: user } = useSession();

  const [profileForm, setProfileForm] = useState<ProfileFormValues>({
    firstname: "",
    lastname: "",
    email: "",
  });
  const [profileErrors, setProfileErrors] = useState<ProfileErrors>({});

  const [passwordForm, setPasswordForm] = useState<PasswordFormValues>(EMPTY_PASSWORD);
  const [passwordErrors, setPasswordErrors] = useState<PasswordErrors>({});

  // Prefill the profile form once the session resolves (parity with the Jinja
  // page's Alpine `init()`).
  useEffect(() => {
    if (user) {
      setProfileForm({
        firstname: user.firstname ?? "",
        lastname: user.lastname ?? "",
        email: user.email ?? "",
      });
    }
  }, [user]);

  const profileMutation = useMutation({
    mutationFn: (values: ProfileFormValues) =>
      api.put<{ message: string }>("/be_auth/update_profile", values),
  });

  const passwordMutation = useMutation({
    mutationFn: (values: PasswordFormValues) =>
      api.put<{ message: string }>("/be_auth/update_password", {
        current_password: values.current_password,
        new_password: values.new_password,
      }),
    onSuccess: () => {
      setPasswordForm(EMPTY_PASSWORD);
    },
  });

  function submitProfile(event: React.FormEvent) {
    event.preventDefault();
    profileMutation.reset();
    const errors = validateProfileForm(profileForm);
    setProfileErrors(errors);
    if (isValid(errors)) {
      profileMutation.mutate(profileForm);
    }
  }

  function submitPassword(event: React.FormEvent) {
    event.preventDefault();
    passwordMutation.reset();
    const errors = validatePasswordForm(passwordForm);
    setPasswordErrors(errors);
    if (isValid(errors)) {
      passwordMutation.mutate(passwordForm);
    }
  }

  const profileErrorMessage =
    profileMutation.error instanceof ApiError
      ? profileMutation.error.message
      : profileMutation.isError
        ? "Erreur lors de la mise à jour du profil"
        : null;

  const passwordErrorMessage =
    passwordMutation.error instanceof ApiError
      ? passwordMutation.error.message
      : passwordMutation.isError
        ? "Erreur lors du changement de mot de passe"
        : null;

  return (
    <div className="mx-auto max-w-2xl py-8">
      <div className="mb-8">
        <h1 className="mb-2 bg-gradient-to-r from-sky-500 to-blue-600 bg-clip-text text-3xl font-bold text-transparent">
          Mon profil
        </h1>
        <p className="text-gray-600 dark:text-gray-400">
          Gérez vos informations personnelles et votre mot de passe
        </p>
      </div>

      {/* Informations personnelles */}
      <section className="mb-6 rounded-xl border border-gray-200 bg-white shadow-lg dark:border-gray-700 dark:bg-gray-800">
        <div className="border-b border-gray-200 px-6 py-4 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Informations personnelles
          </h2>
        </div>
        <form onSubmit={submitProfile} className="space-y-4 p-6" noValidate>
          {profileMutation.isSuccess ? (
            <p
              role="status"
              className="rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700 dark:border-green-800 dark:bg-green-900/20 dark:text-green-300"
            >
              Profil mis à jour avec succès
            </p>
          ) : null}
          {profileErrorMessage ? (
            <p
              role="alert"
              className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300"
            >
              {profileErrorMessage}
            </p>
          ) : null}

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <label htmlFor="firstname" className={labelClass}>
                Prénom
              </label>
              <input
                id="firstname"
                type="text"
                value={profileForm.firstname}
                onChange={(event) =>
                  setProfileForm((form) => ({ ...form, firstname: event.target.value }))
                }
                className={inputClass}
              />
              {profileErrors.firstname ? (
                <p className={fieldErrorClass}>{profileErrors.firstname}</p>
              ) : null}
            </div>
            <div>
              <label htmlFor="lastname" className={labelClass}>
                Nom
              </label>
              <input
                id="lastname"
                type="text"
                value={profileForm.lastname}
                onChange={(event) =>
                  setProfileForm((form) => ({ ...form, lastname: event.target.value }))
                }
                className={inputClass}
              />
              {profileErrors.lastname ? (
                <p className={fieldErrorClass}>{profileErrors.lastname}</p>
              ) : null}
            </div>
          </div>

          <div>
            <label htmlFor="email" className={labelClass}>
              Email
            </label>
            <input
              id="email"
              type="email"
              value={profileForm.email}
              onChange={(event) =>
                setProfileForm((form) => ({ ...form, email: event.target.value }))
              }
              className={inputClass}
            />
            {profileErrors.email ? <p className={fieldErrorClass}>{profileErrors.email}</p> : null}
          </div>

          <div className="pt-2">
            <button
              type="submit"
              disabled={profileMutation.isPending}
              className="inline-flex items-center rounded-lg bg-sky-600 px-4 py-2 font-medium text-white transition-colors hover:bg-sky-700 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:ring-offset-2 disabled:bg-sky-400"
            >
              {profileMutation.isPending ? "Enregistrement…" : "Enregistrer les modifications"}
            </button>
          </div>
        </form>
      </section>

      {/* Changement de mot de passe */}
      <section className="rounded-xl border border-gray-200 bg-white shadow-lg dark:border-gray-700 dark:bg-gray-800">
        <div className="border-b border-gray-200 px-6 py-4 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Changer le mot de passe
          </h2>
        </div>
        <form onSubmit={submitPassword} className="space-y-4 p-6" noValidate>
          {passwordMutation.isSuccess ? (
            <p
              role="status"
              className="rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700 dark:border-green-800 dark:bg-green-900/20 dark:text-green-300"
            >
              Mot de passe modifié avec succès
            </p>
          ) : null}
          {passwordErrorMessage ? (
            <p
              role="alert"
              className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300"
            >
              {passwordErrorMessage}
            </p>
          ) : null}

          <div>
            <label htmlFor="current_password" className={labelClass}>
              Mot de passe actuel
            </label>
            <input
              id="current_password"
              type="password"
              autoComplete="current-password"
              value={passwordForm.current_password}
              onChange={(event) =>
                setPasswordForm((form) => ({ ...form, current_password: event.target.value }))
              }
              className={inputClass}
            />
            {passwordErrors.current_password ? (
              <p className={fieldErrorClass}>{passwordErrors.current_password}</p>
            ) : null}
          </div>

          <div>
            <label htmlFor="new_password" className={labelClass}>
              Nouveau mot de passe
            </label>
            <input
              id="new_password"
              type="password"
              autoComplete="new-password"
              value={passwordForm.new_password}
              onChange={(event) =>
                setPasswordForm((form) => ({ ...form, new_password: event.target.value }))
              }
              className={inputClass}
            />
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              Minimum 8 caractères avec au moins une minuscule, une majuscule et un chiffre
            </p>
            {passwordErrors.new_password ? (
              <p className={fieldErrorClass}>{passwordErrors.new_password}</p>
            ) : null}
          </div>

          <div>
            <label htmlFor="confirm_password" className={labelClass}>
              Confirmer le nouveau mot de passe
            </label>
            <input
              id="confirm_password"
              type="password"
              autoComplete="new-password"
              value={passwordForm.confirm_password}
              onChange={(event) =>
                setPasswordForm((form) => ({ ...form, confirm_password: event.target.value }))
              }
              className={inputClass}
            />
            {passwordErrors.confirm_password ? (
              <p className={fieldErrorClass}>{passwordErrors.confirm_password}</p>
            ) : null}
          </div>

          <div className="pt-2">
            <button
              type="submit"
              disabled={passwordMutation.isPending}
              className="inline-flex items-center rounded-lg bg-sky-600 px-4 py-2 font-medium text-white transition-colors hover:bg-sky-700 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:ring-offset-2 disabled:bg-sky-400"
            >
              {passwordMutation.isPending ? "Modification…" : "Changer le mot de passe"}
            </button>
          </div>
        </form>
      </section>

      <div className="mt-6 text-center">
        <Link to="/" className="text-sm text-sky-600 hover:underline dark:text-sky-400">
          ← Retour aux albums
        </Link>
      </div>
    </div>
  );
}
