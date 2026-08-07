"""Parser for mbn.co.kr article-detail pages.

Extracts (title, section, publishedAt) from ``#content_2020_top`` and an
ordered list of content blocks from ``#newsViewArea``.

Article body markup is inline-styled and inconsistently nested (the whole
body is frequently wrapped in a single unclosed ``<p>``, with headings
expressed as ``<strong><div style="border-top:...">`` and images wrapped in
layout ``<table>``). There is no semantic tag structure to rely on, so block
classification here is a documented heuristic, not a guarantee — hence the
``parseConfidence`` field on every block and the block-level ``sourceSelector``
recording exactly which heuristic fired.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from bs4 import BeautifulSoup, Comment, NavigableString, Tag

from src.parsing.mbn_html_fix import HTML_FIX_VERSION, fix_mbn_html
from src.text.clean import normalize_whitespace

ARTICLE_PARSER_VERSION = "mbn_article_parser@1"

_AD_ID_PREFIXES = ("google_dfp",)
_AD_CLASS_MARKERS = ("news8_bt_bn_area", "relation_news2_2020", "banner")

_HEADING_STYLE_RE = re.compile(r"border-top\s*:", re.IGNORECASE)
_KOREAN_NAME_RE = re.compile(r"[가-힣]{2,4}")
_REPORTER_SUFFIX_RE = re.compile(r"([가-힣]{2,4})\s*기자\s*$")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")

HEADING_CONFIDENCE = 0.70
PARAGRAPH_CONFIDENCE = 0.60
IMAGE_CONFIDENCE = 0.90
TABLE_CONFIDENCE = 0.60
BYLINE_CONFIDENCE = 0.80


@dataclass
class Block:
    blockType: str
    rawText: str
    cleanText: str
    htmlFragment: str
    sourceSelector: str
    parseConfidence: float


@dataclass
class AuthorInfo:
    authorRaw: str | None = None
    authorName: str | None = None
    authorEmail: str | None = None
    authorParseMethod: str = "not_found"
    authorParseStatus: str = "not_found"


@dataclass
class ArticleParseResult:
    title: str | None
    section: str | None
    publishedAtRaw: str | None
    blocks: list[Block] = field(default_factory=list)
    author: AuthorInfo = field(default_factory=AuthorInfo)
    parseStatus: str = "failed"
    usedFallback: bool = False
    failureReason: str | None = None
    parserVersion: str = ARTICLE_PARSER_VERSION


def _is_ad_or_boilerplate(tag: Tag) -> bool:
    tag_id = tag.get("id") or ""
    tag_class = " ".join(tag.get("class") or [])
    if any(tag_id.startswith(p) for p in _AD_ID_PREFIXES):
        return True
    if any(marker in tag_class for marker in _AD_CLASS_MARKERS):
        return True
    return False


def _table_image_srcs(table: Tag) -> list[Tag]:
    return table.find_all("img")


def _table_is_pure_image_wrapper(table: Tag) -> bool:
    imgs = _table_image_srcs(table)
    if not imgs:
        return False
    clone_text = table.get_text(" ", strip=True)
    for img in imgs:
        clone_text = clone_text.replace((img.get("alt") or "").strip(), "")
    return normalize_whitespace(clone_text) == ""


def _img_src(img: Tag) -> str:
    return img.get("data-src") or img.get("src") or ""


def _extract_byline(area: Tag) -> tuple[AuthorInfo, str | None]:
    """Look for a byline near the tail of the body. Checked in order:
    1. an explicit ``<b>`` role tag (e.g. ``[<b>글과 사진</b>최유진]``) —
       the plain text immediately following it, up to ``]``/``<br>``.
    2. a trailing "...OOO 기자" suffix anywhere in the body text.
    3. a bare email address anywhere in the body text.
    """
    # Only a role label containing "글" (written-by) implies the following name is
    # a reporter/writer byline. "사진"(photo credit)/"일러스트"(illustration credit)
    # -only labels, or unrelated in-body bold emphasis, must NOT be mistaken for one.
    b_tags = [b for b in area.find_all("b") if "글" in normalize_whitespace(b.get_text())]
    if b_tags:
        b_tag = b_tags[-1]
        role_text = normalize_whitespace(b_tag.get_text())
        following = []
        node = b_tag.next_sibling
        while node is not None and not (isinstance(node, Tag) and node.name == "br"):
            if isinstance(node, NavigableString):
                following.append(str(node))
            elif isinstance(node, Tag):
                following.append(node.get_text())
            node = node.next_sibling
        following_text = normalize_whitespace("".join(following)).strip("[] 　")
        raw = normalize_whitespace(f"{role_text} {following_text}").strip()
        # The byline name sits immediately after the "글" role label (e.g.
        # "글 변덕호(매경에이엑스) 기자 사진 각 백화점" -> "변덕호"); anything
        # after it is affiliation/parenthetical bio or a trailing separately
        # credited photo/illustration line, so the FIRST match wins, not the last.
        names = _KOREAN_NAME_RE.findall(following_text)
        email_match = _EMAIL_RE.search(raw)
        if names:
            return (
                AuthorInfo(
                    authorRaw=raw,
                    authorName=names[0],
                    authorEmail=email_match.group() if email_match else None,
                    authorParseMethod="b_tag_following_text",
                    authorParseStatus="found",
                ),
                raw,
            )

    tail_text = normalize_whitespace(area.get_text(" "))[-400:]
    m = _REPORTER_SUFFIX_RE.search(tail_text)
    if m:
        return (
            AuthorInfo(
                authorRaw=m.group(0),
                authorName=m.group(1),
                authorEmail=None,
                authorParseMethod="regex_tail_reporter_suffix",
                authorParseStatus="found",
            ),
            m.group(0),
        )

    email_match = _EMAIL_RE.search(tail_text)
    if email_match:
        return (
            AuthorInfo(
                authorRaw=email_match.group(),
                authorName=None,
                authorEmail=email_match.group(),
                authorParseMethod="regex_email_only",
                authorParseStatus="partial",
            ),
            email_match.group(),
        )

    return AuthorInfo(), None


def _walk_blocks(area: Tag, byline_raw: str | None) -> list[Block]:
    blocks: list[Block] = []
    pending: list[str] = []

    def flush_paragraph():
        text = normalize_whitespace("".join(pending))
        pending.clear()
        if text:
            blocks.append(
                Block(
                    blockType="paragraph",
                    rawText=text,
                    cleanText=text,
                    htmlFragment="",
                    sourceSelector="text_run(br_separated)",
                    parseConfidence=PARAGRAPH_CONFIDENCE,
                )
            )

    def is_heading_tag(tag: Tag) -> bool:
        style = tag.get("style") or ""
        if _HEADING_STYLE_RE.search(style):
            return True
        if tag.name == "strong":
            inner_div = tag.find("div")
            if inner_div and _HEADING_STYLE_RE.search(inner_div.get("style") or ""):
                return True
        return False

    def visit(node) -> None:
        if isinstance(node, Comment):
            return
        if isinstance(node, NavigableString):
            pending.append(str(node))
            return
        if not isinstance(node, Tag):
            return

        if node.name in ("script", "style"):
            return
        if node.name == "b":
            # Consumed separately by _extract_byline; do not double-count as paragraph text.
            return
        if _is_ad_or_boilerplate(node):
            return
        if node.name == "br":
            flush_paragraph()
            return
        if node.name == "img":
            flush_paragraph()
            src = _img_src(node)
            alt = normalize_whitespace(node.get("alt") or "")
            blocks.append(
                Block(
                    blockType="image",
                    rawText=src,
                    cleanText=src,
                    htmlFragment=str(node),
                    sourceSelector="img",
                    parseConfidence=IMAGE_CONFIDENCE,
                )
            )
            if alt:
                blocks.append(
                    Block(
                        blockType="caption",
                        rawText=alt,
                        cleanText=alt,
                        htmlFragment=str(node),
                        sourceSelector="img[alt]",
                        parseConfidence=IMAGE_CONFIDENCE,
                    )
                )
            return
        if node.name == "table":
            flush_paragraph()
            if _table_is_pure_image_wrapper(node):
                for img in _table_image_srcs(node):
                    visit(img)
            else:
                raw = node.get_text(" ", strip=True)
                blocks.append(
                    Block(
                        blockType="table",
                        rawText=raw,
                        cleanText=normalize_whitespace(raw),
                        htmlFragment=str(node),
                        sourceSelector="table",
                        parseConfidence=TABLE_CONFIDENCE,
                    )
                )
            return
        if is_heading_tag(node):
            flush_paragraph()
            raw = node.get_text(" ", strip=True)
            blocks.append(
                Block(
                    blockType="heading",
                    rawText=raw,
                    cleanText=normalize_whitespace(raw),
                    htmlFragment=str(node),
                    sourceSelector="style*=border-top (heuristic)",
                    parseConfidence=HEADING_CONFIDENCE,
                )
            )
            return

        # Transparent containers: recurse into children (span/div/p wrappers
        # carry inline text runs with no reliable block semantics of their own).
        for child in node.children:
            visit(child)

    for child in area.children:
        visit(child)
    flush_paragraph()

    if byline_raw:
        blocks.append(
            Block(
                blockType="byline",
                rawText=byline_raw,
                cleanText=normalize_whitespace(byline_raw),
                htmlFragment="",
                sourceSelector="b_tag_or_tail_regex (see author metadata)",
                parseConfidence=BYLINE_CONFIDENCE,
            )
        )

    return blocks


def _find_news_view_area_fallback(html: str) -> str | None:
    """Balanced-``<div>`` substring extraction, used only if CSS/id lookup
    fails even after ``fix_mbn_html``. Independent of full-document tree
    parsing, matching the approach already proven for list pages.
    """
    marker = 'id="newsViewArea"'
    idx = html.find(marker)
    if idx == -1:
        return None
    start = html.rfind("<div", 0, idx)
    if start == -1:
        return None
    depth = 0
    pos = start
    tag_re = re.compile(r"<div\b|</div>", re.IGNORECASE)
    for m in tag_re.finditer(html, start):
        if m.group().lower().startswith("<div"):
            depth += 1
        else:
            depth -= 1
            if depth == 0:
                return html[start : m.end()]
    return None


def parse_article(raw_html: str) -> ArticleParseResult:
    fixed_html, had_gtm_bug = fix_mbn_html(raw_html)
    soup = BeautifulSoup(fixed_html, "html.parser")

    title_el = soup.select_one("#content_2020_top > div > div.box01 > h1")
    section_el = soup.select_one("#content_2020_top > div > div.box01 > span")
    date_el = soup.select_one("#content_2020_top > div > div.box02 > div.txt_box > span > span")

    title = normalize_whitespace(title_el.get_text()) if title_el else None
    section = normalize_whitespace(section_el.get_text()) if section_el else None
    published_raw = normalize_whitespace(date_el.get_text()) if date_el else None

    area = soup.find(id="newsViewArea")
    used_fallback = False
    if area is None:
        used_fallback = True
        fragment_html = _find_news_view_area_fallback(fixed_html)
        if fragment_html is None:
            return ArticleParseResult(
                title=title,
                section=section,
                publishedAtRaw=published_raw,
                parseStatus="failed",
                usedFallback=True,
                failureReason="newsViewArea not found via id lookup or balanced-div fallback",
            )
        area = BeautifulSoup(fragment_html, "html.parser").find(id="newsViewArea")
        if area is None:
            return ArticleParseResult(
                title=title,
                section=section,
                publishedAtRaw=published_raw,
                parseStatus="failed",
                usedFallback=True,
                failureReason="fallback fragment re-parse did not yield newsViewArea",
            )

    author, byline_raw = _extract_byline(area)
    blocks = _walk_blocks(area, byline_raw)

    status = "ok" if title and blocks else "partial"
    return ArticleParseResult(
        title=title,
        section=section,
        publishedAtRaw=published_raw,
        blocks=blocks,
        author=author,
        parseStatus=status,
        usedFallback=used_fallback,
        failureReason=None if status == "ok" else "title or body blocks missing",
    )


def result_to_body_record(article_id: str, result: ArticleParseResult, raw_html_path: str, raw_body_sha256: str, collected_at: str) -> dict[str, Any]:
    clean_body = "\n".join(b.cleanText for b in result.blocks if b.blockType != "byline")
    return {
        "articleId": article_id,
        "rawHtmlPath": raw_html_path,
        "rawBody": "\n".join(b.rawText for b in result.blocks if b.blockType != "byline"),
        "cleanBody": clean_body,
        "bodyLength": len(clean_body),
        "paragraphCount": sum(1 for b in result.blocks if b.blockType == "paragraph"),
        "language": "ko",
        "bodySha256": raw_body_sha256,
        "parserVersion": f"{ARTICLE_PARSER_VERSION}+{HTML_FIX_VERSION}",
        "parseStatus": result.parseStatus,
        "collectedAt": collected_at,
    }


def result_to_block_records(article_id: str, result: ArticleParseResult) -> list[dict[str, Any]]:
    return [
        {
            "articleId": article_id,
            "blockIndex": i,
            "blockType": b.blockType,
            "rawText": b.rawText,
            "cleanText": b.cleanText,
            "htmlFragment": b.htmlFragment,
            "sourceSelector": b.sourceSelector,
            "parseConfidence": b.parseConfidence,
        }
        for i, b in enumerate(result.blocks)
    ]


def result_to_author_record(article_id: str, result: ArticleParseResult) -> dict[str, Any]:
    a = result.author
    return {
        "articleId": article_id,
        "authorRaw": a.authorRaw,
        "authorName": a.authorName,
        "authorEmail": a.authorEmail,
        "authorParseMethod": a.authorParseMethod,
        "authorParseStatus": a.authorParseStatus,
    }
