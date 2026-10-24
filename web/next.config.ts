import type { NextConfig } from "next";

if (process.env.PIXSHARE_ENVIRONMENT === "production") {
  const url = new URL(process.env.NEXT_PUBLIC_API_URL || "http://localhost");
  if (url.protocol !== "https:" || url.hostname === "localhost" || url.username || url.password || url.search || url.hash ||
      !process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY?.startsWith("pk_live_"))
    throw new Error("Production frontend builds require an HTTPS API URL and a live Clerk publishable key");
}

const nextConfig: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  headers() {
    return [{ source: "/:path*", headers: [
      { key: "X-Content-Type-Options", value: "nosniff" },
      { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
      { key: "X-Frame-Options", value: "DENY" },
      { key: "Content-Security-Policy", value: "frame-ancestors 'none'; base-uri 'self'; object-src 'none'" },
      { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
    ] }];
  },
  // Media is fetched by the browser, including when web runs in Docker.
  // API-generated WebP srcsets live in <picture>; original URLs remain fallbacks.
  // Local and absolute S3/CDN URLs are browser-direct. No server-side image
  // proxy, wildcard remote-host allowance, or private-IP exception is enabled.
  images: { unoptimized: true },
};

export default nextConfig;
