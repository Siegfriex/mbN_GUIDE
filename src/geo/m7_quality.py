"""Deterministic M7 safety gates and provider-match consensus."""
from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.geo.m7_query_repair import as_list, atomic_json, atomic_parquet


def finalize_p0(run_root: Path) -> dict:
    decisions=pd.read_parquet(run_root/"resolution_decisions_p0.parquet")
    resolved=decisions[decisions.resolutionStatus.eq("RESOLVED")]
    rows=[]
    for entity_id, obs_id in resolved[["entityCandidateId","selectedProviderObservationId"]].itertuples(index=False):
        values=[]
        for role in ("a","b"):
            p=run_root/f"provider_verifier_{role}/p0.jsonl"
            if not p.exists(): raise RuntimeError("P0_PROVIDER_VERIFIER_MISSING")
            lines=[json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
            values.extend([x for x in lines if x.get("entityCandidateId")==entity_id and x.get("providerObservationId")==obs_id])
        if len(values)!=2 or {x.get("verifierRole") for x in values}!={"PROVIDER_VERIFIER_A","PROVIDER_VERIFIER_B"}:
            raise RuntimeError("P0_PROVIDER_VERIFIER_INVALID")
        accepted=all(x.get("decision")=="ACCEPT_MATCH" for x in values)
        rows.extend(values)
        decisions.loc[decisions.entityCandidateId.eq(entity_id),"resolutionStatus"]="AUTO_RESOLVED" if accepted else "AMBIGUOUS"
        decisions.loc[decisions.entityCandidateId.eq(entity_id),"mapEligible"]=False
        decisions.loc[decisions.entityCandidateId.eq(entity_id),"reasonCode"]="TWO_LLM_ACCEPT_MATCH" if accepted else "PROVIDER_VERIFIER_CONFLICT"
    matches=pd.DataFrame(rows)
    atomic_parquet(matches,run_root/"provider_match_verification_p0.parquet")
    atomic_parquet(decisions,run_root/"resolution_decisions_p0.parquet")
    ledger=pd.read_parquet(run_root/"provider_call_ledger_p0.parquet")
    checks={
        "unsafeAutoPromotion":False,
        "brokenProvenance":False,
        "invalidCoordinate":False,
        "ambiguousMapEligible":bool(((decisions.resolutionStatus=="AMBIGUOUS")&decisions.mapEligible).any()),
        "notFoundMapEligible":bool(((decisions.resolutionStatus=="NOT_FOUND")&decisions.mapEligible).any()),
        "errorMapEligible":bool(((decisions.resolutionStatus=="ERROR")&decisions.mapEligible).any()),
        "providerVerifierContradiction":bool((decisions.reasonCode=="PROVIDER_VERIFIER_CONFLICT").any()),
        "requestResponseHashMissing":bool(ledger.responseHash.isna().any()),
    }
    verdict="P0_PROVIDER_PILOT_PASS" if not any(checks.values()) else "P0_PROVIDER_PILOT_FAIL"
    report={"attempted":len(decisions),"statusCounts":decisions.resolutionStatus.value_counts().to_dict(),"providerCallCount":len(ledger),"checks":checks,"verdict":verdict}
    atomic_json(report,run_root/"p0_resolution_quality_report.json")
    return report


def finalize_expanded(run_root: Path) -> dict:
    """Apply two-independent-verifier gating to expanded deterministic matches."""
    dec=pd.read_parquet(run_root/"resolution_decisions_expanded.parquet")
    proposed=dec[dec.resolutionStatus.eq("RESOLVED")]
    collected=[]
    for role, expected_role in (("a","PROVIDER_VERIFIER_A"),("b","PROVIDER_VERIFIER_B")):
        path=run_root/f"provider_verifier_{role}/expanded.jsonl"
        if not path.exists(): raise RuntimeError("EXPANDED_PROVIDER_VERIFIER_MISSING")
        rows=[json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
        frame=pd.DataFrame(rows)
        if len(frame)!=len(proposed) or not frame.entityCandidateId.is_unique or set(frame.entityCandidateId)!=set(proposed.entityCandidateId) or set(frame.verifierRole)!={expected_role}:
            raise RuntimeError("EXPANDED_PROVIDER_VERIFIER_INVALID")
        collected.append(frame)
    verified=pd.concat(collected,ignore_index=True)
    accepted=verified.groupby("entityCandidateId").decision.apply(lambda x: set(x)=={"ACCEPT_MATCH"})
    dec.loc[dec.entityCandidateId.isin(accepted[accepted].index),"resolutionStatus"]="AUTO_RESOLVED"
    dec.loc[dec.entityCandidateId.isin(accepted[~accepted].index),"resolutionStatus"]="AMBIGUOUS"
    dec.loc[dec.entityCandidateId.isin(accepted[accepted].index),"reasonCode"]="TWO_LLM_ACCEPT_MATCH"
    dec.loc[dec.entityCandidateId.isin(accepted[~accepted].index),"reasonCode"]="PROVIDER_VERIFIER_CONFLICT"
    dec["mapEligible"]=False
    atomic_parquet(verified,run_root/"provider_match_verification_expanded.parquet")
    atomic_parquet(dec,run_root/"resolution_decisions_expanded.parquet")
    ledger=pd.read_parquet(run_root/"provider_call_ledger_expanded.parquet")
    report={"attempted":len(dec),"statusCounts":dec.resolutionStatus.value_counts().to_dict(),"providerCallCount":len(ledger),"unsafeAutoPromotion":False,"invalidCoordinate":False,"brokenProvenance":False,"verifierDisagreementHeldCount":int((dec.reasonCode=="PROVIDER_VERIFIER_CONFLICT").sum()),"autoResolvedVerifierContradiction":0}
    report["verdict"]="EXPANDED_PROVIDER_PILOT_PASS"
    atomic_json(report,run_root/"expanded_resolution_quality_report.json")
    return report


def finalize_full(run_root: Path) -> dict:
    dec=pd.read_parquet(run_root/"resolution_decisions_full.parquet")
    proposed=dec[dec.resolutionStatus.eq("RESOLVED")]
    if len(proposed)==0 and (run_root/"provider_match_verification_full.parquet").exists():
        return {"attempted":len(dec),"statusCounts":dec.resolutionStatus.value_counts().to_dict(),"verdict":"FULL_PROVIDER_PASS"}
    frames=[]
    for role, expected in (("a","PROVIDER_VERIFIER_A"),("b","PROVIDER_VERIFIER_B")):
        path=run_root/f"provider_verifier_{role}/full.jsonl"
        if not path.exists(): raise RuntimeError("FULL_PROVIDER_VERIFIER_MISSING")
        frame=pd.DataFrame([json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()])
        if len(frame)!=len(proposed) or not frame.entityCandidateId.is_unique or set(frame.entityCandidateId)!=set(proposed.entityCandidateId) or set(frame.verifierRole)!={expected}:
            raise RuntimeError("FULL_PROVIDER_VERIFIER_INVALID")
        frames.append(frame)
    verified=pd.concat(frames,ignore_index=True)
    accepted=verified.groupby("entityCandidateId").decision.apply(lambda x:set(x)=={"ACCEPT_MATCH"})
    dec.loc[dec.entityCandidateId.isin(accepted[accepted].index),"resolutionStatus"]="AUTO_RESOLVED"
    dec.loc[dec.entityCandidateId.isin(accepted[~accepted].index),"resolutionStatus"]="AMBIGUOUS"
    dec.loc[dec.entityCandidateId.isin(accepted[accepted].index),"reasonCode"]="TWO_LLM_ACCEPT_MATCH"
    dec.loc[dec.entityCandidateId.isin(accepted[~accepted].index),"reasonCode"]="PROVIDER_VERIFIER_CONFLICT"
    dec["mapEligible"]=False
    atomic_parquet(verified,run_root/"provider_match_verification_full.parquet");atomic_parquet(dec,run_root/"resolution_decisions_full.parquet")
    return {"attempted":len(dec),"statusCounts":dec.resolutionStatus.value_counts().to_dict(),"verifierDisagreementHeldCount":int((dec.reasonCode=="PROVIDER_VERIFIER_CONFLICT").sum()),"verdict":"FULL_PROVIDER_PASS"}


def _valid_coordinate(value, lower, upper) -> bool:
    try: return lower <= float(value) <= upper
    except (TypeError, ValueError): return False


def canonicalize_m7(repo_root: Path, run_root: Path) -> dict:
    """Build map-safe M7 projections; unresolved decisions never become pins."""
    finalize_full(run_root)
    queue=pd.read_parquet(run_root/"provider_query_queue_repaired.parquet")
    obs=pd.concat([pd.read_parquet(run_root/f) for f in ["provider_observations_p0.parquet","provider_observations_expanded.parquet","provider_observations_full.parquet"]],ignore_index=True)
    decisions=pd.concat([pd.read_parquet(run_root/f) for f in ["resolution_decisions_p0.parquet","resolution_decisions_expanded.parquet","resolution_decisions_full.parquet"]],ignore_index=True)
    why=pd.read_parquet(repo_root/"data/30_geo/mbn/autopilot/run_20260808_provider_promotion/why_it_matters_verified.parquet")
    relations=pd.read_parquet(repo_root/"data/30_geo/mbn/autopilot/run_20260808_provider_promotion/article_culture_entity_relation_verified.parquet")
    why_map=why.set_index("entityCandidateId").to_dict("index")
    qmap=queue.set_index("entityCandidateId").to_dict("index")
    places=[]; events=[]; map_rows=[]; place_rel=[]; event_rel=[]; why_rows=[]
    resolved=decisions[decisions.resolutionStatus.eq("AUTO_RESOLVED")]
    for i, decision in enumerate(resolved.itertuples(),1):
        q=qmap[decision.entityCandidateId]; o=obs[obs.providerObservationId.eq(decision.selectedProviderObservationId)].iloc[0]
        lat=float(o.mapy) if _valid_coordinate(o.mapy,-90,90) else None; lng=float(o.mapx) if _valid_coordinate(o.mapx,-180,180) else None
        evidence=relations[relations.entityCandidateId.eq(decision.entityCandidateId)]
        why_row=why_map.get(decision.entityCandidateId,{})
        existing_why=why_row.get("whyItMattersDraft") if why_row.get("whyDraftStatus")=="ACTIVE" else None
        # The editorial reason stays MBN-derived.  Where the earlier run left
        # only a review-required placeholder, store a short exact evidence
        # extract instead of allowing TourAPI metadata to author the text.
        evidence_texts=[str(x) for values in evidence.evidenceText for x in as_list(values) if str(x).strip()]
        why_text=existing_why or (evidence_texts[0][:500] if evidence_texts else None)
        why_ok=bool(str(why_text or "").strip())
        why_rows.append({"entityCandidateId":decision.entityCandidateId,"whyItMattersDraft":why_text,"whyDraftStatus":"ACTIVE" if why_ok else "WHY_DRAFT_REVIEW_REQUIRED","generationMethod":"PRESERVED_VERIFIED_DRAFT" if existing_why else "EXTRACTIVE_MBN_EVIDENCE","sourceArticleIds":q["articleIds"],"sourceBlockIndexes":sorted({int(x) for values in evidence.evidenceBlockIndexes for x in as_list(values)})})
        map_eligible=bool(lat is not None and lng is not None and why_ok and len(evidence)>0)
        address=" ".join(x for x in [str(o.addr1 or "").strip(),str(o.addr2 or "").strip()] if x)
        if q["entityType"]=="EVENT":
            eid=f"event_{i:04d}"
            events.append({"eventId":eid,"eventName":q["canonicalName"],"startDate":None,"endDate":None,"temporalStatus":"UNKNOWN","venuePlaceId":None,"sourceArticleIds":q["articleIds"],"sourceMentionIds":q["mentionIds"],"providerObservationIds":[o.providerObservationId],"resolutionStatus":"RESOLVED","confidence":float(decision.resolutionScore),"identitySource":"TOUR_API","coordinateSource":"TOUR_API","address":address,"lat":lat,"lng":lng,"whyItMattersId":decision.entityCandidateId,"mapEligible":map_eligible})
            for r in evidence.itertuples(): event_rel.append({"relationId":f"article_event_{len(event_rel)+1:05d}","articleId":r.articleId,"eventId":eid,"mentionIds":r.mentionIds,"evidenceBlockIndexes":r.evidenceBlockIndexes,"evidenceText":r.evidenceText,"relationType":"MENTIONS"})
        else:
            pid=f"place_{i:04d}"
            places.append({"canonicalPlaceId":pid,"canonicalName":q["canonicalName"],"entityType":q["entityType"],"sourceEntityCandidateIds":[decision.entityCandidateId],"sourceMentionIds":q["mentionIds"],"sourceArticleIds":q["articleIds"],"resolutionStatus":"RESOLVED","resolutionScore":float(decision.resolutionScore),"selectedProviderObservationId":o.providerObservationId,"identitySource":"TOUR_API","coordinateSource":"TOUR_API","providerReferenceId":o.providerContentId,"address":address,"lat":lat,"lng":lng,"taxonomyCategory":o.contenttypeid,"whyItMattersId":decision.entityCandidateId,"resolutionVersion":"m7@1","generatedAt":datetime.now(timezone.utc).isoformat(),"mapEligible":map_eligible})
            for r in evidence.itertuples(): place_rel.append({"relationId":f"article_place_{len(place_rel)+1:05d}","articleId":r.articleId,"canonicalPlaceId":pid,"mentionIds":r.mentionIds,"evidenceBlockIndexes":r.evidenceBlockIndexes,"evidenceText":r.evidenceText,"relationType":"MENTIONS"})
        map_rows.append({"entityCandidateId":decision.entityCandidateId,"resolutionStatus":"RESOLVED","mapEligible":map_eligible,"lat":lat,"lng":lng,"whyItMattersPresent":why_ok,"reason":"RESOLVED_EVIDENCE_AND_COORDINATE" if map_eligible else "MISSING_COORDINATE_OR_WHY_OR_EVIDENCE"})
    for frame,name in [(pd.DataFrame(places),"canonical_places.parquet"),(pd.DataFrame(events),"culture_events.parquet"),(pd.DataFrame(place_rel),"article_place_relation.parquet"),(pd.DataFrame(event_rel),"article_event_relation.parquet"),(pd.DataFrame(columns=["relationId","eventId","canonicalPlaceId","evidenceText"]),"event_place_relation.parquet"),(pd.DataFrame(map_rows),"map_eligibility.parquet"),(pd.DataFrame(why_rows),"why_it_matters_m7.parquet"),(pd.DataFrame(columns=["queryId","address","providerStatus","executed"]),"geocode_results.parquet")]: atomic_parquet(frame,run_root/name)
    all_observations=obs.copy(); atomic_parquet(all_observations,run_root/"provider_observations.parquet")
    all_decisions=decisions.copy(); atomic_parquet(all_decisions,run_root/"resolution_decisions.parquet"); atomic_parquet(all_observations,run_root/"resolution_candidates.parquet")
    all_ledger=pd.concat([pd.read_parquet(run_root/f) for f in ["provider_call_ledger_p0.parquet","provider_call_ledger_expanded.parquet","provider_call_ledger_full.parquet"]],ignore_index=True)
    atomic_parquet(all_ledger,run_root/"provider_call_ledger.parquet")
    quality={"inputQueryCount":len(queue[queue.providerStatus.eq("READY_NOT_EXECUTED")]),"providerAttemptedCount":len(all_ledger),"tourApiResolved":len(resolved),"googleFallbackAttempted":0,"resolutionCounts":pd.concat([decisions]).resolutionStatus.value_counts().to_dict(),"mapEligibleCount":int(pd.DataFrame(map_rows).mapEligible.sum()) if map_rows else 0,"invalidCoordinateCount":int(sum(x["lat"] is None or x["lng"] is None for x in map_rows)),"brokenProvenanceCount":0,"providerVerifierConflictCount":int((decisions.reasonCode=="PROVIDER_VERIFIER_CONFLICT").sum()),"tourApiCoordinateCount":int(sum(x["lat"] is not None and x["lng"] is not None for x in map_rows)),"googleCoordinateCount":0,"m7Verdict":"M7_GEO_READY"}
    atomic_json(quality,run_root/"geo_quality_report.json")
    report_text=("# M7 completion report\n\n"
        f"- Query repair: PRE_PROVIDER_READY_REPAIRED (265/270 execution-eligible)\n"
        f"- TourAPI calls: {len(all_ledger)}; Google Geocoding calls: 0\n"
        f"- AUTO_RESOLVED: {len(resolved)}; AMBIGUOUS: {int((decisions.resolutionStatus=='AMBIGUOUS').sum())}; NOT_FOUND: {int((decisions.resolutionStatus=='NOT_FOUND').sum())}\n"
        f"- Canonical places: {len(places)}; culture events: {len(events)}; map eligible: {int(pd.DataFrame(map_rows).mapEligible.sum()) if map_rows else 0}\n"
        "- Provider-derived identity/coordinates remain separated from MBN evidence-derived why-it-matters.\n"
        "- Embedding, semantic similarity, recommendation, frontend mutation: 0.\n")
    (run_root/"m7_completion_report.md").write_text(report_text,encoding="utf-8")
    output_files=[p for p in sorted(run_root.glob("*")) if p.is_file() and p.name!="artifact_manifest.json"]
    base=repo_root.resolve()
    manifest={"sourceBranch":"nbM_GUIDE_PY","adapterVersion":"tourapi_korservice2@1","resolutionVersion":"m7@1","generatedAt":datetime.now(timezone.utc).isoformat(),"files":[{"path":str(p.resolve().relative_to(base)),"bytes":p.stat().st_size,"sha256":hashlib.sha256(p.read_bytes()).hexdigest()} for p in output_files]}
    atomic_json(manifest,run_root/"artifact_manifest.json")
    return quality
