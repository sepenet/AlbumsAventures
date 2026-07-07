import { describe, expect, it } from "vitest";

import type { AlbumMediaPage } from "../types/api";
import { formatMonthYear, formatParticipants, getNextMediaOffset } from "./format";

function page(itemCount: number, hasMore: boolean, total: number): AlbumMediaPage {
  return {
    items: Array.from({ length: itemCount }, (_, index) => ({
      filename: `f${index}.jpg`,
      thumbnail_url: `/thumbnails/f${index}.jpg`,
      full_url: `/images/f${index}.jpg`,
      is_video: false,
      has_thumbnail: true,
      width: 1920,
      height: 1080,
    })),
    total,
    has_more: hasMore,
  };
}

describe("formatMonthYear", () => {
  it("formate une date ISO en 'Mois Année' français", () => {
    expect(formatMonthYear("2024-07-15")).toBe("Juillet 2024");
  });

  it("retourne une chaîne vide pour une valeur nulle", () => {
    expect(formatMonthYear(null)).toBe("");
  });

  it("retourne la valeur brute pour une date invalide", () => {
    expect(formatMonthYear("pas-une-date")).toBe("pas-une-date");
  });
});

describe("formatParticipants", () => {
  it("remplace les séparateurs '|' par des virgules", () => {
    expect(formatParticipants("Alice|Bob|Chloé")).toBe("Alice, Bob, Chloé");
  });

  it("affiche un libellé de repli quand il n'y a pas de participants", () => {
    expect(formatParticipants(null)).toBe("Pas de participants");
  });
});

describe("getNextMediaOffset", () => {
  it("retourne 0 quand aucune page n'est encore chargée", () => {
    expect(getNextMediaOffset([])).toBe(0);
  });

  it("retourne le cumul des items chargés quand d'autres pages existent", () => {
    expect(getNextMediaOffset([page(30, true, 75)])).toBe(30);
    expect(getNextMediaOffset([page(30, true, 75), page(30, true, 75)])).toBe(60);
  });

  it("retourne undefined quand la dernière page n'a plus d'items", () => {
    expect(getNextMediaOffset([page(30, true, 45), page(15, false, 45)])).toBeUndefined();
  });
});
