"use client";

import Image from "next/image";
import { useState } from "react";
import { apiUrl } from "@/lib/api";
import type { Post } from "@/lib/types";

export function PostImage({ post, alt, sizes, className, eager = false }: {
  post: Post;
  alt: string;
  sizes: string;
  className: string;
  eager?: boolean;
}) {
  const [failedUrl, setFailedUrl] = useState<string | null>(null);
  const variants = failedUrl === post.url ? [] : post.image?.variants ?? [];
  return (
    <picture>
      {variants.length > 0 && (
        <source
          type="image/webp"
          srcSet={variants.map(variant => `${apiUrl(variant.url)} ${variant.width}w`).join(", ")}
          sizes={sizes}
        />
      )}
      <Image
        key={`${post.url}-${failedUrl === post.url}`}
        src={apiUrl(post.url)}
        alt={alt}
        fill
        unoptimized
        sizes={sizes}
        className={className}
        loading={eager ? "eager" : "lazy"}
        fetchPriority={eager ? "high" : "auto"}
        onError={() => setFailedUrl(post.url)}
      />
    </picture>
  );
}
