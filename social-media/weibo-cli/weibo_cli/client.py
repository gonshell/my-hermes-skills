from __future__ import annotations

import random
import time
from typing import Any

import httpx

from weibo_cli import cache, constants, exceptions, models
from weibo_cli.auth import get_credentials


class WeiboClient:
    """
    HTTP client for Weibo Mobile API (m.weibo.cn).

    Handles all API requests with automatic credential injection,
    rate limiting, and error handling.
    """

    def __init__(
        self,
        credentials: models.Credentials | None = None,
        use_cache: bool = True,
    ) -> None:
        self._credentials = credentials
        self._cache = cache.Cache(ttl=120) if use_cache else None

    @property
    def credentials(self) -> models.Credentials:
        if self._credentials is None:
            self._credentials = get_credentials()
        return self._credentials

    def _headers(self) -> dict[str, str]:
        """Build request headers with auth cookie (optional for public endpoints)."""
        headers = dict(constants.DEFAULT_HEADERS)
        # Only inject cookie if credentials exist and have a cookie
        try:
            creds = self.credentials
            if creds and creds.cookie:
                headers["Cookie"] = creds.cookie
        except exceptions.AuthenticationError:
            pass  # No credentials available — use public endpoints without auth
        return headers

    def _rate_limit(self) -> None:
        """Apply random delay between requests to avoid rate limiting."""
        delay = random.uniform(constants.MIN_REQUEST_DELAY, constants.MAX_REQUEST_DELAY)
        time.sleep(delay)

    def _parse_response(self, resp: httpx.Response) -> dict[str, Any]:
        """Parse and validate API response."""
        try:
            data = resp.json()
        except Exception as e:
            raise exceptions.ParseError(f"Failed to parse JSON: {e}")

        # Check API-level error
        if isinstance(data, dict):
            ok = data.get("ok")
            msg = data.get("msg", "") or data.get("errmsg", "")
            code = data.get("code", 0)

            # ok=-100 means auth required, ok=0 means API error
            if ok == -100 or code == "100005" or "not logged in" in msg.lower():
                raise exceptions.AuthenticationError(
                    "Not authenticated. Run 'weibo login' or 'weibo qr-login' first."
                )
            if code == "100006" or ok == -1:
                raise exceptions.RateLimitError()
            if ok == 0 and msg:
                raise exceptions.APIError(f"API error: {msg}", code=code)

        return data

    def get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        use_cache: bool = False,
    ) -> dict[str, Any]:
        """
        Perform GET request with optional caching.

        Args:
            url: API endpoint URL
            params: query parameters
            use_cache: whether to use cache

        Returns:
            parsed JSON response

        Raises:
            NetworkError: on connection errors
            CookieExpiredError: when cookie expires
            APIError: on API errors
        """
        cache_key = f"GET:{url}:{sorted(params.items()) if params else ()}"
        if use_cache and self._cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        try:
            with httpx.Client(timeout=constants.DEFAULT_TIMEOUT) as client:
                resp = client.get(url, headers=self._headers(), params=params)
                resp.raise_for_status()
                data = self._parse_response(resp)

            if use_cache and self._cache and data:
                self._cache.set(cache_key, data)
            return data

        except httpx.TimeoutException:
            raise exceptions.NetworkError("Request timed out")
        except httpx.NetworkError as e:
            raise exceptions.NetworkError(f"Network error: {e}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise exceptions.CookieExpiredError()
            if e.response.status_code == 429:
                raise exceptions.RateLimitError()
            raise exceptions.NetworkError(f"HTTP {e.response.status_code}: {e}")

    def post(
        self,
        url: str,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Perform POST request.

        Args:
            url: API endpoint URL
            data: form data
            params: query parameters

        Returns:
            parsed JSON response
        """
        try:
            with httpx.Client(timeout=constants.DEFAULT_TIMEOUT) as client:
                resp = client.post(
                    url,
                    headers=self._headers(),
                    data=data or {},
                    params=params,
                )
                resp.raise_for_status()
                return self._parse_response(resp)

        except httpx.TimeoutException:
            raise exceptions.NetworkError("Request timed out")
        except httpx.NetworkError as e:
            raise exceptions.NetworkError(f"Network error: {e}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise exceptions.CookieExpiredError()
            if e.response.status_code == 429:
                raise exceptions.RateLimitError()
            raise exceptions.NetworkError(f"HTTP {e.response.status_code}: {e}")

    # ─── Hot & Timeline ────────────────────────────────────────────────────

    def hot_search(self, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        """Get hot search list."""
        self._rate_limit()
        params = {
            "containerid": "100103type=1",
            "page_type": "searchall",
            "page": page,
            "page_size": page_size,
        }
        return self.get(constants.HOT_SEARCH_URL, params=params)

    def trending(self) -> dict[str, Any]:
        """Get trending topics sidebar."""
        self._rate_limit()
        params = {
            "containerid": "100103type=1",
            "page_type": "trendency",
        }
        return self.get(constants.TRENDING_URL, params=params)

    def feed_topboard(self, page: int = 1) -> dict[str, Any]:
        """Get hot feed timeline (topboard)."""
        self._rate_limit()
        params = {
            "page": page,
        }
        return self.get(constants.FEED_URL, params=params)

    def home_timeline(self, page: int = 1, max_id: int = 0) -> dict[str, Any]:
        """Get home/following timeline."""
        self._rate_limit()
        params = {
            "page": page,
            "max_id": max_id,
        }
        return self.get(constants.HOME_URL, params=params)

    # ─── Status ────────────────────────────────────────────────────────────

    def status(self, mblog_id: str) -> dict[str, Any]:
        """Get single weibo status detail."""
        self._rate_limit()
        params = {"id": mblog_id}
        return self.get(constants.STATUS_URL, params=params)

    def reposts(self, mblog_id: str, page: int = 1) -> dict[str, Any]:
        """Get reposts of a status."""
        self._rate_limit()
        params = {
            "id": mblog_id,
            "page": page,
        }
        return self.get(constants.STATUS_REPOST_URL, params=params)

    def comments(self, mblog_id: str, page: int = 1) -> dict[str, Any]:
        """Get comments of a status."""
        self._rate_limit()
        params = {
            "id": mblog_id,
            "page": page,
        }
        return self.get(constants.COMMENTS_URL, params=params)

    def search(
        self,
        keyword: str,
        page: int = 1,
        page_type: int = 0,
    ) -> dict[str, Any]:
        """
        Search weibos by keyword.

        Args:
            keyword: search keyword
            page: page number
            page_type: 0=综合, 1=关注, 2=热门, 3=实时, 4=用户
        """
        self._rate_limit()
        params = {
            "containerid": f"100103type=1&q={keyword}",
            "page_type": "searchall",
            "page": page,
        }
        return self.get(constants.SEARCH_URL, params=params)

    # ─── User ─────────────────────────────────────────────────────────────

    def user_info(self, uid: str) -> dict[str, Any]:
        """Get user profile info."""
        self._rate_limit()
        params = {"uid": uid}
        return self.get(constants.USER_PROFILE_URL, params=params)

    def user_posts(self, uid: str, page: int = 1) -> dict[str, Any]:
        """Get user's weibo posts."""
        self._rate_limit()
        params = {
            "containerid": f"107603{uid}",
            "page": page,
            "page_size": constants.DEFAULT_PAGE_SIZE,
        }
        return self.get(constants.USER_POSTS_URL, params=params)

    def followers(self, uid: str, page: int = 1) -> dict[str, Any]:
        """Get user's followers."""
        self._rate_limit()
        params = {
            "containerid": f"231051_-_followers_-_{uid}",
            "page": page,
        }
        return self.get(constants.FOLLOWERS_URL, params=params)

    def following(self, uid: str, page: int = 1) -> dict[str, Any]:
        """Get user's following list."""
        self._rate_limit()
        params = {
            "containerid": f"231051_-_following_-_{uid}",
            "page": page,
        }
        return self.get(constants.FOLLOWING_URL, params=params)
