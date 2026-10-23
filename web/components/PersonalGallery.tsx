"use client";
import Link from "next/link";
import { Gallery } from "@/components/Gallery";
import { AuthGate } from "@/components/Feedback";
export function PersonalGallery({ deleted }: { deleted: boolean }) {
  return (
    <main id="main" className="page-shell">
      <AuthGate>
        {deleted && (
          <p className="success-banner" role="status">
            Your post has been deleted.
          </p>
        )}
        <div className="page-heading split-heading">
          <div>
            <span className="eyebrow">A COLLECTION THAT’S ALL YOU</span>
            <h1>
              My gallery<span className="accent">.</span>
            </h1>
            <p>Keep your favorite moments close.</p>
          </div>
          <Link className="button primary" href="/upload">
            ＋ Upload image
          </Link>
        </div>
        <Gallery personal />
      </AuthGate>
    </main>
  );
}
