import type { Metadata } from "next";
import { Show, SignInButton, SignUpButton, UserButton } from "@clerk/nextjs";
import { Geist, Geist_Mono } from "next/font/google";

import { Providers } from "./providers";
import "./globals.css";
import Link from "next/link";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Pix-Share",
  description: "Share and manage your images and files.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full bg-white text-gray-900 dark:bg-[#0d1117] dark:text-gray-100">
        <Providers>
          <header className="border-b border-gray-200 bg-white dark:border-[#30363d] dark:bg-[#010409]">
            <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
              <Link
                href="/posts"
                className="text-lg font-semibold tracking-tight hover:text-gray-600 dark:hover:text-gray-300"
              >
                Pix-Share
              </Link>

              <div className="flex items-center gap-3">
                <Show when="signed-out">
                  <SignInButton>
                    <button
                      type="button"
                      className="rounded-md px-3 py-2 text-sm font-medium hover:bg-gray-100 dark:hover:bg-[#21262d]"
                    >
                      Sign in
                    </button>
                  </SignInButton>

                  <SignUpButton>
                    <button
                      type="button"
                      className="rounded-md border border-gray-300 bg-gray-900 px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-gray-700 dark:border-gray-600 dark:bg-[#238636] dark:hover:bg-[#2ea043]"
                    >
                      Sign up
                    </button>
                  </SignUpButton>
                </Show>

                <Show when="signed-in">
                  <UserButton />
                </Show>
              </div>
            </div>
          </header>

          {children}
        </Providers>
      </body>
    </html>
  );
}
