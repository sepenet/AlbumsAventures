import { useEffect, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";

import { useSession } from "../auth/useSession";
import { api } from "../lib/apiClient";

// Same key as the server-rendered pages (base.html) so the dark-mode choice is
// shared across the Jinja2 and React surfaces during the strangler migration.
const DARK_MODE_KEY = "darkMode";

function useDarkMode(): [boolean, () => void] {
  const [dark, setDark] = useState<boolean>(() => localStorage.getItem(DARK_MODE_KEY) === "true");

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    localStorage.setItem(DARK_MODE_KEY, String(dark));
  }, [dark]);

  return [dark, () => setDark((value) => !value)];
}

export function Layout({ children }: { children: ReactNode }) {
  const { data: user } = useSession();
  const [dark, toggleDark] = useDarkMode();

  async function handleLogout() {
    try {
      // Clears the HttpOnly cookie server-side; there is no JS-held token.
      await api.post("/be_auth/logout");
    } finally {
      // Return to the migrated SPA login page (Phase 3.8).
      window.location.href = "/app/login";
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 text-gray-900 transition-colors duration-300 dark:from-gray-900 dark:to-gray-800 dark:text-gray-100">
      <header className="border-b border-gray-200 bg-white shadow-sm transition-colors duration-300 dark:border-gray-700 dark:bg-gray-800">
        <div className="container mx-auto flex items-center justify-between px-4 py-4">
          <a href="/app/" className="flex items-center space-x-2">
            <span className="bg-gradient-to-r from-sky-500 to-blue-600 bg-clip-text text-xl font-bold text-transparent">
              Albums Aventures
            </span>
          </a>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={toggleDark}
              className="rounded-lg p-2 text-gray-700 transition-colors hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
              aria-label="Basculer le mode sombre"
              title="Mode sombre"
            >
              {dark ? "☀️" : "🌙"}
            </button>
            {user ? (
              <span className="hidden text-sm font-medium text-gray-700 sm:inline dark:text-gray-300">
                {user.email}
              </span>
            ) : null}
            {user ? (
              <Link
                to="/profile"
                className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 transition-colors hover:bg-gray-100 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
              >
                Mon profil
              </Link>
            ) : null}
            {user?.is_superuser ? (
              <Link
                to="/admin"
                className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 transition-colors hover:bg-gray-100 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
              >
                Admin
              </Link>
            ) : null}
            <button
              type="button"
              onClick={handleLogout}
              className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 transition-colors hover:bg-gray-100 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
            >
              Déconnexion
            </button>
          </div>
        </div>
      </header>
      <main className="container mx-auto px-4 py-6">{children}</main>
    </div>
  );
}
