import { useQuery } from "@tanstack/react-query";

import { api } from "../lib/apiClient";
import type { SessionUser } from "../types/api";

// Session state comes exclusively from `GET /be_auth/me`, which reads the
// HttpOnly session cookie server-side. The SPA never stores a token itself.
// `retry: false` so an unauthenticated load fails fast into the auth guard.
export function useSession() {
  return useQuery<SessionUser>({
    queryKey: ["session"],
    queryFn: () => api.get<SessionUser>("/be_auth/me"),
    retry: false,
    staleTime: 5 * 60 * 1000,
  });
}
