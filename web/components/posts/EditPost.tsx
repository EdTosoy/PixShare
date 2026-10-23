"use client";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useSession } from "@/app/providers";
import { getPost } from "@/lib/posts";
import { getCurrentUser } from "@/lib/users";
import { AuthGate, ErrorState } from "../Feedback";
import { PostForm } from "./PostForm";

function Editor({ id }: { id: string }) {
  const { getToken, userId } = useSession();
  const post = useQuery({
    queryKey: ["posts", id],
    queryFn: () => getPost(id, null),
  });
  const owner = useQuery({
    queryKey: ["current-user", userId],
    queryFn: async () => {
      const token = await getToken();
      if (!token) throw new Error("Please sign in again.");
      return getCurrentUser(token);
    },
  });
  if (post.isPending || owner.isPending)
    return (
      <div className="skeleton skeleton-form" role="status">
        Loading your post…
      </div>
    );
  if (post.isError || owner.isError)
    return (
      <ErrorState
        message={
          post.error?.message ??
          owner.error?.message ??
          "Unable to load this post."
        }
        retry={() => {
          void post.refetch();
          void owner.refetch();
        }}
      />
    );
  if (owner.data.id !== post.data.user_id)
    return (
      <div className="state-panel">
        <h1>Only the owner can edit this post.</h1>
        <p>You can manage your own images from your gallery.</p>
        <Link className="button secondary" href={`/posts/${id}`}>
          Back to image
        </Link>
      </div>
    );
  return (
    <>
      <div className="page-heading">
        <Link href={`/posts/${id}`} className="text-link">
          ← Back to image
        </Link>
        <h1>
          Edit your perspective<span className="accent">.</span>
        </h1>
        <p>Update the caption or choose a new image.</p>
      </div>
      <PostForm key={post.data.id} post={post.data} />
    </>
  );
}
export function EditPost({ id }: { id: string }) {
  return (
    <main id="main" className="page-shell form-shell">
      <AuthGate>
        <Editor id={id} />
      </AuthGate>
    </main>
  );
}
