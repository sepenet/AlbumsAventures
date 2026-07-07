import type { ReactNode } from "react";

// Branded, standalone shell for the SPA auth pages (Phase 3.8). These pages sit
// OUTSIDE the authenticated `Layout` (no session nav / logout) and outside
// `RequireAuth`, mirroring the server-rendered auth pages' centered gradient
// card (frontend/templates/{login,signup,...}.html).
export function AuthCard({
  subtitle,
  intro,
  children,
  footer,
}: {
  subtitle: string;
  intro?: string;
  children: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-gray-50 to-gray-100 px-4 py-12 dark:from-gray-900 dark:to-gray-800">
      <div className="w-full max-w-md">
        <div className="overflow-hidden rounded-2xl bg-white shadow-xl dark:bg-gray-800">
          <div className="bg-gradient-to-r from-sky-500 to-blue-600 px-8 py-10 text-center">
            <h1 className="mb-2 text-3xl font-bold text-white">Albums Aventures</h1>
            <p className="text-sm text-sky-100">{subtitle}</p>
          </div>
          <div className="px-8 py-8">
            {intro ? (
              <p className="mb-6 text-center text-sm text-slate-600 dark:text-gray-300">{intro}</p>
            ) : null}
            {children}
          </div>
          {footer ? (
            <div className="border-t border-gray-200 bg-gray-50 px-8 py-6 dark:border-gray-700 dark:bg-gray-900/50">
              {footer}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

/** Inline alert box shared by the auth pages (error = red, success = green). */
export function AuthAlert({ variant, children }: { variant: "error" | "success"; children: ReactNode }) {
  const styles =
    variant === "error"
      ? "bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800 text-red-700 dark:text-red-300"
      : "bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800 text-green-700 dark:text-green-300";
  return (
    <div role="alert" className={`mb-6 rounded-lg border px-4 py-3 text-sm ${styles}`}>
      {children}
    </div>
  );
}

/** Shared field-level error message. */
export function FieldError({ message }: { message?: string }) {
  if (!message) return null;
  return <p className="mt-1 text-sm text-red-600 dark:text-red-400">{message}</p>;
}

// Shared input classes matching the Jinja auth pages.
export const authInputClass =
  "w-full rounded-lg border border-gray-300 bg-white px-4 py-3 text-slate-900 placeholder-gray-400 transition duration-200 focus:border-transparent focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100 dark:placeholder-gray-500";

export const authLabelClass = "mb-2 block text-sm font-semibold text-slate-700 dark:text-gray-200";

export const authSubmitClass =
  "w-full rounded-lg bg-gradient-to-r from-sky-500 to-blue-600 px-4 py-3 font-semibold text-white shadow-md transition duration-200 hover:from-sky-600 hover:to-blue-700 hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-sky-500 disabled:cursor-not-allowed disabled:opacity-60";
