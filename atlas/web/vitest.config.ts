import { defineConfig } from "vitest/config";
import path from "path";

export default defineConfig({
  // the components are Next's (tsconfig keeps JSX as written for Next's
  // compiler); the unit tests that render one need it compiled for React
  // here (Phase 4d: the political lean card and cell)
  oxc: { jsx: { runtime: "automatic" } },
  resolve: {
    alias: { "@": path.resolve(__dirname, "src") },
  },
  test: {
    include: ["tests/**/*.test.ts"],
    environment: "node",
  },
});
