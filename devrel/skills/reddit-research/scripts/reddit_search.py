#!/usr/bin/env python3
"""
Reddit Research Tool - Search subreddits, posts, and comments.

Usage:
    python reddit_search.py subreddits --query "keyword" [--output-dir ./research]
    python reddit_search.py info --subreddit NAME [--output-dir ./research]
    python reddit_search.py posts --subreddit NAME [--sort hot] [--output-dir ./research]
    python reddit_search.py search --query "keyword" [--subreddits "sub1,sub2"] [--output-dir ./research]
    python reddit_search.py comments --post-id ID [--output-dir ./research]

Results are written to disk as markdown files for easy searching with grep/glob.

No API key required (uses public JSON API).

Workflow Strategies:
1. Broad search: search --query "keyword" (searches all of Reddit)
2. Targeted: subreddits --query "topic" → search --query "keyword" --subreddits "found,subs"
3. Direct: search --query "keyword" --subreddits "specific,subs"
"""

import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.parse import urlencode, quote
from urllib.error import HTTPError

BASE_URL = "https://www.reddit.com"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


def api_request(path: str, retries: int = 2) -> dict:
    """Make a request to Reddit's JSON API."""
    # Ensure .json extension
    if "?" in path:
        base, query = path.split("?", 1)
        if not base.endswith(".json"):
            base += ".json"
        url = f"{BASE_URL}{base}?{query}"
    else:
        url = f"{BASE_URL}{path}.json"

    for attempt in range(retries + 1):
        try:
            req = Request(url, headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
            })
            with urlopen(req, timeout=15) as response:
                text = response.read().decode()
                # Check for HTML response (Reddit sometimes does this)
                if text.strip().startswith("<"):
                    if attempt < retries:
                        time.sleep(2)
                        continue
                    return None
                return json.loads(text)
        except HTTPError as e:
            if e.code == 429:
                print("Rate limited. Waiting 60 seconds...", file=sys.stderr)
                time.sleep(60)
                continue
            if e.code == 404:
                return None
            if attempt < retries:
                time.sleep(2)
                continue
            print(f"API Error {e.code}: {path}", file=sys.stderr)
            return None
        except Exception as e:
            if attempt < retries:
                time.sleep(2)
                continue
            print(f"Request failed: {e}", file=sys.stderr)
            return None
    return None


def ensure_output_dir(output_dir: str) -> Path:
    """Create output directory if it doesn't exist."""
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def format_number(n: int) -> str:
    """Format large numbers with K/M suffix."""
    if not n:
        return "0"
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


def format_timestamp(unix_ts: int) -> str:
    """Convert Unix timestamp to readable date."""
    if not unix_ts:
        return "Unknown"
    return datetime.fromtimestamp(unix_ts).strftime("%Y-%m-%d %H:%M")


def normalize_subreddit(name: str) -> str:
    """Normalize subreddit name (remove r/ prefix)."""
    return name.lower().replace("r/", "").strip()


def extract_subreddit_links(text: str) -> list:
    """Extract r/subreddit mentions from text."""
    if not text:
        return []
    matches = re.findall(r"/r/([a-zA-Z0-9_-]+)", text)
    return list(set(matches))


# --- Subreddit Discovery ---

def search_subreddits(query: str, limit: int = 20) -> list:
    """Search for subreddits matching query."""
    path = f"/subreddits/search?q={quote(query)}&limit={limit}&include_over_18=1"
    data = api_request(path)
    if not data:
        return []

    results = []
    for child in data.get("data", {}).get("children", []):
        sub = child.get("data", {})
        results.append({
            "name": sub.get("display_name", ""),
            "subscribers": sub.get("subscribers", 0),
            "description": (sub.get("public_description") or "")[:200],
            "nsfw": sub.get("over18", False),
            "created": sub.get("created_utc"),
            "url": f"https://reddit.com/r/{sub.get('display_name', '')}",
        })

    return results


def get_subreddit_info(name: str) -> dict:
    """Get detailed info about a subreddit."""
    name = normalize_subreddit(name)
    data = api_request(f"/r/{name}/about")
    if not data:
        return None

    sub = data.get("data", {})
    description = sub.get("description", "") or ""
    public_desc = sub.get("public_description", "") or ""

    return {
        "name": sub.get("display_name", name),
        "subscribers": sub.get("subscribers", 0),
        "active_users": sub.get("accounts_active", 0),
        "description": public_desc[:500],
        "full_description": description[:2000],
        "nsfw": sub.get("over18", False),
        "created": sub.get("created_utc"),
        "related_subs": extract_subreddit_links(description + " " + public_desc),
        "url": f"https://reddit.com/r/{sub.get('display_name', name)}",
    }


