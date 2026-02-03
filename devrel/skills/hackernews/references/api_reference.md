# Hacker News API Reference

## Firebase API (Official)

Base: `https://hacker-news.firebaseio.com/v0`

### Story Lists

| Endpoint | Returns | Max Items |
|----------|---------|-----------|
| `GET /topstories.json` | Top story IDs | 500 |
| `GET /newstories.json` | New story IDs | 500 |
| `GET /beststories.json` | Best story IDs | 500 |
| `GET /askstories.json` | Ask HN story IDs | 200 |
| `GET /showstories.json` | Show HN story IDs | 200 |
| `GET /jobstories.json` | Job story IDs | 200 |

### Items

`GET /item/{id}.json`

**Story fields:**
- `id` - Unique item ID
- `by` - Author username
- `title` - Story title
- `url` - External URL (optional for text posts)
- `text` - HTML text (for Ask HN, text posts)
- `score` - Points/upvotes
- `descendants` - Total comment count
- `kids` - Array of direct child comment IDs
- `time` - Unix timestamp
- `type` - "story"

**Comment fields:**
- `id` - Unique item ID
- `by` - Author username
- `text` - HTML comment text
- `parent` - Parent item ID
- `kids` - Array of reply IDs
- `time` - Unix timestamp
- `type` - "comment"
- `deleted` - true if deleted
- `dead` - true if flagged

**Poll fields:**
- `id`, `by`, `title`, `text`, `score`, `time`
- `parts` - Array of poll option IDs
- `kids` - Comment IDs
- `type` - "poll"

**Poll Option fields:**
- `id`, `by`, `text`, `score`, `time`
- `poll` - Parent poll ID
- `type` - "pollopt"

**Job fields:**
- `id`, `by`, `title`, `text`, `url`, `score`, `time`
- `type` - "job"

### Users

`GET /user/{username}.json`

**Fields:**
- `id` - Username
- `created` - Unix timestamp of account creation
- `karma` - User karma score
- `about` - HTML bio (optional)
- `submitted` - Array of submitted item IDs

### Utilities

| Endpoint | Returns |
|----------|---------|
| `GET /maxitem.json` | Largest item ID |
| `GET /updates.json` | `{items: [...], profiles: [...]}` of recent changes |

---

## Algolia Search API

Base: `https://hn.algolia.com/api/v1`

### Endpoints

| Endpoint | Sort |
|----------|------|
| `GET /search` | By relevance |
| `GET /search_by_date` | By date (newest first) |

### Query Parameters

| Param | Description | Example |
|-------|-------------|---------|
| `query` | Search term | `query=rust` |
| `tags` | Filter type | `tags=story`, `tags=(story,poll)`, `tags=comment` |
| `numericFilters` | Numeric filters | `numericFilters=points>100` |
| `page` | Page number (0-indexed) | `page=0` |
| `hitsPerPage` | Results per page (max 1000) | `hitsPerPage=50` |

### Tag Values

- `story` - Stories only
- `comment` - Comments only
- `poll` - Polls only
- `pollopt` - Poll options
- `show_hn` - Show HN posts
- `ask_hn` - Ask HN posts
- `front_page` - Front page items
- `author_{username}` - By specific author

### Numeric Filters

- `points>N` - Minimum points
- `num_comments>N` - Minimum comments
- `created_at_i>N` - After Unix timestamp
- `created_at_i<N` - Before Unix timestamp

### Response Structure

```json
{
  "hits": [
    {
      "objectID": "8863",
      "title": "Story title",
      "url": "https://example.com",
      "author": "username",
      "points": 111,
      "num_comments": 71,
      "created_at": "2007-04-04T19:16:40.000Z",
      "created_at_i": 1175714200,
      "story_text": "Text for Ask HN posts",
      "_tags": ["story", "author_username", "story_8863"]
    }
  ],
  "nbHits": 1000,
  "page": 0,
  "nbPages": 50,
  "hitsPerPage": 20
}
```

### Example Queries

```bash
# Stories about "react" with 100+ points
curl "https://hn.algolia.com/api/v1/search?query=react&tags=story&numericFilters=points>100"

# Comments by user "pg"
curl "https://hn.algolia.com/api/v1/search?tags=comment,author_pg"

# Ask HN posts from last 24 hours
curl "https://hn.algolia.com/api/v1/search_by_date?tags=ask_hn&numericFilters=created_at_i>$(date -v-1d +%s)"

# Front page stories sorted by date
curl "https://hn.algolia.com/api/v1/search_by_date?tags=front_page"
```
