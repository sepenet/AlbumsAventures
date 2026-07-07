import { describe, expect, it } from "vitest";

import {
  isValid,
  validateForgotForm,
  validateLoginForm,
  validateResetForm,
  validateSignupForm,
  type LoginFormValues,
  type ResetFormValues,
  type SignupFormValues,
} from "./authValidation";

function login(overrides: Partial<LoginFormValues> = {}): LoginFormValues {
  return { email: "ada@example.com", password: "Secret1", ...overrides };
}

function signup(overrides: Partial<SignupFormValues> = {}): SignupFormValues {
  return {
    firstname: "Ada",
    lastname: "Lovelace",
    email: "ada@example.com",
    password: "NewPass1",
    confirmPassword: "NewPass1",
    ...overrides,
  };
}

function reset(overrides: Partial<ResetFormValues> = {}): ResetFormValues {
  return { new_password: "NewPass1", confirm_password: "NewPass1", ...overrides };
}

describe("validateLoginForm", () => {
  it("accepts a well-formed login", () => {
    expect(isValid(validateLoginForm(login()))).toBe(true);
  });

  it("rejects an invalid email", () => {
    expect(validateLoginForm(login({ email: "not-an-email" })).email).toBeDefined();
  });

  it("rejects an empty password", () => {
    expect(validateLoginForm(login({ password: "" })).password).toBeDefined();
  });
});

describe("validateSignupForm", () => {
  it("accepts a well-formed signup", () => {
    expect(isValid(validateSignupForm(signup()))).toBe(true);
  });

  it("rejects a too-short firstname", () => {
    expect(validateSignupForm(signup({ firstname: "A" })).firstname).toBeDefined();
  });

  it("rejects a too-short lastname", () => {
    expect(validateSignupForm(signup({ lastname: "B" })).lastname).toBeDefined();
  });

  it("rejects an invalid email", () => {
    expect(validateSignupForm(signup({ email: "bad@" })).email).toBeDefined();
  });

  it("rejects a password below 8 characters", () => {
    expect(validateSignupForm(signup({ password: "Ab1", confirmPassword: "Ab1" })).password).toBeDefined();
  });

  it("rejects a password missing complexity (no uppercase/digit)", () => {
    expect(
      validateSignupForm(signup({ password: "alllowercase", confirmPassword: "alllowercase" })).password,
    ).toBeDefined();
  });

  it("rejects mismatched password confirmation", () => {
    expect(validateSignupForm(signup({ confirmPassword: "Different1" })).confirmPassword).toBeDefined();
  });
});

describe("validateForgotForm", () => {
  it("accepts a valid email", () => {
    expect(isValid(validateForgotForm({ email: "ada@example.com" }))).toBe(true);
  });

  it("rejects a missing email", () => {
    expect(validateForgotForm({ email: "" }).email).toBeDefined();
  });
});

describe("validateResetForm", () => {
  it("accepts a well-formed reset", () => {
    expect(isValid(validateResetForm(reset()))).toBe(true);
  });

  it("rejects a weak new password", () => {
    expect(validateResetForm(reset({ new_password: "short", confirm_password: "short" })).new_password).toBeDefined();
  });

  it("rejects mismatched confirmation", () => {
    expect(validateResetForm(reset({ confirm_password: "Mismatch1" })).confirm_password).toBeDefined();
  });
});
