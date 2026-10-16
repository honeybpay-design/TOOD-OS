import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  rewrites: async () => {
    const apiUrl = process.env.API_URL ?? "http://localhost:8000";
    return [
      // OAuth callback — must come before the catch-all rewrites
      {
        source: "/auth/google/callback",
        destination: `${apiUrl}/v1/auth/google/callback`,
      },
      {
        source: "/api/:path*",
        destination: `${apiUrl}/v1/:path*`,
      },
      // Direct /v1/:path* rewrite for API access
      {
        source: "/v1/:path*",
        destination: `${apiUrl}/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
