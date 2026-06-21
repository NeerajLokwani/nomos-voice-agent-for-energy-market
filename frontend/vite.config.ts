import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In dev, proxy the API routes to the FastAPI backend on :8000 so the React app
// (on :5173) talks to the real orchestrator. In prod, `npm run build` emits ./dist,
// which FastAPI serves directly — same origin, no proxy needed.
const apiRoutes = ["/api", "/cases", "/calls", "/tools", "/results", "/triggers", "/voice", "/elevenlabs", "/twilio", "/health"];

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: Object.fromEntries(
      apiRoutes.map((r) => [r, { target: "http://localhost:8000", changeOrigin: true }])
    ),
  },
  build: { outDir: "dist", emptyOutDir: true },
});
