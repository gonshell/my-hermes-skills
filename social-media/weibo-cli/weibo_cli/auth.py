from __future__ import annotations

import json
import random
import time
from pathlib import Path

import browser_cookie3
import qrcode
from PIL import Image

from weibo_cli import constants, exceptions, models
from weibo_cli.config import load_credentials, save_credentials


# ─── Browser Cookie Extraction ─────────────────────────────────────────────────


def extract_browser_cookie(browser_name: str | None = None) -> str:
    """
    Extract Weibo cookies from a browser.

    Supported browsers: chrome, chromium, edge, firefox, brave, opera, vivaldi, safari, librewolf

    Raises:
        AuthenticationError: if extraction fails
    """
    browsers = {
        "chrome": browser_cookie3.chrome,
        "chromium": browser_cookie3.chromium,
        "edge": browser_cookie3.edge,
        "firefox": browser_cookie3.firefox,
        "brave": browser_cookie3.brave,
        "opera": browser_cookie3.opera,
        "vivaldi": browser_cookie3.vivaldi,
        "safari": browser_cookie3.safari,
        "librewolf": browser_cookie3.librewolf,
    }

    if browser_name:
        browser_fn = browsers.get(browser_name.lower())
        if not browser_fn:
            raise exceptions.AuthenticationError(
                f"Unsupported browser: {browser_name}. "
                f"Supported: {', '.join(browsers.keys())}"
            )
        try:
            cj = browser_fn(domain_name="weibo.cn")
        except Exception as e:
            raise exceptions.AuthenticationError(f"Failed to extract cookies from {browser_name}: {e}")
    else:
        # Try each browser in order
        for name, browser_fn in browsers.items():
            try:
                cj = browser_fn(domain_name="weibo.cn")
                if cj:
                    browser_name = name
                    break
            except Exception:
                continue
        else:
            raise exceptions.AuthenticationError(
                "No Weibo cookies found in any supported browser. "
                "Please login at weibo.com in your browser first."
            )

    # Convert cookiejar to cookie string
    cookie_str = _cj_to_cookie_string(cj)
    if not cookie_str:
        raise exceptions.AuthenticationError(f"No Weibo cookies found in {browser_name}")

    return cookie_str


def _cj_to_cookie_string(cj) -> str:
    """Convert a cookiejar to a cookie header string."""
    cookies = []
    for cookie in cj:
        if cookie.domain in (".weibo.cn", "weibo.cn", ".weibo.com", "weibo.com"):
            cookies.append(f"{cookie.name}={cookie.value}")
    return "; ".join(cookies)


# ─── QR Code Login ────────────────────────────────────────────────────────────


def qr_login() -> models.Credentials:
    """
    Interactive QR code login flow.

    Displays QR code in terminal and waits for user to scan with Weibo app.

    Returns:
        Credentials with cookie, token, and uid

    Raises:
        QRCodeExpiredError: if QR code expires before scan
        AuthenticationError: on other errors
    """
    import httpx

    try:
        client = httpx.Client(timeout=constants.LOGIN_TIMEOUT)
    except Exception as e:
        raise exceptions.AuthenticationError(f"Failed to create HTTP client: {e}")

    try:
        # Step 1: Get QR code ticket
        headers = {
            "User-Agent": constants.DEFAULT_HEADERS["User-Agent"],
            "Referer": constants.BASE_URL,
        }
        resp = client.get(constants.LOGIN_QR_URL, headers=headers, follow_redirects=False)
        if resp.status_code in (301, 302):
            raise exceptions.AuthenticationError(
                "二维码登录已不支持。请使用 'weibo auth login' 从浏览器提取 Cookie 登录。"
            )
        resp.raise_for_status()
        data = resp.json()

        qrid = data.get("qrid")
        image_data = data.get("image")

        if not qrid or not image_data:
            raise exceptions.AuthenticationError("Failed to get QR code from Weibo")

        # Step 2: Display QR code
        _display_qr_code(image_data)

        # Step 3: Poll for scan result
        start_time = time.time()
        while time.time() - start_time < constants.LOGIN_TIMEOUT:
            time.sleep(2)
            poll_resp = client.get(
                f"{constants.LOGIN_TOKEN_URL}/{qrid}",
                headers=headers,
            )
            poll_data = poll_resp.json()
            retcode = poll_data.get("retcode", -1)

            if retcode == 100000:
                # Scan success, get credentials
                result = poll_data.get("result", {})
                cookie = result.get("cookie", "")
                token = result.get("token", "")
                uid = str(result.get("uid", ""))

                creds = models.Credentials(cookie=cookie, token=token, uid=uid)
                save_credentials(creds)
                return creds
            elif retcode == 100002:
                # QR code not scanned yet
                continue
            elif retcode in (100003, 100004, 100005):
                # Expired / cancelled / scanned by others
                raise exceptions.QRCodeExpiredError(
                    f"QR code expired (retcode={retcode}), please retry"
                )
            else:
                raise exceptions.AuthenticationError(
                    f"QR login failed (retcode={retcode}): {poll_data}"
                )

        raise exceptions.QRCodeExpiredError("QR code expired, please retry")

    finally:
        client.close()


def _display_qr_code(base64_image: str) -> None:
    """Display QR code in terminal using Unicode characters."""
    import io
    import base64

    try:
        image_bytes = base64.b64decode(base64_image)
        img = Image.open(io.BytesIO(image_bytes)).convert("L")
        img = img.resize((30, 30))

        pixels = img.load()
        width, height = img.size

        print("\n" + "=" * 40)
        print("  请用微博App扫码登录  (http://weibo.com)")
        print("=" * 40 + "\n")

        # Terminal QR using Unicode block characters
        chars = " .▄▀"
        for y in range(0, height, 2):
            row = ""
            for x in range(width):
                p1 = pixels[x, y]
                p2 = pixels[x, y + 1] if y + 1 < height else 0
                idx = (p1 // 64) * 2 + (p2 // 64)
                row += chars[idx]
            print(row)

        print("\n  [等待扫码中...]")
    except Exception:
        print("\n[无法显示二维码，请在浏览器中打开授权]\n")
        print("请手动访问以下链接完成登录：")
        print(f"  {constants.BASE_URL}/oauth2/qrcode")


# ─── Credential Management ────────────────────────────────────────────────────


def login(cookie_source: str | None = None) -> models.Credentials:
    """
    Login flow: try browser cookie extraction first.

    Args:
        cookie_source: specific browser name (optional)

    Returns:
        Credentials object

    Raises:
        AuthenticationError: if cookie extraction fails
    """
    # Try browser cookie extraction
    cookie_str = extract_browser_cookie(cookie_source)
    creds = models.Credentials(cookie=cookie_str)
    save_credentials(creds)
    return creds


def logout() -> None:
    """Clear saved credentials."""
    save_credentials(models.Credentials())


def check_auth() -> bool:
    """
    Check if credentials exist and are non-empty.

    Returns:
        True if credentials are saved and non-empty
    """
    creds = load_credentials()
    return not creds.is_empty()


def get_credentials() -> models.Credentials:
    """
    Load saved credentials.

    Raises:
        AuthenticationError: if no credentials found
    """
    creds = load_credentials()
    if creds.is_empty():
        raise exceptions.AuthenticationError(
            "Not authenticated. Run 'weibo login' first."
        )
    return creds
