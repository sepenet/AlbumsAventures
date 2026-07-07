import { useState, type FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { AuthAlert, AuthCard, FieldError, authInputClass, authLabelClass, authSubmitClass } from "../components/AuthCard";
import { ApiError } from "../lib/apiClient";
import { forgotPassword } from "../lib/authApi";
import { isValid, validateForgotForm, type ForgotErrors } from "../lib/authValidation";

/**
 * SPA forgot-password page (Phase 3.8). Sends a reset-link request
 * (`POST /be_auth/forgot-password`). The backend always returns the same
 * neutral acknowledgement whether or not the email exists (anti-enumeration),
 * so the page shows that neutral message on success. Mounted OUTSIDE
 * `RequireAuth`/`Layout`; the server-rendered `/forgot-password` page keeps
 * working during the strangler migration.
 */
export function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [errors, setErrors] = useState<ForgotErrors>({});

  const mutation = useMutation({
    mutationFn: () => forgotPassword(email),
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const validation = validateForgotForm({ email });
    setErrors(validation);
    if (!isValid(validation)) return;
    mutation.mutate();
  }

  const serverError = mutation.error instanceof ApiError ? mutation.error.message : null;

  return (
    <AuthCard
      subtitle="Mot de passe oublié"
      intro="Saisissez votre adresse email ; si un compte y est associé, vous recevrez un lien de réinitialisation."
      footer={
        <p className="text-center text-sm text-slate-600 dark:text-gray-400">
          <Link to="/login" className="font-medium text-sky-600 hover:text-sky-700 dark:text-sky-400">
            Retour à la connexion
          </Link>
        </p>
      }
    >
      {mutation.isSuccess ? (
        <AuthAlert variant="success">
          {mutation.data?.message ??
            "Si cette adresse email est associée à un compte, vous recevrez un lien de réinitialisation."}
        </AuthAlert>
      ) : null}
      {serverError ? <AuthAlert variant="error">{serverError}</AuthAlert> : null}

      {!mutation.isSuccess ? (
        <form onSubmit={handleSubmit} className="space-y-5" noValidate>
          <div>
            <label htmlFor="email" className={authLabelClass}>
              Email
            </label>
            <input
              id="email"
              name="email"
              type="email"
              autoComplete="email"
              placeholder="votre.email@exemple.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className={authInputClass}
              autoFocus
            />
            <FieldError message={errors.email} />
          </div>

          <button type="submit" className={authSubmitClass} disabled={mutation.isPending}>
            {mutation.isPending ? "Envoi…" : "Envoyer le lien"}
          </button>
        </form>
      ) : null}
    </AuthCard>
  );
}