def get_popular_subreddits(listing: str = "popular", limit: int = 25) -> list:
    """Get popular or new subreddits."""
    path = f"/subreddits/{listing}?limit={limit}"
    data = api_request(path)
    if not data:
        return []

    results = []
    for child in data.get("data", {}).get("children", []):
        sub = child.get("data", {})
        results.append({
            "name": sub.get("display_name", ""),
            "subscribers": sub.get("subscribers", 0),
            "description": (sub.get("public_description") or "")[:200],
            "url": f"https://reddit.com/r/{sub.get('display_name', '')}",
        })

    return results


# --- Post Search ---

def get_subreddit_posts(name: str, sort: str = "hot", time_filter: str = "day", limit: int = 25) -> list:
    """Get posts from a subreddit."""
    name = normalize_subreddit(name)

    if sort in ["top", "controversial"]:
        path = f"/r/{name}/{sort}?t={time_filter}&limit={limit}"
    else:
        path = f"/r/{name}/{sort}?limit={limit}"

    data = api_request(path)
    if not data:
        return []

    posts = []
    for child in data.get("data", {}).get("children", []):
        post = child.get("data", {})
        posts.append({
            "id": post.get("id", ""),
            "title": post.get("title", ""),
            "author": post.get("author", "[deleted]"),
            "subreddit": post.get("subreddit", ""),
            "score": post.get("score", 0),
            "upvote_ratio": post.get("upvote_ratio", 0),
            "comments": post.get("num_comments", 0),
            "created": post.get("created_utc"),
            "url": post.get("url", ""),
            "selftext": (post.get("selftext") or "")[:500],
            "flair": post.get("link_flair_text"),
            "permalink": f"https://reddit.com{post.get('permalink', '')}",
        })

    return posts


