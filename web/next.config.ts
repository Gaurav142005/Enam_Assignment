import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone", // self-contained server for the Docker image (see /Dockerfile)
  // A first question about a company fetches its transcripts before answering; allow for that through the /api proxy.
  experimental: { proxyTimeout: 120_000 },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${process.env.API_URL ?? "http://localhost:8000"}/:path*` }];
  },
};

export default nextConfig;
