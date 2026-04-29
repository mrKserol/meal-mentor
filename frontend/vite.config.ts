import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      // NOTE: в текущей среде генерация SW через workbox-build падает.
      // Поэтому манифест/иконки подключаем вручную (public/manifest.webmanifest),
      // а минимальный service worker используем из public/sw.js.
      disable: true,
      manifest: false,
      includeAssets: ["icons/apple-touch-icon.png"],
    }),
  ],
  build: {
    // Avoid terser hook early-exit during service worker generation.
    minify: false,
  },
});
