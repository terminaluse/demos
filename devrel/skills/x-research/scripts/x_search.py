#!/usr/bin/env python3
"""
X (Twitter) Research Tool - Search tweets and analyze engagement.

Usage:
    python x_search.py search --query "keyword" [--output-dir ./research]
    python x_search.py drill --id TWEET_ID [--output-dir ./research]
    python x_search.py user --username USERNAME [--output-dir ./research]

Results are written to disk as markdown files for easy searching with grep/glob.

Requires X_BEARER_TOKEN environment variable.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.parse import urlencode
from urllib.error import HTTPError

BEARER_TOKEN = os.environ.get("X_BEARER_TOKEN")
BASE_URL = "https://api.x.com/2"


def api_request(endpoint: str, params: dict = None) -> dict:
    """Make a request to the X API."""
    if not BEARER_TOKEN:
        print("Error: X_BEARER_TOKEN environment variable not set", file=sys.stderr)
        sys.exit(1)

    url = f"{BASE_URL}/{endpoint}"
    if params:
        url = f"{url}?{urlencode(params)}"

    try:
        req = Request(url, headers={
            "Authorization": f"Bearer {BEARER_TOKEN}",
            "Accept": "application/json",
        })
        with urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())
    except HTTPError as e:
        error_body = e.read().decode()
        print(f"API Error {e.code}: {error_body}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        return None


def ensure_output_dir(output_dir: str) -> Path:
    """Create output directory if it doesn't exist."""
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def format_number(n: int) -> str:
    """Format large numbers with K/M suffix."""
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


# --- Search Tweets ---

def search_recent_tweets(query: str, max_results: int = 50) -> dict:
    """Search recent tweets matching query."""
    params = {
        "query": query,
        "max_results": min(max_results, 100),
        "tweet.fields": "id,text,author_id,created_at,public_metrics,conversation_id",
        "user.fields": "id,name,username,public_metrics,verified",
        "expansions": "author_id",
    }

    data = api_request("tweets/search/recent", params)
    if not data:
        return {"tweets": [], "users": {}}

    # Build user lookup
    users = {}
    for user in data.get("includes", {}).get("users", []):
        users[user["id"]] = user

    tweets = []
    for tweet in data.get("data", []):
        author = users.get(tweet.get("author_id"), {})
        metrics = tweet.get("public_metrics", {})
        tweets.append({
            "id": tweet.get("id"),
            "text": tweet.get("text", ""),
            "created_at": tweet.get("created_at", ""),
            "author_id": tweet.get("author_id"),
            "author_name": author.get("name", "Unknown"),
            "author_username": author.get("username", "unknown"),
            "author_followers": author.get("public_metrics", {}).get("followers_count", 0),
            "author_verified": author.get("verified", False),
            "likes": metrics.get("like_count", 0),
            "retweets": metrics.get("retweet_count", 0),
            "replies": metrics.get("reply_count", 0),
            "quotes": metrics.get("quote_count", 0),
            "url": f"https://x.com/{author.get('username', 'i')}/status/{tweet.get('id')}",
        })

    return {
        "tweets": tweets,
        "meta": data.get("meta", {}),
    }


# --- Drill Down ---

def get_liking_users(tweet_id: str, max_results: int = 100) -> list:
    """Get users who liked a tweet."""
    params = {
        "max_results": min(max_results, 100),
        "user.fields": "id,name,username,public_metrics,verified,description",
    }

    data = api_request(f"tweets/{tweet_id}/liking_users", params)
    if not data or "data" not in data:
        return []

    users = []
    for user in data.get("data", []):
        metrics = user.get("public_metrics", {})
        users.append({
            "id": user.get("id"),
            "name": user.get("name", ""),
            "username": user.get("username", ""),
            "followers": metrics.get("followers_count", 0),
            "following": metrics.get("following_count", 0),
            "verified": user.get("verified", False),
            "description": user.get("description", "")[:200],
            "url": f"https://x.com/{user.get('username')}",
        })

    return users


def get_retweeted_by(tweet_id: str, max_results: int = 100) -> list:
    """Get users who retweeted a tweet."""
    params = {
        "max_results": min(max_results, 100),
        "user.fields": "id,name,username,public_metrics,verified,description",
    }

    data = api_request(f"tweets/{tweet_id}/retweeted_by", params)
    if not data or "data" not in data:
        return []

    users = []
    for user in data.get("data", []):
        metrics = user.get("public_metrics", {})
        users.append({
            "id": user.get("id"),
            "name": user.get("name", ""),
            "username": user.get("username", ""),
            "followers": metrics.get("followers_count", 0),
            "following": metrics.get("following_count", 0),
            "verified": user.get("verified", False),
            "description": user.get("description", "")[:200],
            "url": f"https://x.com/{user.get('username')}",
        })

    return users


