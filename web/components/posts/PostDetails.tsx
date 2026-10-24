import type { Post } from "@/lib/types";
import { imageTitle } from "@/lib/images";
export function PostDetails({ post }: { post: Post }) {
  const title = imageTitle(post);
  const hasFullCaption = Boolean(post.caption && (post.caption.length > 200 || post.caption.trim() !== title));
  return (
    <section className="post-details">
      <h1>{title.length > 200 ? "The story behind this image" : title}</h1>
      {hasFullCaption && (
        <details className="post-caption">
          <summary>Read full caption</summary>
          <p>{post.caption}</p>
        </details>
      )}
      <dl>
        <div>
          <dt>Format</dt>
          <dd>{post.file_type.replace("image/", "").toUpperCase()}</dd>
        </div>
        <div>
          <dt>Shared</dt>
          <dd>
            {new Date(post.created_at).toLocaleDateString("en", {
              month: "long",
              day: "numeric",
              year: "numeric",
            })}
          </dd>
        </div>
        <div>
          <dt>Original file</dt>
          <dd className="file-name">{post.file_name}</dd>
        </div>
      </dl>
    </section>
  );
}
