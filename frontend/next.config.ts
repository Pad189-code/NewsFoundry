import type { NextConfig } from "next";

/** Cible du proxy interne (lus au démarrage de Next depuis .env / .env.local). */
const backendProxyTarget = (
  process.env.BACKEND_PROXY_TARGET?.trim() || "http://127.0.0.1:8000"
).replace(/\/+$/, "");

const nextConfig: NextConfig = {
  async rewrites() {
    if (!/^https?:\/\//i.test(backendProxyTarget)) {
      return [];
    }
    return [
      {
        source: "/api-backend/:path*",
        destination: `${backendProxyTarget}/:path*`,
      },
    ];
  },
};

export default nextConfig;
