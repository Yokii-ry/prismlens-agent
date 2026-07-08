import json
import os
import sys
from datetime import datetime
from typing import Any


MAX_STRING_LENGTH = 260
MAX_LIST_ITEMS = 5
MAX_DICT_ITEMS = 12
MAX_DEPTH = 3

COLORS = {
    "api": "\033[36m",
    "worker": "\033[35m",
    "pipeline": "\033[34m",
    "success": "\033[32m",
    "error": "\033[31m",
    "warning": "\033[33m",
    "reset": "\033[0m",
    "muted": "\033[90m",
}


def debug_panel(source: str, title: str, payload: Any | None = None, status: str = "info") -> None:
    """Print a readable terminal panel for local API/worker debugging."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    source_label = source.upper()
    header = f"[{timestamp}] {source_label} | {title}"
    body = _format_payload(payload)
    width = max(72, min(110, max(len(_strip_ansi(header)), _longest_line(body)) + 4))
    line = "=" * width
    color = _color_for(source, status)
    reset = COLORS["reset"] if _should_color() else ""

    print(f"\n{color}{line}{reset}")
    print(f"{color}{header}{reset}")
    print(f"{COLORS['muted'] if _should_color() else ''}{'-' * width}{reset}")
    if body:
        print(body)
    print(f"{color}{line}{reset}\n")


def _format_payload(payload: Any | None) -> str:
    if payload is None:
        return ""
    normalized = _normalize(payload)
    return json.dumps(normalized, ensure_ascii=False, indent=2, default=str)


def _normalize(value: Any, depth: int = 0) -> Any:
    if depth >= MAX_DEPTH:
        return _short_repr(value)
    if isinstance(value, dict):
        items = list(value.items())
        normalized = {
            str(key): _normalize(item_value, depth + 1)
            for key, item_value in items[:MAX_DICT_ITEMS]
        }
        if len(items) > MAX_DICT_ITEMS:
            normalized["_more_keys"] = len(items) - MAX_DICT_ITEMS
        return normalized
    if isinstance(value, (list, tuple, set)):
        items = list(value)
        normalized = [_normalize(item, depth + 1) for item in items[:MAX_LIST_ITEMS]]
        if len(items) > MAX_LIST_ITEMS:
            normalized.append(f"... +{len(items) - MAX_LIST_ITEMS} more")
        return normalized
    if isinstance(value, str):
        return _truncate(value)
    return value


def _short_repr(value: Any) -> str:
    return _truncate(json.dumps(value, ensure_ascii=False, default=str))


def _truncate(value: str) -> str:
    if len(value) <= MAX_STRING_LENGTH:
        return value
    return f"{value[:MAX_STRING_LENGTH]}... ({len(value)} chars)"


def _longest_line(value: str) -> int:
    if not value:
        return 0
    return max(len(_strip_ansi(line)) for line in value.splitlines())


def _strip_ansi(value: str) -> str:
    for color in COLORS.values():
        value = value.replace(color, "")
    return value


def _color_for(source: str, status: str) -> str:
    if not _should_color():
        return ""
    if status in ("success", "error", "warning"):
        return COLORS[status]
    return COLORS.get(source, "")


def _should_color() -> bool:
    return sys.stdout.isatty() and os.getenv("NO_COLOR") is None
