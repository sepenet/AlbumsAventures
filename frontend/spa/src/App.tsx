import { Suspense, lazy } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { RequireAuth } from "./auth/RequireAuth";
import { RequireSuperuser } from "./auth/RequireSuperuser";
import { Layout } from "./components/Layout";
import { AdminPage } from "./pages/AdminPage";
import { AlbumCreatePage } from "./pages/AlbumCreatePage";
import { AlbumDetailPage } from "./pages/AlbumDetailPage";
import { AlbumEditPage } from "./pages/AlbumEditPage";
import { AlbumGridPage } from "./pages/AlbumGridPage";
import { ForgotPasswordPage } from "./pages/ForgotPasswordPage";
import { LoginPage } from "./pages/LoginPage";
import { ProfilePage } from "./pages/ProfilePage";
import { ResetPasswordPage } from "./pages/ResetPasswordPage";
import { SharedAlbumPage } from "./pages/SharedAlbumPage";
import { SignupPage } from "./pages/SignupPage";

// Code-split the upload page (FU-1). The heavy `@uppy/*` ESM stack is only
// needed on `/albums/:id/upload`, so it is lazy-loaded into its own chunk
// instead of bloating the album-grid initial bundle. `UploadPage` (and its
// `useUploader` hook, the sole importer of `@uppy/*`) are reached only through
// this dynamic import, so Vite/Rollup emit them as a separate chunk.
const UploadPage = lazy(() =>
  import("./pages/UploadPage").then((module) => ({ default: module.UploadPage })),
);

function UploadFallback() {
  return (
    <p className="py-12 text-center text-gray-500 dark:text-gray-400">
      Chargement de l&apos;outil d&apos;envoi…
    </p>
  );
}

export function App() {
  return (
    <Routes>
      <Route
        path="/"
        element={
          <RequireAuth>
            <Layout>
              <AlbumGridPage />
            </Layout>
          </RequireAuth>
        }
      />
      {/* Deep-linkable album detail. The FastAPI SPA fallback serves index.html
          for `/app/albums/:id` refreshes; React Router resolves this route. */}
      <Route
        path="/albums/:albumId"
        element={
          <RequireAuth>
            <Layout>
              <AlbumDetailPage />
            </Layout>
          </RequireAuth>
        }
      />
      {/* Upload page (Phase 3.4) — Uppy v5 ESM, bundled by Vite. Deep-linkable
          and refresh-safe via the FastAPI SPA fallback. Lazy-loaded (FU-1):
          the Uppy chunk is fetched only when this route is opened. */}
      <Route
        path="/albums/:albumId/upload"
        element={
          <RequireAuth>
            <Layout>
              <Suspense fallback={<UploadFallback />}>
                <UploadPage />
              </Suspense>
            </Layout>
          </RequireAuth>
        }
      />
      {/* Profile page (Phase 3.5) — cookie-only auth; PUT mutations carry the
          CSRF header via the shared apiClient. Deep-linkable at /app/profile. */}
      <Route
        path="/profile"
        element={
          <RequireAuth>
            <Layout>
              <ProfilePage />
            </Layout>
          </RequireAuth>
        }
      />
      {/* Admin page (Phase 3.6) — superuser-only. RequireSuperuser redirects
          non-admins to the grid; the be_auth admin endpoints re-check
          is_superuser server-side (#485). Deep-linkable at /app/admin. */}
      <Route
        path="/admin"
        element={
          <RequireAuth>
            <RequireSuperuser>
              <Layout>
                <AdminPage />
              </Layout>
            </RequireSuperuser>
          </RequireAuth>
        }
      />
      {/* SPA-native album create/edit (superuser-only) — replace the retired
          Jinja `album_form.html` / `album_edit.html`. Guarded exactly like
          `/admin`: RequireSuperuser redirects non-admins to the grid and the
          be_album mutation endpoints re-check `require_superuser` server-side.
          `/album/new` is declared BEFORE `/album/:albumId/edit` so the literal
          segment is matched first. Deep-linkable and refresh-safe via the
          FastAPI SPA fallback. */}
      <Route
        path="/album/new"
        element={
          <RequireAuth>
            <RequireSuperuser>
              <Layout>
                <AlbumCreatePage />
              </Layout>
            </RequireSuperuser>
          </RequireAuth>
        }
      />
      <Route
        path="/album/:albumId/edit"
        element={
          <RequireAuth>
            <RequireSuperuser>
              <Layout>
                <AlbumEditPage />
              </Layout>
            </RequireSuperuser>
          </RequireAuth>
        }
      />
      {/* Public shared-album flow (Phase 3.7) — deliberately OUTSIDE RequireAuth
          and the authenticated Layout. The share token lives in the URL and the
          PIN is kept in memory; the page only calls the public share endpoints
          (credentials omitted), so it never reads authenticated app data. The
          FastAPI SPA fallback serves index.html for `/app/shared/:token`, which
          cannot shadow `/be_*` or the `/album/shared/images` API (registered
          outside `/app`). */}
      <Route path="/shared/:token" element={<SharedAlbumPage />} />
      <Route path="/shared" element={<SharedAlbumPage />} />
      {/* Public auth pages (Phase 3.8) — deliberately OUTSIDE RequireAuth and the
          authenticated Layout, mirroring the server-rendered auth pages. Login
          sets the existing HttpOnly cookie via be_auth (cookie-only, no token in
          JS) and routes into /app; a 401 is shown inline. The Jinja auth pages
          (/login, /signup, /forgot-password, /reset-password) keep working during
          the strangler migration. */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      {/* Unknown SPA routes (and deep-link refreshes handled by the FastAPI
          fallback) resolve to the grid. */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
