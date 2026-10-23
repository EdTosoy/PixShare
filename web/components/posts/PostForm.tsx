"use client";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useSession } from "@/app/providers";
import { ApiError } from "@/lib/api";
import { createPost, updatePost } from "@/lib/posts";
import type { Post } from "@/lib/types";
import { ImagePicker } from "./ImagePicker";

export function PostForm({ post }: { post?: Post }) {
  const [file, setFile] = useState<File | null>(null);
  const [caption, setCaption] = useState(post?.caption ?? "");
  const [fileError, setFileError] = useState<string | null>(null);
  const errorRef = useRef<HTMLParagraphElement>(null);
  const { getToken } = useSession();
  const router = useRouter();
  const client = useQueryClient();
  const mutation = useMutation({
    mutationFn: async () => {
      const token = await getToken();
      if (!token)
        throw new ApiError("Your session has expired. Please sign in again.", 401);
      if (fileError) throw new Error(fileError);
      if (post)
        return updatePost(
          post.id,
          { caption, ...(file ? { file } : {}) },
          token,
        );
      if (!file) throw new Error("Choose an image to share.");
      return createPost({ file, caption }, token);
    },
    onSuccess: async (updated) => {
      await client.invalidateQueries({ queryKey: ["posts"] });
      client.setQueryData(["posts", updated.id], updated);
      router.push(
        `/posts/${updated.id}?success=${post ? "updated" : "created"}`,
      );
    },
  });
  useEffect(() => {
    if (mutation.isError) errorRef.current?.focus();
  }, [mutation.isError]);
  return (
    <form
      className="post-form"
      aria-busy={mutation.isPending}
      onSubmit={(event) => {
        event.preventDefault();
        mutation.mutate();
      }}
    >
      <fieldset disabled={mutation.isPending}>
        <legend className="sr-only">
          {post ? "Edit your post" : "Share an image"}
        </legend>
        <ImagePicker
          currentPost={post}
          disabled={mutation.isPending}
          onChange={(selected, error) => {
            setFile(selected);
            setFileError(error);
            mutation.reset();
          }}
        />
        <label className="field-label" htmlFor="caption">
          Caption <span className="muted">(optional)</span>
        </label>
        <textarea
          id="caption"
          value={caption}
          onChange={(event) => setCaption(event.target.value)}
          rows={4}
          maxLength={5000}
          placeholder="What’s the story behind this image?"
          aria-describedby="caption-help"
        />
        <p className="field-hint" id="caption-help">
          A little context makes a moment go further. {caption.length}/5000
        </p>
        <p className="privacy-note">
          Your image and caption will be visible to everyone.
        </p>
      </fieldset>
      {mutation.isError && (
        <p ref={errorRef} tabIndex={-1} className="error-banner" role="alert">
          {mutation.error.message}{" "}
          {mutation.error instanceof ApiError && mutation.error.status === 401 && (
            <Link href="/sign-in">Sign in</Link>
          )}
        </p>
      )}
      <div className="form-actions">
        <Link
          className="button secondary"
          href={post ? `/posts/${post.id}` : "/explore"}
        >
          Cancel
        </Link>
        <button
          className="button primary"
          type="submit"
          disabled={
            mutation.isPending || Boolean(fileError) || (!post && !file)
          }
        >
          {mutation.isPending
            ? post
              ? "Saving…"
              : "Uploading…"
            : post
              ? "Save changes"
              : "Share image ↗"}
        </button>
      </div>
      <p className="sr-only" role="status">
        {mutation.isPending ? post ? "Saving changes. Please wait." : "Uploading image. Please wait." : ""}
      </p>
    </form>
  );
}
