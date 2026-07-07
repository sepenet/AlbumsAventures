import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";

import { canAccessAdmin } from "../lib/admin";
import { useSession } from "./useSession";

/**
 * Gate that requires an authenticated superuser (Phase 3.6, mirrors the Phase 1
 * #485 server-side `is_superuser` fix). Rendered inside `RequireAuth`, so the
 * session is already resolved to a valid user here; this narrows further to
 * superusers, redirecting everyone else back to the album grid.
 *
 * This is a UX gate only — it hides admin surfaces from non-admins. The actual
 * authority is server-side: the `be_auth/admin/*` endpoints re-check
 * `is_superuser` and return 403, as does the F-1-hardened create_thumbnails.
 */
export function RequireSuperuser({ children }: { children: ReactNode }) {
  const { data: user } = useSession();

  if (!canAccessAdmin(user)) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}
