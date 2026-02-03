#!/usr/bin/env python3
"""
YouTube Research Tool - Search videos and analyze comments for market signals.

Usage:
    python youtube_search.py search --query "keyword" [--output-dir ./research]
    python youtube_search.py comments --video-id VIDEO_ID [--output-dir ./research]
    python youtube_search.py analyze --video-id VIDEO_ID [--output-dir ./research]

Results are written to disk as markdown files for easy searching with grep/glob.

Requires YOUTUBE_API_KEY environment variable.
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

API_KEY = os.environ.get("YOUTUBE_API_KEY")
BASE_URL = "https://www.googleapis.com/youtube/v3"

# Signal detection patterns
SIGNAL_PATTERNS = {
    "pain_point": [
        r"\b(frustrat|annoy|hate|wish|problem|issue|bug|broken|doesn't work|can't|won't|failed)\b",
        r"\b(terrible|awful|worst|disappointed|useless|waste)\b",
        r"\b(why (can't|won't|doesn't)|should (be|have))\b",
    ],
    "feature_request": [
        r"\b(please add|would be nice|should add|need|want|hoping for|waiting for)\b",
        r"\b(feature request|suggestion|idea|proposal)\b",
        r"\b(can you (add|make|include)|will (there|you) (be|add))\b",
    ],
    "competitor_mention": [
        r"\b(better than|worse than|compared to|switched (to|from)|alternative)\b",
        r"\b(vs\.?|versus|or should i)\b",
        r"\b(I use|I prefer|moved to|came from)\b",
    ],
    "purchase_intent": [
        r"\b(where (can|do) (i|you) (buy|get|purchase))\b",
        r"\b(price|cost|worth|affordable|expensive)\b",
        r"\b(thinking (of|about) (buying|getting)|should i (buy|get))\b",
    ],
}


def api_request(endpoint: str, params: dict) -> dict:
    """Make a request to the YouTube API."""
    if not API_KEY:
        print("Error: YOUTUBE_API_KEY environment variable not set", file=sys.stderr)
        sys.exit(1)

    params["key"] = API_KEY
    url = f"{BASE_URL}/{endpoint}?{urlencode(params)}"

    try:
        req = Request(url, headers={"Accept": "application/json"})
        with urlopen(req) as response:
            return json.loads(response.read().decode())
    except HTTPError as e:
        error_body = e.read().decode()
        print(f"API Error {e.code}: {error_body}", file=sys.stderr)
        sys.exit(1)


def ensure_output_dir(output_dir: str) -> Path:
    """Create output directory if it doesn't exist."""
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def search_videos(query: str, max_results: int = 10, order: str = "relevance") -> list:
    """Search for videos matching the query."""
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": min(max_results, 50),
        "order": order,
    }

    data = api_request("search", params)

    results = []
    for item in data.get("items", []):
        results.append({
            "video_id": item["id"]["videoId"],
            "title": item["snippet"]["title"],
            "channel": item["snippet"]["channelTitle"],
            "description": item["snippet"]["description"][:200],
            "published": item["snippet"]["publishedAt"],
            "url": f"https://youtube.com/watch?v={item['id']['videoId']}",
        })

    return results


def get_comments(video_id: str, max_results: int = 100) -> list:
    """Fetch comments for a video."""
    params = {
        "part": "snippet,replies",
        "videoId": video_id,
        "maxResults": min(max_results, 100),
        "order": "relevance",
        "textFormat": "plainText",
    }

    data = api_request("commentThreads", params)

    comments = []
    for item in data.get("items", []):
        top = item["snippet"]["topLevelComment"]["snippet"]
        comments.append({
            "text": top["textDisplay"],
            "author": top["authorDisplayName"],
            "likes": top.get("likeCount", 0),
            "published": top["publishedAt"],
            "reply_count": item["snippet"].get("totalReplyCount", 0),
        })

        # Include replies if present
        for reply in item.get("replies", {}).get("comments", []):
            r = reply["snippet"]
            comments.append({
                "text": r["textDisplay"],
                "author": r["authorDisplayName"],
                "likes": r.get("likeCount", 0),
                "published": r["publishedAt"],
                "is_reply": True,
            })

    return comments


def detect_signals(text: str, signal_types: list = None) -> dict:
    """Detect market signals in comment text."""
    if signal_types is None:
        signal_types = list(SIGNAL_PATTERNS.keys())

    detected = {}
    text_lower = text.lower()

    for signal_type in signal_types:
        if signal_type not in SIGNAL_PATTERNS:
            continue
        patterns = SIGNAL_PATTERNS[signal_type]
        for pattern in patterns:
            if re.search(pattern, text_lower):
                detected[signal_type] = True
                break

    return detected


def analyze_comments(video_id: str, signal_types: list = None, max_results: int = 100) -> dict:
    """Fetch and analyze comments for signals."""
    comments = get_comments(video_id, max_results)

    analysis = {
        "video_id": video_id,
        "total_comments": len(comments),
        "signals": {st: [] for st in (signal_types or list(SIGNAL_PATTERNS.keys()))},
    }

    for comment in comments:
        signals = detect_signals(comment["text"], signal_types)
        for signal_type in signals:
            analysis["signals"][signal_type].append({
                "text": comment["text"][:500],
                "author": comment["author"],
                "likes": comment["likes"],
            })

    # Add counts
    analysis["signal_counts"] = {k: len(v) for k, v in analysis["signals"].items()}

    return analysis


