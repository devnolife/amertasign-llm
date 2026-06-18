import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Output minimal untuk image Docker produksi (.next/standalone + server.js).
  output: "standalone",
};

export default nextConfig;
