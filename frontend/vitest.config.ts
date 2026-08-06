import { defineConfig } from "vitest/config";

// Unit tests for pure logic (no DOM). Component/E2E testing is out of scope here.
export default defineConfig({
  test: {
    environment: "node",
    include: ["src/**/*.test.{ts,tsx}"],
    coverage: {
      provider: "v8",
      include: ["src/features/catalog/search.ts"],
      reporter: ["text", "text-summary"],
    },
  },
});
