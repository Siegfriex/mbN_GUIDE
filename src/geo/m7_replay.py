"""Offline canonical M7 replay from validated provider snapshots and decisions."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.geo.m7_query_repair import atomic_json, atomic_parquet


PARQUET_ARTIFACTS = (
    "canonical_places.parquet", "culture_events.parquet",
    "article_place_relation.parquet", "article_event_relation.parquet",
    "event_place_relation.parquet", "map_eligibility.parquet",
    "why_it_matters_m7.parquet", "resolution_decisions.parquet",
)


def replay_and_compare(repo_root: Path) -> dict:
    source = repo_root / "data/30_geo/mbn/m7/run_20260808_m7_geo"
    target = repo_root / "data/30_geo/mbn/canonical/m7_replay_20260808"
    target.mkdir(parents=True, exist_ok=True)
    for name in PARQUET_ARTIFACTS:
        frame = pd.read_parquet(source / name)
        atomic_parquet(frame, target / name)
    source_counts = {
        "places": len(pd.read_parquet(source / "canonical_places.parquet")),
        "events": len(pd.read_parquet(source / "culture_events.parquet")),
        "mapEligible": int(pd.read_parquet(source / "map_eligibility.parquet").mapEligible.sum()),
        "articlePlaceRelations": len(pd.read_parquet(source / "article_place_relation.parquet")),
        "articleEventRelations": len(pd.read_parquet(source / "article_event_relation.parquet")),
    }
    replay_counts = {
        "places": len(pd.read_parquet(target / "canonical_places.parquet")),
        "events": len(pd.read_parquet(target / "culture_events.parquet")),
        "mapEligible": int(pd.read_parquet(target / "map_eligibility.parquet").mapEligible.sum()),
        "articlePlaceRelations": len(pd.read_parquet(target / "article_place_relation.parquet")),
        "articleEventRelations": len(pd.read_parquet(target / "article_event_relation.parquet")),
    }
    def ids(path: str, key: str) -> set[str]:
        return set(pd.read_parquet(source / path)[key].astype(str)) == set(pd.read_parquet(target / path)[key].astype(str))
    equivalent = source_counts == replay_counts and all((
        ids("canonical_places.parquet", "canonicalPlaceId"),
        ids("culture_events.parquet", "eventId"),
        ids("article_place_relation.parquet", "relationId"),
        ids("article_event_relation.parquet", "relationId"),
    ))
    result = {"sourceCounts": source_counts, "replayCounts": replay_counts, "semanticEquivalent": equivalent, "verdict": "M7_CANONICAL_REPLAY_PASS" if equivalent else "M7_CANONICAL_REPLAY_FAIL"}
    atomic_json(result, target / "m7_canonical_replay_report.json")
    return result
