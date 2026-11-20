import { defineConfig, loadEnv } from "vite";
import process from "node:process";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "VITE_");
  return {
    plugins: [react(), tailwindcss()],
    server: {
      port: 5173,
      proxy: {
        "/api/v1": {
          target:
            env.VITE_BACKEND_TARGET || "https://proj.telepathystudios.icu/",
          changeOrigin: true,
        },
      },
    },
    base: "/",
  };
});
