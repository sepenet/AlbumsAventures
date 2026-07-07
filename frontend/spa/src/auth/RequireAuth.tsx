import type { ReactNode } from "react";
import { useEffect, useState } from "react";

import { UnauthorizedError } from "../lib/apiClient";
import { useSession } from "./useSession";

// Unauthenticated users are sent to the migrated SPA login page (Phase 3.8).
// A full-page navigation (not React Router) guarantees a clean, session-free
// mount of the login route. The `/app` prefix matches the FastAPI SPA mount.
const LOGIN_URL = "/app/login";

function FullScreenMessage({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-gray-50 to-gray-100 px-4 text-center text-gray-600 dark:from-gray-900 dark:to-gray-800 dark:text-gray-400">
      <p>{children}</p>
    </div>
  );
}

/**
 * Track browser connectivity so the auth guard can show an offline state
 * instead of hard-redirecting to `/login` when the session probe fails only
 * because the network is down. Seeds from `navigator.onLine` and stays in sync
 * via the `online`/`offline` events.
 */
function useOnlineStatus(): boolean {
  const [online, setOnline] = useState(() =>
    typeof navigator === "undefined" ? true : navigator.onLine,
  );
  useEffect(() => {
    const goOnline = () => setOnline(true);
    const goOffline = () => setOnline(false);
    window.addEventListener("online", goOnline);
    window.addEventListener("offline", goOffline);
    return () => {
      window.removeEventListener("online", goOnline);
      window.removeEventListener("offline", goOffline);
    };
  }, []);
  return online;
}

/**
 * Gate that requires a valid cookie session before rendering `children`.
 * A 401 (or missing session) redirects to the server-rendered login page —
 * the cookie-only auth model is preserved end to end.
 *
 * PWA offline safety (Phase 4): the precached app shell can load with no
 * network, so `GET /be_auth/me` may fail with a connectivity error rather than
 * a real 401. In that case the guard shows an explicit OFFLINE state with a
 * retry — it MUST NOT redirect to `/login`, which offline would loop (the login
 * shell reloads, re-probes, fails again). Only a genuine `UnauthorizedError`
 * (real 401) or an authenticated-but-empty session triggers the redirect.
 */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { isPending, isError, error, data, refetch } = useSession();
  const online = useOnlineStatus();

  if (isPending) {
    return <FullScreenMessage>Vérification de la session…</FullScreenMessage>;
  }

  if (isError) {
    if (error instanceof UnauthorizedError) {
      window.location.href = LOGIN_URL;
      return null;
    }
    // Connectivity failure (offline or server unreachable): show an offline
    // state with a retry, never a redirect — avoids the offline login loop.
    if (!online) {
      return (
        <FullScreenMessage>
          Vous êtes hors ligne. Reconnectez-vous à Internet pour accéder à vos albums.{" "}
          <button
            type="button"
            className="text-sky-600 hover:underline dark:text-sky-400"
            onClick={() => refetch()}
          >
            Réessayer
          </button>
        </FullScreenMessage>
      );
    }
    return (
      <FullScreenMessage>
        Erreur de session.{" "}
        <a className="text-sky-600 hover:underline dark:text-sky-400" href={LOGIN_URL}>
          Se reconnecter
        </a>
      </FullScreenMessage>
    );
  }

  if (!data) {
    window.location.href = LOGIN_URL;
    return null;
  }

  return <>{children}</>;
}
