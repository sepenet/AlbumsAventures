// Pure client-side validation helpers for the auth pages (Phase 3.8).
//
// These mirror the field rules of the server-rendered Jinja auth pages
// (frontend/templates/{login,signup,forgot_password,reset_password}.html) so
// the React `/app/{login,signup,forgot-password,reset-password}` variants give
// identical inline feedback before a request is sent. The server remains the
// authority: `be_auth` re-validates credentials, the email-uniqueness rule, the
// reset token, and the password length on every call. These helpers are pure
// (no DOM) so they can be unit-tested under the Vitest `node` environment.

/** Values of the login form. */
export interface LoginFormValues {
  email: string;
  password: string;
}

/** Values of the signup form. */
export interface SignupFormValues {
  firstname: string;
  lastname: string;
  email: string;
  password: string;
  confirmPassword: string;
}

/** Values of the forgot-password form. */
export interface ForgotFormValues {
  email: string;
}

/** Values of the reset-password form (the token comes from the URL). */
export interface ResetFormValues {
  new_password: string;
  confirm_password: string;
}

export type LoginErrors = Partial<Record<keyof LoginFormValues, string>>;
export type SignupErrors = Partial<Record<keyof SignupFormValues, string>>;
export type ForgotErrors = Partial<Record<keyof ForgotFormValues, string>>;
export type ResetErrors = Partial<Record<keyof ResetFormValues, string>>;

// Matches the Jinja pages' email regex (frontend/templates/signup.html).
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
// At least one lowercase, one uppercase, and one digit (signup.html).
const PASSWORD_COMPLEXITY_REGEX = /(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/;

const EMAIL_INVALID = "Adresse email invalide";
const PASSWORD_REQUIRED = "Le mot de passe est requis";
const PASSWORD_TOO_SHORT = "Le mot de passe doit contenir au moins 8 caractères";
const PASSWORD_COMPLEXITY =
  "Le mot de passe doit contenir au moins une minuscule, une majuscule et un chiffre";
const PASSWORD_MISMATCH = "Les mots de passe ne correspondent pas";

/**
 * Validate the login form. The server-rendered page only marks the fields
 * `required` with an `email` input type, so the SPA mirrors that: a
 * syntactically valid email and a non-empty password. Bad credentials are still
 * surfaced by the backend's 401/400 response, not here.
 */
export function validateLoginForm(values: LoginFormValues): LoginErrors {
  const errors: LoginErrors = {};

  if (!values.email || !EMAIL_REGEX.test(values.email)) {
    errors.email = EMAIL_INVALID;
  }

  if (!values.password) {
    errors.password = PASSWORD_REQUIRED;
  }

  return errors;
}

/**
 * Validate the signup form. Rules match the Jinja signup page
 * (frontend/templates/signup.html `validateForm`): firstname/lastname ≥ 2 chars
 * after trim, valid email, password ≥ 8 chars with lower/upper/digit, and the
 * confirmation must match.
 */
export function validateSignupForm(values: SignupFormValues): SignupErrors {
  const errors: SignupErrors = {};

  if (!values.firstname || values.firstname.trim().length < 2) {
    errors.firstname = "Le prénom doit contenir au moins 2 caractères";
  }

  if (!values.lastname || values.lastname.trim().length < 2) {
    errors.lastname = "Le nom doit contenir au moins 2 caractères";
  }

  if (!values.email || !EMAIL_REGEX.test(values.email)) {
    errors.email = EMAIL_INVALID;
  }

  if (!values.password || values.password.length < 8) {
    errors.password = PASSWORD_TOO_SHORT;
  } else if (!PASSWORD_COMPLEXITY_REGEX.test(values.password)) {
    errors.password = PASSWORD_COMPLEXITY;
  }

  if (values.password !== values.confirmPassword) {
    errors.confirmPassword = PASSWORD_MISMATCH;
  }

  return errors;
}

/**
 * Validate the forgot-password form: a syntactically valid email. The backend
 * always returns the same neutral message regardless of whether the email
 * exists (anti-enumeration), so no existence check happens client-side.
 */
export function validateForgotForm(values: ForgotFormValues): ForgotErrors {
  const errors: ForgotErrors = {};

  if (!values.email || !EMAIL_REGEX.test(values.email)) {
    errors.email = EMAIL_INVALID;
  }

  return errors;
}

/**
 * Validate the reset-password form. Mirrors the Jinja reset page: new password
 * ≥ 8 chars with lower/upper/digit and the confirmation must match. The reset
 * token itself is validated server-side.
 */
export function validateResetForm(values: ResetFormValues): ResetErrors {
  const errors: ResetErrors = {};

  if (!values.new_password || values.new_password.length < 8) {
    errors.new_password = PASSWORD_TOO_SHORT;
  } else if (!PASSWORD_COMPLEXITY_REGEX.test(values.new_password)) {
    errors.new_password = PASSWORD_COMPLEXITY;
  }

  if (values.new_password !== values.confirm_password) {
    errors.confirm_password = PASSWORD_MISMATCH;
  }

  return errors;
}

/** Convenience predicate: true when an error map has no entries. */
export function isValid(errors: Record<string, string | undefined>): boolean {
  return Object.keys(errors).length === 0;
}
