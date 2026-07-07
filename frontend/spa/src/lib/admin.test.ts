import { describe, expect, it } from "vitest";

import {
  adminUsersQuery,
  canAccessAdmin,
  deleteGroupConfirmMessage,
  displayName,
  isPending,
  isSelfDemotion,
  pendingCount,
  promoteConfirmMessage,
} from "./admin";
import type { AdminUser, SessionUser } from "../types/api";

function sessionUser(overrides: Partial<SessionUser> = {}): SessionUser {
  return {
    id: 1,
    email: "admin@example.com",
    firstname: "Admin",
    lastname: "User",
    is_active: true,
    is_superuser: true,
    ...overrides,
  };
}

function adminUser(overrides: Partial<AdminUser> = {}): AdminUser {
  return {
    id: 2,
    email: "member@example.com",
    firstname: "Mem",
    lastname: "Ber",
    is_active: true,
    is_superuser: false,
    ...overrides,
  };
}

// The core Phase 3.6 smoke test: the client superuser gate.
describe("canAccessAdmin", () => {
  it("grants access to an authenticated superuser", () => {
    expect(canAccessAdmin(sessionUser({ is_superuser: true }))).toBe(true);
  });

  it("denies a non-superuser", () => {
    expect(canAccessAdmin(sessionUser({ is_superuser: false }))).toBe(false);
  });

  it("denies when there is no session", () => {
    expect(canAccessAdmin(null)).toBe(false);
    expect(canAccessAdmin(undefined)).toBe(false);
  });
});

describe("adminUsersQuery", () => {
  it("maps filter modes to the be_auth query string", () => {
    expect(adminUsersQuery("all")).toBe("");
    expect(adminUsersQuery("pending")).toBe("?filter_pending=true");
    expect(adminUsersQuery("active")).toBe("?filter_active=true");
  });
});

describe("pending helpers", () => {
  it("flags inactive users as pending", () => {
    expect(isPending(adminUser({ is_active: false }))).toBe(true);
    expect(isPending(adminUser({ is_active: true }))).toBe(false);
  });

  it("counts pending users", () => {
    const users = [
      adminUser({ id: 1, is_active: false }),
      adminUser({ id: 2, is_active: true }),
      adminUser({ id: 3, is_active: false }),
    ];
    expect(pendingCount(users)).toBe(2);
  });
});

describe("isSelfDemotion", () => {
  it("blocks an admin removing their own admin rights", () => {
    const current = sessionUser({ id: 5, is_superuser: true });
    const target = adminUser({ id: 5, is_superuser: true });
    expect(isSelfDemotion(current, target, false)).toBe(true);
  });

  it("allows demoting another admin", () => {
    const current = sessionUser({ id: 5, is_superuser: true });
    const target = adminUser({ id: 6, is_superuser: true });
    expect(isSelfDemotion(current, target, false)).toBe(false);
  });

  it("allows promoting oneself (not a demotion)", () => {
    const current = sessionUser({ id: 5, is_superuser: false });
    const target = adminUser({ id: 5, is_superuser: false });
    expect(isSelfDemotion(current, target, true)).toBe(false);
  });
});

describe("confirmation messages", () => {
  it("phrases promotion vs demotion", () => {
    expect(promoteConfirmMessage(adminUser({ is_superuser: false }))).toContain("Accorder");
    expect(promoteConfirmMessage(adminUser({ is_superuser: true }))).toContain("Retirer");
  });

  it("warns about cascading deletes for groups", () => {
    expect(deleteGroupConfirmMessage("Famille")).toContain("Famille");
  });
});

describe("displayName", () => {
  it("joins first and last name", () => {
    expect(displayName({ firstname: "Ada", lastname: "Lovelace" })).toBe("Ada Lovelace");
  });

  it("falls back to email when the name is empty", () => {
    expect(displayName({ firstname: "", lastname: "", email: "a@b.co" })).toBe("a@b.co");
  });
});
