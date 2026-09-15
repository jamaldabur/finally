import type { NextConfig } from "next";

const isProd = process.env.NODE_ENV === "production";

// `output: 'export'` and `rewrites()` are mutually exclusive: a static export has no
// server to apply rewrites, and Next.js errors if `next dev` sees `output: 'export'`
// alongside a rewrite. So only build for static export in production; in dev, skip
// `output: 'export'` entirely and instead proxy `/api/*` to the local FastAPI backend.
// Production is served same-origin by FastAPI, so no proxy is needed there.
const nextConfig: NextConfig = isProd
  ? {
      output: "export",
    }
  : {
      async rewrites() {
        return [
          {
            source: "/api/:path*",
            destination: "http://localhost:8000/api/:path*",
          },
        ];
      },
    };

export default nextConfig;
