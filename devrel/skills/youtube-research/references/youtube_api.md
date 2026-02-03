# YouTube Data API v3 Reference

## Authentication

All requests require an API key via `key` parameter or OAuth 2.0 token.

## Search API

**Endpoint:** `GET https://www.googleapis.com/youtube/v3/search`

**Required parameters:**
- `part=snippet` - Include video metadata
- `key` - API key

**Key parameters:**
| Parameter | Description |
|-----------|-------------|
| `q` | Search query. Supports `-` (exclude) and `|` (OR) |
| `type=video` | Restrict to videos only |
| `maxResults` | 1-50 results (default: 5) |
| `order` | `relevance`, `date`, `viewCount`, `rating` |
| `publishedAfter` | RFC 3339 timestamp filter |
| `regionCode` | ISO 3166-1 country code |
| `relevanceLanguage` | ISO 639-1 language code |
| `videoDuration` | `short` (<4min), `medium` (4-20min), `long` (>20min) |

**Response structure:**
```json
{
  "items": [{
    "id": { "videoId": "..." },
    "snippet": {
      "title": "...",
      "description": "...",
      "channelTitle": "...",
      "publishedAt": "..."
    }
  }],
  "nextPageToken": "...",
  "pageInfo": { "totalResults": 1000 }
}
```

**Quota cost:** 100 units per search

## Comment Threads API

**Endpoint:** `GET https://www.googleapis.com/youtube/v3/commentThreads`

**Required parameters:**
- `part=snippet,replies` - Include comment text and replies
- `videoId` - Target video ID
- `key` - API key

**Key parameters:**
| Parameter | Description |
|-----------|-------------|
| `maxResults` | 1-100 results (default: 20) |
| `order` | `time` or `relevance` |
| `textFormat` | `html` or `plainText` |
| `pageToken` | Pagination token |

**Response structure:**
```json
{
  "items": [{
    "snippet": {
      "topLevelComment": {
        "snippet": {
          "textDisplay": "...",
          "authorDisplayName": "...",
          "likeCount": 5,
          "publishedAt": "..."
        }
      },
      "totalReplyCount": 2
    },
    "replies": {
      "comments": [...]
    }
  }]
}
```

## Rate Limits

- Default quota: 10,000 units/day
- Search: 100 units/call
- CommentThreads: 1 unit/call
