/** @type {import('next').NextConfig} */
const nextConfig = {
  // Standalone runner: self-contained server.js, no node_modules in the
  // final image.
  output: 'standalone',

  // Same-origin proxy: the browser only ever calls /api/* on the Next.js
  // origin; Next.js forwards those requests server-side to the FastAPI
  // backend. This is what makes the JWT cookie first-party on the frontend
  // origin. BACKEND_URL is server-side only — never exposed to the client.
  // NOTE: Next.js resolves rewrites() at BUILD time, so BACKEND_URL must be
  // set as a build arg/env when building (the Dockerfile defaults it to
  // http://backend:8000, the compose-network value).
  async rewrites() {
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';
    return [
      {
        source: '/api/:path*',
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
