"""In-game display size (godogen ASSETS.md Size column)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

_SIZE_RE = re.compile(r"(\d+)\s*[x×]\s*(\d+)", re.IGNORECASE)


@dataclass(frozen=True)
class DisplaySize:
    """How large the asset appears on screen (viewport pixels)."""

    width: int
    height: int

    @classmethod
    def empty(cls) -> DisplaySize:
        return cls(0, 0)

    def is_empty(self) -> bool:
        return self.width <= 0 or self.height <= 0

    def to_dict(self) -> dict[str, int]:
        return {"width": self.width, "height": self.height}

    def to_api_string(self) -> str:
        return f"{self.width}x{self.height}"

    def __str__(self) -> str:
        if self.is_empty():
            return ""
        return f"{self.width}x{self.height} px"


def parse_display_size(raw: Any) -> DisplaySize | None:
    """Parse brief display_size: `{width,height}` or `128x128 px` strings."""
    if raw is None:
        return None
    if isinstance(raw, dict):
        try:
            w, h = int(raw.get("width", 0)), int(raw.get("height", 0))
        except (TypeError, ValueError):
            return None
        if w > 0 and h > 0:
            return DisplaySize(w, h)
        return None
    text = str(raw).strip()
    if not text:
        return None
    match = _SIZE_RE.search(text)
    if not match:
        return None
    w, h = int(match.group(1)), int(match.group(2))
    if w > 0 and h > 0:
        return DisplaySize(w, h)
    return None


def display_size_from_viewport(viewport: dict[str, Any] | None) -> DisplaySize:
    vp = viewport or {}
    try:
        w, h = int(vp.get("width", 0)), int(vp.get("height", 0))
        if w > 0 and h > 0:
            return DisplaySize(w, h)
    except (TypeError, ValueError):
        pass
    return DisplaySize(1280, 720)
