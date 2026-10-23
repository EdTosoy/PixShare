"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getMyPosts, getPosts } from "@/lib/posts";
import { PostCard } from "./posts/PostCard";
import { ErrorState, GallerySkeleton } from "./Feedback";
import { useSession } from "@/app/providers";

const PAGE_SIZE = 12;
export function Gallery({
  personal = false,
  featured = false,
}: {
  personal?: boolean;
  featured?: boolean;
}) {
  const { getToken, userId, isSignedIn } = useSession();
  const [filters, setFilters] = useState({
    type: "",
    sort: "newest" as "newest" | "oldest",
    page: 0,
  });
  const query = useQuery({
    queryKey: ["posts", personal ? userId : "public", filters, featured],
    queryFn: async () => {
      const params = {
        limit: featured ? 6 : PAGE_SIZE + 1,
        offset: filters.page * PAGE_SIZE,
        file_type: filters.type,
        sort: filters.sort,
      };
      if (!personal) return getPosts(null, params);
      const token = await getToken();
      if (!token) throw new Error("Please sign in to view your gallery.");
      return getMyPosts(token, params);
    },
    enabled: !personal || isSignedIn,
  });
  const posts = query.data?.slice(0, featured ? 6 : PAGE_SIZE) ?? [];
  return (
    <section aria-label={featured ? "Featured images" : "Image gallery"}>
      {!featured && (
        <div className="gallery-toolbar">
          <p className="muted">
            {personal
              ? "Your images, all in one place."
              : "A collection of different points of view."}
          </p>
          <div className="filter-controls">
            <label>
              Format
              <select
                value={filters.type}
                onChange={(e) =>
                  setFilters({ ...filters, type: e.target.value, page: 0 })
                }
              >
                <option value="">All images</option>
                <option value="image/jpeg">JPEG</option>
                <option value="image/png">PNG</option>
                <option value="image/webp">WebP</option>
              </select>
            </label>
            <label>
              Sort by
              <select
                value={filters.sort}
                onChange={(e) =>
                  setFilters({
                    ...filters,
                    sort: e.target.value as "newest" | "oldest",
                    page: 0,
                  })
                }
              >
                <option value="newest">Newest first</option>
                <option value="oldest">Oldest first</option>
              </select>
            </label>
          </div>
        </div>
      )}
      {query.isPending ? (
        <GallerySkeleton />
      ) : query.isError ? (
        <ErrorState
          message={query.error.message}
          retry={() => {
            void query.refetch();
          }}
        />
      ) : posts.length === 0 ? (
        <div className="state-panel">
          <h2>
            {filters.type
              ? "No images in this format yet."
              : personal
                ? "Your perspective belongs here."
                : "The gallery is waiting for its first image."}
          </h2>
          <p>
            {filters.type
              ? "Try another format to see more images."
              : "Share a moment, a place, or something that caught your eye."}
          </p>
          {filters.type ? (
            <button
              className="button primary"
              onClick={() => setFilters({ ...filters, type: "", page: 0 })}
            >
              Clear format filter
            </button>
          ) : (
            <Link href="/upload" className="button primary">
              Share an image
            </Link>
          )}
        </div>
      ) : (
        <div className="photo-grid">
          {posts.map((post) => (
            <PostCard key={post.id} post={post} />
          ))}
        </div>
      )}
      {!featured && (
        <nav className="pagination" aria-label="Gallery pagination">
          <button
            className="button secondary"
            disabled={filters.page === 0 || query.isPending}
            onClick={() => setFilters({ ...filters, page: filters.page - 1 })}
          >
            ← Previous
          </button>
          <span aria-live="polite">Page {filters.page + 1}</span>
          <button
            className="button secondary"
            disabled={
              !query.data || query.data.length <= PAGE_SIZE || query.isPending
            }
            onClick={() => setFilters({ ...filters, page: filters.page + 1 })}
          >
            Next →
          </button>
        </nav>
      )}
    </section>
  );
}
