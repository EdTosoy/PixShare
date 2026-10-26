import type { Metadata } from "next";
import Link from "next/link";
import { Providers } from "./providers";
import { Navigation } from "@/components/Navigation";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "PixShare | Your photographs, together",
    template: "%s | PixShare",
  },
  description:
    "A simple online photo album. Upload photographs, add captions, and keep your moments together.",
  manifest: "/site.webmanifest",
  icons: {
    apple: [{ url: "/apple-touch-icon.png", sizes: "180x180", type: "image/png" }],
  },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="stylesheet" href="https://api.fontshare.com/v2/css?f[]=sentient@300,400&display=swap" />
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
          <p>A simple photo album.</p>
          <Link href="/explore">Explore the gallery</Link>
        </footer>
      </body>
    </html>
  );
}
