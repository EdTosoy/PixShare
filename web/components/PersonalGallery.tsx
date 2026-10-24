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
            <h1>My album.</h1>
            <p>Add a photograph or edit a caption.</p>
          </div>
          <Link className="button primary" href="/upload">
            Upload image
          </Link>
        </div>
        <Gallery personal />
      </AuthGate>
    </main>
  );
}
