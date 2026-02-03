#!/usr/bin/env python3
"""
Hacker News Research Tool - Search stories and comments, analyze discussions.

Usage:
    python hn_search.py search --query "keyword" [--output-dir ./research]
    python hn_search.py top [--count 20] [--output-dir ./research]
    python hn_search.py thread --id STORY_ID [--output-dir ./research]
    python hn_search.py user --username USERNAME [--output-dir ./research]

Results are written to disk as markdown files for easy searching with grep/glob.

No API key required.
"""

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from html import unescape
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.parse import urlencode, quote
from urllib.error import HTTPError
import re

FIREBASE_BASE = "https://hacker-news.firebaseio.com/v0"
ALGOLIA_BASE = "https://hn.algolia.com/api/v1"


def api_request(url: str) -> dict:
    """Make a request to an API endpoint."""
    try:
        req = Request(url, headers={"Accept": "application/json", "User-Agent": "HN-Research-Tool/1.0"})
        with urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())
    except HTTPError as e:
        print(f"API Error {e.code}: {url}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        return None


def ensure_output_dir(output_dir: str) -> Path:
    """Create output directory if it doesn't exist."""
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def clean_html(text: str) -> str:
    """Convert HTML to plain text."""
    if not text:
        return ""
    # Unescape HTML entities
    text = unescape(text)
    # Convert <p> and <br> to newlines
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'</p>\s*<p>', '\n\n', text)
    # Remove remaining HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip()


def format_timestamp(unix_ts: int) -> str:
    """Convert Unix timestamp to readable date."""
    if not unix_ts:
        return "Unknown"
    return datetime.fromtimestamp(unix_ts).strftime("%Y-%m-%d %H:%M")


# --- Algolia Search ---

def search_stories(query: str, max_results: int = 30) -> list:
    """Search HN stories via Algolia."""
    params = {
        "query": query,
        "tags": "story",
        "hitsPerPage": min(max_results, 100),
    }
    url = f"{ALGOLIA_BASE}/search?{urlencode(params)}"
    data = api_request(url)

    if not data:
        return []

    results = []
    for hit in data.get("hits", []):
        results.append({
            "id": hit.get("objectID"),
            "title": hit.get("title", ""),
            "url": hit.get("url", ""),
            "author": hit.get("author", ""),
            "points": hit.get("points", 0),
            "comments": hit.get("num_comments", 0),
            "created": hit.get("created_at", ""),
            "hn_url": f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
        })

    return results


def search_comments(query: str, max_results: int = 50) -> list:
    """Search HN comments via Algolia."""
    params = {
        "query": query,
        "tags": "comment",
        "hitsPerPage": min(max_results, 100),
    }
    url = f"{ALGOLIA_BASE}/search?{urlencode(params)}"
    data = api_request(url)

    if not data:
        return []

    results = []
    for hit in data.get("hits", []):
        results.append({
            "id": hit.get("objectID"),
            "text": clean_html(hit.get("comment_text", "")),
            "author": hit.get("author", ""),
            "points": hit.get("points", 0),
            "story_id": hit.get("story_id"),
            "story_title": hit.get("story_title", ""),
            "created": hit.get("created_at", ""),
            "hn_url": f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
        })

    return results


# --- Firebase API ---

def fetch_item(item_id: int) -> dict:
    """Fetch a single item from Firebase."""
    url = f"{FIREBASE_BASE}/item/{item_id}.json"
    return api_request(url)


def fetch_items_parallel(item_ids: list, max_workers: int = 10) -> list:
    """Fetch multiple items in parallel."""
    items = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_item, id): id for id in item_ids}
        for future in as_completed(futures):
            item = future.result()
            if item:
                items.append(item)
    # Sort by original order
    id_to_item = {item["id"]: item for item in items}
    return [id_to_item[id] for id in item_ids if id in id_to_item]


def fetch_top_stories(count: int = 30) -> list:
    """Fetch top stories from Firebase."""
    url = f"{FIREBASE_BASE}/topstories.json"
    ids = api_request(url)
    if not ids:
        return []
    return fetch_items_parallel(ids[:count])


def fetch_new_stories(count: int = 30) -> list:
    """Fetch newest stories from Firebase."""
    url = f"{FIREBASE_BASE}/newstories.json"
    ids = api_request(url)
    if not ids:
        return []
    return fetch_items_parallel(ids[:count])


def fetch_best_stories(count: int = 30) -> list:
    """Fetch best stories from Firebase."""
    url = f"{FIREBASE_BASE}/beststories.json"
    ids = api_request(url)
    if not ids:
        return []
    return fetch_items_parallel(ids[:count])


