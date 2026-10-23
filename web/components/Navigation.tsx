"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { UserButton } from "@clerk/nextjs";
import { useSyncExternalStore } from "react";
import { useSession } from "@/app/providers";

function subscribeTheme(callback: () => void) {
  window.addEventListener("storage", callback);
  window.addEventListener("pixshare-theme", callback);
  const media = window.matchMedia("(prefers-color-scheme: dark)");
  media.addEventListener("change", callback);
  return () => {
    window.removeEventListener("storage", callback);
    window.removeEventListener("pixshare-theme", callback);
    media.removeEventListener("change", callback);
  };
}
function readTheme() {
  try {
    return (
      localStorage.getItem("theme") ??
      (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")
    );
  } catch {
    return "light";
  }
}

export function Navigation() {
  const pathname = usePathname();
  const { isSignedIn, isLoaded } = useSession();
  const theme = useSyncExternalStore(subscribeTheme, readTheme, () => "system");
  return (
    <header className="site-header">
      <div className="nav-shell">
        <Link href="/" className="brand" aria-label="PixShare home">
          <span className="brand-mark" aria-hidden="true">
            p.
          </span>
          PixShare
        </Link>
        <nav aria-label="Main navigation" className="main-nav">
          <Link
            href="/explore"
            aria-current={pathname === "/explore" ? "page" : undefined}
          >
            Explore
          </Link>
          <Link
            href="/me"
            aria-current={pathname === "/me" ? "page" : undefined}
          >
            My gallery
          </Link>
        </nav>
        <div className="nav-actions">
          <button
            className="theme-toggle"
            aria-label="Toggle color theme"
            title="Toggle color theme"
            onClick={() => {
              const next = readTheme() === "dark" ? "light" : "dark";
              document.documentElement.dataset.theme = next;
              try {
                localStorage.setItem("theme", next);
              } catch {
                /* Theme still works without persistence. */
              }
              window.dispatchEvent(new Event("pixshare-theme"));
            }}
          >
            <span aria-hidden="true">{theme === "dark" ? "☀" : "◐"}</span>
          </button>
          <Link className="button primary upload-nav" href="/upload">
            <span aria-hidden="true">＋</span> Upload
            <span className="desktop-word"> image</span>
          </Link>
          {isLoaded &&
            (isSignedIn ? (
              <UserButton />
            ) : (
              <Link href="/sign-in" className="sign-in-link">
                Sign in
              </Link>
            ))}
        </div>
      </div>
    </header>
  );
}
