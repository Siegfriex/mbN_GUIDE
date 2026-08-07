"""Repo-root-relative path resolution.

Notebooks must never hardcode absolute filesystem paths. This module locates
the repository root by walking upward from the current working directory
looking for the ``.git`` marker, then exposes canonical data-layer paths
relative to it.
"""
from __future__ import annotations

from pathlib import Path


class RepoRootNotFoundError(RuntimeError):
    pass


def find_repo_root(start: Path | None = None) -> Path:
    """Walk upward from ``start`` (default: cwd) until a ``.git`` dir is found."""
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").is_dir():
            return candidate
    raise RepoRootNotFoundError(
        f"Could not locate repo root (.git marker) walking up from {current}"
    )


def data_dir(repo_root: Path, *parts: str) -> Path:
    path = repo_root / "data"
    for part in parts:
        path = path / part
    return path


def config_path(repo_root: Path, name: str) -> Path:
    return repo_root / "config" / name


def ensure_parent(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    return path
