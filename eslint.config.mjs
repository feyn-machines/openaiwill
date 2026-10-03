import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    // Local, gitignored agent skills; third-party code we do not lint.
    ".agents/**",
    ".claude/**",
    // Local-only crawler and X login module (ignored by Git, includes vendored JS).
    "local/**",
    // Assembled releases hold the compiled server and its dependencies.
    ".release/**",
  ]),
]);

export default eslintConfig;
