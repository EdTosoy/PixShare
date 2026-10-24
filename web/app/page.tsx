import Link from "next/link";
import { Gallery } from "@/components/Gallery";

export default function Home() {
  return (
    <main id="main" className="page-shell">
      <section className="hero">
        <h1>
          Your photographs,
          <br /> together.
        </h1>
        <div className="hero-bottom">
          <p>
            A simple place to collect and share your photographs.
          </p>
          <Link href="/upload" className="button primary">
            Upload a photograph
          </Link>
        </div>
      </section>
      <div className="section-heading">
        <div>
          <h2>Recent photographs</h2>
        </div>
        <Link className="text-link" href="/explore">
          Explore all images
        </Link>
      </div>
      <Gallery featured />
      <section className="join-panel">
        <div>
          <h2>Something worth keeping?</h2>
          <p>Add a photograph to the album.</p>
        </div>
        <Link href="/upload" className="button secondary">
          Upload an image
        </Link>
      </section>
    </main>
  );
}
