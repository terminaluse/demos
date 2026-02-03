# Reddit JSON API Reference

Reddit provides public JSON endpoints by appending `.json` to most URLs.

**No authentication required** for read-only operations.

## Base URL

`https://www.reddit.com`

## Endpoints

### Subreddit Search

`GET /subreddits/search.json?q={query}&limit={n}`

Returns subreddits matching query.

### Subreddit Info

`GET /r/{subreddit}/about.json`

Returns subreddit metadata: subscribers, description, rules, related subs.

### Popular/New Subreddits

`GET /subreddits/popular.json?limit={n}`
`GET /subreddits/new.json?limit={n}`

### Subreddit Posts

`GET /r/{subreddit}/{sort}.json?limit={n}`

Sort options: `hot`, `new`, `top`, `rising`, `controversial`

For `top`/`controversial`, add `?t={time}` where time is:
`hour`, `day`, `week`, `month`, `year`, `all`

### Search Posts

**Within subreddit:**
`GET /r/{subreddit}/search.json?q={query}&restrict_sr=on&sort={sort}&t={time}&limit={n}`

**All of Reddit:**
`GET /search.json?q={query}&sort={sort}&t={time}&limit={n}`

Sort: `relevance`, `top`, `new`, `comments`

### Post Comments

`GET /r/{subreddit}/comments/{post_id}.json?limit={n}`

Returns [post_data, comments_data] array.

## Response Structure

### Post Object
```json
{
  "id": "abc123",
  "title": "Post title",
  "author": "username",
  "subreddit": "subreddit_name",
  "score": 1234,
  "upvote_ratio": 0.95,
  "num_comments": 56,
  "created_utc": 1234567890,
  "selftext": "Post body text",
  "url": "https://...",
  "permalink": "/r/sub/comments/abc123/..."
}
```

### Subreddit Object
```json
{
  "display_name": "subreddit",
  "subscribers": 1000000,
  "accounts_active": 5000,
  "public_description": "Short description",
  "description": "Full sidebar markdown",
  "over18": false,
  "created_utc": 1234567890
}
```

### Comment Object
```json
{
  "id": "xyz789",
  "author": "username",
  "body": "Comment text",
  "score": 42,
  "created_utc": 1234567890,
  "replies": { "data": { "children": [...] } }
}
```

## Rate Limits

- **Unauthenticated:** ~10 requests/minute
- **With User-Agent:** ~30 requests/minute
- **HTTP 429:** Wait 60 seconds before retrying

## Tips

- Always include a User-Agent header
- Add small delays between requests (0.5-1s)
- Handle 429 responses gracefully
- Reddit sometimes returns HTML - retry on HTML response
