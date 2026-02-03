---
name: youtube-research
description: Search YouTube for videos by keywords and analyze comments for market signals including pain points, feature requests, and competitor mentions. Use when researching product feedback, understanding user sentiment, finding market opportunities, or analyzing what people say in YouTube comments about products/topics.
---

# YouTube Research

Research YouTube videos and comments to find market signals. Results are written to markdown files for easy searching with grep/glob.

## Setup

Set `YOUTUBE_API_KEY` environment variable. Get a key from [Google Cloud Console](https://console.cloud.google.com/apis/credentials).

## Quick Start

```bash
# Search for videos
python scripts/youtube_search.py search -q "product review" -o ./research

# Analyze comments for signals
python scripts/youtube_search.py analyze -v VIDEO_ID -o ./research

# Then search results with grep
grep -r "pain_point" ./research/
grep -r "switched to" ./research/
```

## Signal Types

- **pain_point** - Frustrations, complaints, broken features
- **feature_request** - Suggestions, wants, feature ideas
- **competitor_mention** - Comparisons, alternatives, switching
- **purchase_intent** - Buying questions, price discussions

## Workflow

1. **Search** for videos: `search -q "keyword" -o ./research`
2. **Extract video IDs** from search results markdown
3. **Analyze** each video: `analyze -v VIDEO_ID -o ./research`
4. **Search findings** with grep: `grep -r "pattern" ./research/`

### Search Strategies

| Goal | Query |
|------|-------|
| Reviews | `"[product] review"` |
| Comparisons | `"[product] vs"` |
| Problems | `"[product] problems"` |

### Filter Signals

```bash
python scripts/youtube_search.py analyze -v VIDEO_ID --signals pain_point,feature_request
```

## Output Files

All results written to `--output-dir` (default: `./youtube_research/`):

- `search_*.md` - Video search results with IDs, titles, channels
- `comments_*.md` - Raw comments from a video
- `analysis_*.md` - Comments grouped by signal type

## API Reference

See [references/youtube_api.md](references/youtube_api.md) for YouTube API details.
