"use client";

import Image from "next/image";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useAuth, useUser } from "@clerk/nextjs";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { DeletePostDialog } from "@/components/posts/DeletePostDialog";
import { apiUrl } from "@/lib/api";
import { deletePost, getPost } from "@/lib/posts";
import { getCurrentUser } from "@/lib/users";
import { PostDetails } from "@/components/posts/PostDetails";

export default function PostPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();

  const { getToken } = useAuth();
  const { isLoaded, isSignedIn } = useUser();
  const queryClient = useQueryClient();

  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);

  const currentUserQuery = useQuery({
    queryKey: ["current-user"],
    queryFn: async () => {
      const token = await getToken();

      if (!token) {
        throw new Error("You must be signed in.");
      }

      return getCurrentUser(token);
    },
    enabled: isLoaded && isSignedIn,
  });

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
  const isOwner = currentUserQuery.data?.id === post.user_id;

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
              onClick={() => setIsDeleteModalOpen(true)}
              disabled={deleteMutation.isPending}
              className="rounded-md border border-red-300 px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-50 disabled:opacity-50"
            >
              Delete
            </button>
          </div>
        )}
      </div>

      <DeletePostDialog
        open={isDeleteModalOpen}
        isPending={deleteMutation.isPending}
        error={deleteMutation.error}
        onClose={() => {
          setIsDeleteModalOpen(false);
          deleteMutation.reset();
        }}
        onConfirm={() => {
          deleteMutation.mutate();
        }}
      />

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

      <PostDetails post={post} />
    </main>
  );
}
