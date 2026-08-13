"use client";

import Link from "next/link";
import { useAuth, useUser } from "@clerk/nextjs";
import { useQuery } from "@tanstack/react-query";

import { PostCard } from "@/components/posts/PostCard";
import { getPosts } from "@/lib/posts";

export default function PostsPage() {
  const { getToken } = useAuth();
  const { isLoaded, isSignedIn } = useUser();

  const postsQuery = useQuery({
    queryKey: ["posts"],
    queryFn: async () => {
      const token = await getToken();

      return getPosts(token, {
        limit: 20,
        sort: "newest",
      });
    },
  });

  if (postsQuery.isLoading) {
    return (
      <main className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
        <div className="space-y-4">
          <div className="h-8 w-32 animate-pulse rounded bg-gray-200 dark:bg-[#21262d]" />

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }, (_, index) => (
              <div
                key={index}
                className="overflow-hidden rounded-md border border-gray-200 dark:border-[#30363d]"
              >
                <div className="aspect-square animate-pulse bg-gray-100 dark:bg-[#161b22]" />

                <div className="space-y-2 p-4">
                  <div className="h-4 w-2/3 animate-pulse rounded bg-gray-200 dark:bg-[#21262d]" />
                  <div className="h-3 w-1/3 animate-pulse rounded bg-gray-200 dark:bg-[#21262d]" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </main>
    );
  }

  if (postsQuery.isError) {
    return (
      <main className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
        <div className="rounded-md border border-red-300 bg-red-50 p-4 text-sm text-red-800 dark:border-red-900 dark:bg-[#2d1117] dark:text-red-300">
          Failed to load posts. Please try again.
        </div>
      </main>
    );
  }

  const posts = postsQuery.data ?? [];

  return (
    <main className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
      <div className="mb-8 flex flex-col gap-4 border-b border-gray-200 pb-6 sm:flex-row sm:items-center sm:justify-between dark:border-[#30363d]">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Your posts</h1>

          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            {posts.length} {posts.length === 1 ? "post" : "posts"}
          </p>
        </div>

        <Link
          href="/posts/new"
          className="inline-flex items-center justify-center rounded-md bg-gray-900 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-400 focus:ring-offset-2 dark:bg-[#238636] dark:hover:bg-[#2ea043] dark:focus:ring-offset-[#0d1117]"
        >
          Upload image
        </Link>
      </div>

      {posts.length === 0 ? (
        <div className="rounded-md border border-dashed border-gray-300 px-6 py-16 text-center dark:border-[#30363d]">
          <h2 className="text-base font-semibold">No posts yet</h2>

          <p className="mx-auto mt-2 max-w-md text-sm text-gray-500 dark:text-gray-400">
            Upload your first image to start building your collection.
          </p>

          {isLoaded && isSignedIn && (
            <Link
              href="/posts/new"
              className="mt-6 inline-flex items-center justify-center rounded-md bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-700 dark:bg-[#238636] dark:hover:bg-[#2ea043]"
            >
              Upload image
            </Link>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {posts.map((post) => (
            <PostCard key={post.id} post={post} />
          ))}
        </div>
      )}
    </main>
  );
}