def fetch_thread(story_id: int, max_comments: int = 100) -> dict:
    """Fetch a story and its comments."""
    story = fetch_item(story_id)
    if not story:
        return None

    comments = []
    comment_ids = story.get("kids", [])[:max_comments]

    if comment_ids:
        raw_comments = fetch_items_parallel(comment_ids)
        for c in raw_comments:
            if c and c.get("type") == "comment" and not c.get("deleted") and not c.get("dead"):
                comments.append({
                    "id": c.get("id"),
                    "author": c.get("by", "[deleted]"),
                    "text": clean_html(c.get("text", "")),
                    "time": c.get("time"),
                    "replies": len(c.get("kids", [])),
                })

    return {
        "story": {
            "id": story.get("id"),
            "title": story.get("title", ""),
            "url": story.get("url", ""),
            "author": story.get("by", ""),
            "points": story.get("score", 0),
            "comments_count": story.get("descendants", 0),
            "time": story.get("time"),
            "text": clean_html(story.get("text", "")),
            "hn_url": f"https://news.ycombinator.com/item?id={story.get('id')}",
        },
        "comments": comments,
    }


def fetch_user(username: str) -> dict:
    """Fetch user profile from Firebase."""
    url = f"{FIREBASE_BASE}/user/{username}.json"
    user = api_request(url)
    if not user:
        return None

    return {
        "username": user.get("id"),
        "karma": user.get("karma", 0),
        "created": user.get("created"),
        "about": clean_html(user.get("about", "")),
        "submissions": user.get("submitted", [])[:20],
    }


# --- Write to Markdown ---

def write_search_results(stories: list, comments: list, query: str, output_dir: Path) -> str:
    """Write search results to markdown."""
    safe_query = re.sub(r'[^\w\s-]', '', query)[:50].strip().replace(' ', '_')
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"hn_search_{safe_query}_{timestamp}.md"
    filepath = output_dir / filename

    lines = [
        f"# Hacker News Search: {query}",
        f"",
        f"**Date:** {datetime.now().isoformat()}",
        f"**Stories found:** {len(stories)}",
        f"**Comments found:** {len(comments)}",
        f"",
        f"---",
        f"",
    ]

    if stories:
        lines.extend([
            f"## Stories",
            f"",
        ])
        for i, story in enumerate(stories, 1):
            lines.extend([
                f"### {i}. {story['title']}",
                f"",
                f"- **ID:** `{story['id']}`",
                f"- **Author:** {story['author']}",
                f"- **Points:** {story['points']} | **Comments:** {story['comments']}",
                f"- **URL:** {story['url'] or 'N/A'}",
                f"- **HN Link:** {story['hn_url']}",
                f"- **Date:** {story['created']}",
                f"",
            ])

    if comments:
        lines.extend([
            f"---",
            f"",
            f"## Comments",
            f"",
        ])
        for i, comment in enumerate(comments, 1):
            lines.extend([
                f"### Comment {i} (on: {comment['story_title'][:60]})",
                f"",
                f"- **Author:** {comment['author']}",
                f"- **Story ID:** `{comment['story_id']}`",
                f"- **HN Link:** {comment['hn_url']}",
                f"",
                f"{comment['text'][:1000]}",
                f"",
            ])

    filepath.write_text("\n".join(lines))
    return str(filepath)


