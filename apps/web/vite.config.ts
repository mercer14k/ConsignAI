import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5177,
    proxy: {
      "/api": "http://127.0.0.1:8077",
      "/health": "http://127.0.0.1:8077",
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: "./src/test-setup.ts",
    include: ["src/**/*.test.tsx"],
  },
});
