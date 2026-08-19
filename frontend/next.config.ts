import type { NextConfig } from "next";

// Docker: http://api:8000 — Browser nutzt nur :3000, kein NEXT_PUBLIC nötig
const apiInternal = process.env.API_INTERNAL_URL || "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${apiInternal}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
