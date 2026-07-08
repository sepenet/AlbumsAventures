// @vitest-environment jsdom
//
// Component render tests for the SPA-native album CREATE page. The pure form
// logic (transforms, validation, create orchestration) is covered DOM-free in
// `lib/albumForm.test.ts`; this file exercises the React view layer: initial
// render, required-field validation gating, and the create -> folder happy path
// that ends in a navigate to `/admin`. The `apiClient` and `react-router-dom`
// navigation are mocked so no network or real routing is involved.

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import "@testing-library/jest-dom";

import { api } from "../lib/apiClient";
import { AlbumCreatePage } from "./AlbumCreatePage";

const navigateMock = vi.fn();

vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react-router-dom")>();
  return { ...actual, useNavigate: () => navigateMock };
});

vi.mock("../lib/apiClient", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/apiClient")>();
  return {
    ...actual,
    api: { get: vi.fn(), post: vi.fn(), postForm: vi.fn(), patch: vi.fn(), put: vi.fn(), del: vi.fn() },
  };
});

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AlbumCreatePage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("AlbumCreatePage", () => {
  beforeEach(() => {
    vi.mocked(api.get).mockResolvedValue([{ id: 3, category: "Vacances" }]);
    vi.mocked(api.post).mockResolvedValue({ id: 42 });
    vi.mocked(api.postForm).mockResolvedValue({});
    navigateMock.mockReset();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("renders the create form", async () => {
    renderPage();
    expect(screen.getByRole("heading", { name: /Créer un album/i })).toBeInTheDocument();
    // The category select is populated from the mocked categories query.
    await waitFor(() => expect(screen.getByRole("option", { name: "Vacances" })).toBeInTheDocument());
  });

  it("blocks submission and shows a required-field error when the title is empty", async () => {
    renderPage();
    fireEvent.click(screen.getByRole("button", { name: /Créer l'album/i }));

    expect(await screen.findByText("Le titre est obligatoire.")).toBeInTheDocument();
    // create_album must NOT be called while the form is invalid.
    expect(api.post).not.toHaveBeenCalledWith("/be_album/create_album/", expect.anything());
  });

  it("creates the album then the folder and navigates to /admin on success", async () => {
    renderPage();
    await waitFor(() => expect(screen.getByRole("option", { name: "Vacances" })).toBeInTheDocument());

    fireEvent.change(screen.getByLabelText(/Titre/i), { target: { value: "Randonnée" } });
    fireEvent.change(screen.getByLabelText(/Catégorie/i), { target: { value: "3" } });
    fireEvent.change(screen.getByLabelText(/^Date/i), { target: { value: "2026-07-08" } });

    fireEvent.click(screen.getByRole("button", { name: /Créer l'album/i }));

    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith(
        "/be_album/create_album/",
        expect.objectContaining({ title: "Randonnée", category_id: 3, date: "2026-07-08" }),
      ),
    );
    await waitFor(() => expect(api.postForm).toHaveBeenCalledWith("/be_album/create_album_folder/42", expect.any(FormData)));
    await waitFor(() => expect(navigateMock).toHaveBeenCalledWith("/admin"));
  });
});
