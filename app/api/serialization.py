from app.models.post import Post
from app.schemas.post import PostResponse
from app.storage.base import Storage


async def post_response(post: Post, storage: Storage) -> PostResponse:
    result = PostResponse.model_validate(post)
    result.image = await storage.describe(post.url)
    return result


async def post_responses(posts: list[Post], storage: Storage) -> list[PostResponse]:
    # Bounded API pages; describe reads only small manifests, never decodes images.
    return [await post_response(post, storage) for post in posts]
