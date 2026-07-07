// Pure, DOM-free helpers for the admin page (Phase 3.6). Kept side-effect-free
// so they can be unit-tested under the node-based Vitest environment. The
// React admin page consumes these; the server remains the authority (the
// be_auth admin endpoints enforce is_superuser server-side, and F-1 hardened
// create_thumbnails the same way).

import type { AdminUser, SessionUser } from "../types/api";

/**
 * Client-side gate mirroring the server's superuser check. Returns true only
 * for an authenticated superuser. This governs whether the admin route/link is
 * shown; it is NOT a security boundary on its own — every mutating admin call
 * is re-authorized server-side.
 */
export function canAccessAdmin(user: SessionUser | null | undefined): boolean {
  return Boolean(user?.is_superuser);
}

/** Admin list filter modes, matching the Jinja admin_users toolbar. */
export type UserFilter = "all" | "pending" | "active";

/** Maps a filter mode to the `be_auth/admin/users` query string. */
export function adminUsersQuery(filter: UserFilter): string {
  if (filter === "pending") return "?filter_pending=true";
  if (filter === "active") return "?filter_active=true";
  return "";
}

/** A user is "pending" (awaiting activation) when not yet active. */
export function isPending(user: AdminUser): boolean {
  return !user.is_active;
}

/** Count of users awaiting activation — drives the pending badge. */
export function pendingCount(users: readonly AdminUser[]): number {
  return users.reduce((total, user) => total + (isPending(user) ? 1 : 0), 0);
}

/**
 * Guard for the destructive self-demotion case the server also rejects (400):
 * an admin must not remove their own admin rights. Returned true means the
 * toggle should be blocked client-side before the request.
 */
export function isSelfDemotion(current: SessionUser, target: AdminUser, nextIsSuperuser: boolean): boolean {
  return current.id === target.id && target.is_superuser && !nextIsSuperuser;
}

/** Confirmation prompt for toggling a user's admin role (destructive-ish). */
export function promoteConfirmMessage(user: AdminUser): string {
  const name = `${user.firstname} ${user.lastname}`.trim() || user.email;
  return user.is_superuser
    ? `Retirer les droits administrateur de ${name} ?`
    : `Accorder les droits administrateur à ${name} ?`;
}

/** Confirmation prompt for deleting a group (destructive). */
export function deleteGroupConfirmMessage(groupName: string): string {
  return `Supprimer le groupe « ${groupName} » ? Cette action supprime aussi ses liens utilisateurs et albums.`;
}

/** Full display name with an email fallback. */
export function displayName(user: { firstname: string; lastname: string; email?: string }): string {
  const name = `${user.firstname} ${user.lastname}`.trim();
  return name || user.email || "";
}
