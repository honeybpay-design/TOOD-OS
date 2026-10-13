import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  rewrites: async () => [
    {
      source: "/api/:path*",
      destination: `${process.env.API_URL ?? "http://localhost:8000"}/v1/:path*`,
    },
  ],
};

export default nextConfig;
