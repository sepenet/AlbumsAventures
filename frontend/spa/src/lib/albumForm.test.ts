import { describe, expect, it, vi } from "vitest";

import type { AlbumDetail } from "../types/api";
import {
  emptyAlbumForm,
  isAlbumFormValid,
  runCreateAlbum,
  runUpdateAlbum,
  toDbList,
  toFormValues,
  toWebList,
  toWritePayload,
  validateAlbumForm,
  validateCategoryName,
  type AlbumFormValues,
  type AlbumWritePayload,
} from "./albumForm";

function validForm(overrides: Partial<AlbumFormValues> = {}): AlbumFormValues {
  return {
    title: "Vacances",
    description: "",
    category_id: "3",
    date: "2024-06-15",
    participants: "Jean, Marie",
    location: "",
    tags: "",
    ...overrides,
  };
}

describe("toDbList / toWebList", () => {
  it("converts Web comma form to DB pipe form", () => {
    expect(toDbList("Jean, Marie")).toBe("Jean|Marie");
    expect(toDbList("  a ,b ,, c ")).toBe("a|b|c");
    expect(toDbList("")).toBe("");
  });

  it("converts DB pipe form to Web comma form", () => {
    expect(toWebList("Jean|Marie")).toBe("Jean, Marie");
    expect(toWebList("a| |b||c")).toBe("a, b, c");
    expect(toWebList(null)).toBe("");
    expect(toWebList("")).toBe("");
  });

  it("round-trips normalizing whitespace and empties", () => {
    expect(toWebList(toDbList("  Jean ,, Marie "))).toBe("Jean, Marie");
    expect(toDbList(toWebList("Jean|Marie"))).toBe("Jean|Marie");
  });
});

describe("toWritePayload", () => {
  it("pipe-joins lists and maps empty text to null", () => {
    const payload = toWritePayload(
      validForm({ description: "  ", participants: "Jean, Marie", tags: "été, famille", location: "" }),
    );
    expect(payload).toEqual<AlbumWritePayload>({
      title: "Vacances",
      description: null,
      category_id: 3,
      date: "2024-06-15",
      participants: "Jean|Marie",
      location: null,
      tags: "été|famille",
      image_cover: null,
    });
  });

  it("trims the title and coerces category_id to a number", () => {
    const payload = toWritePayload(validForm({ title: "  Titre  ", category_id: "7" }));
    expect(payload.title).toBe("Titre");
    expect(payload.category_id).toBe(7);
  });
});

describe("toFormValues", () => {
  it("prefills DB-pipe lists into Web-comma form", () => {
    const album: AlbumDetail = {
      id: 1,
      title: "Album Test",
      description: null,
      category_id: 4,
      date: "2024-06-15",
      participants: "Jean|Marie",
      location: "Paris",
      tags: "a|b",
      image_cover: "cover.png",
      category: "Vacances",
    };
    expect(toFormValues(album)).toEqual<AlbumFormValues>({
      title: "Album Test",
      description: "",
      category_id: "4",
      date: "2024-06-15",
      participants: "Jean, Marie",
      location: "Paris",
      tags: "a, b",
    });
  });
});

describe("validateAlbumForm", () => {
  it("accepts a valid form", () => {
    expect(validateAlbumForm(validForm())).toEqual({});
    expect(isAlbumFormValid(validForm())).toBe(true);
  });

  it("requires a title within 50 chars", () => {
    expect(validateAlbumForm(validForm({ title: "" })).title).toBeDefined();
    expect(validateAlbumForm(validForm({ title: "x".repeat(51) })).title).toBeDefined();
  });

  it("requires category_id and a well-formed date", () => {
    expect(validateAlbumForm(validForm({ category_id: "" })).category_id).toBeDefined();
    expect(validateAlbumForm(validForm({ date: "" })).date).toBeDefined();
    expect(validateAlbumForm(validForm({ date: "15/06/2024" })).date).toBeDefined();
  });

  it("rejects over-long optional fields", () => {
    const long = "x".repeat(513);
    expect(validateAlbumForm(validForm({ participants: long })).participants).toBeDefined();
    expect(validateAlbumForm(validForm({ location: long })).location).toBeDefined();
    expect(validateAlbumForm(validForm({ tags: long })).tags).toBeDefined();
  });
});

