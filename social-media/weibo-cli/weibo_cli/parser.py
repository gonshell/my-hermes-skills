from __future__ import annotations

import re
from typing import Any

from weibo_cli import exceptions, models


# ─── Hot Search ───────────────────────────────────────────────────────────────


def parse_hot_search(raw: dict[str, Any]) -> list[models.HotItem]:
    """
    Parse hot search API response.

    Expected structure:
        raw["data"]["cards"] -> list of card groups
        each card -> "card_group" -> list of topics
    """
    items: list[models.HotItem] = []

    try:
        cards = raw.get("data", {}).get("cards", [])
        for card in cards:
            card_group = card.get("card_group", [])
            for topic in card_group:
                # Each topic has "desc1" (rank), "word" (topic name), etc.
                # Rank comes from desc1 or card_type
                word = topic.get("word", "")
                if not word:
                    continue

                # Extract rank if present
                rank = 0
                desc1 = topic.get("desc1", "")
                if desc1:
                    # desc1 format: "#1", "热度值 12345" etc.
                    match = re.search(r"#?(\d+)", desc1)
                    if match:
                        rank = int(match.group(1))

                item = models.HotItem(
                    rank=rank,
                    word=word,
                    num=topic.get("num", 0),
                    label=topic.get("label", ""),
                    mblog_id=topic.get("mblog_id", ""),
                    raw=topic,
                )
                items.append(item)

        # Sort by rank
        items.sort(key=lambda x: x.rank)
        return items

    except Exception as e:
        raise exceptions.ParseError(f"Failed to parse hot search: {e}")


def parse_trending(raw: dict[str, Any]) -> list[models.HotItem]:
    """
    Parse trending sidebar API response.

    Returns the trending sidebar topics in the right rail.
    """
    items: list[models.HotItem] = []

    try:
        cards = raw.get("data", {}).get("cards", [])
        for card in cards:
            card_group = card.get("card_group", [])
            for topic in card_group:
                word = topic.get("word", "")
                if not word:
                    continue

                item = models.HotItem(
                    rank=topic.get("rank", 0),
                    word=word,
                    num=topic.get("num", 0),
                    label=topic.get("label", ""),
                    mblog_id=topic.get("mblog_id", ""),
                    raw=topic,
                )
                items.append(item)

        return items

    except Exception as e:
        raise exceptions.ParseError(f"Failed to parse trending: {e}")


# ─── Feed / Timeline ─────────────────────────────────────────────────────────


def parse_feed(raw: dict[str, Any]) -> list[models.Weibo]:
    """
    Parse topboard/feed API response.

    Expected: raw["data"]["trends"] -> list of weibo objects
    """
    weibos: list[models.Weibo] = []

    try:
        trends = raw.get("data", {}).get("trends", [])
        for item in trends:
            w = _parse_weibo_item(item)
            if w:
                weibos.append(w)

        return weibos

    except Exception as e:
        raise exceptions.ParseError(f"Failed to parse feed: {e}")


def parse_timeline(raw: dict[str, Any]) -> list[models.Weibo]:
    """
    Parse home timeline API response.

    Expected: raw["data"]["list"] -> list of weibo objects
    """
    weibos: list[models.Weibo] = []

    try:
        timeline_list = raw.get("data", {}).get("list", [])
        for item in timeline_list:
            w = _parse_weibo_item(item)
            if w:
                weibos.append(w)

        return weibos

    except Exception as e:
        raise exceptions.ParseError(f"Failed to parse timeline: {e}")


# ─── Status / Comments ───────────────────────────────────────────────────────


def parse_status(raw: dict[str, Any]) -> models.Weibo:
    """
    Parse single status detail response.

    Expected: raw["data"]["status"] -> weibo object
    """
    try:
        status = raw.get("data", {}).get("status", raw.get("data", {}))
        return models.Weibo.from_dict(status)
    except Exception as e:
        raise exceptions.ParseError(f"Failed to parse status: {e}")


def parse_reposts(raw: dict[str, Any]) -> list[models.Weibo]:
    """Parse reposts list."""
    weibos: list[models.Weibo] = []

    try:
        reposts_list = raw.get("data", {}).get("list", [])
        for item in reposts_list:
            w = _parse_weibo_item(item)
            if w:
                weibos.append(w)
        return weibos

    except Exception as e:
        raise exceptions.ParseError(f"Failed to parse reposts: {e}")


def parse_comments(raw: dict[str, Any]) -> list[models.Comment]:
    """Parse comments API response."""
    comments: list[models.Comment] = []

    try:
        comment_list = raw.get("data", {}).get("list", [])
        for item in comment_list:
            comments.append(models.Comment.from_dict(item))
        return comments

    except Exception as e:
        raise exceptions.ParseError(f"Failed to parse comments: {e}")


# ─── User ────────────────────────────────────────────────────────────────────


def parse_user(raw: dict[str, Any]) -> models.User:
    """Parse user profile response."""
    try:
        user_data = raw.get("data", {})
        return models.User.from_dict(user_data)
    except Exception as e:
        raise exceptions.ParseError(f"Failed to parse user: {e}")


def parse_user_posts(raw: dict[str, Any]) -> list[models.Weibo]:
    """
    Parse user posts container API response.

    Expected: raw["data"]["cards"] -> list of cards
    Each card with card_type=9 contains a weibo object.
    """
    weibos: list[models.Weibo] = []

    try:
        cards = raw.get("data", {}).get("cards", [])
        for card in cards:
            card_type = card.get("card_type", 0)
            if card_type == 9:
                mblog = card.get("mblog")
                if mblog:
                    w = _parse_weibo_item(mblog)
                    if w:
                        weibos.append(w)

        return weibos

    except Exception as e:
        raise exceptions.ParseError(f"Failed to parse user posts: {e}")


def parse_followers(raw: dict[str, Any]) -> list[models.User]:
    """Parse followers/following list."""
    users: list[models.User] = []

    try:
        cards = raw.get("data", {}).get("cards", [])
        for card in cards:
            card_group = card.get("card_group", [])
            for user_card in card_group:
                if user_card.get("card_type") == 10:  # user card
                    users.append(models.User.from_dict(user_card))
                elif user_card.get("user"):
                    users.append(models.User.from_dict(user_card["user"]))

        return users

    except Exception as e:
        raise exceptions.ParseError(f"Failed to parse followers: {e}")


# ─── Search ──────────────────────────────────────────────────────────────────


def parse_search(raw: dict[str, Any]) -> list[models.Weibo]:
    """
    Parse search results.

    Expected: raw["data"]["cards"] with card_type=9 weibo objects
    """
    weibos: list[models.Weibo] = []

    try:
        cards = raw.get("data", {}).get("cards", [])
        for card in cards:
            card_type = card.get("card_type", 0)
            if card_type == 9:
                mblog = card.get("mblog")
                if mblog:
                    w = _parse_weibo_item(mblog)
                    if w:
                        weibos.append(w)

        return weibos

    except Exception as e:
        raise exceptions.ParseError(f"Failed to parse search: {e}")


# ─── Internal ────────────────────────────────────────────────────────────────


def _parse_weibo_item(item: dict[str, Any]) -> models.Weibo | None:
    """Parse a weibo/mblog item from any list context."""
    if not item:
        return None
    try:
        return models.Weibo.from_dict(item)
    except Exception:
        return None


# ─── Strip HTML ──────────────────────────────────────────────────────────────


def strip_html(text: str) -> str:
    """Strip HTML tags from text."""
    return re.sub(r"<[^>]+>", "", text)
