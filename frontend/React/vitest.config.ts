import { defineConfig, mergeConfig } from "vitest/config";
import viteConfig from "./vite.config.ts";

// Tests run the app's own Vite setup (React, the @ alias) in a simulated browser.
export default defineConfig((env) =>
  mergeConfig(viteConfig(env), {
    test: { environment: "jsdom", include: ["src/**/*.test.{ts,tsx}"] },
  }),
);