def write_search_results(results: list, query: str, output_dir: Path) -> str:
    """Write search results to markdown file."""
    safe_query = re.sub(r'[^\w\s-]', '', query)[:50].strip().replace(' ', '_')
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"search_{safe_query}_{timestamp}.md"
    filepath = output_dir / filename

    lines = [
        f"# YouTube Search: {query}",
        f"",
        f"**Date:** {datetime.now().isoformat()}",
        f"**Results:** {len(results)} videos",
        f"",
        f"---",
        f"",
    ]

    for i, video in enumerate(results, 1):
        lines.extend([
            f"## {i}. {video['title']}",
            f"",
            f"- **Video ID:** `{video['video_id']}`",
            f"- **Channel:** {video['channel']}",
            f"- **Published:** {video['published']}",
            f"- **URL:** {video['url']}",
            f"",
            f"> {video['description']}",
            f"",
            f"---",
            f"",
        ])

    filepath.write_text("\n".join(lines))
    return str(filepath)


def write_comments(comments: list, video_id: str, output_dir: Path) -> str:
    """Write comments to markdown file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"comments_{video_id}_{timestamp}.md"
    filepath = output_dir / filename

    lines = [
        f"# Comments for Video: {video_id}",
        f"",
        f"**Date:** {datetime.now().isoformat()}",
        f"**Total Comments:** {len(comments)}",
        f"**URL:** https://youtube.com/watch?v={video_id}",
        f"",
        f"---",
        f"",
    ]

    for i, comment in enumerate(comments, 1):
        is_reply = comment.get("is_reply", False)
        prefix = "  > **Reply** | " if is_reply else ""
        lines.extend([
            f"### Comment {i}",
            f"",
            f"{prefix}**Author:** {comment['author']} | **Likes:** {comment['likes']}",
            f"",
            f"{comment['text']}",
            f"",
            f"---",
            f"",
        ])

    filepath.write_text("\n".join(lines))
    return str(filepath)


def write_analysis(analysis: dict, output_dir: Path) -> str:
    """Write signal analysis to markdown file."""
    video_id = analysis["video_id"]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"analysis_{video_id}_{timestamp}.md"
    filepath = output_dir / filename

    lines = [
        f"# Signal Analysis: {video_id}",
        f"",
        f"**Date:** {datetime.now().isoformat()}",
        f"**Total Comments Analyzed:** {analysis['total_comments']}",
        f"**URL:** https://youtube.com/watch?v={video_id}",
        f"",
        f"## Summary",
        f"",
        f"| Signal Type | Count |",
        f"|-------------|-------|",
    ]

    for signal_type, count in analysis["signal_counts"].items():
        lines.append(f"| {signal_type} | {count} |")

    lines.extend(["", "---", ""])

    # Write each signal type section
    for signal_type, comments in analysis["signals"].items():
        lines.extend([
            f"## {signal_type.replace('_', ' ').title()}",
            f"",
            f"**Found:** {len(comments)} comments",
            f"",
        ])

        if not comments:
            lines.extend(["_No comments matched this signal._", "", "---", ""])
            continue

        for i, comment in enumerate(comments, 1):
            lines.extend([
                f"### {i}. {comment['author']} ({comment['likes']} likes)",
                f"",
                f"{comment['text']}",
                f"",
            ])

        lines.extend(["---", ""])

    filepath.write_text("\n".join(lines))
    return str(filepath)


def add_output_arg(parser):
    """Add common output-dir argument to a parser."""
    parser.add_argument("--output-dir", "-o", default="./youtube_research",
                        help="Output directory for results (default: ./youtube_research)")


def main():
    parser = argparse.ArgumentParser(description="YouTube Research Tool")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Search command
    search_p = subparsers.add_parser("search", help="Search for videos")
    search_p.add_argument("--query", "-q", required=True, help="Search query")
    search_p.add_argument("--max-results", "-n", type=int, default=10)
    search_p.add_argument("--order", choices=["relevance", "date", "viewCount"], default="relevance")
    add_output_arg(search_p)

    # Comments command
    comments_p = subparsers.add_parser("comments", help="Get video comments")
    comments_p.add_argument("--video-id", "-v", required=True, help="YouTube video ID")
    comments_p.add_argument("--max-results", "-n", type=int, default=50)
    add_output_arg(comments_p)

    # Analyze command
    analyze_p = subparsers.add_parser("analyze", help="Analyze comments for signals")
    analyze_p.add_argument("--video-id", "-v", required=True, help="YouTube video ID")
    analyze_p.add_argument("--signals", "-s", help="Comma-separated: pain_point,feature_request,competitor_mention,purchase_intent")
    analyze_p.add_argument("--max-results", "-n", type=int, default=100)
    add_output_arg(analyze_p)

    args = parser.parse_args()
    output_dir = ensure_output_dir(args.output_dir)

    if args.command == "search":
        results = search_videos(args.query, args.max_results, args.order)
        filepath = write_search_results(results, args.query, output_dir)
        print(f"Wrote {len(results)} results to: {filepath}")

    elif args.command == "comments":
        comments = get_comments(args.video_id, args.max_results)
        filepath = write_comments(comments, args.video_id, output_dir)
        print(f"Wrote {len(comments)} comments to: {filepath}")

    elif args.command == "analyze":
        signal_types = args.signals.split(",") if args.signals else None
        analysis = analyze_comments(args.video_id, signal_types, args.max_results)
        filepath = write_analysis(analysis, output_dir)
        total_signals = sum(analysis["signal_counts"].values())
        print(f"Wrote analysis ({total_signals} signals found) to: {filepath}")


if __name__ == "__main__":
    main()
