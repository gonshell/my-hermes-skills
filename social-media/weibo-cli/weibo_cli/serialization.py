from __future__ import annotations

import json
import sys
from typing import Any


def to_json(data: Any, pretty: bool = False) -> str:
    """Serialize data to JSON string."""
    if pretty:
        return json.dumps(data, ensure_ascii=False, indent=2, default=str)
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"), default=str)


def to_yaml(data: Any) -> str:
    """
    Simple YAML-like serialization for structured output.

    For full YAML, use the `yaml` package.
    Here we produce a simple key: value format suitable for shell parsing.
    """
    lines: list[str] = []

    def _format(obj: Any, indent: int = 0) -> None:
        prefix = "  " * indent
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, (dict, list)):
                    lines.append(f"{prefix}{k}:")
                    _format(v, indent + 1)
                else:
                    lines.append(f"{prefix}{k}: {v}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                if isinstance(item, (dict, list)):
                    lines.append(f"{prefix}- [item {i}]:")
                    _format(item, indent + 1)
                else:
                    lines.append(f"{prefix}- {item}")
        else:
            lines.append(f"{prefix}{obj}")

    _format(data)
    return "\n".join(lines)


def output_json(data: Any, pretty: bool = False) -> None:
    """Print JSON to stdout."""
    print(to_json(data, pretty=pretty))


def output_yaml(data: Any) -> None:
    """Print YAML-like format to stdout."""
    print(to_yaml(data))


def detect_format(override: str | None) -> str:
    """
    Detect output format.

    Priority:
    1. explicit override (--json / --yaml / --compact)
    2. TTY check: stdout.isatty() -> rich (human), else -> yaml (machine)
    """
    if override:
        return override

    if hasattr(sys.stdout, "isatty") and sys.stdout.isatty():
        return "rich"
    return "yaml"
