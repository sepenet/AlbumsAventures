import type { Config } from "tailwindcss";

// Design tokens are reused from docs/GUIDELINES_UI.md:
//   - accent: sky-500 -> blue-600 gradient, sky-600 primary buttons
//   - surfaces: white / gray-800 cards, gray-50 -> gray-100 (light) and
//     gray-900 -> gray-800 (dark) page backgrounds
//   - dark mode: toggled via the `dark` class on <html>
// These all live in Tailwind's default palette, so this config only enables
// class-based dark mode and content scanning; the token conventions are
// carried by the utility classes used in src/**.
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {},
  },
  plugins: [],
} satisfies Config;
