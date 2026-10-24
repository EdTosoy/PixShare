import { Gallery } from "@/components/Gallery";
export const metadata = { title: "Explore" };
export default function ExplorePage() {
  return (
    <main id="main" className="page-shell">
      <div className="page-heading">
        <h1>Browse photographs.</h1>
        <p>
          Photographs and the moments behind them.
        </p>
      </div>
      <Gallery />
    </main>
  );
}
