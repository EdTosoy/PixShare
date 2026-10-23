export const API_URL = (
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
).replace(/\/$/, "");

export function apiUrl(path: string) {
  if (/^https?:\/\//.test(path)) return path;
  return `${API_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(apiUrl(path), options);
  } catch {
    throw new ApiError(
      "Unable to reach PixShare. Check your connection and try again.",
      0,
    );
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    let message =
      typeof body?.detail === "string"
        ? body.detail
        : "Something went wrong. Please try again.";
    if (response.status === 401)
      message = "Your session has expired. Please sign in again.";
    if (response.status === 403)
      message = "Only the owner can change this post.";
    if (Array.isArray(body?.detail))
      message = "Please check the form values and try again.";
    throw new ApiError(message, response.status);
  }
  return response.json() as Promise<T>;
}
