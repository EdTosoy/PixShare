"use client";

import Image from "next/image";
import Link from "next/link";
import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAuth, useUser } from "@clerk/nextjs";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiUrl } from "@/lib/api";
import { getPost, updatePost } from "@/lib/posts";

export default function EditPostPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();

  const { getToken } = useAuth();
  const { isLoaded, isSignedIn, user } = useUser();

  const queryClient = useQueryClient();

  const [caption, setCaption] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);

  const postQuery = useQuery({
    queryKey: ["posts", params.id],
    enabled: isLoaded && isSignedIn,
    queryFn: async () => {
      const token = await getToken();

      return getPost(params.id, token);
    },
  });

  const post = postQuery.data;

  const isOwner = Boolean(user && post && post.user_id === user.id);

  const mutation = useMutation({
    mutationFn: async () => {
      if (!isOwner) {
        throw new Error("You do not have permission to edit this post.");
      }

      const token = await getToken();

      if (!token) {
        throw new Error("You must be signed in.");
      }

      return updatePost(
        params.id,
        {
          ...(caption !== null ? { caption } : {}),
          ...(file ? { file } : {}),
        },
        token,
      );
    },

    onSuccess: async (updatedPost) => {
      await queryClient.invalidateQueries({
        queryKey: ["posts"],
      });

      await queryClient.invalidateQueries({
        queryKey: ["posts", updatedPost.id],
      });

      router.push(`/posts/${updatedPost.id}`);
    },
  });

  if (!isLoaded) {
    return (
      <main className="mx-auto max-w-2xl px-4 py-10 sm:px-6">
        <div className="animate-pulse space-y-4">
          <div className="h-4 w-24 rounded bg-gray-200 dark:bg-[#21262d]" />
          <div className="h-8 w-40 rounded bg-gray-200 dark:bg-[#21262d]" />
          <div className="h-80 rounded-md bg-gray-200 dark:bg-[#161b22]" />
        </div>
      </main>
    );
  }

  if (!isSignedIn) {
    return (
      <main className="mx-auto max-w-2xl px-4 py-10 sm:px-6">
        <div className="rounded-md border border-gray-300 p-6 dark:border-[#30363d]">
          <h1 className="font-semibold">Sign in required</h1>

          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            You must be signed in to edit a post.
          </p>

          <Link
            href={`/posts/${params.id}`}
            className="mt-4 inline-block text-sm font-medium underline underline-offset-4"
          >
            Back to post
          </Link>
        </div>
      </main>
    );
  }

  if (postQuery.isLoading) {
    return (
      <main className="mx-auto max-w-2xl px-4 py-10 sm:px-6">
        <div className="animate-pulse space-y-6">
          <div className="h-4 w-28 rounded bg-gray-200 dark:bg-[#21262d]" />
          <div className="h-8 w-40 rounded bg-gray-200 dark:bg-[#21262d]" />
          <div className="h-80 rounded-md bg-gray-200 dark:bg-[#161b22]" />
          <div className="h-24 rounded-md bg-gray-200 dark:bg-[#161b22]" />
        </div>
      </main>
    );
  }

  if (postQuery.isError || !post) {
    return (
      <main className="mx-auto max-w-2xl px-4 py-10 sm:px-6">
        <div className="rounded-md border border-gray-300 p-6 dark:border-[#30363d]">
          <h1 className="font-semibold">Post not found</h1>

          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            The post may have been deleted or is no longer available.
          </p>

          <Link
            href="/posts"
            className="mt-4 inline-block text-sm font-medium underline underline-offset-4"
          >
            Back to posts
          </Link>
        </div>
      </main>
    );
  }

  // Authenticated user does not own this post.
  if (!isOwner) {
    return (
      <main className="mx-auto max-w-2xl px-4 py-10 sm:px-6">
        <div className="rounded-md border border-gray-300 p-6 dark:border-[#30363d]">
          <h1 className="font-semibold">You can't edit this post</h1>

          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            Only the owner of this post can make changes.
          </p>

          <Link
            href={`/posts/${post.id}`}
            className="mt-4 inline-block text-sm font-medium underline underline-offset-4"
          >
            Back to post
          </Link>
        </div>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-2xl px-4 py-10 sm:px-6">
      <div className="mb-8 border-b border-gray-200 pb-6 dark:border-[#30363d]">
        <Link
          href={`/posts/${post.id}`}
          className="text-sm text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white"
        >
          ← Back to post
        </Link>

        <h1 className="mt-4 text-2xl font-semibold tracking-tight">
          Edit post
        </h1>

        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Update the caption or replace the image.
        </p>
      </div>

      <div className="overflow-hidden rounded-md border border-gray-200 bg-gray-50 dark:border-[#30363d] dark:bg-[#161b22]">
        <div className="relative h-80">
          <Image
            src={apiUrl(post.url)}
            alt={post.caption ?? post.file_name}
            fill
            sizes="(max-width: 768px) 100vw, 672px"
            className="object-contain"
          />
        </div>
      </div>

      <form
        className="mt-8 space-y-6"
        onSubmit={(event) => {
          event.preventDefault();
          mutation.mutate();
        }}
      >
        <div>
          <label htmlFor="caption" className="mb-2 block text-sm font-medium">
            Caption
          </label>

          <textarea
            id="caption"
            defaultValue={post.caption ?? ""}
            onChange={(event) => setCaption(event.target.value)}
            className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm outline-none placeholder:text-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:border-[#30363d] dark:bg-[#0d1117]"
            rows={4}
            placeholder="Add a caption..."
          />
        </div>

        <div>
          <label
            htmlFor="replace-image"
            className="mb-2 block text-sm font-medium"
          >
            Replace image
          </label>

          <label
            htmlFor="replace-image"
            className="flex cursor-pointer items-center rounded-md border border-gray-300 px-3 py-3 text-sm hover:bg-gray-50 dark:border-[#30363d] dark:hover:bg-[#161b22]"
          >
            <span className="truncate">
              {file ? file.name : "Choose a new image"}
            </span>

            <input
              id="replace-image"
              type="file"
              accept="image/*"
              className="sr-only"
              onChange={(event) => {
                setFile(event.target.files?.[0] ?? null);
              }}
            />
          </label>
        </div>

        {mutation.isError && (
          <div className="rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-800 dark:border-red-900 dark:bg-[#2d1117] dark:text-red-300">
            {mutation.error.message}
          </div>
        )}

        <div className="flex items-center justify-end gap-3 border-t border-gray-200 pt-6 dark:border-[#30363d]">
          <Link
            href={`/posts/${post.id}`}
            className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium hover:bg-gray-50 dark:border-[#30363d] dark:hover:bg-[#161b22]"
          >
            Cancel
          </Link>

          <button
            type="submit"
            disabled={mutation.isPending}
            className="rounded-md bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-700 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-[#238636] dark:hover:bg-[#2ea043]"
          >
            {mutation.isPending ? "Saving..." : "Save changes"}
          </button>
        </div>
      </form>
    </main>
  );
}
