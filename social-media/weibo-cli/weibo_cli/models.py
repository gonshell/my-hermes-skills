from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


# ─── User ─────────────────────────────────────────────────────────────────────


@dataclass
class User:
    id: str
    name: str  # screen_name
    avatar: str  # profile_image_url
    followers_count: int = 0
    friends_count: int = 0  # following count
    statuses_count: int = 0  # posts count
    description: str = ""
    verified: bool = False
    verified_type: int = -1  # -1=none, 0=red, 1=blue, etc.
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> User:
        if data.get("user"):
            data = data["user"]
        return cls(
            id=str(data.get("id", "")),
            name=data.get("screen_name", ""),
            avatar=data.get("profile_image_url", ""),
            followers_count=data.get("followers_count", 0),
            friends_count=data.get("friends_count", 0),
            statuses_count=data.get("statuses_count", 0),
            description=data.get("description", ""),
            verified=data.get("verified", False),
            verified_type=data.get("verified_type", -1),
            raw=data,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "avatar": self.avatar,
            "followers_count": self.followers_count,
            "friends_count": self.friends_count,
            "statuses_count": self.statuses_count,
            "description": self.description,
            "verified": self.verified,
            "verified_type": self.verified_type,
        }


# ─── Weibo / Status ───────────────────────────────────────────────────────────


@dataclass
class Weibo:
    id: str  # mblog_id
    text: str  # raw text (may contain HTML)
    text_raw: str = ""  # stripped text
    user: User | None = None
    created_at: datetime = field(default_factory=datetime.now)
    attitudes_count: int = 0  # likes
    comments_count: int = 0
    reposts_count: int = 0
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def url(self) -> str:
        uid = self.user.id if self.user else ""
        return f"https://weibo.com/{uid}/status/{self.id}"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Weibo:
        user = None
        if data.get("user"):
            user = User.from_dict(data["user"])

        created_at = datetime.now()
        created_str = data.get("created_at", "")
        if created_str:
            try:
                # Weibo format: "Mon Apr 27 20:00:00 +0800 2026"
                created_at = datetime.strptime(created_str, "%a %b %d %H:%M:%S %z %Y")
            except ValueError:
                pass

        text_raw = data.get("text_raw", data.get("text", ""))
        # Strip HTML tags
        import re

        text_raw = re.sub(r"<[^>]+>", "", text_raw)

        return cls(
            id=str(data.get("id", data.get("mblogid", ""))),
            text=data.get("text", ""),
            text_raw=text_raw,
            user=user,
            created_at=created_at,
            attitudes_count=data.get("attitudes_count", 0),
            comments_count=data.get("comments_count", 0),
            reposts_count=data.get("reposts_count", 0),
            raw=data,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "text_raw": self.text_raw,
            "user": self.user.to_dict() if self.user else None,
            "created_at": self.created_at.isoformat(),
            "attitudes_count": self.attitudes_count,
            "comments_count": self.comments_count,
            "reposts_count": self.reposts_count,
            "url": self.url,
        }


# ─── Hot Item ─────────────────────────────────────────────────────────────────


@dataclass
class HotItem:
    rank: int
    word: str  # topic name
    num: int = 0  # search count
    label: str = ""  # "热" / "沸" / "新"
    mblog_id: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any], rank: int = 0) -> HotItem:
        label = ""
        if data.get("word_scheme"):
            # Extract label from scheme label_name
            label_name = data.get("word_scheme", {}).get("label_name", "")
            label = label_name
        return cls(
            rank=rank,
            word=data.get("word", ""),
            num=data.get("num", 0),
            label=label,
            mblog_id=data.get("mblog_id", ""),
            raw=data,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "rank": self.rank,
            "word": self.word,
            "num": self.num,
            "label": self.label,
            "mblog_id": self.mblog_id,
        }


# ─── Comment ──────────────────────────────────────────────────────────────────


@dataclass
class Comment:
    id: str
    text: str
    text_raw: str = ""
    user: User | None = None
    created_at: datetime = field(default_factory=datetime.now)
    like_count: int = 0
    reply_count: int = 0
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Comment:
        user = None
        if data.get("user"):
            user = User.from_dict(data["user"])

        created_at = datetime.now()
        created_str = data.get("created_at", "")
        if created_str:
            try:
                created_at = datetime.strptime(created_str, "%a %b %d %H:%M:%S %z %Y")
            except ValueError:
                pass

        import re

        text_raw = re.sub(r"<[^>]+>", "", data.get("text", ""))
        return cls(
            id=str(data.get("id", "")),
            text=data.get("text", ""),
            text_raw=text_raw,
            user=user,
            created_at=created_at,
            like_count=data.get("like_count", 0),
            reply_count=data.get("reply_count", 0),
            raw=data,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "text_raw": self.text_raw,
            "user": self.user.to_dict() if self.user else None,
            "created_at": self.created_at.isoformat(),
            "like_count": self.like_count,
            "reply_count": self.reply_count,
        }


# ─── Credentials ──────────────────────────────────────────────────────────────


@dataclass
class Credentials:
    cookie: str = ""
    token: str = ""  # Sub token for mobile API
    uid: str = ""  # numeric user id

    def is_empty(self) -> bool:
        return not self.cookie

    def to_dict(self) -> dict[str, str]:
        return {
            "cookie": self.cookie,
            "token": self.token,
            "uid": self.uid,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Credentials:
        return cls(
            cookie=data.get("cookie", ""),
            token=data.get("token", ""),
            uid=data.get("uid", ""),
        )