describe("emptyAlbumForm", () => {
  it("defaults date to today", () => {
    expect(emptyAlbumForm("2026-07-08").date).toBe("2026-07-08");
  });
});

describe("validateCategoryName", () => {
  it("enforces the 3..128 length range", () => {
    expect(validateCategoryName("ab")).not.toBeNull();
    expect(validateCategoryName("abc")).toBeNull();
    expect(validateCategoryName("x".repeat(129))).not.toBeNull();
  });
});

describe("runCreateAlbum", () => {
  it("sequences create -> folder -> cover and returns created", async () => {
    const calls: string[] = [];
    const createAlbum = vi.fn(async () => {
      calls.push("create");
      return { id: 42 };
    });
    const createFolder = vi.fn(async (id: number) => {
      calls.push(`folder:${id}`);
    });
    const uploadCover = vi.fn(async (id: number) => {
      calls.push(`cover:${id}`);
    });
    const cover = new File(["x"], "cover.png", { type: "image/png" });

    const outcome = await runCreateAlbum(toWritePayload(validForm()), cover, {
      createAlbum,
      createFolder,
      uploadCover,
    });

    expect(outcome).toEqual({ status: "created", albumId: 42 });
    expect(calls).toEqual(["create", "folder:42", "cover:42"]);
  });

  it("skips cover upload when no file is chosen", async () => {
    const uploadCover = vi.fn();
    const outcome = await runCreateAlbum(toWritePayload(validForm()), null, {
      createAlbum: async () => ({ id: 5 }),
      createFolder: async () => undefined,
      uploadCover,
    });
    expect(outcome).toEqual({ status: "created", albumId: 5 });
    expect(uploadCover).not.toHaveBeenCalled();
  });

  it("returns partial with the album id when the folder step fails (orphan handling)", async () => {
    const outcome = await runCreateAlbum(toWritePayload(validForm()), null, {
      createAlbum: async () => ({ id: 9 }),
      createFolder: async () => {
        throw new Error("folder boom");
      },
      uploadCover: async () => undefined,
    });
    expect(outcome.status).toBe("partial");
    if (outcome.status === "partial") {
      expect(outcome.albumId).toBe(9);
      expect(outcome.failedStep).toBe("folder");
    }
  });

  it("returns partial (cover) when only the cover upload fails", async () => {
    const cover = new File(["x"], "c.png", { type: "image/png" });
    const outcome = await runCreateAlbum(toWritePayload(validForm()), cover, {
      createAlbum: async () => ({ id: 11 }),
      createFolder: async () => undefined,
      uploadCover: async () => {
        throw new Error("cover boom");
      },
    });
    expect(outcome).toMatchObject({ status: "partial", albumId: 11, failedStep: "cover" });
  });

  it("propagates a create_album failure (no album created)", async () => {
    await expect(
      runCreateAlbum(toWritePayload(validForm()), null, {
        createAlbum: async () => {
          throw new Error("create boom");
        },
        createFolder: async () => undefined,
        uploadCover: async () => undefined,
      }),
    ).rejects.toThrow("create boom");
  });
});

describe("runUpdateAlbum", () => {
  it("patches then uploads the cover and returns saved", async () => {
    const calls: string[] = [];
    const cover = new File(["x"], "c.png", { type: "image/png" });
    const outcome = await runUpdateAlbum(3, toWritePayload(validForm()), cover, {
      updateAlbum: async (id) => {
        calls.push(`patch:${id}`);
      },
      uploadCover: async (id) => {
        calls.push(`cover:${id}`);
      },
    });
    expect(outcome).toEqual({ status: "saved" });
    expect(calls).toEqual(["patch:3", "cover:3"]);
  });

  it("reports cover_failed when the cover upload fails after a successful patch", async () => {
    const cover = new File(["x"], "c.png", { type: "image/png" });
    const outcome = await runUpdateAlbum(3, toWritePayload(validForm()), cover, {
      updateAlbum: async () => undefined,
      uploadCover: async () => {
        throw new Error("cover boom");
      },
    });
    expect(outcome.status).toBe("cover_failed");
  });

  it("propagates an update_album failure", async () => {
    await expect(
      runUpdateAlbum(3, toWritePayload(validForm()), null, {
        updateAlbum: async () => {
          throw new Error("patch boom");
        },
        uploadCover: async () => undefined,
      }),
    ).rejects.toThrow("patch boom");
  });
});
