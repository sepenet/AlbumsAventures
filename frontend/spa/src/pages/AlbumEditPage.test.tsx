// @vitest-environment jsdom
//
// Component render tests for the SPA-native album EDIT page. The pure update
// orchestration and DB<->Web transforms are covered DOM-free in
// `lib/albumForm.test.ts`; this file exercises the React view layer: prefill
// from `get_album_by_id`, the current-cover badge, the directory-rename warning
// banner (parity), required-field validation gating, and the PATCH happy path
// that navigates back to the album detail page. `apiClient` and `react-router-dom`
// routing are mocked so no network or real routing is involved.

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import "@testing-library/jest-dom/vitest";

import { api } from "../lib/apiClient";
import { AlbumEditPage } from "./AlbumEditPage";

const navigateMock = vi.fn();

vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react-router-dom")>();
  return { ...actual, useNavigate: () => navigateMock, useParams: () => ({ albumId: "7" }) };
});

vi.mock("../lib/apiClient", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/apiClient")>();
  return {
    ...actual,
    api: { get: vi.fn(), post: vi.fn(), postForm: vi.fn(), patch: vi.fn(), put: vi.fn(), del: vi.fn() },
  };
});

const ALBUM = {
  id: 7,
  title: "Album Test",
  description: null,
  category_id: 3,
  date: "2024-06-15",
  participants: "Jean|Marie",
  location: "Paris",
  tags: "a|b",
  image_cover: "cover.png",
  category: "Vacances",
};

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AlbumEditPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("AlbumEditPage", () => {
  beforeEach(() => {
    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path.startsWith("/be_album/get_album_by_id/")) return Promise.resolve(ALBUM);
      if (path === "/be_category/get_all_categories/") return Promise.resolve([{ id: 3, category: "Vacances" }]);
      return Promise.resolve(undefined);
    });
    vi.mocked(api.patch).mockResolvedValue({});
    vi.mocked(api.postForm).mockResolvedValue({});
    navigateMock.mockReset();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("prefills the form, shows the current cover and the rename warning", async () => {
    renderPage();
    // Title prefilled from the album read.
    await waitFor(() => expect(screen.getByLabelText(/Titre/i)).toHaveValue("Album Test"));
    // Pipe-stored participants displayed comma-separated (DB -> Web).
    expect(screen.getByLabelText(/Participants/i)).toHaveValue("Jean, Marie");
    // Current-cover badge.
    expect(screen.getByText("cover.png")).toBeInTheDocument();
    // Parity: the directory-rename warning banner.
    expect(screen.getByText(/renomme le dossier de l'album/i)).toBeInTheDocument();
  });

  it("blocks submission and shows a required-field error when the title is cleared", async () => {
    renderPage();
    await waitFor(() => expect(screen.getByLabelText(/Titre/i)).toHaveValue("Album Test"));

    fireEvent.change(screen.getByLabelText(/Titre/i), { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: /Enregistrer/i }));

    expect(await screen.findByText("Le titre est obligatoire.")).toBeInTheDocument();
    expect(api.patch).not.toHaveBeenCalled();
  });

  it("PATCHes update_album and navigates back to the album on success", async () => {
    renderPage();
    await waitFor(() => expect(screen.getByLabelText(/Titre/i)).toHaveValue("Album Test"));

    fireEvent.change(screen.getByLabelText(/Titre/i), { target: { value: "Album Modifié" } });
    fireEvent.click(screen.getByRole("button", { name: /Enregistrer/i }));

    await waitFor(() =>
      expect(api.patch).toHaveBeenCalledWith(
        "/be_album/update_album/7",
        expect.objectContaining({ title: "Album Modifié", category_id: 3 }),
      ),
    );
    await waitFor(() => expect(navigateMock).toHaveBeenCalledWith("/albums/7"));
  });
});