def get_quote_tweets(tweet_id: str, max_results: int = 50) -> list:
    """Get quote tweets for a tweet."""
    params = {
        "max_results": min(max_results, 100),
        "tweet.fields": "id,text,author_id,created_at,public_metrics",
        "user.fields": "id,name,username,public_metrics,verified",
        "expansions": "author_id",
    }

    data = api_request(f"tweets/{tweet_id}/quote_tweets", params)
    if not data:
        return []

    # Build user lookup
    users = {}
    for user in data.get("includes", {}).get("users", []):
        users[user["id"]] = user

    quotes = []
    for tweet in data.get("data", []):
        author = users.get(tweet.get("author_id"), {})
        metrics = tweet.get("public_metrics", {})
        quotes.append({
            "id": tweet.get("id"),
            "text": tweet.get("text", ""),
            "created_at": tweet.get("created_at", ""),
            "author_name": author.get("name", "Unknown"),
            "author_username": author.get("username", "unknown"),
            "author_followers": author.get("public_metrics", {}).get("followers_count", 0),
            "likes": metrics.get("like_count", 0),
            "retweets": metrics.get("retweet_count", 0),
            "url": f"https://x.com/{author.get('username', 'i')}/status/{tweet.get('id')}",
        })

    return quotes


def drill_down_tweet(tweet_id: str, max_users: int = 50) -> dict:
    """Get comprehensive engagement data for a tweet."""
    return {
        "tweet_id": tweet_id,
        "liking_users": get_liking_users(tweet_id, max_users),
        "retweeted_by": get_retweeted_by(tweet_id, max_users),
        "quote_tweets": get_quote_tweets(tweet_id, max_users),
    }


# --- User Lookup ---

def get_user_by_username(username: str) -> dict:
    """Get user profile by username."""
    params = {
        "user.fields": "id,name,username,created_at,description,public_metrics,verified,location,url",
    }

    # Remove @ if present
    username = username.lstrip("@")

    data = api_request(f"users/by/username/{username}", params)
    if not data or "data" not in data:
        return None

    user = data["data"]
    metrics = user.get("public_metrics", {})
    return {
        "id": user.get("id"),
        "name": user.get("name", ""),
        "username": user.get("username", ""),
        "description": user.get("description", ""),
        "location": user.get("location", ""),
        "url": user.get("url", ""),
        "created_at": user.get("created_at", ""),
        "verified": user.get("verified", False),
        "followers": metrics.get("followers_count", 0),
        "following": metrics.get("following_count", 0),
        "tweets": metrics.get("tweet_count", 0),
        "profile_url": f"https://x.com/{user.get('username')}",
    }


# --- Write to Markdown ---

def write_search_results(results: dict, query: str, output_dir: Path) -> str:
    """Write search results to markdown."""
    safe_query = re.sub(r'[^\w\s-]', '', query)[:50].strip().replace(' ', '_')
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"x_search_{safe_query}_{timestamp}.md"
    filepath = output_dir / filename

    tweets = results["tweets"]

    lines = [
        f"# X Search: {query}",
        f"",
        f"**Date:** {datetime.now().isoformat()}",
        f"**Results:** {len(tweets)} tweets",
        f"",
        f"---",
        f"",
    ]

    for i, tweet in enumerate(tweets, 1):
        verified = " ✓" if tweet["author_verified"] else ""
        lines.extend([
            f"## {i}. @{tweet['author_username']}{verified} ({format_number(tweet['author_followers'])} followers)",
            f"",
            f"**{tweet['author_name']}** · {tweet['created_at']}",
            f"",
            f"{tweet['text']}",
            f"",
            f"- **Likes:** {format_number(tweet['likes'])} | **Retweets:** {format_number(tweet['retweets'])} | **Replies:** {format_number(tweet['replies'])} | **Quotes:** {format_number(tweet['quotes'])}",
            f"- **Tweet ID:** `{tweet['id']}`",
            f"- **URL:** {tweet['url']}",
            f"",
            f"---",
            f"",
        ])

    filepath.write_text("\n".join(lines))
    return str(filepath)


