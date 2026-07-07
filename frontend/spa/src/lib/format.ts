// Shared, pure display + pagination helpers used across SPA pages (album grid
// and album detail). Kept DOM-free so they can be unit-tested in the node
// Vitest environment without a browser.

import type { AlbumMediaPage } from "../types/api";

const MONTHS_FR = [
  "Janvier",
  "Février",
  "Mars",
  "Avril",
  "Mai",
  "Juin",
  "Juillet",
  "Août",
  "Septembre",
  "Octobre",
  "Novembre",
  "Décembre",
];

/**
 * Format an ISO date (YYYY-MM-DD) as a French "Month Year" label, matching the
 * server-rendered album grid. Returns the raw value on an unparseable date and
 * an empty string on a nullish one.
 */
export function formatMonthYear(dateStr: string | null | undefined): string {
  if (!dateStr) return "";
  const date = new Date(dateStr);
  if (Number.isNaN(date.getTime())) return dateStr;
  return `${MONTHS_FR[date.getMonth()]} ${date.getFullYear()}`;
}

/**
 * Participants are stored "|"-separated in the DB and displayed
 * comma-separated (parity with the Jinja2 templates).
 */
export function formatParticipants(participants: string | null | undefined): string {
  if (!participants) return "Pas de participants";
  return participants.split("|").join(", ");
}

/**
 * Pagination helper for the album-detail infinite media query. Given every
 * page loaded so far, returns the offset of the next page, or `undefined` when
 * the last page reported no more items (which stops React Query from fetching
 * further pages). The offset is the cumulative count of already-loaded items,
 * matching the `GET /album/{id}/images?offset=&limit=` contract.
 */
export function getNextMediaOffset(pages: AlbumMediaPage[]): number | undefined {
  if (pages.length === 0) return 0;
  const lastPage = pages[pages.length - 1];
  if (!lastPage.has_more) return undefined;
  return pages.reduce((count, page) => count + page.items.length, 0);
}
