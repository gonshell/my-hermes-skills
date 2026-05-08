from __future__ import annotations


class WeiboError(RuntimeError):
    """Base exception for weibo-cli."""

    def __init__(self, message: str, code: int | None = None) -> None:
        super().__init__(message)
        self.code = code


class AuthenticationError(WeiboError):
    """Raised when authentication fails or credentials are missing."""

    def __init__(self, message: str = "Not authenticated") -> None:
        super().__init__(message, code=401)


class CookieExpiredError(AuthenticationError):
    """Raised when cookies have expired."""

    def __init__(self, message: str = "Cookie expired, please re-login") -> None:
        super().__init__(message)


class RateLimitError(WeiboError):
    """Raised when rate limited."""

    def __init__(self, message: str = "Rate limited, please wait") -> None:
        super().__init__(message, code=429)


class APIError(WeiboError):
    """Raised when Weibo API returns an error."""

    def __init__(self, message: str, code: int | None = None) -> None:
        super().__init__(message, code=code)


class NetworkError(WeiboError):
    """Raised on network/connection failures."""

    def __init__(self, message: str = "Network error") -> None:
        super().__init__(message, code=None)


class ParseError(WeiboError):
    """Raised when response parsing fails."""

    def __init__(self, message: str = "Failed to parse response") -> None:
        super().__init__(message, code=None)


class QRCodeExpiredError(WeiboError):
    """Raised when QR code has expired."""

    def __init__(self, message: str = "QR code expired, please retry") -> None:
        super().__init__(message, code=None)


class InvalidParamsError(WeiboError):
    """Raised when parameters are invalid."""

    def __init__(self, message: str = "Invalid parameters") -> None:
        super().__init__(message, code=400)
