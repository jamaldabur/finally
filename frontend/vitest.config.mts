// Vitest configuration for the frontend unit-test suite (Phase 6, TEST-04,
// D-03). Follows the official Next.js Vitest guide bundled with this exact
// installed Next.js version
// (frontend/node_modules/next/dist/docs/01-app/02-guides/testing/vitest.md),
// with two project-specific corrections recorded in 06-02-PLAN.md:
//
// - `.mts` extension (P-02): frontend/package.json has no `"type": "module"`,
//   and `@vitejs/plugin-react@6` / `vite-tsconfig-paths@6` are ESM-only. The
//   `.mts` extension makes this config an ES module regardless of the
//   package's own module type. `tsconfig.json` already includes `**/*.mts`,
//   so `npm run typecheck` covers this file too.
// - `vite-tsconfig-paths` resolves the project's `@/*` alias
//   (frontend/tsconfig.json) inside Vitest, which does not read
//   `tsconfig.json` path mappings on its own.
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import tsconfigPaths from "vite-tsconfig-paths";

export default defineConfig({
  plugins: [tsconfigPaths(), react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
    include: ["**/*.test.ts", "**/*.test.tsx"],
    exclude: ["node_modules/**", ".next/**", "out/**"],
  },
});
