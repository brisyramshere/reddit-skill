# Reddit API Quick Reference

## Authentication

```
POST https://www.reddit.com/api/v1/access_token
Authorization: Basic base64(client_id:client_secret)
Content-Type: application/x-www-form-urlencoded
Body: grant_type=client_credentials
```

Response: `{ "access_token": "...", "token_type": "bearer", "expires_in": 3600 }`

All subsequent requests go to `https://oauth.reddit.com` with header `Authorization: bearer <token>`.

## Search

| Endpoint | Description |
|----------|-------------|
| `GET /search` | Search all of Reddit |
| `GET /r/{subreddit}/search?restrict_sr=true` | Search within a subreddit |

**Parameters:**
- `q` (required) - Query string. Supports `AND`, `OR`, `NOT`, `subreddit:xxx`
- `sort` - `relevance` (default), `hot`, `new`, `top`, `comments`
- `t` - Time range: `hour`, `day`, `week`, `month`, `year`, `all`
- `limit` - 1-100 (default 25)
- `after` / `before` - Pagination cursors (fullname, e.g. `t3_abc123`)
- `type` - `link` (posts), `sr` (subreddits), `comment`
- `restrict_sr` - `true` to limit to subreddit

## Subreddit Listings

| Endpoint | Description | Extra Params |
|----------|-------------|--------------|
| `GET /r/{sub}/hot` | Hot posts | `g` (geo filter) |
| `GET /r/{sub}/new` | Newest posts | - |
| `GET /r/{sub}/top` | Top posts | `t` (time range, required) |
| `GET /r/{sub}/rising` | Rising posts | - |
| `GET /r/{sub}/controversial` | Controversial | `t` (time range) |

**Common params:** `limit` (1-100), `after`, `before`, `count`, `show`

## Post Detail

| Endpoint | Description |
|----------|-------------|
| `GET /comments/{post_id}` | Post + comment tree |
| `GET /r/{sub}/comments/{post_id}` | Same, with subreddit |
| `GET /api/info?id=t3_{post_id}` | Post metadata only |

## Comments

`GET /comments/{post_id}` returns array of two Listings:
1. Post detail (kind: t3)
2. Comment tree (kind: t1, nested via `replies`)

**Parameters:**
- `sort` - `confidence` (best), `top`, `new`, `controversial`, `old`, `random`, `qa`
- `limit` - Max comments (default ~200, max 500)
- `depth` - Nesting depth (max 10)
- `comment` - Focus on specific comment ID

## Subreddit Info

| Endpoint | Description |
|----------|-------------|
| `GET /r/{sub}/about` | Subreddit metadata |

Returns: `display_name`, `title`, `subscribers`, `accounts_active`, `public_description`, `description`, `created_utc`, `subreddit_type`, `over18`

## Rate Limits

- **Authenticated (OAuth):** 100 requests/minute
- **Unauthenticated:** 10 requests/minute
- Response headers: `X-Ratelimit-Used`, `X-Ratelimit-Remaining`, `X-Ratelimit-Reset`
- HTTP 429 when exceeded

## User-Agent

Required format: `<platform>:<app_id>:<version> (by /u/<username>)`

Example: `linux:com.myapp:v1.0 (by /u/myuser)`

## Reddit Fullname Types

| Prefix | Type |
|--------|------|
| `t1_` | Comment |
| `t2_` | Account |
| `t3_` | Link/Post |
| `t4_` | Message |
| `t5_` | Subreddit |
