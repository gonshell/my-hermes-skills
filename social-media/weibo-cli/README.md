# weibo-cli

A CLI for Weibo (微博) — search, browse hot topics, read timelines, and explore user profiles from the terminal.

## Installation

```bash
pip install weibo-cli
```

Or from source:

```bash
git clone https://github.com/yourname/weibo-cli.git
cd weibo-cli
pip install -e .
```

## Quick Start

```bash
# Login (extracts cookies from your browser automatically)
weibo auth login

# Hot search
weibo hot

# Search
weibo search Python

# User profile
weibo user 1195230310
```

## Commands

- `weibo hot` — Hot search list
- `weibo trending` — Trending topics
- `weibo search <keyword>` — Search weibos
- `weibo timeline [uid]` — User timeline
- `weibo user <uid>` — User profile
- `weibo status <id>` — Status detail
- `weibo comments <id>` — Status comments
- `weibo followers <uid>` — User followers
- `weibo following <uid>` — User following
- `weibo auth status` — Check login status
- `weibo auth login` — Login via browser cookie extraction
- `weibo auth logout` — Logout

## Authentication

Browser cookie extraction (recommended):

```bash
weibo auth login
```

This will automatically extract cookies from your default browser
(Chrome, Edge, Firefox, Safari, etc.) where you're already logged in
to weibo.com or m.weibo.cn.

## License

MIT
