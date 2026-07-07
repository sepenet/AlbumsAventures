import { useCallback, useEffect } from "react";

import type { MediaItem } from "../types/api";

interface LightboxProps {
  items: MediaItem[];
  /** Index of the currently displayed item, or `null` when the lightbox is closed. */
  index: number | null;
  onClose: () => void;
  onNavigate: (nextIndex: number) => void;
}

/**
 * Minimal, dependency-free fullscreen media viewer — a PhotoSwipe-equivalent
 * for the SPA that avoids the CDN `<script>`/`<link>` the Jinja2 page used
 * (keeping the tightened same-origin CSP intact). Images are shown at their
 * `full_url`; videos play inline with native controls. Keyboard: Escape closes,
 * ArrowLeft/ArrowRight navigate.
 */
export function Lightbox({ items, index, onClose, onNavigate }: LightboxProps) {
  const isOpen = index !== null && index >= 0 && index < items.length;

  const goPrev = useCallback(() => {
    if (index === null) return;
    onNavigate((index - 1 + items.length) % items.length);
  }, [index, items.length, onNavigate]);

  const goNext = useCallback(() => {
    if (index === null) return;
    onNavigate((index + 1) % items.length);
  }, [index, items.length, onNavigate]);

  useEffect(() => {
    if (!isOpen) return;

    function handleKey(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
      else if (event.key === "ArrowLeft") goPrev();
      else if (event.key === "ArrowRight") goNext();
    }

    document.addEventListener("keydown", handleKey);
    // Prevent the page behind the overlay from scrolling while it is open.
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", handleKey);
      document.body.style.overflow = previousOverflow;
    };
  }, [isOpen, onClose, goPrev, goNext]);

  if (!isOpen || index === null) return null;

  const current = items[index];

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={current.filename}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/90"
      onClick={onClose}
    >
      {/* Close */}
      <button
        type="button"
        onClick={onClose}
        aria-label="Fermer"
        className="absolute right-4 top-4 z-10 rounded-full bg-white/10 p-2 text-white transition-colors hover:bg-white/20"
      >
        <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>

      {items.length > 1 ? (
        <>
          <button
            type="button"
            onClick={(event) => {
              event.stopPropagation();
              goPrev();
            }}
            aria-label="Image précédente"
            className="absolute left-4 z-10 rounded-full bg-white/10 p-2 text-white transition-colors hover:bg-white/20"
          >
            <svg className="h-8 w-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <button
            type="button"
            onClick={(event) => {
              event.stopPropagation();
              goNext();
            }}
            aria-label="Image suivante"
            className="absolute right-4 z-10 rounded-full bg-white/10 p-2 text-white transition-colors hover:bg-white/20"
          >
            <svg className="h-8 w-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </>
      ) : null}

      {/* Media — stop propagation so clicking the media itself does not close. */}
      <div
        className="flex max-h-[90vh] max-w-[90vw] items-center justify-center"
        onClick={(event) => event.stopPropagation()}
      >
        {current.is_video ? (
          <video
            key={current.full_url}
            src={current.full_url}
            controls
            autoPlay
            className="max-h-[90vh] max-w-[90vw] rounded-lg"
          />
        ) : (
          <img
            src={current.full_url}
            alt={current.filename}
            className="max-h-[90vh] max-w-[90vw] rounded-lg object-contain"
          />
        )}
      </div>
    </div>
  );
}
