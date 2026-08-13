"use client";

import Image from "next/image";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useAuth, useUser } from "@clerk/nextjs";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiUrl } from "@/lib/api";
import { deletePost, getPost } from "@/lib/posts";

export default function PostPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { getToken } = useAuth();
  const queryClient = useQueryClient();
  const { isLoaded, isSignedIn, user } = useUser();

  const postQuery = useQuery({
    queryKey: ["posts", params.id],
    queryFn: async () => {
      const token = await getToken();

      return getPost(params.id, token);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async () => {
      const token = await getToken();

      if (!token) {
        throw new Error("You must be signed in.");
      }

      return deletePost(params.id, token);
    },

    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["posts"],
      });

      router.push("/posts");
    },
  });

  if (postQuery.isLoading) {
    return (
      <main className="mx-auto max-w-4xl px-4 py-10 sm:px-6">
        <div className="aspect-video animate-pulse rounded-md bg-gray-100 dark:bg-[#161b22]" />
      </main>
    );
  }

  if (postQuery.isError || !postQuery.data) {
    return (
      <main className="mx-auto max-w-4xl px-4 py-10 sm:px-6">
        <div className="rounded-md border border-gray-300 p-6 dark:border-[#30363d]">
          <h1 className="font-semibold">Post not found</h1>

          <Link
            href="/posts"
            className="mt-4 inline-block text-sm underline underline-offset-4"
          >
            Back to posts
          </Link>
        </div>
      </main>
    );
  }

  const post = postQuery.data;

  const isOwner = isLoaded && isSignedIn && user.id === post.user_id;

  return (
    <main className="mx-auto max-w-4xl px-4 py-10 sm:px-6">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <Link
          href="/posts"
          className="text-sm text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white"
        >
          ← Back to posts
        </Link>

        {isOwner && (
          <div className="flex gap-2">
            <Link
              href={`/posts/${post.id}/edit`}
              className="rounded-md border border-gray-300 px-3 py-2 text-sm font-medium hover:bg-gray-50"
            >
              Edit
            </Link>

            <button
              type="button"
              onClick={() => {
                if (
                  window.confirm("Delete this post? This cannot be undone.")
                ) {
                  deleteMutation.mutate();
                }
              }}
              disabled={deleteMutation.isPending}
              className="rounded-md border border-red-300 px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-50 disabled:opacity-50"
            >
              {deleteMutation.isPending ? "Deleting..." : "Delete"}
            </button>
          </div>
        )}
      </div>

      {deleteMutation.isError && (
        <div className="mb-4 rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-800 dark:border-red-900 dark:bg-[#2d1117] dark:text-red-300">
          {deleteMutation.error.message}
        </div>
      )}

      <div className="overflow-hidden rounded-md border border-gray-200 bg-gray-50 dark:border-[#30363d] dark:bg-[#161b22]">
        <div className="relative min-h-75">
          <Image
            src={apiUrl(post.url)}
            alt={post.caption ?? post.file_name}
            fill
            sizes="(max-width: 768px) 100vw, 768px"
            className="object-contain"
          />
        </div>
      </div>

      <section className="mt-6 border-t border-gray-200 pt-6 dark:border-[#30363d]">
        <h1 className="text-xl font-semibold">
          {post.caption || post.file_name}
        </h1>

        <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-gray-500 dark:text-gray-400">File name</dt>
            <dd className="mt-1 break-all">{post.file_name}</dd>
          </div>

          <div>
            <dt className="text-gray-500 dark:text-gray-400">File type</dt>
            <dd className="mt-1">{post.file_type}</dd>
          </div>

          <div>
            <dt className="text-gray-500 dark:text-gray-400">Created</dt>
            <dd className="mt-1">
              {new Date(post.created_at).toLocaleString()}
            </dd>
          </div>

          <div>
            <dt className="text-gray-500 dark:text-gray-400">Updated</dt>
            <dd className="mt-1">
              {new Date(post.updated_at).toLocaleString()}
            </dd>
          </div>
        </dl>
      </section>
    </main>
  );
}
