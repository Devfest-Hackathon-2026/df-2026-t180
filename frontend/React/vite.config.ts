import { fileURLToPath, URL } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  return {
    plugins: [react()],
    resolve: {
      alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
    },
    server: {
      // The admin screens call /api; in development that goes to the local FastAPI server.
      proxy: { "/api": env.VITE_API_PROXY || "http://127.0.0.1:8000" },
    },
  };
});