def search_posts(query: str, subreddits: list = None, sort: str = "relevance",
                 time_filter: str = "all", limit: int = 50) -> list:
    """Search posts across Reddit or specific subreddits."""
    all_posts = []

    if subreddits:
        # Search each subreddit individually
        per_sub_limit = max(10, limit // len(subreddits))
        for sub in subreddits:
            sub = normalize_subreddit(sub)
            path = f"/r/{sub}/search?q={quote(query)}&restrict_sr=on&sort={sort}&t={time_filter}&limit={per_sub_limit}"
            data = api_request(path)
            if data:
                for child in data.get("data", {}).get("children", []):
                    post = child.get("data", {})
                    all_posts.append({
                        "id": post.get("id", ""),
                        "title": post.get("title", ""),
                        "author": post.get("author", "[deleted]"),
                        "subreddit": post.get("subreddit", ""),
                        "score": post.get("score", 0),
                        "comments": post.get("num_comments", 0),
                        "created": post.get("created_utc"),
                        "selftext": (post.get("selftext") or "")[:300],
                        "permalink": f"https://reddit.com{post.get('permalink', '')}",
                    })
            time.sleep(0.5)  # Rate limiting between subreddits
    else:
        # Search all of Reddit
        path = f"/search?q={quote(query)}&sort={sort}&t={time_filter}&limit={limit}"
        data = api_request(path)
        if data:
            for child in data.get("data", {}).get("children", []):
                post = child.get("data", {})
                all_posts.append({
                    "id": post.get("id", ""),
                    "title": post.get("title", ""),
                    "author": post.get("author", "[deleted]"),
                    "subreddit": post.get("subreddit", ""),
                    "score": post.get("score", 0),
                    "comments": post.get("num_comments", 0),
                    "created": post.get("created_utc"),
                    "selftext": (post.get("selftext") or "")[:300],
                    "permalink": f"https://reddit.com{post.get('permalink', '')}",
                })

    # Sort by score
    all_posts.sort(key=lambda p: p.get("score", 0), reverse=True)
    return all_posts[:limit]


# --- Comments ---

def get_post_comments(post_id: str, limit: int = 100) -> dict:
    """Get comments from a post."""
    # Handle full URLs
    if post_id.startswith("http"):
        match = re.search(r"comments/([a-z0-9]+)", post_id, re.I)
        if match:
            post_id = match.group(1)

    # First get post info to find subreddit
    post_data = api_request(f"/by_id/t3_{post_id}")
    if not post_data:
        return None

    children = post_data.get("data", {}).get("children", [])
    if not children:
        return None

    post_info = children[0].get("data", {})
    subreddit = post_info.get("subreddit", "")

    if not subreddit:
        return None

    # Fetch comments
    data = api_request(f"/r/{subreddit}/comments/{post_id}?limit={limit}")
    if not data or len(data) < 2:
        return None

    def parse_comments(children, depth=0):
        results = []
        for c in children:
            if c.get("kind") != "t1":
                continue
            cdata = c.get("data", {})
            results.append({
                "id": cdata.get("id", ""),
                "author": cdata.get("author", "[deleted]"),
                "body": (cdata.get("body") or "")[:1000],
                "score": cdata.get("score", 0),
                "depth": depth,
                "created": cdata.get("created_utc"),
            })
            # Recursively get replies
            replies = cdata.get("replies")
            if replies and isinstance(replies, dict):
                reply_children = replies.get("data", {}).get("children", [])
                results.extend(parse_comments(reply_children, depth + 1))
        return results

    comments = parse_comments(data[1].get("data", {}).get("children", []))

    return {
        "post": {
            "id": post_info.get("id", ""),
            "title": post_info.get("title", ""),
            "author": post_info.get("author", "[deleted]"),
            "subreddit": subreddit,
            "score": post_info.get("score", 0),
            "selftext": (post_info.get("selftext") or "")[:1000],
            "permalink": f"https://reddit.com{post_info.get('permalink', '')}",
        },
        "comments": comments,
    }


# --- Write to Markdown ---

def write_subreddit_search(results: list, query: str, output_dir: Path) -> str:
    """Write subreddit search results to markdown."""
    safe_query = re.sub(r'[^\w\s-]', '', query)[:50].strip().replace(' ', '_')
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"reddit_subs_{safe_query}_{timestamp}.md"
    filepath = output_dir / filename

    lines = [
        f"# Reddit Subreddit Search: {query}",
        f"",
        f"**Date:** {datetime.now().isoformat()}",
        f"**Results:** {len(results)} subreddits",
        f"",
        f"---",
        f"",
    ]

    for i, sub in enumerate(results, 1):
        nsfw = " (NSFW)" if sub.get("nsfw") else ""
        lines.extend([
            f"## {i}. r/{sub['name']}{nsfw}",
            f"",
            f"- **Subscribers:** {format_number(sub['subscribers'])}",
            f"- **URL:** {sub['url']}",
            f"",
            f"> {sub['description']}",
            f"",
            f"---",
            f"",
        ])

    filepath.write_text("\n".join(lines))
    return str(filepath)


def write_subreddit_info(info: dict, output_dir: Path) -> str:
    """Write subreddit info to markdown."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"reddit_info_{info['name']}_{timestamp}.md"
    filepath = output_dir / filename

    nsfw = " (NSFW)" if info.get("nsfw") else ""

    lines = [
        f"# r/{info['name']}{nsfw}",
        f"",
        f"**URL:** {info['url']}",
        f"**Subscribers:** {format_number(info['subscribers'])}",
        f"**Active Users:** {format_number(info['active_users'])}",
        f"**Created:** {format_timestamp(info['created'])}",
        f"",
        f"## Description",
        f"",
        f"{info['description']}",
        f"",
    ]

    if info.get("related_subs"):
        lines.extend([
            f"## Related Subreddits",
            f"",
            ", ".join(f"r/{s}" for s in info["related_subs"][:20]),
            f"",
        ])

    if info.get("full_description") and len(info["full_description"]) > len(info["description"]):
        lines.extend([
            f"## Full Description",
            f"",
            f"{info['full_description']}",
            f"",
        ])

    filepath.write_text("\n".join(lines))
    return str(filepath)


def write_posts(posts: list, source: str, output_dir: Path) -> str:
    """Write posts to markdown."""
    safe_source = re.sub(r'[^\w\s-]', '', source)[:50].strip().replace(' ', '_')
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"reddit_posts_{safe_source}_{timestamp}.md"
    filepath = output_dir / filename

    lines = [
        f"# Reddit Posts: {source}",
        f"",
        f"**Date:** {datetime.now().isoformat()}",
        f"**Results:** {len(posts)} posts",
        f"",
        f"---",
        f"",
    ]

    for i, post in enumerate(posts, 1):
        lines.extend([
            f"## {i}. {post['title']}",
            f"",
            f"- **Subreddit:** r/{post['subreddit']}",
            f"- **Author:** u/{post['author']}",
            f"- **Score:** {format_number(post['score'])} | **Comments:** {format_number(post['comments'])}",
            f"- **Posted:** {format_timestamp(post.get('created'))}",
            f"- **Post ID:** `{post['id']}`",
            f"- **URL:** {post['permalink']}",
            f"",
        ])
        if post.get("selftext"):
            lines.extend([
                f"> {post['selftext'][:400]}{'...' if len(post.get('selftext', '')) > 400 else ''}",
                f"",
            ])
        lines.extend(["---", ""])

    filepath.write_text("\n".join(lines))
    return str(filepath)


def write_search_results(posts: list, query: str, subreddits: list, output_dir: Path) -> str:
    """Write search results to markdown."""
    safe_query = re.sub(r'[^\w\s-]', '', query)[:50].strip().replace(' ', '_')
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"reddit_search_{safe_query}_{timestamp}.md"
    filepath = output_dir / filename

    scope = f"r/{', r/'.join(subreddits)}" if subreddits else "all of Reddit"

    lines = [
        f"# Reddit Search: {query}",
        f"",
        f"**Date:** {datetime.now().isoformat()}",
        f"**Scope:** {scope}",
        f"**Results:** {len(posts)} posts",
        f"",
        f"---",
        f"",
    ]

    # Group by subreddit for easier reading
    by_subreddit = {}
    for post in posts:
        sub = post.get("subreddit", "unknown")
        if sub not in by_subreddit:
            by_subreddit[sub] = []
        by_subreddit[sub].append(post)

    for subreddit, sub_posts in sorted(by_subreddit.items(), key=lambda x: -len(x[1])):
        lines.extend([
            f"## r/{subreddit} ({len(sub_posts)} posts)",
            f"",
        ])

        for post in sub_posts:
            lines.extend([
                f"### {post['title']}",
                f"",
                f"- **Author:** u/{post['author']}",
                f"- **Score:** {format_number(post['score'])} | **Comments:** {format_number(post['comments'])}",
                f"- **Post ID:** `{post['id']}`",
                f"- **URL:** {post['permalink']}",
                f"",
            ])
            if post.get("selftext"):
                lines.extend([
                    f"> {post['selftext'][:300]}{'...' if len(post.get('selftext', '')) > 300 else ''}",
                    f"",
                ])

        lines.extend(["---", ""])

    filepath.write_text("\n".join(lines))
    return str(filepath)


def write_comments(data: dict, output_dir: Path) -> str:
    """Write comments to markdown."""
    post = data["post"]
    comments = data["comments"]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"reddit_comments_{post['id']}_{timestamp}.md"
    filepath = output_dir / filename

    lines = [
        f"# {post['title']}",
        f"",
        f"**Subreddit:** r/{post['subreddit']}",
        f"**Author:** u/{post['author']}",
        f"**Score:** {format_number(post['score'])}",
        f"**URL:** {post['permalink']}",
        f"",
    ]

    if post.get("selftext"):
        lines.extend([
            f"## Post Content",
            f"",
            f"{post['selftext']}",
            f"",
        ])

    lines.extend([
        f"---",
        f"",
        f"## Comments ({len(comments)})",
        f"",
    ])

    for i, comment in enumerate(comments, 1):
        indent = "  " * comment.get("depth", 0)
        lines.extend([
            f"{indent}### {i}. u/{comment['author']} ({format_number(comment['score'])} points)",
            f"",
            f"{indent}{comment['body']}",
            f"",
        ])

    filepath.write_text("\n".join(lines))
    return str(filepath)


# --- CLI ---

def add_output_arg(parser):
    """Add common output-dir argument."""
    parser.add_argument("--output-dir", "-o", default="./reddit_research",
                        help="Output directory (default: ./reddit_research)")


def main():
    parser = argparse.ArgumentParser(
        description="Reddit Research Tool",
        epilog="""
Workflow Strategies:
  1. Broad search:   search -q "keyword" (searches all of Reddit)
  2. Targeted:       subreddits -q "topic" → search -q "keyword" -s "found,subs"
  3. Direct:         search -q "keyword" -s "specific,subs"
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subreddit search command
    subs_p = subparsers.add_parser("subreddits", help="Search for subreddits")
    subs_p.add_argument("--query", "-q", required=True, help="Search query")
    subs_p.add_argument("--limit", "-n", type=int, default=20)
    add_output_arg(subs_p)

    # Subreddit info command
    info_p = subparsers.add_parser("info", help="Get subreddit details")
    info_p.add_argument("--subreddit", "-r", required=True, help="Subreddit name")
    add_output_arg(info_p)

    # Popular/new subreddits command
    popular_p = subparsers.add_parser("popular", help="List popular or new subreddits")
    popular_p.add_argument("--type", "-t", choices=["popular", "new"], default="popular")
    popular_p.add_argument("--limit", "-n", type=int, default=25)
    add_output_arg(popular_p)

    # Get posts from subreddit
    posts_p = subparsers.add_parser("posts", help="Get posts from a subreddit")
    posts_p.add_argument("--subreddit", "-r", required=True, help="Subreddit name")
    posts_p.add_argument("--sort", "-s", choices=["hot", "new", "top", "rising"], default="hot")
    posts_p.add_argument("--time", "-t", choices=["hour", "day", "week", "month", "year", "all"], default="day")
    posts_p.add_argument("--limit", "-n", type=int, default=25)
    add_output_arg(posts_p)

    # Search posts command
    search_p = subparsers.add_parser("search", help="Search posts")
    search_p.add_argument("--query", "-q", required=True, help="Search query")
    search_p.add_argument("--subreddits", "-s", help="Comma-separated subreddits (omit for all)")
    search_p.add_argument("--sort", choices=["relevance", "top", "new", "comments"], default="relevance")
    search_p.add_argument("--time", "-t", choices=["hour", "day", "week", "month", "year", "all"], default="all")
    search_p.add_argument("--limit", "-n", type=int, default=50)
    add_output_arg(search_p)

    # Get comments command
    comments_p = subparsers.add_parser("comments", help="Get post comments")
    comments_p.add_argument("--post-id", "-p", required=True, help="Post ID or URL")
    comments_p.add_argument("--limit", "-n", type=int, default=100)
    add_output_arg(comments_p)

    args = parser.parse_args()
    output_dir = ensure_output_dir(args.output_dir)

    if args.command == "subreddits":
        results = search_subreddits(args.query, args.limit)
        filepath = write_subreddit_search(results, args.query, output_dir)
        print(f"Wrote {len(results)} subreddits to: {filepath}")

    elif args.command == "info":
        info = get_subreddit_info(args.subreddit)
        if info:
            filepath = write_subreddit_info(info, output_dir)
            print(f"Wrote subreddit info to: {filepath}")
        else:
            print(f"Error: Subreddit r/{args.subreddit} not found", file=sys.stderr)
            sys.exit(1)

    elif args.command == "popular":
        results = get_popular_subreddits(args.type, args.limit)
        filepath = write_subreddit_search(results, f"{args.type}_subreddits", output_dir)
        print(f"Wrote {len(results)} {args.type} subreddits to: {filepath}")

    elif args.command == "posts":
        posts = get_subreddit_posts(args.subreddit, args.sort, args.time, args.limit)
        filepath = write_posts(posts, f"r/{args.subreddit}_{args.sort}", output_dir)
        print(f"Wrote {len(posts)} posts to: {filepath}")

    elif args.command == "search":
        subreddits = [s.strip() for s in args.subreddits.split(",")] if args.subreddits else None
        posts = search_posts(args.query, subreddits, args.sort, args.time, args.limit)
        filepath = write_search_results(posts, args.query, subreddits, output_dir)
        print(f"Wrote {len(posts)} posts to: {filepath}")

    elif args.command == "comments":
        data = get_post_comments(args.post_id, args.limit)
        if data:
            filepath = write_comments(data, output_dir)
            print(f"Wrote {len(data['comments'])} comments to: {filepath}")
        else:
            print(f"Error: Could not fetch post {args.post_id}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
