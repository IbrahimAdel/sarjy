import path from "node:path"

import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vitest/config"

const PROXY_TARGET = process.env.VITE_PROXY_TARGET ?? "http://localhost:8000"

const proxy = {
  "/auth": PROXY_TARGET,
  "/.well-known": PROXY_TARGET,
  "/metrics": PROXY_TARGET,
  "/ws": { target: PROXY_TARGET, ws: true },
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(import.meta.dirname, "./src"),
    },
  },
  server: {
    proxy,
  },
  preview: {
    host: true,
    allowedHosts: true,
    proxy,
  },
  test: {
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
  },
})
