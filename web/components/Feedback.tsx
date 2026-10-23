import Link from "next/link";
import { useSession } from "@/app/providers";

export function ErrorState({
  message,
  retry,
}: {
  message: string;
  retry?: () => void;
}) {
  return (
    <div className="state-panel" role="alert">
      <h2>That didn’t quite work.</h2>
      <p>{message}</p>
      {retry && (
        <button className="button secondary" onClick={retry}>
          Try again
        </button>
      )}
    </div>
  );
}
export function GallerySkeleton() {
  return (
    <div className="photo-grid" aria-label="Loading images" role="status">
      {Array.from({ length: 6 }, (_, i) => (
        <div className="skeleton skeleton-card" key={i} />
      ))}
      <span className="sr-only">Loading images…</span>
    </div>
  );
}
export function AuthGate({ children }: { children: React.ReactNode }) {
  const session = useSession();
  if (!session.isLoaded)
    return (
      <div role="status" className="skeleton skeleton-form">
        Loading your session…
      </div>
    );
  if (!session.isSignedIn)
    return (
      <div className="state-panel">
        <span className="eyebrow">YOUR SPACE</span>
        <h1>Make yourself at home.</h1>
        <p>
          {session.configured
            ? "Sign in to share your images and manage your gallery."
            : "Public browsing is available. Add Clerk keys to enable sign-in and sharing."}
        </p>
        {session.configured && (
          <Link className="button primary" href="/sign-in">
            Sign in to PixShare
          </Link>
        )}
        <Link className="text-link" href="/explore">
          Explore images ↗
        </Link>
      </div>
    );
  return children;
}
