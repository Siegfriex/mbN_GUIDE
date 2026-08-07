"""Orchestrates fetch -> raw-HTML persistence -> parse for one MBN article.

Every article, success or failure, produces a raw-HTML file (on success) and
a full attempt log (always) — nothing is dropped or silently nulled.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from src.collection.http_client import attempts_to_records, fetch_with_retry
from src.io.hashing import sha256_file
from src.parsing.mbn_article_parser import (
    parse_article,
    result_to_author_record,
    result_to_block_records,
    result_to_body_record,
)


def collect_article(
    article_id: str,
    url: str,
    *,
    raw_html_dir: Path,
    repo_root: Path,
    collected_at: str,
) -> dict[str, Any]:
    fetch_result = fetch_with_retry(url)
    attempt_records = attempts_to_records(article_id, fetch_result.attempts)

    if not fetch_result.ok or fetch_result.text is None:
        return {
            "articleId": article_id,
            "url": url,
            "ok": False,
            "httpStatus": fetch_result.statusCode,
            "failureReason": fetch_result.failureReason or "unknown fetch failure",
            "attempts": attempt_records,
            "body_record": None,
            "block_records": [],
            "author_record": None,
        }

    html_path = raw_html_dir / f"{article_id}.html"
    html_path.write_text(fetch_result.text, encoding="utf-8")
    raw_sha256 = sha256_file(html_path)
    relative_html_path = str(html_path.relative_to(repo_root))

    parse_result = parse_article(fetch_result.text)
    body_record = result_to_body_record(article_id, parse_result, relative_html_path, raw_sha256, collected_at)
    block_records = result_to_block_records(article_id, parse_result)
    author_record = result_to_author_record(article_id, parse_result)

    return {
        "articleId": article_id,
        "url": url,
        "ok": True,
        "httpStatus": fetch_result.statusCode,
        "failureReason": None if parse_result.parseStatus == "ok" else parse_result.failureReason,
        "attempts": attempt_records,
        "body_record": body_record,
        "block_records": block_records,
        "author_record": author_record,
        "usedFallback": parse_result.usedFallback,
    }
