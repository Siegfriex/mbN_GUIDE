"""Site-wide markup repair for mbn.co.kr pages.

Root cause (discovered empirically, recorded here so it is not re-derived):
Every mbn.co.kr page embeds a Google Tag Manager fallback block of the form

    <!-- Google Tag Manager (noscript) -->
    <noscript>
        <iframe src="..." height="0" width="0" style="..."></noscript>

The ``<iframe>`` is missing its ``</iframe>`` closing tag. Because
``<iframe>`` is not a CDATA/raw-text element for Python's ``html.parser``
(only ``script``/``style`` are), the parser treats the iframe as an
still-open tag for the REMAINDER of the document. Every subsequent tag
(including ``#content_2020_top`` and ``#newsViewArea``) then gets attached
under that dangling iframe instead of the real tree, so ``soup.find(id=...)``
returns nothing for anything below the header. ``lxml`` exhibits the same
failure on this markup.

The fix is narrowly scoped to this one boilerplate block (safe: it is
tracking-pixel markup, never article content) rather than a general
HTML-repair pass, so it cannot accidentally alter article body content.
"""
from __future__ import annotations

import re

_GTM_NOSCRIPT_RE = re.compile(
    r"<!-- Google Tag Manager \(noscript\) -->.*?<!-- End Google Tag Manager \(noscript\) -->",
    re.DOTALL,
)

HTML_FIX_VERSION = "mbn_html_fix@1"


def fix_mbn_html(raw_html: str) -> tuple[str, bool]:
    """Return (fixed_html, was_fallback_pattern_present)."""
    fixed, n_subs = _GTM_NOSCRIPT_RE.subn("", raw_html)
    return fixed, n_subs > 0
