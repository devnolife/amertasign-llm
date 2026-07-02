import type { NextConfig } from "next";

// Origin yang diizinkan saat dev di belakang tunnel (Cloudflare/Dev Tunnels).
// Tambahan spesifik bisa di-inject lewat env NEXT_ALLOWED_DEV_ORIGIN.
const allowedDevOrigins = [
  "*.trycloudflare.com",
  "*.devtunnels.ms",
  ...(process.env.NEXT_ALLOWED_DEV_ORIGIN
    ? [process.env.NEXT_ALLOWED_DEV_ORIGIN]
    : []),
];

const nextConfig: NextConfig = {
  // Output minimal untuk image Docker produksi (.next/standalone + server.js).
  output: "standalone",
  allowedDevOrigins,
};

export default nextConfig;
