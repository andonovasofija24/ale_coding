"""Request language detection (Macedonian / English)."""
from typing import Literal, Optional

from fastapi import Header

Lang = Literal["mk", "en"]
DEFAULT_LANG: Lang = "mk"
SUPPORTED: tuple[Lang, ...] = ("mk", "en")


def parse_language(accept_language: Optional[str]) -> Lang:
    """Pick the first supported language from an Accept-Language header.

    Handles both the plain value the frontend sends ("mk") and a full
    browser-style header ("en-US,en;q=0.9,mk;q=0.8").
    """
    if not accept_language:
        return DEFAULT_LANG
    for part in accept_language.split(","):
        code = part.split(";")[0].strip().lower()[:2]
        if code in SUPPORTED:
            return code  # type: ignore[return-value]
    return DEFAULT_LANG


async def get_language(accept_language: Optional[str] = Header(default=None)) -> Lang:
    return parse_language(accept_language)
