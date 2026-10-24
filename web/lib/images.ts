import type { Post } from "./types";

export function imageTitle(post: Pick<Post, "caption">): string {
  return post.caption?.trim().split(/\r?\n/, 1)[0].trim() || "Untitled image";
}

// Captions are the available human descriptions. Keep accessible names concise;
// filenames remain metadata, never a substitute for an image description.
export function imageDescription(post: Pick<Post, "caption">): string {
  const caption = post.caption?.replace(/\s+/g, " ").trim();
  if (!caption) return "Shared image";
  if (caption.length <= 160) return caption;
  const shortened = caption.slice(0, 157);
  const boundary = shortened.lastIndexOf(" ");
  return `${boundary > 100 ? shortened.slice(0, boundary) : shortened}…`;
}

export const DETAIL_SIZES = "(max-width: 700px) calc(100vw - 40px), (max-width: 1000px) calc(100vw - 56px), (max-width: 1152px) calc(100vw - 96px), 1056px";
