import Link from "next/link";
import { GALLERY_SIZES, imageDescription } from "@/lib/images";
import type { Post } from "@/lib/types";
import { PostImage } from "./PostImage";

export function PostCard({ post }: { post: Post }) {
  return (
    <Link href={`/posts/${post.id}`} className="photo-card" aria-label={`View image: ${imageDescription(post)}`}>
      <div className="photo-frame">
        <PostImage
          post={post}
          alt=""
          sizes={GALLERY_SIZES}
          className="object-cover"
        />
      </div>
      <div className="photo-caption">
        <p>{post.caption?.trim() || "Untitled image"}</p>
        <span>
          {post.file_type.replace("image/", "").toUpperCase()}{" "}
          <span aria-hidden="true">↗</span>
        </span>
      </div>
    </Link>
  );
}
