"""DataFrame <-> parquet/csv I/O helpers with lightweight schema checks."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.io.hashing import sha256_file
from src.io.paths import ensure_parent


def write_table(df: pd.DataFrame, path: Path, *, required_columns: list[str] | None = None) -> dict:
    """Write ``df`` to ``path`` (parquet) and a sibling ``.csv``.

    Returns a manifest dict with row count and sha256 for both artifacts,
    suitable for embedding in a notebook's closing quality-report cell.
    """
    if required_columns is not None:
        missing = set(required_columns) - set(df.columns)
        if missing:
            raise ValueError(f"write_table: missing required columns {missing} for {path}")

    ensure_parent(path)
    parquet_path = path.with_suffix(".parquet")
    csv_path = path.with_suffix(".csv")

    df.to_parquet(parquet_path, index=False)
    df.to_csv(csv_path, index=False)

    return {
        "row_count": len(df),
        "parquet_path": str(parquet_path),
        "parquet_sha256": sha256_file(parquet_path),
        "csv_path": str(csv_path),
        "csv_sha256": sha256_file(csv_path),
    }


def read_table(path: Path) -> pd.DataFrame:
    parquet_path = path.with_suffix(".parquet")
    if parquet_path.exists():
        return pd.read_parquet(parquet_path)
    csv_path = path.with_suffix(".csv")
    if csv_path.exists():
        return pd.read_csv(csv_path)
    raise FileNotFoundError(f"Neither {parquet_path} nor {csv_path} exists")
