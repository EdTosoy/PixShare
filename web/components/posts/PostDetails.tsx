import type { Post } from "@/lib/types";
export function PostDetails({ post }: { post: Post }) {
  const hasLongCaption = Boolean(post.caption && post.caption.length > 200);
  return (
    <section className="post-details">
      <span className="eyebrow">A SHARED PERSPECTIVE</span>
      <h1>{hasLongCaption ? "The story behind this image" : post.caption?.trim() || "Untitled image"}</h1>
      {hasLongCaption && (
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
