import { useState, type FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";

import { AuthAlert, AuthCard, FieldError, authInputClass, authLabelClass, authSubmitClass } from "../components/AuthCard";
import { ApiError } from "../lib/apiClient";
import { resetPassword } from "../lib/authApi";
import { isValid, validateResetForm, type ResetErrors } from "../lib/authValidation";

/**
 * SPA reset-password page (Phase 3.8). The reset token is read from the URL
 * query (`?token=…`), matching the link the backend emails
 * (`{frontend_url}/reset-password?token=…`). Client-side validation mirrors the
 * Jinja reset page (password policy + confirmation match); the token itself is
 * validated server-side. Mounted OUTSIDE `RequireAuth`/`Layout`; the
 * server-rendered `/reset-password` page keeps working during the strangler
 * migration.
 */
export function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";

  const [values, setValues] = useState({ new_password: "", confirm_password: "" });
  const [errors, setErrors] = useState<ResetErrors>({});

  const mutation = useMutation({
    mutationFn: () => resetPassword(token, values.new_password),
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const validation = validateResetForm(values);
    setErrors(validation);
    if (!isValid(validation)) return;
    mutation.mutate();
  }

  const serverError = mutation.error instanceof ApiError ? mutation.error.message : null;

  const footer = (
    <p className="text-center text-sm text-slate-600 dark:text-gray-400">
      <Link to="/login" className="font-medium text-sky-600 hover:text-sky-700 dark:text-sky-400">
        Retour à la connexion
      </Link>
    </p>
  );

  // No token in the URL → the link is malformed; guide the user back.
  if (!token) {
    return (
      <AuthCard subtitle="Réinitialisation" footer={footer}>
        <AuthAlert variant="error">
          Lien de réinitialisation invalide ou incomplet. Veuillez redemander un lien.
        </AuthAlert>
      </AuthCard>
    );
  }

  if (mutation.isSuccess) {
    return (
      <AuthCard subtitle="Réinitialisation" footer={footer}>
        <AuthAlert variant="success">
          Votre mot de passe a été réinitialisé. Vous pouvez maintenant vous connecter.
        </AuthAlert>
      </AuthCard>
    );
  }

  return (
    <AuthCard subtitle="Réinitialisation" intro="Choisissez un nouveau mot de passe." footer={footer}>
      {serverError ? <AuthAlert variant="error">{serverError}</AuthAlert> : null}

      <form onSubmit={handleSubmit} className="space-y-5" noValidate>
        <div>
          <label htmlFor="new_password" className={authLabelClass}>
            Nouveau mot de passe
          </label>
          <input
            id="new_password"
            type="password"
            autoComplete="new-password"
            placeholder="••••••••"
            value={values.new_password}
            onChange={(e) => setValues((v) => ({ ...v, new_password: e.target.value }))}
            className={authInputClass}
            autoFocus
          />
          <FieldError message={errors.new_password} />
        </div>

        <div>
          <label htmlFor="confirm_password" className={authLabelClass}>
            Confirmer le mot de passe
          </label>
          <input
            id="confirm_password"
            type="password"
            autoComplete="new-password"
            placeholder="••••••••"
            value={values.confirm_password}
            onChange={(e) => setValues((v) => ({ ...v, confirm_password: e.target.value }))}
            className={authInputClass}
          />
          <FieldError message={errors.confirm_password} />
        </div>

        <button type="submit" className={authSubmitClass} disabled={mutation.isPending}>
          {mutation.isPending ? "Réinitialisation…" : "Réinitialiser le mot de passe"}
        </button>
      </form>
    </AuthCard>
  );
}
