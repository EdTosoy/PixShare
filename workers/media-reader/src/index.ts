interface Env {
  MEDIA: R2Bucket;
}

const CACHE_CONTROL = "public, max-age=31536000, immutable";
const MIME_TYPES = { jpg: "image/jpeg", png: "image/png", webp: "image/webp" };
// S3Storage uses uuid4().hex groups; generate_variants caps the longest edge at 1920.
const IMAGE_PATH = /^\/pixshare\/media\/[a-f0-9]{32}\/(?:original\.(jpg|png|webp)|variants\/v1-([1-9]\d{0,3})\.webp)$/;

function errorResponse(request: Request, status: number, message: string): Response {
  return new Response(request.method === "HEAD" ? null : message, {
    status,
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Cache-Control": "no-store",
      "X-Content-Type-Options": "nosniff",
      ...(status === 405 ? { Allow: "GET, HEAD" } : {}),
    },
  });
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    if (request.method !== "GET" && request.method !== "HEAD") {
      return errorResponse(request, 405, "Method not allowed");
    }

    // Do not decode paths or normalize traversal into an allowed key. Query
    // strings never participate in key selection or change response headers.
    const path = request.url.replace(/^https?:\/\/[^/]+/, "").split("?")[0];
    const match = IMAGE_PATH.exec(path);
    if (!match || match[0] !== path || (match[2] && Number(match[2]) > 1920)) {
      return errorResponse(request, 404, "Not found");
    }
    const contentType = MIME_TYPES[(match[1] ?? "webp") as keyof typeof MIME_TYPES];
    const key = path.slice(1);

    try {
      let body: ReadableStream | null = null;
      let object: R2Object | null;
      if (request.method === "HEAD") {
        object = await env.MEDIA.head(key);
      } else {
        const result = await env.MEDIA.get(key);
        object = result;
        body = result?.body ?? null;
      }
      if (!object) return errorResponse(request, 404, "Not found");

      // Deliberately omit customMetadata and arbitrary stored HTTP metadata.
      const headers = new Headers({
        "Content-Type": contentType,
        "Content-Length": String(object.size),
        "Cache-Control": CACHE_CONTROL,
        "ETag": object.httpEtag,
        "X-Content-Type-Options": "nosniff",
      });
      return new Response(body, { headers });
    } catch {
      // SDK errors may contain keys, internal details or credentials.
      return errorResponse(request, 503, "Media temporarily unavailable");
    }
  },
} satisfies ExportedHandler<Env>;
