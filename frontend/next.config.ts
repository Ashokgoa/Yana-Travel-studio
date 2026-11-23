import type { NextConfig } from "next";

/**
 * Where the Next server forwards API calls. Browsers never talk to the backend
 * directly: they call /api/v1/* on the same origin (port 3000), and Next proxies
 * it here. This lets other machines on the network use the app through a single
 * port, keeps the backend private on 127.0.0.1, and keeps the session cookie
 * same-origin. Read at build/start time (server-side only).
 */
const BACKEND_URL = (process.env.BACKEND_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");

const nextConfig: NextConfig = {
  // Test-only: lets an isolated second dev server run next to your own (Next allows
  // one dev server per build folder). Unset in normal use.
  ...(process.env.NEXT_DIST_DIR ? { distDir: process.env.NEXT_DIST_DIR } : {}),
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  async rewrites() {
    return [{ source: "/api/v1/:path*", destination: `${BACKEND_URL}/api/v1/:path*` }];
  },
};

export default nextConfig;
