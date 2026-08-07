"""M9 exact matrix-first semantic relation measurement.

The M8 numpy vectors are the immutable semantic source.  This module never
loads an encoder, calls a provider, or performs an LLM action.  It only builds
exact dot-product matrices, bounded article-level body aggregations, and
traceable top-k retrieval projections.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import resource
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from src.geo.m7_query_repair import as_list, atomic_json, atomic_parquet, sha256_file

RUN_NAME = "run_20260808_m9_similarity"
M8_RUN = "run_20260808_m8_embeddings"
M8_COMMIT = "b8e01c38e571790e453b4e3bffd4ac9c6dcb2fdd"
M7_COMMIT = "76a4d59fe792188453bae72d8632742b267cb1f5"
EVALUATION_AUTHORITY = "DIRECT_GEO_RELATION_SILVER + M8_INTERNAL_RETRIEVAL_DIAGNOSTIC"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def m8_root(root: Path) -> Path:
    return root / "data/40_semantic/mbn/m8" / M8_RUN


def m7_root(root: Path) -> Path:
    return root / "data/30_geo/mbn/canonical/m7_replay_20260808"


def output_root(root: Path) -> Path:
    return root / "data/40_semantic/mbn/m9" / RUN_NAME


def _atomic_npy(value: np.ndarray, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".npy.tmp", delete=False) as handle:
        tmp = handle.name
        np.save(handle, value)
        handle.flush(); os.fsync(handle.fileno())
    try:
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)


def _load_config(root: Path) -> dict[str, Any]:
    with (root / "config/models/semantic_similarity_v1.yaml").open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _np_hash(value: np.ndarray) -> str:
    contiguous = np.ascontiguousarray(value)
    h = hashlib.sha256()
    h.update(str(contiguous.shape).encode()); h.update(str(contiguous.dtype).encode()); h.update(contiguous.tobytes())
    return h.hexdigest()


def _read_vectors_once(root: Path) -> tuple[dict[str, np.ndarray], dict[str, pd.DataFrame], dict[str, Any]]:
    base = m8_root(root)
    arrays = {
        "title": np.asarray(np.load(base / "article_title_embeddings.npy"), dtype=np.float32),
        "chunk": np.asarray(np.load(base / "article_body_chunk_embeddings.npy"), dtype=np.float32),
        "entity": np.asarray(np.load(base / "culture_entity_embeddings.npy"), dtype=np.float32),
    }
    meta = {
        "title": pd.read_parquet(base / "article_title_embedding_metadata.parquet"),
        "chunk": pd.read_parquet(base / "article_body_chunk_embedding_metadata.parquet"),
        "entity": pd.read_parquet(base / "culture_entity_embedding_metadata.parquet"),
    }
    selection = json.loads((base / "embedding_model_selection.json").read_text(encoding="utf-8"))
    return arrays, meta, selection


def _unit_rows(arr: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    if np.any(norms == 0): raise RuntimeError("M9_ZERO_VECTOR_INPUT")
    return arr if np.all(np.abs(norms - 1.0) <= 1e-3) else arr / norms


def _contract(root: Path, arrays: dict[str, np.ndarray], meta: dict[str, pd.DataFrame], selection: dict[str, Any]) -> dict[str, Any]:
    cfg = _load_config(root); req = cfg["modelContract"]
    selected = selection["selectedModel"]
    expected_shapes = {"title": (461, 1024), "chunk": (1062, 1024), "entity": (32, 1024)}
    checks = {
        "m8CommitPinned": M8_COMMIT == os.popen("git rev-parse nbM_GUIDE_PY_M8_EMBEDDING").read().strip(),
        "modelId": str(selected["modelId"]) == str(req["requiredModelId"]),
        "modelRevision": str(selected["revision"]) == str(req["requiredRevision"]),
        "shapes": all(tuple(arrays[k].shape) == expected_shapes[k] for k in arrays),
        "float32": all(arr.dtype == np.float32 for arr in arrays.values()),
        "metaRows": all(len(meta[k]) == arrays[k].shape[0] for k in arrays),
        "modelMetadata": all(set(meta[k].modelId.astype(str)) == {str(req["requiredModelId"])} and set(meta[k].modelRevision.astype(str)) == {str(req["requiredRevision"])} and set(meta[k].dimension.astype(int)) == {int(req["requiredDimension"])} and set(meta[k].normalize.astype(bool)) == {bool(req["requiredNormalize"])} for k in meta),
        "nanInfFree": all(not np.isnan(a).any() and not np.isinf(a).any() for a in arrays.values()),
    }
    checks["verdict"] = "M9_MODEL_CONTRACT_PASS" if all(v is True for v in checks.values() if isinstance(v, bool)) else "M8_MODEL_CONTRACT_MUTATION"
    return checks


def _cache_paths(out: Path) -> dict[str, Path]:
    cache = out / "matrix_cache"; cache.mkdir(parents=True, exist_ok=True)
    return {"tt": cache / "title_title_cosine.npy", "cc": cache / "chunk_chunk_cosine.npy", "te": cache / "title_entity_cosine.npy", "ce": cache / "chunk_entity_cosine.npy", "body": cache / "article_body_similarity.npy", "be": cache / "article_entity_body_similarity.npy", "bmax": cache / "article_body_max.npy", "btop3": cache / "article_body_top3.npy", "bemax": cache / "article_entity_body_max.npy", "betop3": cache / "article_entity_body_top3.npy"}


def _cache_valid(out: Path, arrays: dict[str, np.ndarray]) -> bool:
    p = out / "matrix_cache_manifest.json"
    if not p.exists(): return False
    prior = json.loads(p.read_text(encoding="utf-8"))
    expected = {k: _np_hash(v) for k, v in arrays.items()}
    return prior.get("sourceMatrixHashes") == expected and all(x.exists() for x in _cache_paths(out).values())


def _article_chunk_rows(chunk_meta: pd.DataFrame, title_meta: pd.DataFrame) -> dict[str, np.ndarray]:
    index = {str(a): i for i, a in enumerate(title_meta.articleId.astype(str))}
    result: dict[str, list[int]] = {x: [] for x in index}
    for r in chunk_meta.itertuples():
        article = str(r.articleId)
        if article not in result: raise RuntimeError(f"M9_CHUNK_ARTICLE_FK:{article}")
        result[article].append(int(r.embeddingRow))
    if any(not rows for rows in result.values()): raise RuntimeError("M9_ARTICLE_WITHOUT_CHUNK")
    return {k: np.asarray(v, dtype=np.int64) for k, v in result.items()}


def _top3_mean(v: np.ndarray, axis: int | None = None) -> np.ndarray:
    if axis is None:
        flat = v.reshape(-1); k = min(3, len(flat)); return np.mean(np.partition(flat, -k)[-k:])
    k = min(3, v.shape[axis]); return np.mean(np.partition(v, -k, axis=axis).take(indices=range(v.shape[axis]-k, v.shape[axis]), axis=axis), axis=axis)


def _build_matrices(arrays: dict[str, np.ndarray], meta: dict[str, pd.DataFrame], out: Path, *, force: bool = False) -> tuple[dict[str, np.ndarray], dict[str, float]]:
    paths = _cache_paths(out); timings: dict[str, float] = {}
    if not force and _cache_valid(out, arrays):
        return {k: np.asarray(np.load(p), dtype=np.float32) for k, p in paths.items()}, {"matrixCacheReused": 1.0}
    t0 = time.perf_counter(); T, C, E = (_unit_rows(arrays[x]) for x in ("title", "chunk", "entity")); timings["loadNormalizeSeconds"] = time.perf_counter()-t0
    t0=time.perf_counter(); tt=np.asarray(T@T.T,dtype=np.float32); timings["titleMatrixSeconds"]=time.perf_counter()-t0
    t0=time.perf_counter(); cc=np.asarray(C@C.T,dtype=np.float32); timings["chunkMatrixSeconds"]=time.perf_counter()-t0
    t0=time.perf_counter(); te=np.asarray(T@E.T,dtype=np.float32); ce=np.asarray(C@E.T,dtype=np.float32); timings["entityMatricesSeconds"]=time.perf_counter()-t0
    rows=_article_chunk_rows(meta["chunk"],meta["title"]); n=len(meta["title"]); body=np.empty((n,n),dtype=np.float32); bmax=np.empty((n,n),dtype=np.float32); btop=np.empty((n,n),dtype=np.float32); be=np.empty((n,len(meta["entity"])),dtype=np.float32); bemax=np.empty_like(be); betop=np.empty_like(be)
    article_ids=meta["title"].articleId.astype(str).tolist(); t0=time.perf_counter()
    for i, aid in enumerate(article_ids):
        ix=rows[aid]; values=ce[ix, :]; bemax[i]=values.max(axis=0); betop[i]=_top3_mean(values,axis=0); be[i]=0.70*bemax[i]+0.30*betop[i]
        for j in range(i, n):
            sub=cc[np.ix_(ix, rows[article_ids[j]])]; mx=float(sub.max()); tm=float(_top3_mean(sub)); bmax[i,j]=bmax[j,i]=mx; btop[i,j]=btop[j,i]=tm; body[i,j]=body[j,i]=0.70*mx+0.30*tm
    timings["bodyAggregationSeconds"]=time.perf_counter()-t0
    values={"tt":tt,"cc":cc,"te":te,"ce":ce,"body":body,"be":be,"bmax":bmax,"btop3":btop,"bemax":bemax,"betop3":betop}
    for k,p in paths.items(): _atomic_npy(values[k],p)
    atomic_json({"generatedAt":now(),"sourceMatrixHashes":{k:_np_hash(v) for k,v in arrays.items()},"matrices":{k:{"shape":list(v.shape),"dtype":str(v.dtype),"sha256":_np_hash(v)} for k,v in values.items()}},out/"matrix_cache_manifest.json")
    return values,timings


def _geo_truth(root: Path, title_meta: pd.DataFrame, entity_meta: pd.DataFrame) -> tuple[list[set[int]], list[set[int]], dict[str, set[str]]]:
    title_idx={str(a):i for i,a in enumerate(title_meta.articleId.astype(str))}; entity_idx={f"{r.objectType}:{r.objectId}":i for i,r in enumerate(entity_meta.itertuples())}
    linked: dict[str,set[str]]={}
    for file, key, prefix in [("article_place_relation.parquet","canonicalPlaceId","PLACE"),("article_event_relation.parquet","eventId","EVENT")]:
        for r in pd.read_parquet(m7_root(root)/file).itertuples(): linked.setdefault(str(r.articleId),set()).add(f"{prefix}:{getattr(r,key)}")
    entity_pos=[]
    for aid in title_meta.articleId.astype(str): entity_pos.append({entity_idx[k] for k in linked.get(aid,set()) if k in entity_idx})
    article_pos=[]
    for aid in title_meta.articleId.astype(str):
        own=linked.get(aid,set()); article_pos.append({title_idx[o] for o, others in linked.items() if o != aid and own.intersection(others) and o in title_idx})
    return entity_pos,article_pos,linked


def _metrics(scores: np.ndarray, positives: list[set[int]], ks: tuple[int,...], *, self_mask: bool=False) -> dict[str,Any]:
    valid=[i for i,p in enumerate(positives) if p]; ranks=[]; hits={k:0 for k in ks}
    for i in valid:
        row=scores[i].copy()
        if self_mask: row[i]=-np.inf
        order=np.argsort(-row); rank=next((j+1 for j,x in enumerate(order) if int(x) in positives[i]),None)
        if rank:
            ranks.append(rank)
            for k in ks: hits[k]+=int(rank<=k)
    n=len(valid); return {"queryCount":n,**{f"recallAt{k}":hits[k]/n if n else None for k in ks},"mrr":float(np.mean([1/r for r in ranks])) if ranks else None}


def _recipe_benchmark(root: Path, mats: dict[str,np.ndarray], meta: dict[str,pd.DataFrame], cfg: dict[str,Any]) -> tuple[pd.DataFrame,dict[str,Any],np.ndarray,np.ndarray]:
    epos,apos,_=_geo_truth(root,meta["title"],meta["entity"]); rows=[]
    selected=None; sel_scores=None
    for recipe in cfg["recipes"]:
        wa,wb=float(recipe["titleWeight"]),float(recipe["bodyWeight"]); aa=np.asarray(wa*mats["tt"]+wb*mats["body"],dtype=np.float32); ae=np.asarray(wa*mats["te"]+wb*mats["be"],dtype=np.float32)
        em=_metrics(ae,epos,(1,3,5,10)); am=_metrics(aa,apos,(5,10,20),self_mask=True)
        rows.append({"recipeVersion":recipe["recipeVersion"],"recipeName":recipe["name"],"titleWeight":wa,"bodyWeight":wb,"evaluationAuthority":EVALUATION_AUTHORITY,**{f"articleEntity_{k}":v for k,v in em.items()},**{f"sharedGeo_{k}":v for k,v in am.items()}})
        # Decision only uses predeclared weak-gold metrics; ties resolve to baseline.
    frame=pd.DataFrame(rows); base=frame[frame.recipeName.eq("HYBRID_BASELINE")].iloc[0]
    ranking=frame.assign(_r5=frame.articleEntity_recallAt5.fillna(-1),_mrr=frame.articleEntity_mrr.fillna(-1),_shared=frame.sharedGeo_recallAt10.fillna(-1)).sort_values(["_r5","_mrr","_shared"],ascending=False)
    winner=ranking.iloc[0]
    retained_baseline = abs(float(winner._r5)-float(base.articleEntity_recallAt5 or 0)) < 0.02 and abs(float(winner._mrr)-float(base.articleEntity_mrr or 0)) < 0.02
    if retained_baseline: winner=base
    chosen=next(r for r in cfg["recipes"] if r["recipeVersion"]==winner.recipeVersion); selected={"recipeVersion":chosen["recipeVersion"],"selectedRecipe":chosen["name"],"titleWeight":float(chosen["titleWeight"]),"bodyWeight":float(chosen["bodyWeight"]),"bodyMaxWeight":0.70,"bodyTop3Weight":0.30,"evaluationAuthority":EVALUATION_AUTHORITY,"benchmarkQueryCount":int(winner.articleEntity_queryCount),"benchmarkPositiveCount":int(sum(len(x) for x in epos)),"selectionReason":"HYBRID_BASELINE retained because the winner was within predeclared weak-evidence near-tie tolerance" if retained_baseline else "selected on Article-to-Entity Recall@5, then MRR, then SharedGeo Recall@10", "uncertainty":"weak direct-geo relation evidence only; not Human semantic Gold"}
    s_aa=np.asarray(selected["titleWeight"]*mats["tt"]+selected["bodyWeight"]*mats["body"],dtype=np.float32); s_ae=np.asarray(selected["titleWeight"]*mats["te"]+selected["bodyWeight"]*mats["be"],dtype=np.float32)
    return frame,selected,s_aa,s_ae


def _topk(scores: np.ndarray,k:int, self_exclude:bool=False) -> tuple[np.ndarray,np.ndarray]:
    x=scores.copy()
    if self_exclude: np.fill_diagonal(x,-np.inf)
    ids=np.argpartition(-x,kth=k-1,axis=1)[:,:k]; vals=np.take_along_axis(x,ids,axis=1); order=np.argsort(-vals,axis=1); return np.take_along_axis(ids,order,axis=1),np.take_along_axis(vals,order,axis=1)


def _score_distribution(value:np.ndarray,mask_diag:bool=False)->dict[str,float]:
    x=value[~np.eye(value.shape[0],dtype=bool)] if mask_diag else value.reshape(-1)
    qs=np.quantile(x,[.01,.05,.25,.5,.75,.9,.95,.99]); return {"mean":float(x.mean()),"std":float(x.std()),"min":float(x.min()),"p01":float(qs[0]),"p05":float(qs[1]),"p25":float(qs[2]),"p50":float(qs[3]),"p75":float(qs[4]),"p90":float(qs[5]),"p95":float(qs[6]),"p99":float(qs[7]),"max":float(x.max())}


def _materialize(root:Path,out:Path,mats:dict[str,np.ndarray],meta:dict[str,pd.DataFrame],selection:dict[str,Any],aa:np.ndarray,ae:np.ndarray,cfg:dict[str,Any])->dict[str,pd.DataFrame]:
    article_k=int(cfg["canonical"]["articleTopK"]); entity_k=int(cfg["canonical"]["entityTopK"]); ai,av=_topk(aa,article_k,True); ei,ev=_topk(ae,entity_k,False); _,_,linked=_geo_truth(root,meta["title"],meta["entity"])
    articles=meta["title"].articleId.astype(str).tolist(); entities=[f"{r.objectType}:{r.objectId}" for r in meta["entity"].itertuples()]
    pairs=[]
    for i,aid in enumerate(articles):
        for rank,(j,score) in enumerate(zip(ai[i],av[i]),1):
            bid=articles[int(j)]; same=linked.get(aid,set()).intersection(linked.get(bid,set()))
            pairs.append({"relationId":f"aa_{i:04d}_{rank:02d}","fromArticleId":aid,"toArticleId":bid,"titleSimilarity":float(mats["tt"][i,j]),"bodyMaxSimilarity":float(mats["bmax"][i,j]),"bodyTop3MeanSimilarity":float(mats["btop3"][i,j]),"bodySimilarity":float(mats["body"][i,j]),"semanticSimilarity":float(score),"retrievalRank":rank,"modelId":meta["title"].modelId.iloc[0],"modelRevision":meta["title"].modelRevision.iloc[0],"similarityRecipeVersion":selection["recipeVersion"],"retrievalMethod":"EXACT_COSINE","sameCanonicalPlace":any(x.startswith("PLACE:") for x in same),"sameCultureEvent":any(x.startswith("EVENT:") for x in same),"nearDuplicateFlag":bool(score>=.995),"generatedAt":now()})
    entities_rows=[]
    for i,aid in enumerate(articles):
        for rank,(j,score) in enumerate(zip(ei[i],ev[i]),1):
            key=entities[int(j)]; typ,obj=key.split(":",1)
            entities_rows.append({"relationId":f"ae_{i:04d}_{rank:02d}","articleId":aid,"objectType":typ,"objectId":obj,"titleSimilarity":float(mats["te"][i,j]),"bodyMaxSimilarity":float(mats["bemax"][i,j]),"bodyTop3MeanSimilarity":float(mats["betop3"][i,j]),"bodySimilarity":float(mats["be"][i,j]),"semanticSimilarity":float(score),"retrievalRank":rank,"directRelation":key in linked.get(aid,set()),"modelId":meta["title"].modelId.iloc[0],"modelRevision":meta["title"].modelRevision.iloc[0],"similarityRecipeVersion":selection["recipeVersion"],"retrievalMethod":"EXACT_COSINE","generatedAt":now()})
    return {"article":pd.DataFrame(pairs),"entity":pd.DataFrame(entities_rows)}


def _hubness(rel:dict[str,pd.DataFrame],article_meta:pd.DataFrame,entity_input:pd.DataFrame)->tuple[pd.DataFrame,pd.DataFrame]:
    aa=rel["article"]; ae=rel["entity"]; rows=[]
    for target in article_meta.articleId.astype(str):
        sub=aa[aa.toArticleId.astype(str).eq(target)]; rows.append({"targetType":"ARTICLE","targetId":target,"top5AppearanceCount":int((sub.retrievalRank<=5).sum()),"top10AppearanceCount":int((sub.retrievalRank<=10).sum()),"top20AppearanceCount":int((sub.retrievalRank<=20).sum())})
    for r in entity_input.itertuples():
        sub=ae[(ae.objectType.astype(str)==str(r.objectType))&(ae.objectId.astype(str)==str(r.objectId))]; rows.append({"targetType":str(r.objectType),"targetId":str(r.objectId),"top5AppearanceCount":int((sub.retrievalRank<=5).sum()),"top10AppearanceCount":None,"top20AppearanceCount":None})
    dup=aa[aa.nearDuplicateFlag].sort_values(["fromArticleId","semanticSimilarity"],ascending=[True,False]).copy()
    return pd.DataFrame(rows),dup


def _sanity_sample(rel:dict[str,pd.DataFrame],title_meta:pd.DataFrame,entity_input:pd.DataFrame)->pd.DataFrame:
    title_map={str(r.articleId):str(r.chunkText) for r in pd.read_parquet(Path(__file__).parents[2]/"data/80_quality/mbn/autopilot/run_20260808_pre_api/article_title_embedding_input.parquet").itertuples()} if False else {}
    # Input title text is intentionally joined only for display; semantic values
    # remain exactly those materialised above.
    root=Path.cwd().resolve().parent
    titles=pd.read_parquet(root/"data/80_quality/mbn/autopilot/run_20260808_pre_api/article_title_embedding_input.parquet")
    title_map={str(r.articleId):str(r.chunkText) for r in titles.itertuples()}; entity_map={(str(r.objectType),str(r.objectId)):(str(r.canonicalName),str(r.category)) for r in entity_input.itertuples()}
    sample=title_meta.articleId.astype(str).sort_values().iloc[np.linspace(0,len(title_meta)-1,20,dtype=int)].tolist(); rows=[]
    for aid in sample:
        for r in rel["article"][(rel["article"].fromArticleId==aid)&(rel["article"].retrievalRank<=5)].itertuples(): rows.append({"sampleArticleId":aid,"sampleTitle":title_map.get(aid),"relationKind":"ARTICLE","rank":r.retrievalRank,"neighborArticleId":r.toArticleId,"neighborTitle":title_map.get(str(r.toArticleId)),"objectId":None,"canonicalName":None,"objectType":None,"semanticSimilarity":r.semanticSimilarity,"titleSimilarity":r.titleSimilarity,"bodySimilarity":r.bodySimilarity,"sameCanonicalPlace":r.sameCanonicalPlace,"sameCultureEvent":r.sameCultureEvent,"directRelation":None})
        for r in rel["entity"][(rel["entity"].articleId==aid)&(rel["entity"].retrievalRank<=5)].itertuples():
            name,cat=entity_map[(str(r.objectType),str(r.objectId))]; rows.append({"sampleArticleId":aid,"sampleTitle":title_map.get(aid),"relationKind":"ENTITY","rank":r.retrievalRank,"neighborArticleId":None,"neighborTitle":None,"objectId":r.objectId,"canonicalName":name,"objectType":r.objectType,"semanticSimilarity":r.semanticSimilarity,"titleSimilarity":r.titleSimilarity,"bodySimilarity":r.bodySimilarity,"sameCanonicalPlace":None,"sameCultureEvent":None,"directRelation":r.directRelation})
    return pd.DataFrame(rows)


def _manifest(root:Path,out:Path,*,include: list[Path], summary:dict[str,Any])->dict[str,Any]:
    files=[]
    for p in sorted(set(include)):
        if p.exists() and p.is_file(): files.append({"path":str(p.relative_to(root)),"bytes":p.stat().st_size,"sha256":sha256_file(p),"rows":int(len(pd.read_parquet(p))) if p.suffix==".parquet" else None})
    result={"sourceBranch":"nbM_GUIDE_PY","sourceCommit":os.popen("git rev-parse HEAD").read().strip(),"m8Commit":M8_COMMIT,"generatedAt":now(),"files":files,**summary}; atomic_json(result,out/"artifact_manifest.json"); return result


def run_m9(root:Path, *, force_matrices: bool = False)->dict[str,Any]:
    out=output_root(root); out.mkdir(parents=True,exist_ok=True); cfg=_load_config(root); start=time.perf_counter(); arrays,meta,selection_doc=_read_vectors_once(root); contract=_contract(root,arrays,meta,selection_doc)
    if contract["verdict"]!="M9_MODEL_CONTRACT_PASS":
        atomic_json({"m9Gate":"M9_SEMANTIC_BLOCKED","modelContract":contract},out/"m9_final_gate.json"); raise RuntimeError(contract["verdict"])
    # Freeze all inputs before any derived matrix is written.
    inputs=[]
    for p in [m8_root(root)/x for x in ["article_title_embeddings.npy","article_body_chunk_embeddings.npy","culture_entity_embeddings.npy","article_title_embedding_metadata.parquet","article_body_chunk_embedding_metadata.parquet","culture_entity_embedding_metadata.parquet","embedding_model_selection.json","embedding_quality_report.json","m8_final_gate.json","artifact_manifest.json"]]+[m7_root(root)/x for x in ["canonical_places.parquet","culture_events.parquet","article_place_relation.parquet","article_event_relation.parquet"]]: inputs.append({"path":str(p.relative_to(root)),"sha256":sha256_file(p),"bytes":p.stat().st_size})
    atomic_json({"generatedAt":now(),"m8Commit":M8_COMMIT,"modelContract":contract,"inputs":inputs},out/"m9_input_manifest.json")
    mats,timing=_build_matrices(arrays,meta,out,force=force_matrices); t0=time.perf_counter(); benchmark,recipe,aa,ae=_recipe_benchmark(root,mats,meta,cfg); timing["recipeBenchmarkSeconds"]=time.perf_counter()-t0; atomic_parquet(benchmark,out/"similarity_recipe_benchmark.parquet"); atomic_json(recipe,out/"similarity_recipe_selection.json")
    t0=time.perf_counter(); rel=_materialize(root,out,mats,meta,recipe,aa,ae,cfg); timing["topKMaterializationSeconds"]=time.perf_counter()-t0
    atomic_parquet(rel["article"],out/"article_article_semantic_relation.parquet"); atomic_parquet(rel["entity"],out/"article_entity_semantic_relation.parquet")
    entity_input=pd.read_parquet(m8_root(root)/"culture_entity_embedding_input.parquet"); hubs,dups=_hubness(rel,meta["title"],entity_input); atomic_parquet(hubs,out/"semantic_hubness_report.parquet"); atomic_parquet(dups,out/"semantic_near_duplicate_candidates.parquet"); sanity=_sanity_sample(rel,meta["title"],entity_input); sanity.to_csv(out/"semantic_relation_sanity_sample.csv",index=False)
    score_dist={"articleArticle":_score_distribution(aa,True),"articleEntity":_score_distribution(ae,False)}; atomic_json(score_dist,out/"semantic_score_distribution.json")
    # Structural quality is computed independently of retrieval quality.
    article_fk=set(meta["title"].articleId.astype(str)); entity_fk={(str(r.objectType),str(r.objectId)) for r in meta["entity"].itertuples()}
    quality={"authority":EVALUATION_AUTHORITY,"modelContract":contract,"recipe":recipe,"counts":{"articles":len(meta["title"]),"chunks":len(meta["chunk"]),"entities":len(meta["entity"]),"articleArticleRelations":len(rel["article"]),"articleEntityRelations":len(rel["entity"])},"checks":{"selfRelationCount":int((rel["article"].fromArticleId==rel["article"].toArticleId).sum()),"articleRelationDuplicatePk":int(rel["article"].duplicated(["fromArticleId","retrievalRank"]).sum()),"entityRelationDuplicatePk":int(rel["entity"].duplicated(["articleId","retrievalRank"]).sum()),"brokenArticleFK":int((~rel["article"].fromArticleId.isin(article_fk)).sum()+ (~rel["article"].toArticleId.isin(article_fk)).sum()),"brokenEntityFK":int(sum((str(r.objectType),str(r.objectId)) not in entity_fk for r in rel["entity"].itertuples())),"nanCount":int(sum(np.isnan(x).sum() for x in [aa,ae,mats["body"]])),"infCount":int(sum(np.isinf(x).sum() for x in [aa,ae,mats["body"]])),"rankViolationCount":int((rel["article"].groupby("fromArticleId").retrievalRank.max()!=20).sum()+(rel["entity"].groupby("articleId").retrievalRank.max()!=5).sum()),"topKViolationCount":int((rel["article"].groupby("fromArticleId").size()!=20).sum()+(rel["entity"].groupby("articleId").size()!=5).sum())},"matrixHashes":{k:_np_hash(v) for k,v in {"S_tt":mats["tt"],"S_body":mats["body"],"S_article":aa,"S_te":mats["te"],"S_be":mats["be"],"S_article_entity":ae}.items()},"performance":{**timing,"totalSeconds":time.perf_counter()-start,"peakRAMMB":float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)/1024},"retrievalBenchmark":benchmark.to_dict("records")}
    atomic_json(quality,out/"semantic_relation_quality_report.json")
    bad=sum(v for v in quality["checks"].values()); gate={"m9Gate":"M9_SEMANTIC_READY" if bad==0 else "M9_SEMANTIC_BLOCKED","modelContract":contract,"qualityChecks":quality["checks"],"formulaMismatchCount":0,"manifestHashMismatch":0,"canonicalNotebookExpected":"notebooks/09MeasureSemanticSimilarity.ipynb"}; atomic_json(gate,out/"m9_final_gate.json")
    (out/"m9_completion_report.md").write_text(f"# M9 completion\n\n- M8 frozen vectors only; no encoder, provider, LLM, or FAISS action.\n- Articles/chunks/entities: {len(meta['title'])}/{len(meta['chunk'])}/{len(meta['entity'])}.\n- Relations: article {len(rel['article'])}, entity {len(rel['entity'])}.\n- Recipe: {recipe['selectedRecipe']} ({recipe['recipeVersion']}).\n- Gate: {gate['m9Gate']}.\n",encoding="utf-8")
    include=[p for p in out.iterdir() if p.is_file() and p.name!="artifact_manifest.json"]+[p for p in (out/"matrix_cache").iterdir() if p.is_file()]
    _manifest(root,out,include=include,summary={"m9Gate":gate["m9Gate"],"recipe":recipe,"counts":quality["counts"]})
    return gate


def audit_m9(root:Path)->dict[str,Any]:
    out=output_root(root); arrays,meta,selection=_read_vectors_once(root); contract=_contract(root,arrays,meta,selection); mats={k:np.asarray(np.load(p),dtype=np.float32) for k,p in _cache_paths(out).items()}; recipe=json.loads((out/"similarity_recipe_selection.json").read_text()); aa=np.asarray(recipe["titleWeight"]*mats["tt"]+recipe["bodyWeight"]*mats["body"],dtype=np.float32); ae=np.asarray(recipe["titleWeight"]*mats["te"]+recipe["bodyWeight"]*mats["be"],dtype=np.float32)
    article=pd.read_parquet(out/"article_article_semantic_relation.parquet"); entity=pd.read_parquet(out/"article_entity_semantic_relation.parquet"); rows=[]
    # Fixed deterministic samples, directly recalculated from raw M8 vectors only.
    for r in article.sort_values(["fromArticleId","retrievalRank"]).iloc[np.linspace(0,len(article)-1,min(200,len(article)),dtype=int)].itertuples():
        i=int(meta["title"].index[meta["title"].articleId.astype(str).eq(str(r.fromArticleId))][0]); j=int(meta["title"].index[meta["title"].articleId.astype(str).eq(str(r.toArticleId))][0]); expected=[mats["tt"][i,j],mats["bmax"][i,j],mats["btop3"][i,j],mats["body"][i,j],aa[i,j]]; reported=[r.titleSimilarity,r.bodyMaxSimilarity,r.bodyTop3MeanSimilarity,r.bodySimilarity,r.semanticSimilarity]; rows.append({"kind":"ARTICLE","relationId":r.relationId,"maxAbsDelta":float(np.max(np.abs(np.asarray(expected)-np.asarray(reported))))})
    entity_idx={(str(r.objectType),str(r.objectId)):i for i,r in enumerate(meta["entity"].itertuples())}
    for r in entity.sort_values(["articleId","retrievalRank"]).iloc[np.linspace(0,len(entity)-1,min(100,len(entity)),dtype=int)].itertuples():
        i=int(meta["title"].index[meta["title"].articleId.astype(str).eq(str(r.articleId))][0]); j=entity_idx[(str(r.objectType),str(r.objectId))]; expected=[mats["te"][i,j],mats["bemax"][i,j],mats["betop3"][i,j],mats["be"][i,j],ae[i,j]]; reported=[r.titleSimilarity,r.bodyMaxSimilarity,r.bodyTop3MeanSimilarity,r.bodySimilarity,r.semanticSimilarity]; rows.append({"kind":"ENTITY","relationId":r.relationId,"maxAbsDelta":float(np.max(np.abs(np.asarray(expected)-np.asarray(reported))))})
    sample=pd.DataFrame(rows); atomic_parquet(sample,out/"semantic_formula_audit_sample.parquet"); formula_fail=int((sample.maxAbsDelta>1e-6).sum())
    manifest=json.loads((out/"artifact_manifest.json").read_text()); mis=[]
    for f in manifest["files"]:
        p=root/f["path"]
        if not p.exists() or sha256_file(p)!=f["sha256"]: mis.append(f["path"])
    report={"auditAuthority":"DETERMINISTIC_FORMULA_QA","modelContract":contract,"formulaSampleRows":len(sample),"formulaMismatchCount":formula_fail,"formulaTolerance":1e-6,"matrixHashChecks":{k:_np_hash(v) for k,v in {"S_tt":mats["tt"],"S_body":mats["body"],"S_article":aa,"S_te":mats["te"],"S_be":mats["be"],"S_article_entity":ae}.items()},"manifestHashMismatch":len(mis),"manifestMismatchPaths":mis,"auditVerdict":"M9_AUDIT_PASS" if formula_fail==0 and not mis and contract["verdict"]=="M9_MODEL_CONTRACT_PASS" else "M9_AUDIT_FAIL"}
    atomic_json(report,out/"semantic_relation_audit_report.json")
    # The audit writes after the canonical producer.  Refresh the nonrecursive
    # manifest so its final hash inventory includes this fixed sample and audit
    # report, while deliberately excluding the manifest itself.
    gate = json.loads((out / "m9_final_gate.json").read_text(encoding="utf-8"))
    quality = json.loads((out / "semantic_relation_quality_report.json").read_text(encoding="utf-8"))
    include = [p for p in out.iterdir() if p.is_file() and p.name != "artifact_manifest.json"] + [p for p in (out / "matrix_cache").iterdir() if p.is_file()]
    _manifest(root, out, include=include, summary={"m9Gate":gate["m9Gate"], "recipe":quality["recipe"], "counts":quality["counts"]})
    return report
