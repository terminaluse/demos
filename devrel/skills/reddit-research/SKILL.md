---
name: reddit-research
description: Search Reddit for subreddits, posts, and comments. Use when researching what Reddit thinks about a topic, finding relevant communities, searching discussions, or analyzing post comments. Supports broad searches across all of Reddit, targeted searches within specific subreddits, or discovering relevant subreddits first then drilling down.
---

# Reddit Research

Search Reddit for subreddits, posts, and comments. Results written to markdown files for grep/glob searching.

**No API key required** (uses public JSON API).

## Quick Start

```bash
# Search all of Reddit for posts
python scripts/reddit_search.py search -q "cursor ide" -o ./research

# Search specific subreddits
python scripts/reddit_search.py search -q "cursor ide" -s "programming,vscode" -o ./research

# Find relevant subreddits first
python scripts/reddit_search.py subreddits -q "code editor" -o ./research

# Get comments from a post
python scripts/reddit_search.py comments -p POST_ID -o ./research

# Grep through results
grep -r "vscode" ./research/
```

## Search Strategies

Choose based on your research needs:

### 1. Broad Search (all of Reddit)
```bash
python scripts/reddit_search.py search -q "keyword"
```
Best for: Initial exploration, finding where discussions happen.

### 2. Targeted Search (specific subreddits)
```bash
python scripts/reddit_search.py search -q "keyword" -s "sub1,sub2,sub3"
```
Best for: When you know the relevant communities.

### 3. Discovery → Targeted
```bash
# Step 1: Find relevant subreddits
python scripts/reddit_search.py subreddits -q "topic"

# Step 2: Search within discovered subreddits
python scripts/reddit_search.py search -q "keyword" -s "discovered,subs"
```
Best for: Comprehensive research on unfamiliar topics.

## Commands

| Command | Description |
|---------|-------------|
| `subreddits -q QUERY` | Find subreddits matching topic |
| `info -r SUBREDDIT` | Get subreddit details + related subs |
| `popular --type [popular\|new]` | List trending subreddits |
| `posts -r SUBREDDIT` | Get posts from a subreddit |
| `search -q QUERY [-s SUBS]` | Search posts (all or specific subs) |
| `comments -p POST_ID` | Get post comments |

## Output Files

All results written to `--output-dir` (default: `./reddit_research/`):

| File Pattern | Contents |
|--------------|----------|
| `reddit_subs_*.md` | Subreddit search results |
| `reddit_info_*.md` | Subreddit details |
| `reddit_posts_*.md` | Posts from a subreddit |
| `reddit_search_*.md` | Post search results (grouped by sub) |
| `reddit_comments_*.md` | Post with comments |

## Examples

```bash
# Research what Reddit thinks about a product
python scripts/reddit_search.py search -q "notion vs obsidian" -o ./research

# Find AI/ML communities
python scripts/reddit_search.py subreddits -q "machine learning" -n 30 -o ./research

# Get top posts from a subreddit
python scripts/reddit_search.py posts -r programming --sort top --time week -o ./research

# Deep dive into a discussion
python scripts/reddit_search.py comments -p abc123 -o ./research
```

## API Reference

See [references/api_reference.md](references/api_reference.md) for endpoint details.
