import { describe, expect, it } from "vitest";

import {
  isValid,
  validatePasswordForm,
  validateProfileForm,
  type PasswordFormValues,
  type ProfileFormValues,
} from "./profileValidation";

function profile(overrides: Partial<ProfileFormValues> = {}): ProfileFormValues {
  return { firstname: "Ada", lastname: "Lovelace", email: "ada@example.com", ...overrides };
}

function password(overrides: Partial<PasswordFormValues> = {}): PasswordFormValues {
  return {
    current_password: "OldPass1",
    new_password: "NewPass1",
    confirm_password: "NewPass1",
    ...overrides,
  };
}

describe("validateProfileForm", () => {
  it("accepts a well-formed profile", () => {
    expect(isValid(validateProfileForm(profile()))).toBe(true);
  });

  it("rejects a too-short firstname", () => {
    expect(validateProfileForm(profile({ firstname: "A" })).firstname).toBeDefined();
  });

  it("rejects a too-short lastname", () => {
    expect(validateProfileForm(profile({ lastname: "" })).lastname).toBeDefined();
  });

  it("rejects a malformed email", () => {
    expect(validateProfileForm(profile({ email: "not-an-email" })).email).toBeDefined();
  });
});

describe("validatePasswordForm", () => {
  it("accepts a valid password change", () => {
    expect(isValid(validatePasswordForm(password()))).toBe(true);
  });

  // The core Phase 3.5 smoke test: client-side password-mismatch detection.
  it("flags a confirmation that does not match the new password", () => {
    const errors = validatePasswordForm(password({ confirm_password: "Different1" }));
    expect(errors.confirm_password).toBe("Les mots de passe ne correspondent pas");
  });

  it("requires the current password", () => {
    expect(validatePasswordForm(password({ current_password: "" })).current_password).toBeDefined();
  });

  it("rejects a new password shorter than 8 characters", () => {
    const errors = validatePasswordForm(
      password({ new_password: "Ab1", confirm_password: "Ab1" }),
    );
    expect(errors.new_password).toBeDefined();
  });

  it("rejects a new password missing complexity (no uppercase/digit)", () => {
    const errors = validatePasswordForm(
      password({ new_password: "alllowercase", confirm_password: "alllowercase" }),
    );
    expect(errors.new_password).toBeDefined();
  });
});
