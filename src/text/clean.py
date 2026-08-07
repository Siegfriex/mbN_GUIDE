"""Text normalization utilities shared by parsers.

These operate on already-extracted text (post block-extraction). They never
touch ``rawTitle`` or ``rawBracketToken`` — those are contractually immutable.
"""
from __future__ import annotations

import re
import unicodedata

_WHITESPACE_RE = re.compile(r"\s+")
_ZERO_WIDTH_RE = re.compile("[​‌‍﻿]")


def normalize_whitespace(text: str) -> str:
    text = _ZERO_WIDTH_RE.sub("", text)
    text = unicodedata.normalize("NFC", text)
    return _WHITESPACE_RE.sub(" ", text).strip()


def is_boilerplate_line(text: str) -> bool:
    """Heuristic filter for share/ad/copyright/UI boilerplate lines."""
    t = text.strip()
    if not t:
        return True
    boilerplate_markers = (
        "Copyright",
        "무단전재",
        "재배포 금지",
        "구독",
        "좋아요",
        "관련기사",
        "관련 기사",
        "화제 뉴스",
        "맞춤뉴스",
    )
    return any(marker in t for marker in boilerplate_markers)


def looks_like_reporter_suffix(text: str) -> bool:
    return bool(re.search(r"[가-힣]{2,4}\s*기자\s*$", text.strip()))
