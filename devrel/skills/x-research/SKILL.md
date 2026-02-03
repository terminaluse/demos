---
name: x-research
description: Search X (Twitter) for recent tweets and analyze engagement. Use when researching what people are saying on X/Twitter about a topic, analyzing tweet engagement (likes, retweets, quotes), finding influential accounts discussing a subject, or drilling down into viral tweets to understand who's engaging.
---

# X Research

Search X for tweets and analyze engagement. Results written to markdown files for grep/glob searching.

## Setup

Set `X_BEARER_TOKEN` environment variable. Get a token from [X Developer Portal](https://developer.x.com/).

## Quick Start

```bash
# Search recent tweets
python scripts/x_search.py search -q "product name" -o ./research

# Drill down into an interesting tweet
python scripts/x_search.py drill --id 1234567890 -o ./research

# Get user profile
python scripts/x_search.py user -u elonmusk -o ./research

# Search results
grep -r "followers" ./research/
```

## Commands

| Command | Description |
|---------|-------------|
| `search -q QUERY` | Search recent tweets |
| `drill --id ID` | Get liking users, retweeters, quote tweets |
| `user -u USERNAME` | Get user profile |

## Workflow

1. **Search** for topic: `search -q "keyword" -o ./research`
2. **Find tweet IDs** with high engagement in results
3. **Drill down**: `drill --id TWEET_ID -o ./research`
4. **Analyze** who's engaging (followers, verified status)
5. **Grep findings**: `grep -r "pattern" ./research/`

### Search Query Syntax

| Operator | Example |
|----------|---------|
| From user | `from:username` |
| Exclude RTs | `-is:retweet` |
| With media | `has:media` |
| Language | `lang:en` |
| Boolean | `(cursor OR vscode) editor` |

## Output Files

All results written to `--output-dir` (default: `./x_research/`):

| File Pattern | Contents |
|--------------|----------|
| `x_search_*.md` | Tweet search results with metrics |
| `x_drill_*.md` | Liking users, retweeters, quote tweets |
| `x_user_*.md` | User profiles |

## Drill-Down Analysis

The `drill` command fetches:
- **Liking users** - Sorted by follower count
- **Retweeted by** - Who amplified the tweet
- **Quote tweets** - What people are saying about it

Useful for finding influential accounts engaging with content.

## API Reference

See [references/api_reference.md](references/api_reference.md) for endpoint details and rate limits.
