import Image from "next/image";
import Link from "next/link";

import { apiUrl } from "@/lib/api";
import type { Post } from "@/lib/types";

type PostCardProps = {
  post: Post;
};

export function PostCard({ post }: PostCardProps) {
  return (
    <Link
      href={`/posts/${post.id}`}
      className="group overflow-hidden rounded-md border border-gray-200 bg-white transition hover:border-gray-400 hover:shadow-sm dark:border-[#30363d] dark:bg-[#0d1117] dark:hover:border-gray-500"
    >
      <div className="relative aspect-square overflow-hidden bg-gray-100 dark:bg-[#161b22]">
        <Image
          src={apiUrl(post.url)}
          alt={post.caption ?? post.file_name}
          fill
          sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
          className="object-cover transition duration-200 group-hover:scale-[1.02]"
        />
      </div>

      <div className="p-4">
        <p className="truncate text-sm font-medium">
          {post.caption || post.file_name}
        </p>

        <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
          {new Date(post.created_at).toLocaleDateString()}
        </p>
      </div>
    </Link>
  );
}
