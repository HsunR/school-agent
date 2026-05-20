import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Allow large uploads (e.g. knowledge base files) through the API proxy
  middlewareClientMaxBodySize: "50MB",

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
