/** @type {import('next').NextConfig} */
const nextConfig = {
  // PGlite (Postgres WASM) and postgres.js must stay server-side, unbundled.
  serverExternalPackages: ["@electric-sql/pglite", "postgres", "bcryptjs"],
  poweredByHeader: false,
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
        ],
      },
    ];
  },
};
export default nextConfig;
