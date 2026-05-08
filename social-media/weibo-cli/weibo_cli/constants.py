from __future__ import annotations

# ─── API Endpoints ────────────────────────────────────────────────────────────

BASE_URL = "https://m.weibo.cn"
API_BASE = f"{BASE_URL}/api"

# Hot & Timeline
HOT_SEARCH_URL = f"{API_BASE}/container/getIndex"
TRENDING_URL = f"{API_BASE}/container/getIndex"
FEED_URL = f"{API_BASE}/feed/topboard"
HOME_URL = f"{API_BASE}/feed/friend"

# User
USER_PROFILE_URL = f"{API_BASE}/user/info"
USER_POSTS_URL = f"{API_BASE}/container/getIndex"

# Status
STATUS_URL = f"{API_BASE}/statuses/one"
STATUS_REPOST_URL = f"{API_BASE}/statuses/repostTimeline"
COMMENTS_URL = f"{API_BASE}/comments/show"
SEARCH_URL = f"{API_BASE}/search"
FOLLOWERS_URL = f"{API_BASE}/container/getIndex"
FOLLOWING_URL = f"{API_BASE}/container/getIndex"

# Auth
LOGIN_QR_URL = f"{BASE_URL}/oauth2/qrcode"
LOGIN_TOKEN_URL = f"{BASE_URL}/oauth2/access_token"
LOGIN_SSO_URL = f"{BASE_URL}/oauth2/authorize"

# ─── Default Headers ──────────────────────────────────────────────────────────

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
        "Mobile/15E148 Safari/604.1"
    ),
    "Referer": BASE_URL,
    "Accept": "application/json, text/plain",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "X-Requested-With": "XMLHttpRequest",
}

# ─── Config ──────────────────────────────────────────────────────────────────

CONFIG_DIR = "~/.config/weibo-cli"
CREDENTIALS_FILE = f"{CONFIG_DIR}/credentials.json"
CONFIG_FILE = f"{CONFIG_DIR}/config.json"
CACHE_DIR = f"{CONFIG_DIR}/cache"

# ─── Timeouts ────────────────────────────────────────────────────────────────

DEFAULT_TIMEOUT = 15.0
LOGIN_TIMEOUT = 120.0

# ─── Rate Limiting ───────────────────────────────────────────────────────────

MIN_REQUEST_DELAY = 0.8
MAX_REQUEST_DELAY = 3.0

# ─── Pagination ───────────────────────────────────────────────────────────────

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 50
