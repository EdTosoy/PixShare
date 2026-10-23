import type { Metadata } from "next";
import Link from "next/link";
import { Providers } from "./providers";
import { Navigation } from "@/components/Navigation";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "PixShare — A place for your perspective",
    template: "%s · PixShare",
  },
  description:
    "Discover a new perspective. A simple home for the photographs, moments, and ideas you want to share.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `try{const t=localStorage.getItem('theme');if(t==='light'||t==='dark')document.documentElement.dataset.theme=t}catch{}`,
          }}
        />
      </head>
      <body>
        <a className="skip-link" href="#main">
          Skip to content
        </a>
        <Providers>
          <Navigation />
          {children}
        </Providers>
        <footer className="site-footer">
          <Link className="brand" href="/">
            PixShare<span aria-hidden="true">.</span>
          </Link>
          <p>A little more perspective.</p>
          <Link href="/explore">Explore the gallery ↗</Link>
        </footer>
      </body>
    </html>
  );
}
