import type { Post } from "@/lib/types";

type PostDetailsProps = {
  post: Post;
};

export function PostDetails({ post }: PostDetailsProps) {
  return (
    <section className="mt-6 border-t border-gray-200 pt-6 dark:border-[#30363d]">
      <h1 className="text-xl font-semibold">
        {post.caption || post.file_name}
      </h1>

      <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-2">
        <div>
          <dt className="text-gray-500 dark:text-gray-400">File name</dt>
          <dd className="mt-1 break-all">{post.file_name}</dd>
        </div>

        <div>
          <dt className="text-gray-500 dark:text-gray-400">File type</dt>
          <dd className="mt-1">{post.file_type}</dd>
        </div>

        <div>
          <dt className="text-gray-500 dark:text-gray-400">Created</dt>
          <dd className="mt-1">{new Date(post.created_at).toLocaleString()}</dd>
        </div>

        <div>
          <dt className="text-gray-500 dark:text-gray-400">Updated</dt>
          <dd className="mt-1">{new Date(post.updated_at).toLocaleString()}</dd>
        </div>
      </dl>
    </section>
  );
}
