# Reddit Reader Skill

A [Claude Code Agent Skill](https://support.claude.com/en/articles/12512176-what-are-skills) for searching and reading Reddit content via the Reddit OAuth2 API.

## Features

- **Search** - Search posts across all of Reddit or within a specific subreddit, with sort and time range filters
- **List** - Browse subreddit posts by category (hot, new, top, rising, controversial)
- **Read** - Read full post content with nested comment trees
- **Subreddit Info** - View subreddit metadata (subscribers, description, etc.)

## Setup

### 1. Get Reddit API Credentials

1. Go to [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps)
2. Click "create another app..."
3. Choose **script** type
4. Fill in name and redirect URI (use `http://localhost:8080`)
5. Note down your `client_id` (under the app name) and `client_secret`

### 2. Set Environment Variables

```bash
export REDDIT_CLIENT_ID="your_client_id"
export REDDIT_CLIENT_SECRET="your_client_secret"
```

Add these to your `~/.bashrc` or `~/.zshrc` for persistence.

### 3. Install Dependency

```bash
pip install requests
```

### 4. Install Skill

Copy or symlink this folder to your Claude Code skills directory:

```bash
# Option A: Symlink (recommended, stays in sync with repo)
ln -s /path/to/reddit-skill ~/.claude/skills/reddit-reader

# Option B: Copy
cp -r /path/to/reddit-skill ~/.claude/skills/reddit-reader
```

## Usage

Once installed, just ask Claude naturally:

- "搜索 Reddit 上关于 Claude Code 的讨论"
- "看看 r/ClaudeAI 最近有什么热帖"
- "读一下这个 Reddit 帖子 https://reddit.com/r/..."
- "Reddit 上大家怎么看 Cursor vs Claude Code"

### Direct Script Usage

You can also run the script directly:

```bash
# Search
python3 scripts/reddit_reader.py search "Claude Code tips" --sort hot --time week --limit 15

# List subreddit posts
python3 scripts/reddit_reader.py list r/ClaudeAI --category top --time month --limit 20

# Read a post with comments
python3 scripts/reddit_reader.py read "https://www.reddit.com/r/ClaudeAI/comments/abc123/..."

# Subreddit info
python3 scripts/reddit_reader.py subreddit ClaudeAI
```

### Command Reference

| Command | Description | Key Options |
|---------|-------------|-------------|
| `search <query>` | Search posts | `--subreddit`, `--sort`, `--time`, `--limit` |
| `list <subreddit>` | Browse posts | `--category`, `--time`, `--limit` |
| `read <post_id_or_url>` | Read post + comments | `--comment-sort`, `--comment-limit`, `--comment-depth` |
| `subreddit <name>` | Subreddit info | - |

#### Sort Options

- **Search sort**: `relevance`, `hot`, `new`, `top`, `comments`
- **List categories**: `hot`, `new`, `top`, `rising`, `controversial`
- **Comment sort**: `best`, `top`, `new`, `controversial`, `old`
- **Time range**: `hour`, `day`, `week`, `month`, `year`, `all`

## File Structure

```
reddit-skill/
├── SKILL.md                  # Skill entry point (loaded by Claude)
├── README.md                 # This file
├── scripts/
│   └── reddit_reader.py      # Core Python script
└── references/
    └── reddit_api.md         # Reddit API quick reference
```

## Limitations

- Read-only access (no posting or commenting)
- 100 requests/minute rate limit (OAuth authenticated)
- Search results capped at ~1000 items
- Cannot access private subreddits or deleted content

## License

MIT
