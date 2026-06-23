import type { NextConfig } from "next";

const configuredBackendUrl = process.env.BACKEND_URL?.trim();
const isProductionBuild = process.env.NODE_ENV === "production";

if (isProductionBuild && !configuredBackendUrl) {
  throw new Error("BACKEND_URL is required for production builds.");
}

const backendUrl = configuredBackendUrl || "http://localhost:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
      {
        source: "/health",
        destination: `${backendUrl}/health`,
      },
    ];
  },
};

export default nextConfig;
