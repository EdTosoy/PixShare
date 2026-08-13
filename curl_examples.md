# curl examples for PixShare API

Replace HOST (default: http://localhost:8000) and add an Authorization header if required.

1) List posts
```bash
curl -X GET "http://localhost:8000/posts"
```

2) Get a single post
```bash
curl -X GET "http://localhost:8000/posts/<POST_UUID>"
```

3) Create a post (multipart)
```bash
curl -X POST "http://localhost:8000/posts" \
  -H "Authorization: Bearer <TOKEN>" \
  -F "file=@/path/to/photo.jpg" \
  -F "caption=My demo photo"
```

4) Replace a post file (PATCH)
```bash
curl -X PATCH "http://localhost:8000/posts/<POST_UUID>" \
  -H "Authorization: Bearer <TOKEN>" \
  -F "file=@/path/to/new_photo.jpg" \
  -F "caption=Updated caption"
```

5) Delete a post
```bash
curl -X DELETE "http://localhost:8000/posts/<POST_UUID>" \
  -H "Authorization: Bearer <TOKEN>"
```
