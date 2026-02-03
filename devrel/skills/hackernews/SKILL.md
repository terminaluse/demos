---
name: hackernews
description: Search and research Hacker News discussions, stories, and community opinions. Use when users ask about HN, want to know what HN thinks about a topic, search for tech discussions, find startup/programming debates, or request "what does Hacker News say about X". Triggers on /hn, /hackernews commands or questions mentioning Hacker News, HN, tech community opinions, or Y Combinator news.
---

# Hacker News Research

Search and analyze Hacker News content. Results written to markdown files for grep/glob searching.

**No API key required.**

## Quick Start

```bash
# Search stories and comments
python scripts/hn_search.py search -q "rust vs go" -o ./research

# Get top stories
python scripts/hn_search.py top --type top -n 20 -o ./research

# Fetch a discussion thread
python scripts/hn_search.py thread --id 12345678 -o ./research

# Search results
grep -r "performance" ./research/
```

## Commands

| Command | Description |
|---------|-------------|
| `search -q QUERY` | Search stories and comments via Algolia |
| `top --type [top\|new\|best]` | Fetch top/new/best stories |
| `thread --id ID` | Fetch story with comments |
| `user --username NAME` | Fetch user profile |

## Workflow

1. **Search** for topic: `search -q "topic" -o ./research`
2. **Find story IDs** in search results markdown
3. **Fetch threads** for interesting stories: `thread --id ID -o ./research`
4. **Grep findings**: `grep -r "pattern" ./research/`

## Output Files

All results written to `--output-dir` (default: `./hn_research/`):

| File Pattern | Contents |
|--------------|----------|
| `hn_search_*.md` | Search results (stories + comments) |
| `hn_top_*.md` | Top/new/best story listings |
| `hn_thread_*.md` | Full discussion threads |
| `hn_user_*.md` | User profiles |

## API Reference

See [references/api_reference.md](references/api_reference.md) for API details.

### Direct API Access

Firebase (specific items):
```
https://hacker-news.firebaseio.com/v0/item/{id}.json
https://hacker-news.firebaseio.com/v0/topstories.json
```

Algolia (search):
```
https://hn.algolia.com/api/v1/search?query={term}&tags=story
https://hn.algolia.com/api/v1/search?query={term}&tags=comment
```
