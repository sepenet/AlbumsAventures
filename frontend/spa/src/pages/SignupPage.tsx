import { useState, type FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";

import { AuthAlert, AuthCard, FieldError, authInputClass, authLabelClass, authSubmitClass } from "../components/AuthCard";
import { ApiError } from "../lib/apiClient";
import { signup } from "../lib/authApi";
import { isValid, validateSignupForm, type SignupErrors, type SignupFormValues } from "../lib/authValidation";

const EMPTY: SignupFormValues = {
  firstname: "",
  lastname: "",
  email: "",
  password: "",
  confirmPassword: "",
};

/**
 * SPA signup page (Phase 3.8). Client-side validation mirrors the Jinja signup
 * page (frontend/templates/signup.html); the server forces the new account to
 * inactive/non-admin (SEC-03) and awaits admin activation. On success the user
 * is routed to the login page with a success banner — matching the Jinja flow.
 * Mounted OUTSIDE `RequireAuth`/`Layout`; the server-rendered `/signup` page
 * keeps working during the strangler migration.
 */
export function SignupPage() {
  const navigate = useNavigate();
  const [values, setValues] = useState<SignupFormValues>(EMPTY);
  const [errors, setErrors] = useState<SignupErrors>({});

  const mutation = useMutation({
    mutationFn: () => signup(values),
    onSuccess: () => navigate("/login?registered=true", { replace: true }),
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const validation = validateSignupForm(values);
    setErrors(validation);
    if (!isValid(validation)) return;
    mutation.mutate();
  }

  const serverError = mutation.error instanceof ApiError ? mutation.error.message : null;

  function field(name: keyof SignupFormValues) {
    return {
      value: values[name],
      onChange: (e: React.ChangeEvent<HTMLInputElement>) =>
        setValues((v) => ({ ...v, [name]: e.target.value })),
      className: authInputClass,
    };
  }

  return (
    <AuthCard
      subtitle="Créer un compte"
      intro="Rejoignez-nous pour partager vos albums photos et aventures"
      footer={
        <p className="text-center text-sm text-slate-600 dark:text-gray-400">
          Déjà un compte ?{" "}
          <Link to="/login" className="font-medium text-sky-600 hover:text-sky-700 dark:text-sky-400">
            Se connecter
          </Link>
        </p>
      }
    >
      {serverError ? <AuthAlert variant="error">{serverError}</AuthAlert> : null}

      <form onSubmit={handleSubmit} className="space-y-5" noValidate>
        <div>
          <label htmlFor="firstname" className={authLabelClass}>
            Prénom
          </label>
          <input id="firstname" type="text" autoComplete="given-name" placeholder="Jean" autoFocus {...field("firstname")} />
          <FieldError message={errors.firstname} />
        </div>

        <div>
          <label htmlFor="lastname" className={authLabelClass}>
            Nom
          </label>
          <input id="lastname" type="text" autoComplete="family-name" placeholder="Dupont" {...field("lastname")} />
          <FieldError message={errors.lastname} />
        </div>

        <div>
          <label htmlFor="email" className={authLabelClass}>
            Email
          </label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            placeholder="votre.email@exemple.com"
            {...field("email")}
          />
          <FieldError message={errors.email} />
        </div>

        <div>
          <label htmlFor="password" className={authLabelClass}>
            Mot de passe
          </label>
          <input
            id="password"
            type="password"
            autoComplete="new-password"
            placeholder="••••••••"
            {...field("password")}
          />
          <FieldError message={errors.password} />
        </div>

        <div>
          <label htmlFor="confirmPassword" className={authLabelClass}>
            Confirmer le mot de passe
          </label>
          <input
            id="confirmPassword"
            type="password"
            autoComplete="new-password"
            placeholder="••••••••"
            {...field("confirmPassword")}
          />
          <FieldError message={errors.confirmPassword} />
        </div>

        <button type="submit" className={authSubmitClass} disabled={mutation.isPending}>
          {mutation.isPending ? "Création…" : "Créer mon compte"}
        </button>
      </form>
    </AuthCard>
  );
}
