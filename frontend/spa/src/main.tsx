import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";

import { App } from "./App";
import { queryClient } from "./lib/queryClient";
import "./index.css";

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("Élément racine #root introuvable");
}

createRoot(rootElement).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      {/* basename must match the FastAPI /app mount (frontend/spa_serving.py). */}
      <BrowserRouter basename="/app">
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
