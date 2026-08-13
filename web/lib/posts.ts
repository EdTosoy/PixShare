import { apiFetch } from "./api";
import type { CreatePostInput, Post, UpdatePostInput } from "./types";

export type GetPostsParams = {
  limit?: number;
  offset?: number;
  file_type?: string;
  sort?: "newest" | "oldest";
};

function toQueryString(params: GetPostsParams) {
  const searchParams = new URLSearchParams();

  if (params.limit !== undefined) {
    searchParams.set("limit", String(params.limit));
  }

  if (params.offset !== undefined) {
    searchParams.set("offset", String(params.offset));
  }

  if (params.file_type) {
    searchParams.set("file_type", params.file_type);
  }

  if (params.sort) {
    searchParams.set("sort", params.sort);
  }

  const query = searchParams.toString();

  return query ? `?${query}` : "";
}

export async function getPosts(
  token: string | null,
  params: GetPostsParams = {},
): Promise<Post[]> {
  return apiFetch<Post[]>(
    `/posts${toQueryString(params)}`,
    token
      ? {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      : undefined,
  );
}

export async function getPost(id: string, token: string | null): Promise<Post> {
  return apiFetch<Post>(
    `/posts/${id}`,
    token
      ? {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      : undefined,
  );
}

export async function createPost(
  input: CreatePostInput,
  token: string,
): Promise<Post> {
  const formData = new FormData();

  formData.append("file", input.file);

  if (input.caption !== undefined) {
    formData.append("caption", input.caption);
  }

  return apiFetch<Post>("/posts", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: formData,
  });
}

export async function updatePost(
  id: string,
  input: UpdatePostInput,
  token: string,
): Promise<Post> {
  const formData = new FormData();

  if (input.caption !== undefined) {
    formData.append("caption", input.caption);
  }

  if (input.file) {
    formData.append("file", input.file);
  }

  return apiFetch<Post>(`/posts/${id}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: formData,
  });
}

export async function deletePost(id: string, token: string): Promise<Post> {
  return apiFetch<Post>(`/posts/${id}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}
