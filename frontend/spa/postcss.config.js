// PostCSS pipeline for the Vite build: Tailwind compiles the utility classes,
// autoprefixer adds vendor prefixes. This replaces the runtime Tailwind CDN
// (cdn.tailwindcss.com) for the SPA surface with a local, hashed CSS bundle
// served under 'self' (CSP-friendly).
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
