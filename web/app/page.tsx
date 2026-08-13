import Link from "next/link";

export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-6xl flex-col items-center justify-center px-6">
      <h1 className="text-5xl font-bold tracking-tight">PixShare</h1>

      <p className="mt-4 text-center text-gray-600">
        Share and manage your images.
      </p>

      <Link
        href="/posts"
        className="mt-8 rounded-lg bg-black px-5 py-3 text-white"
      >
        View posts
      </Link>
    </main>
  );
}
