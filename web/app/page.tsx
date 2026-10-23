import Link from "next/link";
import { Gallery } from "@/components/Gallery";

export default function Home() {
  return (
    <main id="main" className="page-shell">
      <section className="hero">
        <div className="eyebrow">
          <span className="status-dot" /> A HOME FOR YOUR PERSPECTIVE
        </div>
        <h1>
          Life looks different
          <br />
          through <em>your lens.</em>
        </h1>
        <div className="hero-bottom">
          <p>
            Small moments. Wide horizons. Everyday discoveries.
            <br className="desktop-word" /> A simple space to share what you
            see.
          </p>
          <Link href="/upload" className="button primary">
            Share your perspective <span aria-hidden="true">↗</span>
          </Link>
        </div>
      </section>
      <div className="section-heading">
        <div>
          <span className="eyebrow">THE COMMUNITY GALLERY</span>
          <h2>Fresh perspectives</h2>
        </div>
        <Link className="text-link" href="/explore">
          Explore all images <span aria-hidden="true">↗</span>
        </Link>
      </div>
      <Gallery featured />
      <section className="join-panel">
        <div>
          <span className="eyebrow">THERE’S MORE TO SEE</span>
          <h2>Something worth sharing?</h2>
          <p>Your next favorite image could be yours.</p>
        </div>
        <Link href="/upload" className="button secondary">
          Upload an image ↗
        </Link>
      </section>
    </main>
  );
}
