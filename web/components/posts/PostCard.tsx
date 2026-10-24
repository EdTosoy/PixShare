import Link from "next/link";
import type { CSSProperties } from "react";
import { imageDescription } from "@/lib/images";
import type { Post } from "@/lib/types";
import { PostImage } from "./PostImage";

export function PostCard({ post }: { post: Post }) {
  // Bound extreme/legacy frames; contain still shows the entire photograph.
  const ratio = post.image && post.image.width > 0 && post.image.height > 0
    ? Math.min(2, Math.max(0.5, post.image.width / post.image.height))
    : 4 / 3;
  const style = { "--photo-ratio": ratio } as CSSProperties;
  // Desktop rows cap at 360px. Mobile images fill the content width.
  const sizes = `(max-width: 700px) calc(100vw - 40px), ${Math.ceil(ratio * 360)}px`;
  return (
    <Link href={`/posts/${post.id}`} className="photo-card" style={style} aria-label={`View image: ${imageDescription(post)}`}>
      <div className="photo-frame">
        <PostImage
          post={post}
          alt=""
          sizes={sizes}
          className="object-contain"
        />
      </div>
      <div className="photo-caption">
        <p>{post.caption?.trim() || "Untitled image"}</p>
      </div>
    </Link>
  );
}
