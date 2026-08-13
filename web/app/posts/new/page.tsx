"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import { useMutation } from "@tanstack/react-query";

import { createPost } from "@/lib/posts";

export default function NewPostPage() {
  const router = useRouter();
  const { getToken } = useAuth();

  const [file, setFile] = useState<File | null>(null);
  const [caption, setCaption] = useState("");

  const mutation = useMutation({
    mutationFn: async () => {
      if (!file) {
        throw new Error("Please select an image.");
      }

      const token = await getToken();

      if (!token) {
        throw new Error("You must be signed in.");
      }

      return createPost(
        {
          file,
          caption,
        },
        token,
      );
    },

    onSuccess: (post) => {
      router.push(`/posts/${post.id}`);
    },
  });

  return (
    <main className="mx-auto max-w-2xl px-4 py-10 sm:px-6">
      <div className="mb-8 border-b border-gray-200 pb-6 dark:border-[#30363d]">
        <Link
          href="/posts"
          className="text-sm text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white"
        >
          ← Back to posts
        </Link>

        <h1 className="mt-4 text-2xl font-semibold tracking-tight">
          Upload image
        </h1>

        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Add an image and an optional caption.
        </p>
      </div>

      <form
        className="space-y-6"
        onSubmit={(event) => {
          event.preventDefault();
          mutation.mutate();
        }}
      >
        <div>
          <label htmlFor="image" className="mb-2 block text-sm font-medium">
            Image
          </label>

          <label
            htmlFor="image"
            className="flex cursor-pointer flex-col items-center justify-center rounded-md border border-dashed border-gray-300 px-6 py-12 text-center hover:border-gray-500 hover:bg-gray-50 dark:border-[#30363d] dark:hover:bg-[#161b22]"
          >
            <span className="text-sm font-medium">
              {file ? file.name : "Choose an image"}
            </span>

            <span className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              PNG, JPG, JPEG, GIF, or WebP
            </span>

            <input
              id="image"
              type="file"
              accept="image/*"
              className="sr-only"
              onChange={(event) => {
                setFile(event.target.files?.[0] ?? null);
              }}
            />
          </label>
        </div>

        <div>
          <label htmlFor="caption" className="mb-2 block text-sm font-medium">
            Caption
          </label>

          <textarea
            id="caption"
            value={caption}
            onChange={(event) => setCaption(event.target.value)}
            className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm outline-none placeholder:text-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:border-[#30363d] dark:bg-[#0d1117]"
            rows={4}
            placeholder="Add a caption..."
          />
        </div>

        {mutation.isError && (
          <div className="rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-800 dark:border-red-900 dark:bg-[#2d1117] dark:text-red-300">
            {mutation.error.message}
          </div>
        )}

        <div className="flex items-center justify-end gap-3 border-t border-gray-200 pt-6 dark:border-[#30363d]">
          <Link
            href="/posts"
            className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium hover:bg-gray-50 dark:border-[#30363d] dark:hover:bg-[#161b22]"
          >
            Cancel
          </Link>

          <button
            type="submit"
            disabled={!file || mutation.isPending}
            className="rounded-md bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-700 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-[#238636] dark:hover:bg-[#2ea043]"
          >
            {mutation.isPending ? "Uploading..." : "Upload image"}
          </button>
        </div>
      </form>
    </main>
  );
}
