"""M7 TourAPI router and checkpointed provider execution.

Only the Korea Tourism Organization KorService2 API is used here.  Google
Geocoding is intentionally absent from this stage: it is permitted only after
an accepted Tour identity with a complete address but invalid coordinates.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote

import pandas as pd
import requests

from src.geo.m7_query_repair import atomic_json, atomic_parquet, as_list, canon, sha256_file

ADAPTER_VERSION = "tourapi_korservice2@1"
BASE_URL = "https://apis.data.go.kr/B551011/KorService2"
CONTENT_TYPES = {"12": "ATTRACTION", "14": "CULTURAL_FACILITY", "15": "EVENT", "32": "LODGING", "38": "SHOPPING", "39": "FOOD"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_bytes(data: bytes, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False, suffix=".tmp") as handle:
        handle.write(data); handle.flush(); os.fsync(handle.fileno()); tmp=handle.name
    os.replace(tmp,path)


def _load_tour_key(repo_root: Path) -> str:
    p=repo_root / "config/local_provider_secrets.py"
    spec=importlib.util.spec_from_file_location("m7_local_provider_secrets", p)
    if spec is None or spec.loader is None:
        raise RuntimeError("CREDENTIAL_MISSING")
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    key=getattr(module,"TOUR_API_SERVICE_KEY",None)
    if not key:
        raise RuntimeError("CREDENTIAL_MISSING")
    # Data.go.kr keys are frequently stored already percent-encoded; decode
    # once before requests serializes the parameter.
    return unquote(str(key))


def build_routes(run_root: Path) -> pd.DataFrame:
    queue=pd.read_parquet(run_root/"provider_query_queue_repaired.parquet")
    rows=[]
    for row in queue.itertuples():
        route="NO_SAFE_PROVIDER_ROUTE"
        operation=None
        if row.providerStatus=="READY_NOT_EXECUTED":
            if row.entityType=="EVENT":
                route="TOUR_KEYWORD"; operation="searchKeyword2"
            elif row.entityType in {"PLACE_POI","VENUE"}:
                route="TOUR_KEYWORD"; operation="searchKeyword2"
        rows.append({"queryId":row.queryId,"entityCandidateId":row.entityCandidateId,"entityType":row.entityType,"queryText":row.queryText,"priority":row.priority,"route":route,"operation":operation,"googleFallbackEligible":False,"routeVersion":"m7_router@1"})
    frame=pd.DataFrame(rows); atomic_parquet(frame,run_root/"provider_resolution_plan.parquet")
    return frame


def _request_fingerprint(query_text: str, operation: str) -> str:
    return hashlib.sha256(f"{operation}|{query_text}|numOfRows=5|pageNo=1|arrange=A".encode()).hexdigest()


def _parse_items(payload: Any) -> tuple[str | None, str | None, list[dict[str,Any]]]:
    if not isinstance(payload,dict): return None,"NON_JSON",[]
    root=payload.get("response",payload)
    header=root.get("header",{}) if isinstance(root,dict) else {}
    code=str(header.get("resultCode")) if header else None
    body=root.get("body",{}) if isinstance(root,dict) else {}
    items=body.get("items",{}) if isinstance(body,dict) else {}
    values=items.get("item",[]) if isinstance(items,dict) else []
    if isinstance(values,dict): values=[values]
    return code, str(header.get("resultMsg")) if header else None, [x for x in values if isinstance(x,dict)]


def _token_overlap(left:str,right:str)->float:
    a=set(re.findall(r"[0-9A-Za-z가-힣]+",left));b=set(re.findall(r"[0-9A-Za-z가-힣]+",right))
    return len(a&b)/max(len(a|b),1)


def _score(row:dict[str,Any], item:dict[str,Any]) -> tuple[float,dict[str,float]]:
    title=str(item.get("title") or "")
    address=" ".join(str(item.get(k) or "") for k in ("addr1","addr2"))
    target=canon(row["queryText"]); name=canon(row["canonicalName"])
    exact=1.0 if name and (name==canon(title) or name in canon(title) or canon(title) in name) else 0.0
    overlap=_token_overlap(str(row["canonicalName"]), title)
    name_score=max(exact,overlap)
    region=str(row.get("regionHint") or "").strip()
    area=1.0 if not region else (1.0 if canon(region) in canon(address+" "+title) else 0.0)
    ctype=str(item.get("contenttypeid") or "")
    expected={"EVENT":{"15"},"VENUE":{"14","12","39"},"PLACE_POI":{"12","14","32","38","39"}}.get(row["entityType"],set())
    type_score=1.0 if ctype in expected else 0.0
    score=0.65*name_score+0.20*area+0.15*type_score
    return score,{"nameMatch":name_score,"areaMatch":area,"typeMatch":type_score}


def execute_p0(repo_root: Path, run_root: Path) -> tuple[pd.DataFrame,pd.DataFrame,pd.DataFrame]:
    routes=pd.read_parquet(run_root/"provider_resolution_plan.parquet")
    queue=pd.read_parquet(run_root/"provider_query_queue_repaired.parquet")
    p0=queue[(queue.providerStatus=="READY_NOT_EXECUTED")&(queue.priority=="P0")].merge(routes[["queryId","route","operation"]],on="queryId",how="left")
    key=_load_tour_key(repo_root)
    raw_root=repo_root/"data/10_raw/providers/tourapi/run_20260808_m7_geo"
    existing_ledger=run_root/"provider_call_ledger_p0.parquet"
    cached=pd.read_parquet(existing_ledger) if existing_ledger.exists() else pd.DataFrame()
    observations=[]; ledger=[]; decisions=[]
    for row in p0.to_dict("records"):
        fp=_request_fingerprint(str(row["queryText"]),str(row["operation"]))
        prior=cached[(cached.queryId==row["queryId"])&(cached.requestFingerprint==fp)&(cached.success==True)] if len(cached) else pd.DataFrame()
        raw_path=raw_root/f"{row['queryId']}_{fp}.json"
        if len(prior) or raw_path.exists():
            # Re-read the traceable raw payload; never reissue a success call.
            data=raw_path.read_bytes(); payload=json.loads(data)
            result_code,_,_=_parse_items(payload); status=200; cache_hit=True
            if len(prior):
                prior_row=prior.iloc[-1].to_dict(); prior_row["cacheHit"]=True; ledger.append(prior_row)
            else:
                ledger.append({"callId":f"p0_{row['queryId']}","queryId":row["queryId"],"provider":"TOUR_API_KOR_SERVICE2","operation":row["operation"],"attempt":0,"startedAt":utc_now(),"finishedAt":utc_now(),"httpStatus":status,"providerResultCode":result_code,"responseBytes":len(data),"responseHash":hashlib.sha256(data).hexdigest(),"requestFingerprint":fp,"cacheHit":True,"success":True,"errorClass":None})
        else:
            params={"MobileOS":"ETC","MobileApp":"MBN_GUIDE","_type":"json","pageNo":1,"numOfRows":5,"arrange":"A","keyword":row["queryText"],"serviceKey":key}
            started=utc_now(); response=None; error=None
            for attempt in range(1,4):
                try:
                    response=requests.get(f"{BASE_URL}/{row['operation']}",params=params,timeout=25)
                    break
                except requests.RequestException as exc:
                    error=type(exc).__name__
                    if attempt<3: time.sleep(2**(attempt-1))
            finished=utc_now()
            if response is None:
                ledger.append({"callId":f"p0_{row['queryId']}","queryId":row["queryId"],"provider":"TOUR_API_KOR_SERVICE2","operation":row["operation"],"attempt":3,"startedAt":started,"finishedAt":finished,"httpStatus":None,"providerResultCode":None,"responseBytes":0,"responseHash":None,"requestFingerprint":fp,"cacheHit":False,"success":False,"errorClass":error or "TRANSPORT_ERROR"})
                decisions.append({"queryId":row["queryId"],"entityCandidateId":row["entityCandidateId"],"resolutionStatus":"ERROR","resolutionScore":None,"selectedProviderObservationId":None,"mapEligible":False,"reasonCode":error or "TRANSPORT_ERROR"})
                continue
            status=response.status_code; data=response.content; raw_hash=hashlib.sha256(data).hexdigest(); _atomic_bytes(data,raw_root/f"{row['queryId']}_{fp}.json")
            try: payload=response.json()
            except ValueError: payload={}
            result_code,_,_= _parse_items(payload); cache_hit=False
            ledger.append({"callId":f"p0_{row['queryId']}","queryId":row["queryId"],"provider":"TOUR_API_KOR_SERVICE2","operation":row["operation"],"attempt":1,"startedAt":started,"finishedAt":finished,"httpStatus":status,"providerResultCode":result_code,"responseBytes":len(data),"responseHash":raw_hash,"requestFingerprint":fp,"cacheHit":cache_hit,"success":status==200,"errorClass":None if status==200 else "HTTP_ERROR"})
        if status in {401,403}:
            raise RuntimeError("TOUR_API_AUTH_FAILURE")
        if status != 200:
            decisions.append({"queryId":row["queryId"],"entityCandidateId":row["entityCandidateId"],"resolutionStatus":"ERROR","resolutionScore":None,"selectedProviderObservationId":None,"mapEligible":False,"reasonCode":"HTTP_ERROR"}); continue
        code,msg,items=_parse_items(payload)
        if code not in {None,"0000","0"}:
            decisions.append({"queryId":row["queryId"],"entityCandidateId":row["entityCandidateId"],"resolutionStatus":"ERROR","resolutionScore":None,"selectedProviderObservationId":None,"mapEligible":False,"reasonCode":f"TOUR_{code}"}); continue
        scored=[]
        for i,item in enumerate(items,1):
            score,components=_score(row,item); oid=f"obs_{row['queryId']}_{i:02d}"
            scored.append((score,oid,item,components))
            observations.append({"providerObservationId":oid,"queryId":row["queryId"],"entityCandidateId":row["entityCandidateId"],"provider":"TOUR_API_KOR_SERVICE2","operation":row["operation"],"providerContentId":str(item.get("contentid") or "") or None,"title":item.get("title"),"addr1":item.get("addr1"),"addr2":item.get("addr2"),"mapx":item.get("mapx"),"mapy":item.get("mapy"),"contenttypeid":str(item.get("contenttypeid") or "") or None,"lclsSystm1":item.get("lclsSystm1"),"lclsSystm2":item.get("lclsSystm2"),"lclsSystm3":item.get("lclsSystm3"),"matchScore":score,"scoreComponents":components})
        scored.sort(key=lambda x:(-x[0],x[1]))
        if not scored: status_name="NOT_FOUND"; best=None; reason="NO_PROVIDER_CANDIDATE"; score=None
        else:
            score,best,item,parts=scored[0]; margin=score-(scored[1][0] if len(scored)>1 else 0)
            status_name="RESOLVED" if score>=.80 and margin>=.12 else "AMBIGUOUS"; reason="DETERMINISTIC_MATCH" if status_name=="RESOLVED" else "LOW_SCORE_OR_MARGIN"
        decisions.append({"queryId":row["queryId"],"entityCandidateId":row["entityCandidateId"],"resolutionStatus":status_name,"resolutionScore":score,"selectedProviderObservationId":best,"mapEligible":False,"reasonCode":reason})
    obs=pd.DataFrame(observations); led=pd.DataFrame(ledger); dec=pd.DataFrame(decisions)
    atomic_parquet(obs,run_root/"provider_observations_p0.parquet");atomic_parquet(led,run_root/"provider_call_ledger_p0.parquet");atomic_parquet(dec,run_root/"resolution_decisions_p0.parquet")
    return obs,led,dec


def execute_expanded_pilot(repo_root: Path, run_root: Path) -> tuple[pd.DataFrame,pd.DataFrame,pd.DataFrame,pd.DataFrame]:
    """Run P1 plus deterministic P2/P3 samples through the same P0-safe adapter.

    A stage-local queue reuses the idempotent call implementation without
    changing canonical repaired priorities or triggering previously-run P0s.
    """
    queue=pd.read_parquet(run_root/"provider_query_queue_repaired.parquet")
    ready=queue[queue.providerStatus.eq("READY_NOT_EXECUTED")].copy()
    p1=ready[ready.priority.eq("P1")]
    p2=ready[ready.priority.eq("P2")].sort_values(["entityType","verificationConfidence","entityCandidateId"],ascending=[True,False,True]).head(30)
    p3=ready[ready.priority.eq("P3")].sort_values("entityCandidateId").head(15)
    selected=pd.concat([p1,p2,p3],ignore_index=True).drop_duplicates("queryId")
    selected["expandedSourcePriority"]=selected.priority
    selected["priority"]="P0"  # stage-local selection token for execute_p0 only
    work=run_root/"expanded_pilot_work"; work.mkdir(parents=True,exist_ok=True)
    atomic_parquet(selected,work/"provider_query_queue_repaired.parquet")
    plan=build_routes(work)
    obs,ledger,dec=execute_p0(repo_root,work)
    # Restore original tier in every published expanded artifact.
    lookup=selected.set_index("queryId")["expandedSourcePriority"].to_dict()
    dec["expandedSourcePriority"]=dec.queryId.map(lookup)
    obs["expandedSourcePriority"]=obs.queryId.map(lookup) if len(obs) else pd.Series(dtype="object")
    ledger["expandedSourcePriority"]=ledger.queryId.map(lookup) if len(ledger) else pd.Series(dtype="object")
    atomic_parquet(selected,run_root/"expanded_pilot_selection.parquet")
    atomic_parquet(obs,run_root/"provider_observations_expanded.parquet")
    atomic_parquet(ledger,run_root/"provider_call_ledger_expanded.parquet")
    atomic_parquet(dec,run_root/"resolution_decisions_expanded.parquet")
    return selected,obs,ledger,dec


def execute_remaining_queue(repo_root: Path, run_root: Path) -> tuple[pd.DataFrame,pd.DataFrame,pd.DataFrame,pd.DataFrame]:
    """Complete the evidence-safe queue after both pilot gates have passed."""
    queue=pd.read_parquet(run_root/"provider_query_queue_repaired.parquet")
    expanded=pd.read_parquet(run_root/"expanded_pilot_selection.parquet")
    p0=pd.read_parquet(run_root/"resolution_decisions_p0.parquet")
    used=set(expanded.queryId)|set(p0.queryId)
    selected=queue[(queue.providerStatus=="READY_NOT_EXECUTED")&(~queue.queryId.isin(used))].copy()
    selected["fullSourcePriority"]=selected.priority; selected["priority"]="P0"
    work=run_root/"full_queue_work";work.mkdir(parents=True,exist_ok=True)
    atomic_parquet(selected,work/"provider_query_queue_repaired.parquet");build_routes(work)
    obs,ledger,dec=execute_p0(repo_root,work)
    lookup=selected.set_index("queryId")["fullSourcePriority"].to_dict()
    for frame in (obs,ledger,dec): frame["fullSourcePriority"]=frame.queryId.map(lookup) if len(frame) else pd.Series(dtype="object")
    atomic_parquet(selected,run_root/"full_queue_selection.parquet");atomic_parquet(obs,run_root/"provider_observations_full.parquet");atomic_parquet(ledger,run_root/"provider_call_ledger_full.parquet");atomic_parquet(dec,run_root/"resolution_decisions_full.parquet")
    return selected,obs,ledger,dec