def write_drill_down(data: dict, output_dir: Path) -> str:
    """Write drill-down analysis to markdown."""
    tweet_id = data["tweet_id"]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"x_drill_{tweet_id}_{timestamp}.md"
    filepath = output_dir / filename

    liking = data["liking_users"]
    retweeted = data["retweeted_by"]
    quotes = data["quote_tweets"]

    lines = [
        f"# Tweet Drill-Down: {tweet_id}",
        f"",
        f"**Date:** {datetime.now().isoformat()}",
        f"**Tweet URL:** https://x.com/i/status/{tweet_id}",
        f"",
        f"## Summary",
        f"",
        f"| Metric | Count |",
        f"|--------|-------|",
        f"| Liking Users | {len(liking)} |",
        f"| Retweeted By | {len(retweeted)} |",
        f"| Quote Tweets | {len(quotes)} |",
        f"",
        f"---",
        f"",
    ]

    # Liking users
    lines.extend([
        f"## Liking Users ({len(liking)})",
        f"",
    ])
    if liking:
        # Sort by followers
        liking_sorted = sorted(liking, key=lambda u: u["followers"], reverse=True)
        for user in liking_sorted[:20]:
            verified = " ✓" if user["verified"] else ""
            lines.extend([
                f"### @{user['username']}{verified} ({format_number(user['followers'])} followers)",
                f"",
                f"**{user['name']}**",
                f"",
                f"> {user['description']}",
                f"",
            ])
    else:
        lines.append("_No liking users found._\n")

    lines.extend(["---", ""])

    # Retweeted by
    lines.extend([
        f"## Retweeted By ({len(retweeted)})",
        f"",
    ])
    if retweeted:
        retweeted_sorted = sorted(retweeted, key=lambda u: u["followers"], reverse=True)
        for user in retweeted_sorted[:20]:
            verified = " ✓" if user["verified"] else ""
            lines.extend([
                f"### @{user['username']}{verified} ({format_number(user['followers'])} followers)",
                f"",
                f"**{user['name']}**",
                f"",
                f"> {user['description']}",
                f"",
            ])
    else:
        lines.append("_No retweets found._\n")

    lines.extend(["---", ""])

    # Quote tweets
    lines.extend([
        f"## Quote Tweets ({len(quotes)})",
        f"",
    ])
    if quotes:
        for i, quote in enumerate(quotes, 1):
            lines.extend([
                f"### {i}. @{quote['author_username']} ({format_number(quote['author_followers'])} followers)",
                f"",
                f"{quote['text']}",
                f"",
                f"- **Likes:** {format_number(quote['likes'])} | **Retweets:** {format_number(quote['retweets'])}",
                f"- **URL:** {quote['url']}",
                f"",
            ])
    else:
        lines.append("_No quote tweets found._\n")

    filepath.write_text("\n".join(lines))
    return str(filepath)


def write_user_profile(user: dict, output_dir: Path) -> str:
    """Write user profile to markdown."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"x_user_{user['username']}_{timestamp}.md"
    filepath = output_dir / filename

    verified = " ✓" if user["verified"] else ""

    lines = [
        f"# X User: @{user['username']}{verified}",
        f"",
        f"**Name:** {user['name']}",
        f"**ID:** `{user['id']}`",
        f"**Profile:** {user['profile_url']}",
        f"",
        f"## Stats",
        f"",
        f"| Metric | Count |",
        f"|--------|-------|",
        f"| Followers | {format_number(user['followers'])} |",
        f"| Following | {format_number(user['following'])} |",
        f"| Tweets | {format_number(user['tweets'])} |",
        f"",
    ]

    if user.get("location"):
        lines.append(f"**Location:** {user['location']}\n")

    if user.get("url"):
        lines.append(f"**Website:** {user['url']}\n")

    if user.get("created_at"):
        lines.append(f"**Joined:** {user['created_at']}\n")

    if user.get("description"):
        lines.extend([
            f"",
            f"## Bio",
            f"",
            f"{user['description']}",
            f"",
        ])

    filepath.write_text("\n".join(lines))
    return str(filepath)


# --- CLI ---

def add_output_arg(parser):
    """Add common output-dir argument."""
    parser.add_argument("--output-dir", "-o", default="./x_research",
                        help="Output directory (default: ./x_research)")


def main():
    parser = argparse.ArgumentParser(description="X (Twitter) Research Tool")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Search command
    search_p = subparsers.add_parser("search", help="Search recent tweets")
    search_p.add_argument("--query", "-q", required=True, help="Search query")
    search_p.add_argument("--max-results", "-n", type=int, default=50)
    add_output_arg(search_p)

    # Drill command
    drill_p = subparsers.add_parser("drill", help="Drill down into a tweet")
    drill_p.add_argument("--id", "-i", required=True, help="Tweet ID")
    drill_p.add_argument("--max-users", "-n", type=int, default=50)
    add_output_arg(drill_p)

    # User command
    user_p = subparsers.add_parser("user", help="Get user profile")
    user_p.add_argument("--username", "-u", required=True, help="X username")
    add_output_arg(user_p)

    args = parser.parse_args()
    output_dir = ensure_output_dir(args.output_dir)

    if args.command == "search":
        results = search_recent_tweets(args.query, args.max_results)
        filepath = write_search_results(results, args.query, output_dir)
        print(f"Wrote {len(results['tweets'])} tweets to: {filepath}")

    elif args.command == "drill":
        data = drill_down_tweet(args.id, args.max_users)
        filepath = write_drill_down(data, output_dir)
        total = len(data["liking_users"]) + len(data["retweeted_by"]) + len(data["quote_tweets"])
        print(f"Wrote drill-down ({total} engagements) to: {filepath}")

    elif args.command == "user":
        user = get_user_by_username(args.username)
        if user:
            filepath = write_user_profile(user, output_dir)
            print(f"Wrote user profile to: {filepath}")
        else:
            print(f"Error: Could not fetch user @{args.username}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
