import { Gallery } from "@/components/Gallery";
export const metadata = { title: "Explore" };
export default function ExplorePage() {
  return (
    <main id="main" className="page-shell">
      <div className="page-heading">
        <span className="eyebrow">OPEN YOUR EYES TO SOMETHING NEW</span>
        <h1>
          Explore perspectives<span className="accent">.</span>
        </h1>
        <p>
          Places, moments, and ideas. See the world through someone else’s lens.
        </p>
      </div>
      <Gallery />
    </main>
  );
}
