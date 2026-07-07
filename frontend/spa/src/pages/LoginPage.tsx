import { useState, type FormEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";

import { useSession } from "../auth/useSession";
import { AuthAlert, AuthCard, FieldError, authInputClass, authLabelClass, authSubmitClass } from "../components/AuthCard";
import { AuthError, login } from "../lib/authApi";
import { isValid, validateLoginForm, type LoginErrors } from "../lib/authValidation";

/**
 * SPA login page (Phase 3.8). Cookie-only auth (PD-01): a successful login sets
 * the existing HttpOnly session cookie server-side — no token is stored in JS.
 * On success the cached session is invalidated and the user is routed into the
 * app grid (`/app`). A 401/400 from the backend is shown inline. This page is
 * mounted OUTSIDE `RequireAuth`/`Layout`; the server-rendered `/login` page
 * keeps working during the strangler migration.
 */
export function LoginPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();
  const justRegistered = searchParams.get("registered") === "true";

  const [values, setValues] = useState({ email: "", password: "" });
  const [errors, setErrors] = useState<LoginErrors>({});

  // If a valid session already exists, skip the form and go straight to the app
  // (mirrors the Jinja page's `checkIfAlreadyLoggedIn`).
  const session = useSession();

  const mutation = useMutation({
    mutationFn: () => login(values.email, values.password),
    onSuccess: async () => {
      // Re-fetch `/be_auth/me` so the guard sees the new cookie session, then
      // route into the app.
      await queryClient.invalidateQueries({ queryKey: ["session"] });
      navigate("/", { replace: true });
    },
  });

  if (session.isSuccess && session.data) {
    return <Navigate to="/" replace />;
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const validation = validateLoginForm(values);
    setErrors(validation);
    if (!isValid(validation)) return;
    mutation.mutate();
  }

  const serverError = mutation.error instanceof AuthError ? mutation.error.message : null;

  return (
    <AuthCard
      subtitle="Connexion"
      intro="Connectez-vous pour accéder à vos albums photos et aventures"
      footer={
        <p className="text-center text-sm text-slate-600 dark:text-gray-400">
          Pas encore de compte ?{" "}
          <Link to="/signup" className="font-medium text-sky-600 hover:text-sky-700 dark:text-sky-400">
            Créer un compte
          </Link>
        </p>
      }
    >
      {justRegistered ? (
        <AuthAlert variant="success">
          Inscription réussie ! Vous pourrez vous connecter dès qu'un administrateur aura activé votre compte.
        </AuthAlert>
      ) : null}
      {serverError ? <AuthAlert variant="error">{serverError}</AuthAlert> : null}

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
            value={values.email}
            onChange={(e) => setValues((v) => ({ ...v, email: e.target.value }))}
            className={authInputClass}
            autoFocus
          />
          <FieldError message={errors.email} />
        </div>

        <div>
          <label htmlFor="password" className={authLabelClass}>
            Mot de passe
          </label>
          <input
            id="password"
            name="password"
            type="password"
            autoComplete="current-password"
            placeholder="••••••••"
            value={values.password}
            onChange={(e) => setValues((v) => ({ ...v, password: e.target.value }))}
            className={authInputClass}
          />
          <FieldError message={errors.password} />
        </div>

        <div className="text-right">
          <Link
            to="/forgot-password"
            className="text-sm font-medium text-sky-600 hover:text-sky-700 dark:text-sky-400"
          >
            Mot de passe oublié ?
          </Link>
        </div>

        <button type="submit" className={authSubmitClass} disabled={mutation.isPending}>
          {mutation.isPending ? "Connexion…" : "Se connecter"}
        </button>
      </form>
    </AuthCard>
  );
}
