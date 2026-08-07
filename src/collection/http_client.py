"""Rate-limited HTTP GET with retry, returning full attempt metadata.

Every attempt (successful or not) is recorded — retries, timeouts, the
user-agent used, and the HTTP status — so collection failures never disappear
silently; the caller decides how to record ``parseStatus``/failure reason.
"""
from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any

import requests

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) mbN_GUIDE_PY-research-collector/1.0"


@dataclass
class FetchAttempt:
    attemptNumber: int
    url: str
    httpStatus: int | None
    ok: bool
    errorType: str | None
    errorMessage: str | None
    elapsedSeconds: float


@dataclass
class FetchResult:
    url: str
    ok: bool
    statusCode: int | None
    text: str | None
    userAgent: str
    attempts: list[FetchAttempt] = field(default_factory=list)
    failureReason: str | None = None


def fetch_with_retry(
    url: str,
    *,
    timeout: float = 15.0,
    max_retries: int = 4,
    base_backoff_seconds: float = 1.5,
    rate_limit_min_seconds: float = 0.4,
    rate_limit_jitter_seconds: float = 0.3,
) -> FetchResult:
    attempts: list[FetchAttempt] = []
    for attempt_number in range(1, max_retries + 1):
        start = time.monotonic()
        try:
            resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
            elapsed = time.monotonic() - start
            attempts.append(
                FetchAttempt(
                    attemptNumber=attempt_number,
                    url=url,
                    httpStatus=resp.status_code,
                    ok=resp.ok,
                    errorType=None if resp.ok else "http_error",
                    errorMessage=None if resp.ok else f"HTTP {resp.status_code}",
                    elapsedSeconds=elapsed,
                )
            )
            if resp.ok:
                resp.encoding = "utf-8"
                time.sleep(rate_limit_min_seconds + random.random() * rate_limit_jitter_seconds)
                return FetchResult(
                    url=url,
                    ok=True,
                    statusCode=resp.status_code,
                    text=resp.text,
                    userAgent=USER_AGENT,
                    attempts=attempts,
                )
            logger.warning("fetch_with_retry: HTTP %s for %s (attempt %d)", resp.status_code, url, attempt_number)
        except requests.exceptions.RequestException as exc:
            elapsed = time.monotonic() - start
            attempts.append(
                FetchAttempt(
                    attemptNumber=attempt_number,
                    url=url,
                    httpStatus=None,
                    ok=False,
                    errorType=type(exc).__name__,
                    errorMessage=str(exc),
                    elapsedSeconds=elapsed,
                )
            )
            logger.warning("fetch_with_retry: %s for %s (attempt %d)", exc, url, attempt_number)

        if attempt_number < max_retries:
            time.sleep(base_backoff_seconds * attempt_number)

    time.sleep(rate_limit_min_seconds + random.random() * rate_limit_jitter_seconds)
    last = attempts[-1]
    return FetchResult(
        url=url,
        ok=False,
        statusCode=last.httpStatus,
        text=None,
        userAgent=USER_AGENT,
        attempts=attempts,
        failureReason=last.errorMessage,
    )


def attempts_to_records(article_id: str, attempts: list[FetchAttempt]) -> list[dict[str, Any]]:
    return [
        {
            "articleId": article_id,
            "attemptNumber": a.attemptNumber,
            "url": a.url,
            "httpStatus": a.httpStatus,
            "ok": a.ok,
            "errorType": a.errorType,
            "errorMessage": a.errorMessage,
            "elapsedSeconds": a.elapsedSeconds,
        }
        for a in attempts
    ]
