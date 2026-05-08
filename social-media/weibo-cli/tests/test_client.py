"""Unit tests for weibo_cli client module."""
import pytest
from unittest.mock import patch, MagicMock

from weibo_cli import client, constants, exceptions


class TestWeiboClient:
    def test_init(self):
        c = client.WeiboClient(use_cache=False)
        assert c._credentials is None
        assert c._cache is None

    def test_credentials_lazy_load(self):
        c = client.WeiboClient(use_cache=False)
        # Don't call c.credentials here as it will try to load real credentials

    @patch("weibo_cli.client.httpx.Client")
    @patch("weibo_cli.client.get_credentials")
    def test_get_success(self, mock_get_creds, mock_httpx):
        mock_get_creds.return_value = MagicMock(cookie="SUB=abc")
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": 1, "data": {"list": []}}
        mock_response.raise_for_status = MagicMock()

        mock_client_instance = MagicMock()
        mock_client_instance.get.return_value = mock_response
        mock_httpx.return_value.__enter__.return_value = mock_client_instance

        c = client.WeiboClient(use_cache=False)
        c._credentials = MagicMock(cookie="SUB=abc")
        result = c.get("https://example.com/api", params={"page": 1})

        assert result["ok"] == 1
        mock_client_instance.get.assert_called_once()

    @patch("weibo_cli.client.httpx.Client")
    def test_get_timeout(self, mock_httpx):
        import httpx
        mock_httpx.return_value.__enter__.side_effect = httpx.TimeoutException("timeout")

        c = client.WeiboClient(use_cache=False)
        with pytest.raises(exceptions.NetworkError, match="timed out"):
            c.get("https://example.com/api")

    @patch("weibo_cli.client.httpx.Client")
    def test_get_auth_error(self, mock_httpx):
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": -100, "msg": "need login"}
        mock_response.raise_for_status = MagicMock()
        mock_client_instance = MagicMock()
        mock_client_instance.get.return_value = mock_response
        mock_httpx.return_value.__enter__.return_value = mock_client_instance

        c = client.WeiboClient(use_cache=False)
        with pytest.raises(exceptions.AuthenticationError):
            c.get("https://example.com/api")

    @patch("weibo_cli.client.httpx.Client")
    def test_get_api_error(self, mock_httpx):
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": 0, "msg": "server error"}
        mock_response.raise_for_status = MagicMock()
        mock_client_instance = MagicMock()
        mock_client_instance.get.return_value = mock_response
        mock_httpx.return_value.__enter__.return_value = mock_client_instance

        c = client.WeiboClient(use_cache=False)
        with pytest.raises(exceptions.APIError):
            c.get("https://example.com/api")


class TestCredentialsProperty:
    @patch("weibo_cli.client.get_credentials")
    def test_credentials_loads_from_get_credentials(self, mock_get):
        mock_get.return_value = MagicMock(cookie="SUB=test")
        c = client.WeiboClient(use_cache=False)
        creds = c.credentials
        assert creds.cookie == "SUB=test"
        mock_get.assert_called_once()

    @patch("weibo_cli.client.get_credentials")
    def test_credentials_cached(self, mock_get):
        mock_get.return_value = MagicMock(cookie="SUB=test")
        c = client.WeiboClient(use_cache=False)
        _ = c.credentials
        _ = c.credentials
        mock_get.assert_called_once()  # Only called once
