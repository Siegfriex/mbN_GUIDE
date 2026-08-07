"""Evidence-only M7 provider queue reconstruction.

This module intentionally does not call a network service.  It rebuilds
provider queries from the post-verification member mentions rather than
reusing the pre-audit query text or broad, pre-verification region groups.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd


VALID_TYPES = {"PLACE_POI", "VENUE", "EVENT"}
ELIGIBLE_STATUSES = {"LLM_VERIFIED", "LLM_CORRECTED", "LLM_SPLIT_VERIFIED"}
PRIORITY_VERSION = "provider_priority_v1"
REPAIR_VERSION = "m7_query_repair@1"


def canon(value: Any) -> str:
    return re.sub(r"[\s\(\)\[\]{}·,\.:;!?\"'‘’“”\-…]", "", str(value or "")).lower()


def as_list(value: Any) -> list[Any]:
    """Normalise Arrow/Pandas list scalars without truth-testing ndarrays."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    if hasattr(value, "tolist"):
        value = value.tolist()
    return list(value) if isinstance(value, (list, tuple, set)) else [value]


def present(value: Any) -> bool:
    return value is not None and not (isinstance(value, float) and pd.isna(value)) and bool(str(value).strip())


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_parquet(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".tmp.parquet", delete=False) as handle:
        tmp = handle.name
    try:
        frame.to_parquet(tmp, index=False)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def atomic_json(value: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, suffix=".tmp", delete=False) as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, default=str)
        handle.flush(); os.fsync(handle.fileno()); tmp = handle.name
    os.replace(tmp, path)


def _literal_supported(name: str, rows: pd.DataFrame) -> bool:
    target = canon(name)
    return bool(target) and any(target in canon(r.rawMention) or target in canon(r.evidenceText) for r in rows.itertuples())


def _direct_region_evidence(regions: list[Any], member_rows: pd.DataFrame, canonical_name: str) -> tuple[str | None, str | None, int | None]:
    """Return only a region literally occurring in that verified member evidence.

    The old queue drew a first region from a wide pre-verification group.  This
    deliberately refuses same-corpus guesses and cross-article enrichment.
    """
    name = canon(canonical_name)
    for region in regions or []:
        value = str(region or "").strip()
        if not value:
            continue
        target = canon(value)
        for row in member_rows.itertuples():
            text = str(row.evidenceText)
            compact = canon(text)
            # A region elsewhere in a long list or a quoted external context
            # is not a safe disambiguator.  Keep it only when it co-occurs
            # with the verified name in one sentence-like unit and close by.
            if not (target and name and target in compact and name in compact):
                continue
            for sentence in re.split(r"(?<=[.!?。])|\n", text):
                sent = canon(sentence)
                if target in sent and name in sent and abs(sent.find(target) - sent.find(name)) <= 80:
                    return value, str(row.articleId), int(row.blockIndex)
    return None, None, None


def compute_priority(row: dict[str, Any]) -> str:
    if row["entityType"] == "EVENT":
        return "P3"
    multiple_articles = len(set(map(str, row["articleIds"]))) >= 2
    strong_name = bool(row["nameEvidenceSupported"])
    strong_region = present(row.get("regionEvidenceArticleId"))
    strong_verification = float(row["verificationConfidence"]) >= 0.85
    unsplit = not present(row.get("splitFromEntityCandidateId"))
    if multiple_articles and strong_name and strong_region and strong_verification and unsplit:
        return "P0"
    if strong_name and strong_verification:
        return "P1"
    return "P2"


