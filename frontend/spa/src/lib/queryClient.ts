import { QueryClient } from "@tanstack/react-query";

import { UnauthorizedError } from "./apiClient";

// A 401 means the session is gone — retrying can't recover it, so the auth
// guard redirects to /login instead. Other transient failures get a couple of
// retries.
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, error) =>
        !(error instanceof UnauthorizedError) && failureCount < 2,
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    },
  },
});
