#!/usr/bin/env python3
"""Reddit Reader - Access Reddit via OAuth2 API.

Usage:
    python3 reddit_reader.py search "query" [options]
    python3 reddit_reader.py list <subreddit> [options]
    python3 reddit_reader.py read <post_id_or_url> [options]
    python3 reddit_reader.py subreddit <name>

Requires environment variables:
    REDDIT_CLIENT_ID
    REDDIT_CLIENT_SECRET
"""

import argparse
import os
import re
import sys
import time
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    print("Error: requests library required. Install with: pip install requests", file=sys.stderr)
    sys.exit(1)

# --- Constants ---
API_BASE = "https://oauth.reddit.com"
TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
USER_AGENT = "linux:reddit-reader-skill:v1.0 (by /u/reddit_reader_skill)"
DEFAULT_LIMIT = 10
MAX_LIMIT = 100


# --- Authentication ---
class RedditAuth:
    """Handle Reddit OAuth2 client_credentials authentication."""

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token: str | None = None
        self.token_expiry: float = 0

    def get_token(self) -> str:
        if self.token and time.time() < self.token_expiry - 60:
            return self.token

        resp = requests.post(
            TOKEN_URL,
            auth=(self.client_id, self.client_secret),
            data={"grant_type": "client_credentials"},
            headers={"User-Agent": USER_AGENT},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        if "access_token" not in data:
            print(f"Error: Failed to obtain token: {data}", file=sys.stderr)
            sys.exit(1)

        self.token = data["access_token"]
        self.token_expiry = time.time() + data.get("expires_in", 3600)
        return self.token

    def headers(self) -> dict:
        return {
            "Authorization": f"bearer {self.get_token()}",
            "User-Agent": USER_AGENT,
        }


# --- API Client ---
class RedditClient:
    """Reddit API client with rate limiting."""

    def __init__(self, auth: RedditAuth):
        self.auth = auth
        self.remaining: float | None = None

    def get(self, path: str, params: dict | None = None) -> dict:
        if self.remaining is not None and self.remaining < 5:
            time.sleep(2)

        url = f"{API_BASE}{path}"
        resp = requests.get(url, headers=self.auth.headers(), params=params, timeout=30)

        # Track rate limits
        if "X-Ratelimit-Remaining" in resp.headers:
            self.remaining = float(resp.headers["X-Ratelimit-Remaining"])

        if resp.status_code == 429:
            reset = float(resp.headers.get("X-Ratelimit-Reset", 60))
            print(f"Rate limited. Waiting {reset:.0f}s...", file=sys.stderr)
            time.sleep(reset)
            return self.get(path, params)

        resp.raise_for_status()
        return resp.json()


# --- Formatting Helpers ---
def ts_to_str(utc_ts: float) -> str:
    """Convert UTC timestamp to readable string."""
    dt = datetime.fromtimestamp(utc_ts, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M UTC")


def format_score(score: int) -> str:
    if abs(score) >= 1000:
        return f"{score / 1000:.1f}k"
    return str(score)


def truncate(text: str, max_len: int = 200) -> str:
    if not text or len(text) <= max_len:
        return text or ""
    return text[:max_len] + "..."


def extract_post_id(input_str: str) -> str:
    """Extract post ID from URL or direct ID input."""
    # Full URL: https://www.reddit.com/r/xxx/comments/abc123/...
    m = re.search(r"/comments/([a-z0-9]+)", input_str)
    if m:
        return m.group(1)
    # Short URL: https://redd.it/abc123
    m = re.search(r"redd\.it/([a-z0-9]+)", input_str)
    if m:
        return m.group(1)
    # Direct ID (possibly with t3_ prefix)
    return input_str.removeprefix("t3_")


def clean_subreddit(name: str) -> str:
    """Remove r/ prefix if present."""
    return name.removeprefix("r/").removeprefix("/r/")


# --- Output Formatters ---
def format_post_list(posts: list[dict], title: str) -> str:
    """Format a list of posts as Markdown."""
    lines = [f"# {title}\n"]

    if not posts:
        lines.append("No posts found.\n")
        return "\n".join(lines)

    for i, post in enumerate(posts, 1):
        d = post["data"]
        flair = f" [{d['link_flair_text']}]" if d.get("link_flair_text") else ""
        nsfw = " [NSFW]" if d.get("over_18") else ""

        lines.append(f"## {i}. {d['title']}{flair}{nsfw}")
        lines.append("")
        lines.append(
            f"- **Subreddit**: r/{d['subreddit']} | **Author**: u/{d['author']} | "
            f"**Score**: {format_score(d.get('score', 0))} | "
            f"**Comments**: {d.get('num_comments', 0)} | "
            f"**Time**: {ts_to_str(d['created_utc'])}"
        )

        selftext = d.get("selftext", "")
        if selftext:
            lines.append(f"- **Preview**: {truncate(selftext, 150)}")

        if not d.get("is_self") and d.get("url"):
            lines.append(f"- **Link**: {d['url']}")

        lines.append(f"- **Post ID**: `{d['id']}` | **URL**: https://reddit.com{d['permalink']}")
        lines.append("")

    return "\n".join(lines)


def format_post_detail(post_data: dict) -> str:
    """Format a single post's full detail."""
    d = post_data
    lines = [f"# {d['title']}\n"]

    lines.append(f"- **Subreddit**: r/{d['subreddit']}")
    lines.append(f"- **Author**: u/{d['author']}")
    lines.append(
        f"- **Score**: {format_score(d.get('score', 0))} "
        f"(upvote ratio: {d.get('upvote_ratio', 0):.0%})"
    )
    lines.append(f"- **Comments**: {d.get('num_comments', 0)}")
    lines.append(f"- **Time**: {ts_to_str(d['created_utc'])}")
    if d.get("link_flair_text"):
        lines.append(f"- **Flair**: {d['link_flair_text']}")
    if d.get("over_18"):
        lines.append("- **NSFW**: Yes")
    lines.append(f"- **URL**: https://reddit.com{d['permalink']}")
    lines.append("")

    # Post body
    selftext = d.get("selftext", "")
    if selftext:
        lines.append("---\n")
        lines.append(selftext)
        lines.append("")
    elif not d.get("is_self") and d.get("url"):
        lines.append(f"**Link**: {d['url']}\n")

    return "\n".join(lines)


def format_comment_tree(comments: list[dict], depth: int = 0) -> str:
    """Recursively format comment tree with indentation."""
    lines = []

    for comment in comments:
        if comment.get("kind") == "more":
            count = comment.get("data", {}).get("count", 0)
            if count > 0:
                indent = "  " * depth
                lines.append(f"{indent}*[{count} more comments]*\n")
            continue

        d = comment.get("data", {})
        if not d.get("body"):
            continue

        indent = "  " * depth
        author = d.get("author", "[deleted]")
        score = format_score(d.get("score", 0))

        lines.append(f"{indent}**u/{author}** ({score} points) - {ts_to_str(d['created_utc'])}")
        lines.append("")

        # Indent the comment body
        for line in d["body"].split("\n"):
            lines.append(f"{indent}{line}")
        lines.append("")

        # Recurse into replies
        replies = d.get("replies")
        if isinstance(replies, dict):
            children = replies.get("data", {}).get("children", [])
            if children:
                lines.append(format_comment_tree(children, depth + 1))

    return "\n".join(lines)


def format_subreddit_info(data: dict) -> str:
    """Format subreddit information."""
    d = data
    lines = [f"# r/{d['display_name']}\n"]
    lines.append(f"- **Title**: {d.get('title', 'N/A')}")
    lines.append(f"- **Subscribers**: {d.get('subscribers', 0):,}")
    lines.append(f"- **Active Users**: {d.get('accounts_active', 0):,}")
    lines.append(f"- **Created**: {ts_to_str(d['created_utc'])}")
    lines.append(f"- **Type**: {d.get('subreddit_type', 'N/A')}")
    if d.get("over18"):
        lines.append("- **NSFW**: Yes")
    lines.append("")

    desc = d.get("public_description") or d.get("description", "")
    if desc:
        lines.append("## Description\n")
        lines.append(desc)
        lines.append("")

    return "\n".join(lines)


# --- Commands ---
def cmd_search(client: RedditClient, args: argparse.Namespace) -> None:
    """Search Reddit posts."""
    params = {
        "q": args.query,
        "sort": args.sort,
        "t": args.time,
        "limit": min(args.limit, MAX_LIMIT),
        "type": "link",
    }

    if args.subreddit:
        sub = clean_subreddit(args.subreddit)
        path = f"/r/{sub}/search"
        params["restrict_sr"] = "true"
        title = f'Search results for "{args.query}" in r/{sub}'
    else:
        path = "/search"
        title = f'Search results for "{args.query}" (all Reddit)'

    title += f" | sort: {args.sort} | time: {args.time} | limit: {args.limit}"

    data = client.get(path, params)
    posts = data.get("data", {}).get("children", [])
    print(format_post_list(posts, title))


def cmd_list(client: RedditClient, args: argparse.Namespace) -> None:
    """List posts from a subreddit."""
    sub = clean_subreddit(args.subreddit)
    category = args.category

    params = {"limit": min(args.limit, MAX_LIMIT)}
    if category in ("top", "controversial") and args.time:
        params["t"] = args.time

    path = f"/r/{sub}/{category}"
    title = f"r/{sub} - {category}"
    if category in ("top", "controversial"):
        title += f" ({args.time})"
    title += f" | limit: {args.limit}"

    data = client.get(path, params)
    posts = data.get("data", {}).get("children", [])
    print(format_post_list(posts, title))


def cmd_read(client: RedditClient, args: argparse.Namespace) -> None:
    """Read a post with its comments."""
    post_id = extract_post_id(args.post)

    params = {
        "sort": args.comment_sort,
        "limit": args.comment_limit,
        "depth": args.comment_depth,
    }

    # Use /comments/{id} endpoint - no subreddit needed
    data = client.get(f"/comments/{post_id}", params)

    if not isinstance(data, list) or len(data) < 2:
        print("Error: Unexpected response format.", file=sys.stderr)
        sys.exit(1)

    # First listing: post detail
    post_children = data[0].get("data", {}).get("children", [])
    if post_children:
        post = post_children[0].get("data", {})
        print(format_post_detail(post))

    # Second listing: comments
    comment_children = data[1].get("data", {}).get("children", [])
    if comment_children:
        print(f"---\n\n## Comments (sort: {args.comment_sort})\n")
        print(format_comment_tree(comment_children))
    else:
        print("\n*No comments yet.*\n")


def cmd_subreddit(client: RedditClient, args: argparse.Namespace) -> None:
    """Get subreddit information."""
    sub = clean_subreddit(args.name)
    data = client.get(f"/r/{sub}/about")
    info = data.get("data", {})
    print(format_subreddit_info(info))


# --- Main ---
def main():
    client_id = os.environ.get("REDDIT_CLIENT_ID", "")
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET", "")

    if not client_id or not client_secret:
        print(
            "Error: REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET environment variables must be set.\n"
            "Get credentials at: https://www.reddit.com/prefs/apps\n"
            "Create a 'script' type application.",
            file=sys.stderr,
        )
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Reddit Reader - Access Reddit via OAuth2 API")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # search
    p_search = subparsers.add_parser("search", help="Search Reddit posts")
    p_search.add_argument("query", help="Search query string")
    p_search.add_argument("--subreddit", "-s", help="Restrict search to a subreddit")
    p_search.add_argument(
        "--sort", default="relevance",
        choices=["relevance", "hot", "new", "top", "comments"],
        help="Sort order (default: relevance)",
    )
    p_search.add_argument(
        "--time", "-t", default="all",
        choices=["hour", "day", "week", "month", "year", "all"],
        help="Time range (default: all)",
    )
    p_search.add_argument(
        "--limit", "-l", type=int, default=DEFAULT_LIMIT,
        help=f"Number of results (default: {DEFAULT_LIMIT}, max: {MAX_LIMIT})",
    )

    # list
    p_list = subparsers.add_parser("list", help="List posts from a subreddit")
    p_list.add_argument("subreddit", help="Subreddit name (e.g., ClaudeAI or r/ClaudeAI)")
    p_list.add_argument(
        "--category", "-c", default="hot",
        choices=["hot", "new", "top", "rising", "controversial"],
        help="Post category (default: hot)",
    )
    p_list.add_argument(
        "--time", "-t", default="week",
        choices=["hour", "day", "week", "month", "year", "all"],
        help="Time range for top/controversial (default: week)",
    )
    p_list.add_argument(
        "--limit", "-l", type=int, default=DEFAULT_LIMIT,
        help=f"Number of results (default: {DEFAULT_LIMIT}, max: {MAX_LIMIT})",
    )

    # read
    p_read = subparsers.add_parser("read", help="Read a post with comments")
    p_read.add_argument("post", help="Post ID or full Reddit URL")
    p_read.add_argument(
        "--comment-sort", default="top",
        choices=["best", "top", "new", "controversial", "old"],
        help="Comment sort order (default: top)",
    )
    p_read.add_argument(
        "--comment-limit", type=int, default=30,
        help="Max comments to fetch (default: 30)",
    )
    p_read.add_argument(
        "--comment-depth", type=int, default=5,
        help="Comment nesting depth (default: 5)",
    )

    # subreddit
    p_sub = subparsers.add_parser("subreddit", help="Get subreddit information")
    p_sub.add_argument("name", help="Subreddit name (e.g., ClaudeAI)")

    args = parser.parse_args()
    auth = RedditAuth(client_id, client_secret)
    client = RedditClient(auth)

    commands = {
        "search": cmd_search,
        "list": cmd_list,
        "read": cmd_read,
        "subreddit": cmd_subreddit,
    }
    commands[args.command](client, args)


if __name__ == "__main__":
    main()
