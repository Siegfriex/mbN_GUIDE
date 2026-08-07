"""Assertions and diagnostic reports used before/after DataFrame merges.

These are intentionally strict (raise) for primary-key violations that would
silently corrupt downstream joins, and non-raising (return dict) for
diagnostic counts that belong in a quality report.
"""
from __future__ import annotations

from typing import Any

import pandas as pd


class PrimaryKeyViolation(ValueError):
    pass


def assert_primary_key(df: pd.DataFrame, key_columns: list[str], *, context: str) -> None:
    if df.empty:
        return
    n_dupes = int(df.duplicated(subset=key_columns, keep=False).sum())
    if n_dupes:
        raise PrimaryKeyViolation(
            f"[{context}] {n_dupes} rows violate primary key uniqueness on {key_columns}"
        )
    n_null = int(df[key_columns].isna().any(axis=1).sum())
    if n_null:
        raise PrimaryKeyViolation(
            f"[{context}] {n_null} rows have null values in primary key {key_columns}"
        )


def null_counts(df: pd.DataFrame, columns: list[str] | None = None) -> dict[str, int]:
    cols = columns or list(df.columns)
    return {c: int(df[c].isna().sum()) for c in cols}


def duplicate_report(df: pd.DataFrame, subset_list: list[list[str]]) -> dict[str, int]:
    report: dict[str, int] = {}
    for subset in subset_list:
        key = "+".join(subset)
        report[key] = int(df.duplicated(subset=subset, keep=False).sum())
    return report


def cardinality(df: pd.DataFrame, columns: list[str]) -> dict[str, int]:
    return {c: int(df[c].nunique(dropna=True)) for c in columns}


def quality_status(*, row_count: int, expected_row_count: int | None, blocking_issues: list[str]) -> str:
    if blocking_issues:
        return "FAIL"
    if expected_row_count is not None and row_count != expected_row_count:
        return "WARN"
    return "PASS"


def summarize_for_report(df: pd.DataFrame, key_columns: list[str], dup_subsets: list[list[str]]) -> dict[str, Any]:
    return {
        "row_count": int(len(df)),
        "null_counts": null_counts(df),
        "duplicate_counts": duplicate_report(df, dup_subsets),
        "cardinality": cardinality(df, key_columns),
    }