def rebuild_queue(repo_root: Path, output_root: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    source = repo_root / "data/30_geo/mbn/autopilot/run_20260808_provider_promotion"
    full = repo_root / "data/80_quality/mbn/autopilot/run_20260808_pre_api/culture_entity_mentions.parquet"
    candidates = pd.read_parquet(source / "verified_pre_provider_entity_candidates.parquet")
    mentions = pd.read_parquet(full)
    mentions["mentionId"] = mentions["mentionId"].astype(str)
    mentions["articleId"] = mentions["articleId"].astype(str)
    by_id = mentions.set_index("mentionId", drop=False)
    rows: list[dict[str, Any]] = []
    for candidate in candidates.sort_values("entityCandidateId").itertuples():
        member_ids = [str(x) for x in as_list(candidate.mentionIds)]
        member = by_id.loc[[x for x in member_ids if x in by_id.index]].copy()
        name = str(candidate.verifiedCanonicalQueryName or "").strip()
        name_ok = _literal_supported(name, member)
        region, region_article, region_block = _direct_region_evidence(as_list(candidate.regionHints), member, name)
        allowed = (
            candidate.entityType in VALID_TYPES
            and candidate.verificationStatus in ELIGIBLE_STATUSES
            and bool(candidate.shouldResolve)
            and bool(candidate.shouldMap)
            and name_ok
            and len(member) == len(member_ids)
        )
        evidence_status = "EVIDENCE_BACKED" if allowed else "HOLD_QUERY_NAME_UNSUPPORTED" if not name_ok else "HOLD_INELIGIBLE"
        query_text = " ".join(x for x in [name, region] if x)
        row = {
            "entityCandidateId": str(candidate.entityCandidateId),
            "entityType": candidate.entityType,
            "canonicalName": name,
            "queryText": query_text if allowed else None,
            "regionHint": region,
            "regionEvidenceArticleId": region_article,
            "regionEvidenceBlockIndex": region_block,
            "articleIds": list(map(str, as_list(candidate.articleIds))),
            "mentionIds": member_ids,
            "evidenceBlockIndexes": sorted({int(x) for x in member.blockIndex}) if len(member) else [],
            "verificationStatus": candidate.verificationStatus,
            "verificationConfidence": float(candidate.verificationConfidence),
            "splitFromEntityCandidateId": None if pd.isna(candidate.splitFromEntityCandidateId) else candidate.splitFromEntityCandidateId,
            "nameEvidenceSupported": name_ok,
            "queryEvidenceStatus": evidence_status,
            "executed": False,
        }
        row["priority"] = compute_priority(row) if allowed else "HOLD"
        row["providerStatus"] = "READY_NOT_EXECUTED" if allowed else evidence_status
        row["queryId"] = "m7q_" + hashlib.sha256(row["entityCandidateId"].encode()).hexdigest()[:16]
        rows.append(row)
    rebuilt = pd.DataFrame(rows)
    ready = rebuilt[rebuilt.providerStatus.eq("READY_NOT_EXECUTED")].copy()
    validation = validate_rebuilt_queue(repo_root, rebuilt, mentions)
    atomic_parquet(rebuilt, output_root / "provider_query_queue_repaired.parquet")
    atomic_parquet(validation, output_root / "repaired_queue_validation_detail.parquet")
    atomic_json({
        "repairVersion": REPAIR_VERSION,
        "priorityVersion": PRIORITY_VERSION,
        "inputCandidateCount": len(candidates),
        "repairedQueueCount": len(rebuilt),
        "readyCount": len(ready),
        "unsupportedNameAddedCount": int((~rebuilt.nameEvidenceSupported).sum()),
        "unsupportedRegionAddedCount": int((validation.unsupportedRegion).sum()),
        "priorityMismatchCount": int((~validation.priorityMatch).sum()),
        "verdict": "PRE_PROVIDER_READY_REPAIRED" if bool(validation.gatePass.all()) else "QUERY_EVIDENCE_REPAIR_FAILED",
    }, output_root / "repaired_queue_quality_report.json")
    return rebuilt, validation


def validate_rebuilt_queue(repo_root: Path, queue: pd.DataFrame, mentions: pd.DataFrame | None = None) -> pd.DataFrame:
    if mentions is None:
        mentions = pd.read_parquet(repo_root / "data/80_quality/mbn/autopilot/run_20260808_pre_api/culture_entity_mentions.parquet")
    mentions["mentionId"] = mentions.mentionId.astype(str)
    mentions["articleId"] = mentions.articleId.astype(str)
    by_id = mentions.set_index("mentionId", drop=False)
    all_entities = set(pd.read_parquet(repo_root / "data/30_geo/mbn/autopilot/run_20260808_provider_promotion/verified_pre_provider_entity_candidates.parquet").entityCandidateId.astype(str))
    rows=[]
    for row in queue.itertuples():
        ids=[str(x) for x in as_list(row.mentionIds)]
        member=by_id.loc[[x for x in ids if x in by_id.index]] if ids else pd.DataFrame()
        unsupported_name=bool(row.providerStatus == "READY_NOT_EXECUTED" and not _literal_supported(str(row.canonicalName), member))
        unsupported_region=False
        if present(row.regionHint):
            target=canon(row.regionHint)
            unsupported_region=not any(target in canon(x) for x in member.evidenceText)
        expected=compute_priority(row._asdict()) if row.providerStatus == "READY_NOT_EXECUTED" else "HOLD"
        invalid_type=row.entityType not in VALID_TYPES
        rejected_or_abstain=row.verificationStatus not in ELIGIBLE_STATUSES
        broken_article=not set(map(str,as_list(row.articleIds))).issubset(set(member.articleId.astype(str)))
        broken_block=not set(map(int,as_list(row.evidenceBlockIndexes))).issubset(set(member.blockIndex.astype(int)))
        broken_entity=str(row.entityCandidateId) not in all_entities
        gate=not any([unsupported_name,unsupported_region,invalid_type,rejected_or_abstain,broken_article,broken_block,broken_entity,expected != row.priority])
        rows.append({"queryId":row.queryId,"entityCandidateId":row.entityCandidateId,"unsupportedName":unsupported_name,"unsupportedRegion":unsupported_region,"priorityMatch":expected==row.priority,"expectedPriority":expected,"reportedPriority":row.priority,"brokenArticleFK":broken_article,"brokenBlockFK":broken_block,"brokenEntityFK":broken_entity,"rejectedPromoted":bool(row.providerStatus=="READY_NOT_EXECUTED" and rejected_or_abstain),"abstainPromoted":bool(row.providerStatus=="READY_NOT_EXECUTED" and row.verificationStatus=="LLM_ABSTAIN"),"invalidTypePromoted":bool(row.providerStatus=="READY_NOT_EXECUTED" and invalid_type),"gatePass":gate})
    return pd.DataFrame(rows)
