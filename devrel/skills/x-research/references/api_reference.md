# X API v2 Reference

## Authentication

All requests require a Bearer token via `Authorization: Bearer {token}` header.

Set `X_BEARER_TOKEN` environment variable.

## Endpoints

### Search Recent Tweets

`GET https://api.x.com/2/tweets/search/recent`

| Parameter | Description |
|-----------|-------------|
| `query` | Search query (1-4096 chars) |
| `max_results` | 10-100 results |
| `start_time` | UTC timestamp (YYYY-MM-DDTHH:mm:ssZ) |
| `end_time` | UTC timestamp |
| `sort_order` | `recency` or `relevancy` |

**Query operators:**
- `from:username` - Tweets by user
- `to:username` - Replies to user
- `has:media` - With media
- `has:links` - With links
- `-is:retweet` - Exclude retweets
- `lang:en` - Language filter

### Get Liking Users

`GET https://api.x.com/2/tweets/{id}/liking_users`

| Parameter | Description |
|-----------|-------------|
| `id` | Tweet ID (path) |
| `max_results` | 1-100 (default: 100) |

### Get Retweeted By

`GET https://api.x.com/2/tweets/{id}/retweeted_by`

| Parameter | Description |
|-----------|-------------|
| `id` | Tweet ID (path) |
| `max_results` | 1-100 (default: 100) |

### Get Quote Tweets

`GET https://api.x.com/2/tweets/{id}/quote_tweets`

| Parameter | Description |
|-----------|-------------|
| `id` | Tweet ID (path) |
| `max_results` | 10-100 (default: 10) |

### Get User by Username

`GET https://api.x.com/2/users/by/username/{username}`

## Common Fields

### Tweet Fields
`id,text,author_id,created_at,public_metrics,conversation_id`

### User Fields
`id,name,username,public_metrics,verified,description`

### Public Metrics (Tweet)
```json
{
  "like_count": 100,
  "retweet_count": 50,
  "reply_count": 25,
  "quote_count": 10
}
```

### Public Metrics (User)
```json
{
  "followers_count": 1000,
  "following_count": 500,
  "tweet_count": 2500
}
```

## Rate Limits

| Endpoint | App Limit | User Limit |
|----------|-----------|------------|
| Search Recent | 450/15min | 180/15min |
| Liking Users | 75/15min | 75/15min |
| Retweeted By | 75/15min | 75/15min |
| Quote Tweets | 75/15min | 75/15min |
