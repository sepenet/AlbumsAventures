// Pure client-side validation helpers for the profile page (Phase 3.5).
//
// These mirror the field rules of the server-rendered Jinja profile page
// (frontend/templates/profile.html) so the React `/app/profile` variant gives
// identical inline feedback before a mutation is sent. The server remains the
// authority: `PUT /be_auth/update_profile` re-validates the profile fields
// (backend/db/schemas.py `UserProfileUpdate`) and `PUT /be_auth/update_password`
// re-verifies the current password and hashes the new one. These helpers are
// pure (no DOM) so they can be unit-tested under the Vitest `node` environment.

/** Values of the "informations personnelles" form. */
export interface ProfileFormValues {
  firstname: string;
  lastname: string;
  email: string;
}

/** Values of the "changer le mot de passe" form. */
export interface PasswordFormValues {
  current_password: string;
  new_password: string;
  confirm_password: string;
}

/** Per-field error messages keyed by the offending field name. */
export type ProfileErrors = Partial<Record<keyof ProfileFormValues, string>>;
export type PasswordErrors = Partial<Record<keyof PasswordFormValues, string>>;

// Matches the Jinja page's email regex (frontend/templates/profile.html).
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
// At least one lowercase, one uppercase, and one digit.
const PASSWORD_COMPLEXITY_REGEX = /(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/;

/**
 * Validate the profile form. Returns a map of field -> message; an empty object
 * means the form is valid. Rules match the Jinja profile page (firstname/lastname
 * ≥ 2 chars after trim, syntactically valid email).
 */
export function validateProfileForm(values: ProfileFormValues): ProfileErrors {
  const errors: ProfileErrors = {};

  if (!values.firstname || values.firstname.trim().length < 2) {
    errors.firstname = "Le prénom doit contenir au moins 2 caractères";
  }

  if (!values.lastname || values.lastname.trim().length < 2) {
    errors.lastname = "Le nom doit contenir au moins 2 caractères";
  }

  if (!values.email || !EMAIL_REGEX.test(values.email)) {
    errors.email = "Adresse email invalide";
  }

  return errors;
}

/**
 * Validate the password-change form. Returns a map of field -> message; an empty
 * object means the form is valid. Rules match the Jinja profile page: current
 * password required, new password ≥ 8 chars with lower/upper/digit, and the
 * confirmation must match the new password (the mismatch check).
 */
export function validatePasswordForm(values: PasswordFormValues): PasswordErrors {
  const errors: PasswordErrors = {};

  if (!values.current_password) {
    errors.current_password = "Le mot de passe actuel est requis";
  }

  if (!values.new_password || values.new_password.length < 8) {
    errors.new_password = "Le mot de passe doit contenir au moins 8 caractères";
  } else if (!PASSWORD_COMPLEXITY_REGEX.test(values.new_password)) {
    errors.new_password =
      "Le mot de passe doit contenir au moins une minuscule, une majuscule et un chiffre";
  }

  if (values.new_password !== values.confirm_password) {
    errors.confirm_password = "Les mots de passe ne correspondent pas";
  }

  return errors;
}

/** Convenience predicate: true when an error map has no entries. */
export function isValid(errors: Record<string, string | undefined>): boolean {
  return Object.keys(errors).length === 0;
}
