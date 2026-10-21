import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  rewrites: async () => {
    const apiUrl = process.env.API_URL ?? "http://localhost:8000";
    return [
      {
        source: "/v1/:path*",
        destination: apiUrl + "/v1/:path*",
      },
    ];
  },
};

export default nextConfig;
