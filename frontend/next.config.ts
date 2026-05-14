import type { NextConfig } from "next";

/**
 * Appels API same-origin via ``/api-backend/*`` : proxy implémenté dans
 * ``src/app/api-backend/[[...path]]/route.ts`` (lit ``BACKEND_PROXY_TARGET``
 * à l’exécution — requis sur Vercel ; défaut local ``http://127.0.0.1:8000``).
 */
const nextConfig: NextConfig = {};

export default nextConfig;
