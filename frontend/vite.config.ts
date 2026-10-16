import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In local development the SPA is served by Vite and proxies API calls to the
// Django dev server, keeping everything same-origin so session cookies + CSRF
// work without cross-site configuration.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": { target: "http://127.0.0.1:8000", changeOrigin: false },
      "/healthz": { target: "http://127.0.0.1:8000", changeOrigin: false },
      "/readyz": { target: "http://127.0.0.1:8000", changeOrigin: false },
      "/admin": { target: "http://127.0.0.1:8000", changeOrigin: false },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: true,
  },
});
