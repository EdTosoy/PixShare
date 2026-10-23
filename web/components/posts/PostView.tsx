"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useSession } from "@/app/providers";
import { ApiError } from "@/lib/api";
import { DETAIL_SIZES, imageDescription } from "@/lib/images";
import { deletePost, getPost } from "@/lib/posts";
import { getCurrentUser } from "@/lib/users";
import { ErrorState } from "../Feedback";
import { DeletePostDialog } from "./DeletePostDialog";
import { PostDetails } from "./PostDetails";
import { PostImage } from "./PostImage";

export function PostView({ id, success }: { id: string; success?: string }) {
  const { getToken, isSignedIn, userId } = useSession();
  const client = useQueryClient();
  const router = useRouter();
  const [deleting, setDeleting] = useState(false);
  const post = useQuery({
    queryKey: ["posts", id],
    queryFn: () => getPost(id, null),
  });
  const owner = useQuery({
    queryKey: ["current-user", userId],
    enabled: isSignedIn,
    queryFn: async () => {
      const token = await getToken();
      if (!token) throw new Error("Please sign in again.");
      return getCurrentUser(token);
    },
  });
  const mutation = useMutation({
    mutationFn: async () => {
      const token = await getToken();
      if (!token)
        throw new Error("Your session has expired. Please sign in again.");
      return deletePost(id, token);
    },
    onSuccess: async () => {
      setDeleting(false);
      client.removeQueries({ queryKey: ["posts", id], exact: true });
      await client.invalidateQueries({ queryKey: ["posts"] });
      router.push("/me?deleted=1");
    },
  });
  return (
    <main id="main" className="page-shell detail-shell">
      <Link href="/explore" className="text-link">
        ← Back to explore
      </Link>
      {post.isPending ? (
        <div className="skeleton skeleton-detail" role="status">
          Loading image…
        </div>
      ) : post.isError ? (
        post.error instanceof ApiError &&
        [404, 422].includes(post.error.status) ? (
          <div className="state-panel">
            <h1>Image not found.</h1>
            <p>It may have been removed, or the link may be incorrect.</p>
            <Link className="button secondary" href="/explore">
              Explore more images
            </Link>
          </div>
        ) : (
          <ErrorState
            message={post.error.message}
            retry={() => {
              void post.refetch();
            }}
          />
        )
      ) : (
        <>
          {success && ["created", "updated"].includes(success) && (
            <p className="success-banner" role="status">
              {success === "created"
                ? "Your image is now in the gallery."
                : "Your changes have been saved."}
            </p>
          )}
          <div className="detail-image">
            <PostImage
              post={post.data}
              alt={imageDescription(post.data)}
              sizes={DETAIL_SIZES}
              eager
              className="object-contain"
            />
          </div>
          <div className="detail-info">
            <PostDetails post={post.data} />
            {isSignedIn && owner.data?.id === post.data.user_id && (
              <div className="owner-actions">
                <Link className="button secondary" href={`/posts/${id}/edit`}>
                  Edit post
                </Link>
                <button
                  className="button danger-outline"
                  onClick={() => setDeleting(true)}
                >
                  Delete
                </button>
              </div>
            )}
          </div>
          {isSignedIn && owner.isError && (
            <p className="error-banner" role="alert">
              Unable to check ownership.{" "}
              <button
                className="text-link"
                onClick={() => {
                  void owner.refetch();
                }}
              >
                Try again
              </button>
            </p>
          )}
          <DeletePostDialog
            open={deleting}
            isPending={mutation.isPending}
            error={mutation.error}
            onClose={() => {
              setDeleting(false);
              mutation.reset();
            }}
            onConfirm={() => mutation.mutate()}
          />
        </>
      )}
    </main>
  );
}
