import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Allow accessing Next.js dev server across LAN IPs and mDNS
  // @ts-ignore Next.js allowedDevOrigins
  allowedDevOrigins: [
    "localhost",
    "127.0.0.1",
    "raspi5.local",
    "raspi2w.local",
    "192.168.0.120",
    "192.168.0.95",
  ],
};

export default nextConfig;
