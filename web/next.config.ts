import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  // Media is fetched by the browser, including when web runs in Docker.
  // API-generated WebP srcsets live in <picture>; original URLs remain fallbacks.
  images: { unoptimized: true },
};

export default nextConfig;
