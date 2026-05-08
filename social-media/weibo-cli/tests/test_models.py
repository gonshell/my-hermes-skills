"""Unit tests for weibo_cli models."""
from datetime import datetime

import pytest

from weibo_cli.models import (
    Comment,
    Credentials,
    HotItem,
    User,
    Weibo,
)


class TestHotItem:
    def test_from_dict_basic(self):
        raw = {
            "word": "Python 3.13",
            "num": 1234567,
            "mblog_id": "NsIjy4WXe",
        }
        item = HotItem.from_dict(raw, rank=1)
        assert item.word == "Python 3.13"
        assert item.num == 1234567
        assert item.rank == 1
        assert item.mblog_id == "NsIjy4WXe"

    def test_from_dict_with_label(self):
        raw = {
            "word": "热点",
            "num": 999,
            "word_scheme": {"label_name": "沸"},
        }
        item = HotItem.from_dict(raw, rank=2)
        assert item.label == "沸"

    def test_from_dict_missing_fields(self):
        raw = {"word": "Test"}
        item = HotItem.from_dict(raw)
        assert item.word == "Test"
        assert item.num == 0
        assert item.label == ""


class TestUser:
    def test_from_dict(self):
        raw = {
            "id": "1195230310",
            "screen_name": "test_user",
            "followers_count": 1234567,
            "friends_count": 500,
            "statuses_count": 9999,
            "verified": True,
            "verified_type": 0,
            "description": "这是一个测试用户",
            "profile_image_url": "https://example.com/avatar.jpg",
        }
        user = User.from_dict(raw)
        assert user.id == "1195230310"
        assert user.name == "test_user"
        assert user.followers_count == 1234567
        assert user.verified is True
        assert user.description == "这是一个测试用户"

    def test_from_dict_minimal(self):
        raw = {"id": "123", "screen_name": "MinUser"}
        user = User.from_dict(raw)
        assert user.id == "123"
        assert user.name == "MinUser"
        assert user.followers_count == 0
        assert user.verified is False

    def test_from_dict_nested_user(self):
        """User can be extracted from parent dict with 'user' key."""
        parent = {
            "user": {
                "id": "999",
                "screen_name": "nested_user",
            }
        }
        user = User.from_dict(parent)
        assert user.id == "999"
        assert user.name == "nested_user"


class TestWeibo:
    def test_from_dict_full(self):
        raw = {
            "id": "NsIjy4WXe",
            "text": "<p>这是微博正文</p>",
            "created_at": "Mon Apr 27 10:30:00 +0800 2026",
            "reposts_count": 100,
            "comments_count": 50,
            "attitudes_count": 200,
            "user": {
                "id": "1195230310",
                "screen_name": "测试用户",
            },
        }
        wb = Weibo.from_dict(raw)
        assert wb.id == "NsIjy4WXe"
        assert "这是微博正文" in wb.text_raw
        assert wb.reposts_count == 100
        assert wb.comments_count == 50
        assert wb.attitudes_count == 200
        assert wb.user is not None
        assert wb.user.name == "测试用户"

    def test_from_dict_no_user(self):
        raw = {
            "id": "abc123",
            "text": "No user attached",
        }
        wb = Weibo.from_dict(raw)
        assert wb.user is None

    def test_url_property(self):
        raw = {
            "id": "xyz",
            "text": "test",
            "user": {"id": "123", "screen_name": "u"},
        }
        wb = Weibo.from_dict(raw)
        assert "123" in wb.url and "xyz" in wb.url


class TestCredentials:
    def test_to_dict(self):
        creds = Credentials(cookie="SUB=abc123; SSOLogin=xyz", token="tok", uid="1195230310")
        d = creds.to_dict()
        assert d["cookie"] == "SUB=abc123; SSOLogin=xyz"
        assert d["token"] == "tok"
        assert d["uid"] == "1195230310"

    def test_from_dict(self):
        d = {"cookie": "SUB=xyz", "token": "t", "uid": "555"}
        creds = Credentials.from_dict(d)
        assert creds.cookie == "SUB=xyz"
        assert creds.token == "t"
        assert creds.uid == "555"

    def test_is_empty(self):
        empty = Credentials()
        assert empty.is_empty() is True
        with_creds = Credentials(cookie="SUB=x")
        assert with_creds.is_empty() is False


class TestComment:
    def test_from_dict(self):
        raw = {
            "id": "c1",
            "text": "<p>评论内容</p>",
            "created_at": "Mon Apr 27 10:30:00 +0800 2026",
            "like_count": 42,
            "reply_count": 5,
            "user": {"id": "u1", "screen_name": " commenter"},
        }
        c = Comment.from_dict(raw)
        assert c.id == "c1"
        assert "评论内容" in c.text_raw
        assert c.like_count == 42
        assert c.user.name == " commenter"
