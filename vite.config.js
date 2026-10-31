import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    fs: { deny: ["**/.env", "**/.env.*", "**/*.{crt,pem}", "**/.git/**", "**/instance/**"] },
    proxy: {
      "/api": "http://localhost:5000",
      "/health": "http://localhost:5000",
    },
  },
  test: {
    include: ["src/**/*.test.{js,jsx,ts,tsx}"],
    environment: "jsdom",
    setupFiles: "./src/test-setup.js",
    globals: true,
  },
});
