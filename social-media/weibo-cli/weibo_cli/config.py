from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from weibo_cli import constants, models


def _expand_path(path: str) -> Path:
    return Path(os.path.expanduser(path))


def _ensure_config_dir() -> Path:
    config_path = _expand_path(constants.CONFIG_DIR)
    config_path.mkdir(parents=True, exist_ok=True)
    return config_path


# ─── Credentials ──────────────────────────────────────────────────────────────


def load_credentials() -> models.Credentials:
    """Load saved credentials from disk."""
    path = _expand_path(constants.CREDENTIALS_FILE)
    if not path.exists():
        return models.Credentials()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return models.Credentials.from_dict(data)
    except (json.JSONDecodeError, IOError):
        return models.Credentials()


def save_credentials(creds: models.Credentials) -> None:
    """Save credentials to disk."""
    _ensure_config_dir()
    path = _expand_path(constants.CREDENTIALS_FILE)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(creds.to_dict(), f, ensure_ascii=False, indent=2)
    # Restrict permissions
    os.chmod(path, 0o600)


# ─── Config ──────────────────────────────────────────────────────────────────


def load_config() -> dict[str, Any]:
    """Load user config from disk."""
    path = _expand_path(constants.CONFIG_FILE)
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_config(config: dict[str, Any]) -> None:
    """Save user config to disk."""
    _ensure_config_dir()
    path = _expand_path(constants.CONFIG_FILE)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
