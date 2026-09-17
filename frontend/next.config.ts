import type { NextConfig } from "next";

// D-10 / PLAN.md §3: static export, single-origin deployment behind FastAPI.
// Do NOT add rewrites/redirects/headers here — Next.js errors on those under
// `output: 'export'`, including during `next dev` (02-RESEARCH.md Pitfall 1).
// Local dev instead targets the backend via NEXT_PUBLIC_API_BASE_URL
// (see lib/api.ts / lib/priceStore.tsx) plus a dev-only CORS middleware on
// the FastAPI app (backend/app/main.py).
const nextConfig: NextConfig = {
  output: "export",
  images: { unoptimized: true },
};

export default nextConfig;