def write_top_stories(stories: list, story_type: str, output_dir: Path) -> str:
    """Write top/new/best stories to markdown."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"hn_{story_type}_{timestamp}.md"
    filepath = output_dir / filename

    lines = [
        f"# Hacker News {story_type.title()} Stories",
        f"",
        f"**Date:** {datetime.now().isoformat()}",
        f"**Count:** {len(stories)}",
        f"",
        f"---",
        f"",
    ]

    for i, story in enumerate(stories, 1):
        lines.extend([
            f"## {i}. {story.get('title', 'No title')}",
            f"",
            f"- **ID:** `{story.get('id')}`",
            f"- **Author:** {story.get('by', 'Unknown')}",
            f"- **Points:** {story.get('score', 0)} | **Comments:** {story.get('descendants', 0)}",
            f"- **URL:** {story.get('url', 'N/A')}",
            f"- **HN Link:** https://news.ycombinator.com/item?id={story.get('id')}",
            f"- **Posted:** {format_timestamp(story.get('time'))}",
            f"",
        ])
        if story.get("text"):
            lines.extend([
                f"> {clean_html(story.get('text'))[:500]}",
                f"",
            ])

    filepath.write_text("\n".join(lines))
    return str(filepath)


def write_thread(thread: dict, output_dir: Path) -> str:
    """Write a discussion thread to markdown."""
    story = thread["story"]
    comments = thread["comments"]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"hn_thread_{story['id']}_{timestamp}.md"
    filepath = output_dir / filename

    lines = [
        f"# {story['title']}",
        f"",
        f"**ID:** `{story['id']}`",
        f"**Author:** {story['author']}",
        f"**Points:** {story['points']} | **Comments:** {story['comments_count']}",
        f"**URL:** {story['url'] or 'N/A'}",
        f"**HN Link:** {story['hn_url']}",
        f"**Posted:** {format_timestamp(story['time'])}",
        f"",
    ]

    if story.get("text"):
        lines.extend([
            f"## Story Text",
            f"",
            f"{story['text']}",
            f"",
        ])

    lines.extend([
        f"---",
        f"",
        f"## Comments ({len(comments)} loaded)",
        f"",
    ])

    for i, comment in enumerate(comments, 1):
        lines.extend([
            f"### {i}. {comment['author']} ({format_timestamp(comment['time'])})",
            f"",
            f"{comment['text']}",
            f"",
            f"_Replies: {comment['replies']}_",
            f"",
            f"---",
            f"",
        ])

    filepath.write_text("\n".join(lines))
    return str(filepath)


def write_user(user: dict, output_dir: Path) -> str:
    """Write user profile to markdown."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"hn_user_{user['username']}_{timestamp}.md"
    filepath = output_dir / filename

    lines = [
        f"# HN User: {user['username']}",
        f"",
        f"**Karma:** {user['karma']}",
        f"**Created:** {format_timestamp(user['created'])}",
        f"**Profile:** https://news.ycombinator.com/user?id={user['username']}",
        f"",
    ]

    if user.get("about"):
        lines.extend([
            f"## About",
            f"",
            f"{user['about']}",
            f"",
        ])

    lines.extend([
        f"## Recent Submissions (IDs)",
        f"",
        f"```",
        ", ".join(str(s) for s in user["submissions"]),
        f"```",
        f"",
    ])

    filepath.write_text("\n".join(lines))
    return str(filepath)


# --- CLI ---

def add_output_arg(parser):
    """Add common output-dir argument."""
    parser.add_argument("--output-dir", "-o", default="./hn_research",
                        help="Output directory (default: ./hn_research)")


def main():
    parser = argparse.ArgumentParser(description="Hacker News Research Tool")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Search command
    search_p = subparsers.add_parser("search", help="Search stories and comments")
    search_p.add_argument("--query", "-q", required=True, help="Search query")
    search_p.add_argument("--max-stories", "-s", type=int, default=20)
    search_p.add_argument("--max-comments", "-c", type=int, default=30)
    add_output_arg(search_p)

    # Top/New/Best stories command
    stories_p = subparsers.add_parser("top", help="Fetch top/new/best stories")
    stories_p.add_argument("--type", "-t", choices=["top", "new", "best"], default="top")
    stories_p.add_argument("--count", "-n", type=int, default=30)
    add_output_arg(stories_p)

    # Thread command
    thread_p = subparsers.add_parser("thread", help="Fetch a discussion thread")
    thread_p.add_argument("--id", "-i", required=True, type=int, help="Story ID")
    thread_p.add_argument("--max-comments", "-n", type=int, default=100)
    add_output_arg(thread_p)

    # User command
    user_p = subparsers.add_parser("user", help="Fetch user profile")
    user_p.add_argument("--username", "-u", required=True, help="HN username")
    add_output_arg(user_p)

    args = parser.parse_args()
    output_dir = ensure_output_dir(args.output_dir)

    if args.command == "search":
        stories = search_stories(args.query, args.max_stories)
        comments = search_comments(args.query, args.max_comments)
        filepath = write_search_results(stories, comments, args.query, output_dir)
        print(f"Wrote {len(stories)} stories and {len(comments)} comments to: {filepath}")

    elif args.command == "top":
        if args.type == "top":
            stories = fetch_top_stories(args.count)
        elif args.type == "new":
            stories = fetch_new_stories(args.count)
        else:
            stories = fetch_best_stories(args.count)
        filepath = write_top_stories(stories, args.type, output_dir)
        print(f"Wrote {len(stories)} {args.type} stories to: {filepath}")

    elif args.command == "thread":
        thread = fetch_thread(args.id, args.max_comments)
        if thread:
            filepath = write_thread(thread, output_dir)
            print(f"Wrote thread with {len(thread['comments'])} comments to: {filepath}")
        else:
            print(f"Error: Could not fetch thread {args.id}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "user":
        user = fetch_user(args.username)
        if user:
            filepath = write_user(user, output_dir)
            print(f"Wrote user profile to: {filepath}")
        else:
            print(f"Error: Could not fetch user {args.username}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
