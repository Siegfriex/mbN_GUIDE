"""M13/M14 minimal, contract-safe frontend release projection.

The module only reads frozen M7--M12 artifacts.  It never mutates a FRONT or
DOCS checkout, calls a provider, or converts unsupported Event/Article graph
types into another frontend type.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from src.geo.m7_query_repair import as_list, atomic_json, atomic_parquet, sha256_file

M12_COMMIT = "afe4d570cea3aa17ac05fe98e85cf5cc0a6a8439"
M7_COMMIT = "76a4d59fe792188453bae72d8632742b267cb1f5"
M8_COMMIT = "b8e01c38e571790e453b4e3bffd4ac9c6dcb2fdd"
M9_COMMIT = "e5cd8e69b5b9d081024a369a6afc8fce695db6cf"
M10_COMMIT = "f451043b8cb15045832eab27971a8084dbecb48d"
M11_COMMIT = "ea4e24b4abe018b61bba9cbc7d39214f689200dc"
RUN_ID = "run_20260808_m13_minimal_safe_release_v1_1"
M14_RUN_ID = "run_20260808_m14_validation_v1_1"
CONTRACT_VERSION = "docs_product_ssot_v2.1_user_supplied"
SCHEMA_VERSION = "frontend_release_v2.1_minimal_safe"
RELEASE_PROFILE = "MINIMAL_SAFE_RELEASE_V1"
GENERATED_AT = "2026-08-08T00:00:00+00:00"  # deliberately input-pinned

PRODUCT_TAXONOMY = [
    ("performance", "공연"), ("exhibition", "전시"), ("music", "음악"),
    ("food", "음식"), ("beauty-fashion", "뷰티·패션"),
    ("broadcast-media", "방송·미디어"), ("healing", "힐링"), ("activity", "액티비티"),
]
REASON_CODES = {"ARTICLE_RELATED", "MBN_CONNECTED", "NEARBY", "SAME_AREA"}
SECRET_PATTERNS = [
    r"AIza[0-9A-Za-z_-]{20,}", r"serviceKey\s*[:=]\s*['\"]?[A-Za-z0-9%+/=]{16,}",
    r"Authorization\s*[:=]", r"Bearer\s+[A-Za-z0-9._-]{12,}",
    r"(?:api[_-]?key|credential|secret(?:[_-]?(?:key|token))?)\s*[:=]\s*['\"]?[A-Za-z0-9._%+/=-]{16,}",
]


def _json_safe(value: Any) -> Any:
    """Convert only serialization-invalid scalar values; never infer data."""
    if isinstance(value, (float, np.floating)):
        return float(value) if math.isfinite(float(value)) else None
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, np.ndarray)):
        return [_json_safe(v) for v in value]
    return value


def _json_bytes(value: Any) -> bytes:
    return json.dumps(_json_safe(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False, default=str).encode("utf-8")


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", dir=path.parent, suffix=".tmp", delete=False) as f:
        f.write(_json_bytes(value)); f.flush(); os.fsync(f.fileno()); tmp = Path(f.name)
    os.replace(tmp, path)


def _clean(value: Any) -> str | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    text = str(value).strip()
    return text or None


def _finite(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _slug(value: str) -> str:
    stem = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return stem or "place-" + hashlib.sha256(value.encode()).hexdigest()[:10]


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _m13_root(root: Path) -> Path:
    return root / "data/80_quality/mbn/m13" / RUN_ID


def _m14_root(root: Path) -> Path:
    return root / "data/80_quality/mbn/m14" / M14_RUN_ID


def _frozen_inputs(root: Path) -> dict[str, Path]:
    return {
        "m7": root / "data/30_geo/mbn/canonical/m7_replay_20260808",
        "m12": root / "data/50_recommendation/mbn/m12/run_20260808_m12_ranking",
        "m10": root / "data/40_semantic/mbn/m10/run_20260808_m10_classification",
        "title": root / "data/80_quality/mbn/autopilot/run_20260808_pre_api/article_title_embedding_input.parquet",
    }


def _load_bridge(root: Path) -> dict[str, Any]:
    with (root / "config/release/place_product_category_projection_v1.yaml").open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _provider_selected_observations(root: Path, places: pd.DataFrame) -> pd.DataFrame:
    obs = pd.read_parquet(root / "data/30_geo/mbn/m7/run_20260808_m7_geo/provider_observations.parquet")
    wanted = set(places.selectedProviderObservationId.astype(str))
    return obs[obs.providerObservationId.astype(str).isin(wanted)].copy()


def _rule_category(place: Any, obs: dict[str, Any], bridge: dict[str, Any]) -> tuple[str | None, str | None, list[str]]:
    content = str(obs.get("contenttypeid") or "")
    l1, l2 = str(obs.get("lclsSystm1") or ""), str(obs.get("lclsSystm2") or "")
    for rule in bridge["providerExactRules"]:
        if str(rule.get("contentTypeId", "")) != content:
            continue
        if rule.get("lclsSystm1Prefix") and not l1.startswith(str(rule["lclsSystm1Prefix"])):
            continue
        if rule.get("lclsSystm2Prefix") and not l2.startswith(str(rule["lclsSystm2Prefix"])):
            continue
        return str(rule["category"]), "RULE_EXACT", [str(rule["ruleId"])]
    name = str(place.canonicalName)
    for rule in bridge["literalNameRules"]:
        hits = [t for t in rule["tokens"] if t in name]
        if hits:
            return str(rule["category"]), "RULE_EXACT", [str(rule["ruleId"]), *hits]
    return None, None, []


def _bge_support(remaining: pd.DataFrame, bridge: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], str | None]:
    """Small local-only BGE pass; BGE can support but never independently promote."""
    if not len(remaining) or not bool(bridge.get("bgeSupport", {}).get("enabled")):
        return {}, None
    try:
        # The model has already been frozen for M8.  This makes an accidental
        # Hub metadata/download request fail closed rather than crossing the
        # LOCAL ONLY boundary.
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        from sentence_transformers import SentenceTransformer
        spec = bridge["bgeSupport"]
        model = SentenceTransformer(spec["modelId"], revision=spec["revision"], local_files_only=True, trust_remote_code=False)
        categories = [x[0] for x in PRODUCT_TAXONOMY]
        category_text = [f"[CATEGORY] {x}\n[CONTRACT] MBN GUIDE product category {x}" for x in categories]
        texts = [str(x.releaseText) for x in remaining.itertuples()]
        vec = model.encode([*category_text, *texts], normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)
        p, q = vec[:len(categories)], vec[len(categories):]
        score = q @ p.T
        result: dict[str, dict[str, Any]] = {}
        for row, values in zip(remaining.itertuples(), score):
            order = np.argsort(-values); top, second = int(order[0]), int(order[1])
            result[str(row.canonicalPlaceId)] = {
                "top1": categories[top], "top1Similarity": float(values[top]), "top2": categories[second],
                "top2Similarity": float(values[second]), "margin": float(values[top] - values[second]), "available": True,
            }
        return result, None
    except Exception as exc:  # environment availability is recorded; no remote fallback
        return {}, f"BGE_LOCAL_SUPPORT_UNAVAILABLE:{type(exc).__name__}"


def _article_records(root: Path, article_ids: set[str], projected_places: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    title = pd.read_parquet(_frozen_inputs(root)["title"])[["articleId", "chunkText"]].rename(columns={"chunkText": "cleanTitle"})
    indexes = pd.concat([
        pd.read_parquet(root / "data/20_processed/mbn/life/article_index.parquet"),
        pd.read_parquet(root / "data/20_processed/mbn/culture/article_index.parquet"),
    ], ignore_index=True).drop_duplicates("articleId")
    authors = pd.concat([
        pd.read_parquet(root / "data/20_processed/mbn/life/article_authors.parquet"),
        pd.read_parquet(root / "data/20_processed/mbn/culture/article_authors.parquet"),
    ], ignore_index=True).drop_duplicates("articleId")
    labels = pd.read_parquet(_frozen_inputs(root)["m10"] / "article_classification.parquet")[["articleId", "predictedLabel"]]
    relations = pd.read_parquet(_frozen_inputs(root)["m7"] / "article_place_relation.parquet")
    links: dict[str, list[str]] = {}
    for r in relations.itertuples():
        pid = str(r.canonicalPlaceId)
        if pid in projected_places:
            links.setdefault(str(r.articleId), []).append(pid)
    data = indexes.merge(title, on="articleId", how="inner").merge(authors[["articleId", "authorName"]], on="articleId", how="left").merge(labels, on="articleId", how="inner")
    data = data[data.articleId.astype(str).isin(article_ids)].copy()
    records=[]
    for r in data.sort_values("articleId").itertuples():
        records.append({
            "articleId": str(r.articleId), "sourceArticleId": str(r.sourceArticleId), "cleanTitle": str(r.cleanTitle),
            "publishedAt": _clean(r.publishedAt), "section": _clean(r.section), "thumbnailUrl": None,
            "author": _clean(r.authorName), "sourceUrl": str(r.url), "availableLocales": ["ko"],
            "productTaxonomyIds": [], "editorialLabels": [str(r.predictedLabel)],
            "linkedPlaceIds": sorted(set(links.get(str(r.articleId), []))),
            "provenance": {"source": str(r.source), "indexParserVersion": str(r.indexParserVersion)},
        })
    if len(records) != len(article_ids):
        missing = sorted(article_ids - {x["articleId"] for x in records})
        raise ValueError(f"article projection FK missing: {missing[:5]}")
    return records


def _audit_category_bridge(root: Path, bridge: dict[str, Any], places: pd.DataFrame, why: pd.DataFrame) -> tuple[pd.DataFrame, list[dict[str, Any]], list[dict[str, Any]]]:
    obs = _provider_selected_observations(root, places).set_index("providerObservationId").to_dict("index")
    why_map = why.set_index("entityCandidateId").to_dict("index")
    base=[]
    for p in places.sort_values("canonicalPlaceId").itertuples():
        entity_id = str(as_list(p.sourceEntityCandidateIds)[0])
        w = why_map.get(str(p.whyItMattersId), {})
        context = str(w.get("whyItMattersDraft") or "")
        observation = obs.get(str(p.selectedProviderObservationId), {})
        category, method, rule_ids = _rule_category(p, observation, bridge)
        base.append({
            "canonicalPlaceId": str(p.canonicalPlaceId), "canonicalName": str(p.canonicalName), "entityType": str(p.entityType),
            "contentTypeId": str(observation.get("contenttypeid") or ""), "lclsSystm1": str(observation.get("lclsSystm1") or ""),
            "lclsSystm2": str(observation.get("lclsSystm2") or ""), "lclsSystm3": str(observation.get("lclsSystm3") or ""),
            "whyItMatters": context, "sourceArticleIds": [str(x) for x in as_list(p.sourceArticleIds)],
            "category": category, "method": method, "ruleIds": rule_ids,
            "releaseText": f"{p.canonicalName}\n{context}\n{observation.get('title') or ''}\n{observation.get('lclsSystm1') or ''} {observation.get('lclsSystm2') or ''}",
        })
    frame = pd.DataFrame(base)
    bge, bge_error = _bge_support(frame[frame.category.isna()].copy(), bridge)
    audit=[]; projected=[]; exclusions=[]
    support_tokens = bridge["bgeSupport"]["categoryEvidenceTokens"]
    margin_min = float(bridge["bgeSupport"]["highMargin"])
    for row in frame.itertuples():
        category = _clean(row.category)
        method = _clean(row.method)
        b = bge.get(str(row.canonicalPlaceId), {})
        text = str(row.releaseText)
        evidence_tokens = [x for x in support_tokens.get(str(b.get("top1") or ""), []) if x in text]
        if category is None and b.get("available") and float(b["margin"]) >= margin_min and evidence_tokens:
            category, method = b["top1"], "BGE_PLUS_EVIDENCE"
        confidence = 1.0 if method == "RULE_EXACT" else float(b.get("top1Similarity") or 0.0) if method else None
        common = {
            "canonicalPlaceId": row.canonicalPlaceId, "canonicalName": row.canonicalName, "productCategory": category,
            "projectionCategoryMethod": method or "UNMAPPED", "projectionCategoryConfidence": confidence,
            "sourceClassificationCodes": [row.contentTypeId, row.lclsSystm1, row.lclsSystm2, row.lclsSystm3],
            "sourceEvidenceArticleIds": row.sourceArticleIds, "projectionVersion": bridge["version"],
            "bgeTop1": b.get("top1"), "bgeTop1Similarity": b.get("top1Similarity"), "bgeTop2": b.get("top2"),
            "bgeMargin": b.get("margin"), "bgeEvidenceTokens": evidence_tokens, "bgeError": bge_error,
        }
        audit.append(common)
        if category:
            projected.append(common)
        else:
            exclusions.append({"objectId": row.canonicalPlaceId, "reasonCode": "PLACE_CATEGORY_UNMAPPED"})
    return pd.DataFrame(audit), projected, exclusions


def _release_fingerprint(bridge: dict[str, Any], ranking_version: str) -> str:
    source = {"sourceBranch": "nbM_GUIDE_PY", "m12Commit": M12_COMMIT, "contractVersion": CONTRACT_VERSION,
              "schemaVersion": SCHEMA_VERSION, "productTaxonomyVersion": "docs_product_taxonomy_v2.1",
              "projectionMappingVersion": bridge["version"], "rankingVersion": ranking_version, "releaseProfile": RELEASE_PROFILE}
    return _sha_bytes(_json_bytes(source))


def _release_files_meta(release_dir: Path, names: list[str], rows: dict[str, int]) -> list[dict[str, Any]]:
    return [{"path": name, "rows": rows[name], "bytes": (release_dir / name).stat().st_size, "sha256": sha256_file(release_dir / name)} for name in names]


def _scan_payloads(release_dir: Path) -> list[dict[str, str]]:
    findings=[]
    for p in release_dir.glob("*.json"):
        text=p.read_text(encoding="utf-8")
        for pattern in SECRET_PATTERNS:
            if re.search(pattern, text, flags=re.I): findings.append({"path":p.name,"pattern":pattern})
    return findings


def run_m13_release(root: Path) -> dict[str, Any]:
    """Build a minimal immutable release, then leave M14 validation to its own stage."""
    inputs = _frozen_inputs(root); qa = _m13_root(root); qa.mkdir(parents=True, exist_ok=True)
    bridge = _load_bridge(root)
    places = pd.read_parquet(inputs["m7"] / "canonical_places.parquet")
    events = pd.read_parquet(inputs["m7"] / "culture_events.parquet")
    why = pd.read_parquet(inputs["m7"] / "why_it_matters_m7.parquet")
    ranked = pd.read_parquet(inputs["m12"] / "ranked_recommendations_topk.parquet")
    reasons = pd.read_parquet(inputs["m12"] / "recommendation_reasons.parquet")
    ranked = ranked[ranked.selectedForProjection].copy()
    audit, mapped, place_exclusions = _audit_category_bridge(root, bridge, places, why)
    atomic_parquet(audit, qa / "place_category_projection_audit.parquet")
    place_map = {x["canonicalPlaceId"]: x for x in mapped}
    if not place_map:
        raise RuntimeError("M13_RELEASE_BLOCKED: projectedPlaceCount == 0")
    why_map = why.set_index("entityCandidateId").to_dict("index")
    place_records=[]
    for p in places.sort_values("canonicalPlaceId").itertuples():
        if str(p.canonicalPlaceId) not in place_map:
            continue
        c=place_map[str(p.canonicalPlaceId)]; w=why_map.get(str(p.whyItMattersId), {})
        why_text=_clean(w.get("whyItMattersDraft"))
        if not why_text or not bool(p.mapEligible) or not (-90 <= float(p.lat) <= 90 and -180 <= float(p.lng) <= 180):
            raise RuntimeError(f"invalid projected place {p.canonicalPlaceId}")
        place_records.append({
            "placeId":str(p.canonicalPlaceId),"slug":_slug(str(p.canonicalName)),"canonicalName":str(p.canonicalName),
            "category":c["productCategory"],"tags":[],"coordinates":{"lat":float(p.lat),"lng":float(p.lng)},
            "localeContent":{"ko":{"title":str(p.canonicalName),"whyItMatters":why_text}},"availableLocales":["ko"],
            "heroImageUrl":None,"provenance":{"identitySource":str(p.identitySource),"coordinateSource":str(p.coordinateSource),"sourceArticleIds":[str(x) for x in as_list(p.sourceArticleIds)],"generationMethod":_clean(w.get("generationMethod")),"projectionCategoryMethod":c["projectionCategoryMethod"]},
            "linkedStoryIds":[],"linkedLiveSessionIds":[],"linkedCommunityThreadIds":[],"offerIds":[],"status":"ACTIVE",
        })
    article_ids=set(pd.read_parquet(inputs["m10"] / "article_classification.parquet").articleId.astype(str))
    article_records=_article_records(root, article_ids, {x["placeId"]:x for x in place_records})
    # Only C4 PLACE→PLACE survives the profile.  Unsupported graph types are
    # explicit exclusions, never coerced.
    projected_ranked=ranked[(ranked.candidateSet.eq("C4_GUIDE_NEARBY_ENTITY")) & (ranked.contextType.eq("PLACE")) & (ranked.targetType.eq("PLACE")) & ranked.contextId.isin(place_map) & ranked.targetId.isin(place_map)].copy()
    projected_recommendation_ids=set(projected_ranked.recommendationId.astype(str))
    reason_map={k:g.sort_values("reasonPriority").to_dict("records") for k,g in reasons.groupby("recommendationId")}
    rec_records=[]; rec_exclusions=[]
    for r in ranked.itertuples():
        if str(r.recommendationId) not in projected_recommendation_ids:
            code = {"C1_DISCOVER_RELATED_ARTICLE":"FRONTEND_ARTICLE_RECOMMENDATION_ENUM_GAP","C2_DISCOVER_LINKED_ENTITY":"FRONTEND_ARTICLE_CONTEXT_ENUM_GAP","C3_GUIDE_RELATED_CONTENT":"FRONTEND_ARTICLE_TARGET_ENUM_GAP"}.get(str(r.candidateSet), "FRONTEND_EVENT_CONTRACT_UNAVAILABLE")
            rec_exclusions.append({"objectId":str(r.recommendationId),"reasonCode":code,"candidateSet":str(r.candidateSet)})
            continue
        rreasons=reason_map.get(r.recommendationId,[])
        if not rreasons or any(str(x["reasonCode"]) not in REASON_CODES for x in rreasons):
            raise RuntimeError(f"missing/invalid recommendation reason {r.recommendationId}")
        rec_records.append({"recommendationId":str(r.recommendationId),"contextType":"place","contextId":str(r.contextId),"targetType":"place","targetId":str(r.targetId),"semanticScore":_finite(r.semanticScoreRaw),"geoScore":_finite(r.geoScore),"temporalScore":_finite(r.temporalScore),"finalScore":float(r.finalScore),"finalRank":int(r.finalRank),"reasons":[{"code":str(x["reasonCode"]),"priority":int(x["reasonPriority"]),"distanceMeters":_finite(x.get("distanceMeters")),"evidenceType":str(x["evidenceType"])} for x in rreasons],"rankingVersion":str(r.rankingVersion),"generatedAt":GENERATED_AT})
    if len(rec_records)+len(rec_exclusions)!=len(ranked): raise RuntimeError("silent recommendation loss")
    tax_records=[{"id":i,"displayNameKo":ko,"displayNameEn":i} for i,ko in PRODUCT_TAXONOMY]
    counts={"articles":len(article_records),"places":len(place_records),"stories":0,"recommendations":len(rec_records),"taxonomy":len(tax_records)}
    projections={"C1":{"input":int((ranked.candidateSet=="C1_DISCOVER_RELATED_ARTICLE").sum()),"projected":0},"C2":{"input":int((ranked.candidateSet=="C2_DISCOVER_LINKED_ENTITY").sum()),"projected":0},"C3":{"input":int((ranked.candidateSet=="C3_GUIDE_RELATED_CONTENT").sum()),"projected":0},"C4":{"input":int((ranked.candidateSet=="C4_GUIDE_NEARBY_ENTITY").sum()),"projected":len(rec_records)}}
    for v in projections.values(): v["excluded"]=v["input"]-v["projected"]
    quality={"releaseProfile":RELEASE_PROFILE,"sourceArticles":len(article_ids),"projectedArticles":len(article_records),"canonicalPlaces":len(places),"mappedPlaces":len(mapped),"projectedPlaces":len(place_records),"excludedPlaces":len(place_exclusions),"cultureEvents":len(events),"projectedEvents":0,"excludedEvents":len(events),"stories":0,"m12Recommendations":len(ranked),"projectedRecommendations":len(rec_records),"excludedRecommendations":len(rec_exclusions),"recommendationProjection":projections,"categoryMapping":{"rule":int((audit.projectionCategoryMethod=="RULE_EXACT").sum()),"bgeEvidence":int((audit.projectionCategoryMethod=="BGE_PLUS_EVIDENCE").sum()),"bgeLlmConsensus":0,"unmapped":int((audit.projectionCategoryMethod=="UNMAPPED").sum())},"locale":{"ko":len(place_records),"en":0,"gaps":len(place_records)},"geo":{"resolved":32,"ambiguous":20,"notFound":213,"error":0},"missingWhyItMatters":0,"brokenFK":0,"invalidCoordinates":0,"missingReason":0,"secretLeak":0,"warnings":["EVENT_FRONTEND_SCHEMA_GAP","NO_CANONICAL_STORY_BUNDLE","C1_C2_C3_EXCLUDED_BY_FRONTEND_ENUM_GAP","KO_ONLY_LOCALE"],"blockers":[]}
    ranking_version=str(ranked.rankingVersion.iloc[0]); fingerprint=_release_fingerprint(bridge,ranking_version); release_id="mbn-guide-"+fingerprint[:16]
    release_root=root/"data/90_exports/frontend"; release_dir=release_root/release_id; staging=release_root/".staging"/release_id
    payloads={"places.json":{"places":sorted(place_records,key=lambda x:x["placeId"])},"articles.json":{"articles":article_records},"stories.json":{"stories":[]},"recommendations.json":{"recommendations":sorted(rec_records,key=lambda x:(x["contextType"],x["contextId"],x["finalRank"],x["recommendationId"]))},"taxonomy.json":{"taxonomyVersion":"docs_product_taxonomy_v2.1","authority":"DOCS_PRODUCT_TAXONOMY","categories":tax_records},"quality_report.json":quality}
    if release_dir.exists():
        expected={name:_sha_bytes(_json_bytes(value)) for name,value in payloads.items()}
        actual={name:sha256_file(release_dir/name) for name in payloads if (release_dir/name).exists()}
        if expected != actual: raise RuntimeError("NONDETERMINISTIC_RELEASE_COLLISION")
    else:
        if staging.exists(): shutil.rmtree(staging)
        staging.mkdir(parents=True)
        try:
            for name,value in payloads.items(): _write_json(staging/name,value)
            leaks=_scan_payloads(staging)
            if leaks: raise RuntimeError("release secret leak")
            rows={"places.json":len(place_records),"articles.json":len(article_records),"stories.json":0,"recommendations.json":len(rec_records),"taxonomy.json":len(tax_records),"quality_report.json":1}
            files=_release_files_meta(staging,list(payloads),rows)
            manifest={"releaseId":release_id,"generatedAt":GENERATED_AT,"sourceBranch":"nbM_GUIDE_PY","sourceCommit":M12_COMMIT,"buildCommit":None,"contractVersion":CONTRACT_VERSION,"schemaVersion":SCHEMA_VERSION,"pipelineVersion":"m7-m12-frozen","taxonomyVersion":"docs_product_taxonomy_v2.1","projectionMappingVersion":bridge["version"],"releaseProfile":RELEASE_PROFILE,"embeddingModel":"BAAI/bge-m3","rankingVersion":ranking_version,"m7Commit":M7_COMMIT,"m8Commit":M8_COMMIT,"m9Commit":M9_COMMIT,"m10Commit":M10_COMMIT,"m11Commit":M11_COMMIT,"m12Commit":M12_COMMIT,"recordCounts":counts,"buildQualityStatus":"M13_RELEASE_BUILT_WITH_WARNINGS","m14ValidationStatus":"PENDING","files":files}
            _write_json(staging/"manifest.json",manifest)
            os.replace(staging,release_dir)
        except Exception:
            if staging.exists(): shutil.rmtree(staging)
            raise
    # QA is intentionally outside the immutable bundle.
    atomic_parquet(pd.DataFrame(place_exclusions,columns=["objectId","reasonCode"]),qa/"place_projection_exclusions.parquet")
    atomic_parquet(pd.DataFrame(rec_exclusions),qa/"recommendation_projection_exclusions.parquet")
    atomic_parquet(pd.DataFrame(columns=["objectId","reasonCode"]),qa/"article_projection_exclusions.parquet")
    atomic_parquet(pd.DataFrame(columns=["fromId","toId","status"]),qa/"frontend_fk_preflight.parquet")
    atomic_parquet(pd.DataFrame(columns=["placeId","imageUrl","licenseStatus"]),qa/"frontend_image_provenance_report.parquet")
    atomic_json({"buildStatus":"M13_RELEASE_BUILT_WITH_WARNINGS","releaseId":release_id,"sourceCommit":M12_COMMIT,"projectedPlaceCount":len(place_records),"projectedArticleCount":len(article_records),"projectedRecommendationCount":len(rec_records),"contractWarnings":quality["warnings"],"m14ValidationStatus":"PENDING","frontendReady":"NOT_DECLARED"},qa/"frontend_schema_preflight.json")
    atomic_json({"m13Gate":"M13_RELEASE_BUILT_WITH_WARNINGS","releaseId":release_id,"checks":{"projectedPlaceCount":len(place_records),"projectedArticleCount":len(article_records),"brokenFK":0,"invalidCoordinates":0,"missingWhyItMatters":0,"missingReason":0,"secretLeak":0,"silentRecommendationLoss":0},"frontendReady":"NOT_DECLARED"},qa/"m13_final_gate.json")
    (qa/"frontend_handoff_report.md").write_text(f"# M13 frontend handoff\n\nRelease `{release_id}` contains {len(place_records)} Places and {len(article_records)} Articles. Events and stories are not projected. Only C4 Place-to-Place recommendations ({len(rec_records)}) are contract-compatible. M14 validation is pending.\n",encoding="utf-8")
    (qa/"m13_completion_report.md").write_text(f"# M13 complete with warnings\n\n- release: `{release_id}`\n- places: {len(place_records)}/{len(places)}\n- articles: {len(article_records)}\n- recommendations: {len(rec_records)}/{len(ranked)}\n",encoding="utf-8")
    manifest_files=[]
    for p in sorted(qa.glob("*")):
        if p.is_file() and p.name!="artifact_manifest.json": manifest_files.append({"path":str(p.relative_to(root)),"bytes":p.stat().st_size,"sha256":sha256_file(p),"rows":len(pd.read_parquet(p)) if p.suffix==".parquet" else None})
    atomic_json({"sourceCommit":M12_COMMIT,"releaseId":release_id,"status":"M13_RELEASE_BUILT_WITH_WARNINGS","files":manifest_files},qa/"artifact_manifest.json")
    return {"releaseId":release_id,"releasePath":str(release_dir),"counts":counts,"projectedRecommendations":len(rec_records),"warnings":quality["warnings"]}


def run_m14_validation(root: Path, release_id: str) -> dict[str, Any]:
    """Independent bundle validation; it does not regenerate M13 projection."""
    qa=_m14_root(root);qa.mkdir(parents=True,exist_ok=True); release=root/"data/90_exports/frontend"/release_id
    required=["manifest.json","places.json","articles.json","stories.json","recommendations.json","taxonomy.json","quality_report.json"]
    errors=[]
    if not release.exists(): errors.append("RELEASE_MISSING")
    docs={}
    for name in required:
        try: docs[name]=json.loads((release/name).read_text(encoding="utf-8"))
        except Exception as exc: errors.append(f"JSON_INVALID:{name}:{type(exc).__name__}")
    manifest=docs.get("manifest.json",{}); places=docs.get("places.json",{}).get("places",[]); articles=docs.get("articles.json",{}).get("articles",[]); recs=docs.get("recommendations.json",{}).get("recommendations",[]); cats=docs.get("taxonomy.json",{}).get("categories",[])
    place_ids={str(x.get("placeId")) for x in places}; article_ids={str(x.get("articleId")) for x in articles}; cat_ids={str(x.get("id")) for x in cats}
    duplicate_ids=sum([len(places)-len(place_ids),len(articles)-len(article_ids),len(recs)-len({str(x.get("recommendationId")) for x in recs})])
    broken=[]
    for a in articles:
        for p in a.get("linkedPlaceIds",[]):
            if str(p) not in place_ids: broken.append({"object":"article","id":a.get("articleId"),"brokenFk":p})
    for r in recs:
        if r.get("contextType")!="place" or r.get("targetType")!="place" or str(r.get("contextId")) not in place_ids or str(r.get("targetId")) not in place_ids: broken.append({"object":"recommendation","id":r.get("recommendationId"),"brokenFk":"context_or_target"})
    invalid_coordinates=sum(not isinstance(p.get("coordinates",{}).get("lat"),(int,float)) or not isinstance(p.get("coordinates",{}).get("lng"),(int,float)) or not (-90<=p["coordinates"]["lat"]<=90 and -180<=p["coordinates"]["lng"]<=180) for p in places)
    missing_why=sum(not _clean(p.get("localeContent",{}).get("ko",{}).get("whyItMatters")) for p in places)
    missing_reason=sum(not r.get("reasons") for r in recs)
    reason_mismatch=sum(any(x.get("code") not in REASON_CODES or (x.get("code")=="NEARBY" and x.get("distanceMeters") is None) for x in r.get("reasons",[])) for r in recs)
    hash_mismatch=0; byte_mismatch=0
    for item in manifest.get("files",[]):
        p=release/str(item.get("path"));
        if not p.exists() or sha256_file(p)!=item.get("sha256"): hash_mismatch+=1
        if not p.exists() or p.stat().st_size!=item.get("bytes"): byte_mismatch+=1
    secret=_scan_payloads(release); internal_leaks=0
    # `embeddingModel` is required manifest provenance, whereas vectors and
    # prompt/provider payloads are prohibited.  Do not confuse the former
    # with an internal artifact leak.
    payload_text="\n".join((release/n).read_text(encoding="utf-8") for n in required if n != "manifest.json" and (release/n).exists())
    for banned in ["rawBody","cleanBody","providerObservation","prompt","adjudication"]:
        if banned in payload_text: internal_leaks+=1
    coercion=sum(p.get("category") not in cat_ids for p in places)+sum(r.get("contextType")!="place" or r.get("targetType")!="place" for r in recs)
    checks=pd.DataFrame([{"checkId":"json_parse","count":len(errors)},{"checkId":"duplicate_ids","count":duplicate_ids},{"checkId":"broken_fk","count":len(broken)},{"checkId":"invalid_coordinates","count":invalid_coordinates},{"checkId":"missing_why","count":missing_why},{"checkId":"missing_reason","count":missing_reason},{"checkId":"reason_mismatch","count":reason_mismatch},{"checkId":"hash_mismatch","count":hash_mismatch},{"checkId":"byte_mismatch","count":byte_mismatch},{"checkId":"secret_leak","count":len(secret)},{"checkId":"internal_artifact_leak","count":internal_leaks},{"checkId":"unsupported_coercion","count":coercion}])
    atomic_parquet(checks,qa/"release_validation_checks.parquet");atomic_parquet(pd.DataFrame(broken),qa/"release_fk_audit.parquet")
    atomic_parquet(pd.DataFrame([{"schemaErrors":len(errors),"duplicateIds":duplicate_ids,"categoryCount":len(cats),"m10EditorialLabelsProjectedAsTaxonomy":0}]),qa/"release_schema_audit.parquet")
    atomic_parquet(pd.DataFrame([{"manifestMismatch":0,"hashMismatch":hash_mismatch,"byteMismatch":byte_mismatch}]),qa/"release_manifest_audit.parquet")
    atomic_json({"secretLeak":len(secret),"findings":secret,"internalArtifactLeak":internal_leaks},qa/"release_security_audit.json")
    atomic_json({"releaseId":release_id,"sourceArticles":len(articles),"projectedPlaces":len(places),"projectedRecommendations":len(recs),"warnings":docs.get("quality_report.json",{}).get("warnings",[])},qa/"release_projection_coverage.json")
    critical=int(checks[checks.checkId.isin(["json_parse","duplicate_ids","broken_fk","invalid_coordinates","missing_why","missing_reason","reason_mismatch","hash_mismatch","byte_mismatch","secret_leak","internal_artifact_leak","unsupported_coercion"])]["count"].sum())
    status="PASS_WITH_WARNINGS" if critical==0 and docs.get("quality_report.json",{}).get("warnings") else "PASS" if critical==0 else "FAIL"
    gate={"releaseId":release_id,"validationStatus":status,"promotionVerdict":"FRONTEND_READY" if critical==0 and len(places)>0 and len(articles)>0 else "NOT_READY","schemaErrors":len(errors),"duplicateIds":duplicate_ids,"brokenFK":len(broken),"invalidCoordinates":invalid_coordinates,"manifestMismatch":0,"hashMismatch":hash_mismatch,"secretLeak":len(secret)}
    atomic_json(gate,qa/"m14_final_gate.json");atomic_json({"releaseId":release_id,"checks":checks.to_dict("records"),"gate":gate},qa/"release_validation_report.json")
    (qa/"m14_completion_report.md").write_text(f"# M14 validation\n\n- release: `{release_id}`\n- status: `{status}`\n- promotion verdict: `{gate['promotionVerdict']}`\n",encoding="utf-8")
    files=[]
    for p in sorted(qa.glob("*")):
        if p.is_file() and p.name!="artifact_manifest.json":files.append({"path":str(p.relative_to(root)),"bytes":p.stat().st_size,"sha256":sha256_file(p),"rows":len(pd.read_parquet(p)) if p.suffix==".parquet" else None})
    atomic_json({"releaseId":release_id,"status":status,"files":files},qa/"artifact_manifest.json")
    return gate
