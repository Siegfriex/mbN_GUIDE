"""Notebook-first M8 local text embedding control-plane helpers.

This module deliberately produces vectors and QA evidence only.  It does not
materialise article-to-article or semantic relation artifacts (reserved for M9).
"""
from __future__ import annotations

import gc
import hashlib
import json
import os
import platform
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from src.geo.m7_query_repair import as_list, atomic_json, atomic_parquet, sha256_file

RUN_NAME = "run_20260808_m8_embeddings"
RECIPE_VERSION = "m8_embedding_recipe@1"
BENCHMARK_AUTHORITY = "WEAK_RETRIEVAL_BENCHMARK"


def _canonical(root: Path) -> Path:
    return root / "data/30_geo/mbn/canonical/m7_replay_20260808"


def _inputs(root: Path) -> tuple[Path, Path]:
    base = root / "data/80_quality/mbn/autopilot/run_20260808_pre_api"
    return base / "article_title_embedding_input.parquet", base / "article_body_chunk_embedding_input.parquet"


def output_root(root: Path) -> Path:
    return root / "data/40_semantic/mbn/m8" / RUN_NAME


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _atomic_npy(value: np.ndarray, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".tmp.npy", delete=False) as handle:
        tmp = handle.name
        np.save(handle, value)
        handle.flush(); os.fsync(handle.fileno())
    try:
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def validate_frozen_inputs(root: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    title_path, body_path = _inputs(root)
    title, body = pd.read_parquet(title_path), pd.read_parquet(body_path)
    checks = {
        "titleRows": len(title), "bodyChunkRows": len(body),
        "titleArticleUnique": bool(title.articleId.astype(str).is_unique),
        "bodyArticleChunkUnique": bool(not body.duplicated(["articleId", "chunkId"]).any()),
        "titleTextNonempty": bool(title.chunkText.fillna("").astype(str).str.strip().ne("").all()),
        "bodyTextNonempty": bool(body.chunkText.fillna("").astype(str).str.strip().ne("").all()),
        "titleHashPresent": bool(title.chunkTextHash.notna().all()),
        "bodyHashPresent": bool(body.chunkTextHash.notna().all()),
        "titleExpected461": len(title) == 461,
        "bodyExpected1062": len(body) == 1062,
        "titleInputSha256": sha256_file(title_path),
        "bodyInputSha256": sha256_file(body_path),
    }
    # Existing input preparation is the source of body provenance.  Check all
    # non-title chunk block lists are populated without rewriting their recipe.
    checks["bodyBlockProvenancePresent"] = bool(body.blockIndexes.map(lambda x: len(as_list(x)) > 0).all())
    checks["verdict"] = "M8_INPUT_FREEZE_PASS" if all(v is True for k, v in checks.items() if isinstance(v, bool)) else "M8_INPUT_FREEZE_FAIL"
    return title, body, checks


def build_culture_entity_input(root: Path, target: Path | None = None) -> pd.DataFrame:
    canonical = _canonical(root)
    places = pd.read_parquet(canonical / "canonical_places.parquet")
    events = pd.read_parquet(canonical / "culture_events.parquet")
    why = pd.read_parquet(canonical / "why_it_matters_m7.parquet").set_index("entityCandidateId").to_dict("index")
    rows: list[dict[str, Any]] = []
    for row in places[places.mapEligible].itertuples():
        w = why.get(str(row.whyItMattersId), {})
        context = str(w.get("whyItMattersDraft") or "").strip()
        category = str(row.taxonomyCategory)
        text = f"[NAME]\n{row.canonicalName}\n\n[CATEGORY]\n{category}\n\n[CONTEXT]\n{context}"
        rows.append({"objectType": "PLACE", "objectId": str(row.canonicalPlaceId), "canonicalName": row.canonicalName,
                     "category": category, "whyItMatters": context, "sourceArticleIds": as_list(row.sourceArticleIds),
                     "sourceEvidenceBlockIds": as_list(w.get("sourceBlockIndexes")), "embeddingText": text,
                     "inputHash": _hash_text(text), "textRecipeVersion": "m8_culture_entity@1"})
    for row in events[events.mapEligible].itertuples():
        w = why.get(str(row.whyItMattersId), {})
        context = str(w.get("whyItMattersDraft") or "").strip()
        text = f"[NAME]\n{row.eventName}\n\n[CATEGORY]\nEVENT\n\n[CONTEXT]\n{context}"
        rows.append({"objectType": "EVENT", "objectId": str(row.eventId), "canonicalName": row.eventName,
                     "category": "EVENT", "whyItMatters": context, "sourceArticleIds": as_list(row.sourceArticleIds),
                     "sourceEvidenceBlockIds": as_list(w.get("sourceBlockIndexes")), "embeddingText": text,
                     "inputHash": _hash_text(text), "textRecipeVersion": "m8_culture_entity@1"})
    result = pd.DataFrame(rows).sort_values(["objectType", "objectId"]).reset_index(drop=True)
    if len(result) != 32 or result.duplicated(["objectType", "objectId"]).any() or result.embeddingText.str.strip().eq("").any():
        raise RuntimeError("M8_ENTITY_INPUT_INVALID")
    if target is not None:
        atomic_parquet(result, target)
    return result


def _load_specs(root: Path) -> dict[str, Any]:
    with (root / "config/models/embedding_models_v1.yaml").open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _load_encoder(spec: dict[str, Any]):
    from sentence_transformers import SentenceTransformer
    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = SentenceTransformer(spec["modelId"], revision=spec["revision"], trust_remote_code=False, device=device)
    model.max_seq_length = int(spec["maxSequenceLength"])
    return model, device


def _encode(model, texts: list[str], spec: dict[str, Any], *, query: bool = False, batch_size: int = 32) -> np.ndarray:
    prefix = spec["queryPrefix"] if query else spec["documentPrefix"]
    values = [prefix + str(x) for x in texts]
    # SentenceTransformers uses inference_mode internally; explicit normalized
    # float32 arrays make the persisted contract independent of device dtype.
    result = model.encode(values, batch_size=batch_size, show_progress_bar=False, normalize_embeddings=bool(spec["normalize"]), convert_to_numpy=True)
    return np.asarray(result, dtype=np.float32)


def _retrieval_metrics(scores: np.ndarray, positives: list[set[int]], ks: tuple[int, ...]) -> dict[str, Any]:
    ranks=[]; hits={k:0 for k in ks}; valid=0
    for i, target in enumerate(positives):
        if not target: continue
        valid += 1; order=np.argsort(-scores[i])
        rank=next((n+1 for n, candidate in enumerate(order) if int(candidate) in target), None)
        if rank is not None:
            ranks.append(rank)
            for k in ks: hits[k] += int(rank <= k)
    return {"queryCount":valid, **{f"recallAt{k}": hits[k]/valid if valid else None for k in ks}, "mrr":float(np.mean([1/r for r in ranks])) if ranks else 0.0}


def _article_entity_map(root: Path) -> dict[str, set[str]]:
    canonical = _canonical(root)
    result: dict[str, set[str]] = {}
    for path, key, prefix in [("article_place_relation.parquet", "canonicalPlaceId", "PLACE"), ("article_event_relation.parquet", "eventId", "EVENT")]:
        df=pd.read_parquet(canonical/path)
        for row in df.itertuples(): result.setdefault(str(row.articleId),set()).add(f"{prefix}:{getattr(row,key)}")
    return result


def benchmark_models(root: Path, out: Path | None = None) -> tuple[pd.DataFrame, dict[str, Any], pd.DataFrame]:
    titles, chunks, frozen = validate_frozen_inputs(root)
    entities = build_culture_entity_input(root)
    specs = _load_specs(root); records=[]
    titles=titles.sort_values("articleId").reset_index(drop=True); chunks=chunks.sort_values(["articleId","chunkId"]).reset_index(drop=True)
    chunk_idx={str(a):set(g.index) for a,g in chunks.groupby(chunks.articleId.astype(str))}
    entity_keys=[f"{r.objectType}:{r.objectId}" for r in entities.itertuples()]
    entity_idx={key:i for i,key in enumerate(entity_keys)}; relation_map=_article_entity_map(root)
    article_body_top=chunks.groupby(chunks.articleId.astype(str)).chunkText.first().to_dict()
    cached = None
    if out is not None and (out / "embedding_benchmark_results.parquet").exists():
        prior = pd.read_parquet(out / "embedding_benchmark_results.parquet")
        expected = {x["modelId"] for x in specs["candidates"]}
        if set(prior.modelId.astype(str)) == expected and set(prior.task.astype(str)) == {"TITLE_TO_OWN_BODY", "ARTICLE_TO_CULTURE_ENTITY"}:
            cached = prior
    for spec in specs["candidates"] if cached is None else []:
        started=time.perf_counter(); model, device=_load_encoder(spec)
        tvec=_encode(model,titles.chunkText.tolist(),spec)
        cvec=_encode(model,chunks.chunkText.tolist(),spec)
        evec=_encode(model,entities.embeddingText.tolist(),spec)
        elapsed=time.perf_counter()-started
        a_scores=tvec @ cvec.T
        a_pos=[chunk_idx.get(str(a),set()) for a in titles.articleId]
        a=_retrieval_metrics(a_scores,a_pos,(1,5,10)); a.update({"modelId":spec["modelId"],"task":"TITLE_TO_OWN_BODY"})
        # Query recipe is explicit and evidence-only: title plus the first
        # ordered body semantic chunk, capped only for benchmark prompt size.
        b_rows=[]; b_text=[]
        for row in titles.itertuples():
            positives=relation_map.get(str(row.articleId),set())
            if positives:
                b_rows.append(row); b_text.append(str(row.chunkText)+"\n"+str(article_body_top.get(str(row.articleId),""))[:1000])
        if b_rows:
            bvec=_encode(model,b_text,spec,query=True); b_scores=bvec @ evec.T
            b_pos=[{entity_idx[x] for x in relation_map[str(r.articleId)] if x in entity_idx} for r in b_rows]
            b=_retrieval_metrics(b_scores,b_pos,(1,3,5)); b.update({"modelId":spec["modelId"],"task":"ARTICLE_TO_CULTURE_ENTITY"})
        else: b={"modelId":spec["modelId"],"task":"ARTICLE_TO_CULTURE_ENTITY","queryCount":0,"recallAt1":None,"recallAt3":None,"recallAt5":None,"mrr":None}
        records.extend([a,b])
        del model, tvec, cvec, evec; gc.collect()
        try:
            import torch
            if torch.cuda.is_available(): torch.cuda.empty_cache()
        except Exception: pass
        records[-1]["wallSeconds"] = elapsed; records[-1]["textsPerSecond"]=(len(titles)+len(chunks)+len(entities))/elapsed
        records[-2]["wallSeconds"] = elapsed; records[-2]["textsPerSecond"]=(len(titles)+len(chunks)+len(entities))/elapsed
        records[-1]["device"] = device; records[-2]["device"] = device
        records[-1]["dimension"] = int(spec.get("dimension", 0) or 0); records[-2]["dimension"] = int(spec.get("dimension", 0) or 0)
    frame=cached if cached is not None else pd.DataFrame(records)
    # Quality is weighted only across measurable tasks; runtime is normalized.
    summary=[]
    for spec in specs["candidates"]:
        rows=frame[frame.modelId.eq(spec["modelId"])]
        a=rows[rows.task.eq("TITLE_TO_OWN_BODY")].iloc[0]; b=rows[rows.task.eq("ARTICLE_TO_CULTURE_ENTITY")].iloc[0]
        quality=0.45*(float(a.recallAt5)+float(a.mrr))/2 + (0.55*(float(b.recallAt3)+float(b.mrr))/2 if int(b.queryCount)>0 else 0)
        effective=0.45+(0.55 if int(b.queryCount)>0 else 0); quality/=effective
        summary.append({"modelId":spec["modelId"],"revision":spec["revision"],"qualityScore":quality,"textsPerSecond":float(a.textsPerSecond),"device":a.device})
    selection=pd.DataFrame(summary); speed=selection.textsPerSecond
    selection["runtimeScore"]=(speed-speed.min())/(speed.max()-speed.min()) if speed.max()>speed.min() else 1.0
    selection["selectionScore"]=specs["selection"]["qualityWeight"]*selection.qualityScore+specs["selection"]["runtimeWeight"]*selection.runtimeScore
    selection=selection.sort_values(["selectionScore","qualityScore"],ascending=False).reset_index(drop=True)
    weighted_winner=selection.iloc[0]
    quality_winner=selection.sort_values("qualityScore",ascending=False).iloc[0]
    material_delta=float(specs["selection"].get("materialQualityDelta",0.05))
    if float(quality_winner.qualityScore-weighted_winner.qualityScore) > material_delta:
        selected=quality_winner.to_dict(); selection_reason="QUALITY_GUARD_OVERRIDE_RUNTIME"
    else:
        selected=weighted_winner.to_dict(); selection_reason="WEIGHTED_QUALITY_RUNTIME_SELECTION"
    decision={"authority":BENCHMARK_AUTHORITY,"inputFreeze":frozen,"taskNotes":{"TITLE_TO_OWN_BODY":"self-article retrieval consistency, not semantic Human Gold","ARTICLE_TO_CULTURE_ENTITY":"direct M7 geo relations as weak positives","SHARED_GEO_ARTICLE":"INSUFFICIENT_WEAK_GOLD; not used in selection"},"selectedModel":selected,"selectionReason":selection_reason,"selectionWeights":specs["selection"],"modelSelectionVerdict":"SELECTED_MODEL"}
    if out is not None:
        atomic_parquet(frame,out/"embedding_benchmark_results.parquet"); atomic_parquet(selection,out/"embedding_model_selection_table.parquet"); atomic_json(decision,out/"embedding_model_selection.json")
    return frame, decision, selection


def _token_audit(model, spec: dict[str, Any], collections: dict[str, pd.DataFrame], text_columns: dict[str, str]) -> dict[str, Any]:
    result={}
    for name, frame in collections.items():
        texts=frame[text_columns[name]].fillna("").astype(str).tolist(); counts=[]
        for text in texts:
            counts.append(len(model.tokenizer(text, add_special_tokens=True, truncation=False)["input_ids"]))
        exceeds=sum(c>int(spec["maxSequenceLength"]) for c in counts)
        result[name]={"rows":len(texts),"maxSequenceLength":int(spec["maxSequenceLength"]),"maxTokens":max(counts) if counts else 0,"tokenCountP95":float(np.percentile(counts,95)) if counts else 0,"truncatedCount":exceeds,"truncationRate":exceeds/len(texts) if texts else 0.0}
    return result


def _metadata(frame: pd.DataFrame, *, id_columns: list[str], spec: dict[str, Any], dimension: int, hashes: pd.Series) -> pd.DataFrame:
    data=pd.DataFrame({"embeddingRow":np.arange(len(frame),dtype=np.int64),"embeddingId":[f"m8_{i:06d}" for i in range(len(frame))]})
    for c in id_columns: data[c]=frame[c].tolist()
    data["modelId"]=spec["modelId"]; data["modelRevision"]=spec["revision"]; data["dimension"]=dimension
    data["pooling"]=spec["pooling"];data["normalize"]=bool(spec["normalize"]);data["textRecipeVersion"]=RECIPE_VERSION;data["inputHash"]=hashes.tolist();data["generatedAt"]=_now()
    return data


def generate_m8(root: Path) -> dict[str, Any]:
    out=output_root(root); out.mkdir(parents=True,exist_ok=True)
    titles,chunks,frozen=validate_frozen_inputs(root)
    entities=build_culture_entity_input(root,out/"culture_entity_embedding_input.parquet")
    _, selection_doc, selection = benchmark_models(root,out)
    # `selection` remains score-sorted for transparent comparison, whereas
    # the decision document applies the material-quality guard.
    selected=dict(selection_doc["selectedModel"])
    spec=next(x for x in _load_specs(root)["candidates"] if x["modelId"]==selected["modelId"])
    model,device=_load_encoder(spec)
    token_audit=_token_audit(model,spec,{"titles":titles,"bodyChunks":chunks,"cultureEntities":entities},{"titles":"chunkText","bodyChunks":"chunkText","cultureEntities":"embeddingText"})
    if token_audit["titles"]["truncatedCount"] != 0 or token_audit["bodyChunks"]["truncationRate"] > 0.05:
        gate={"m8Gate":"M8_MODEL_SELECTION_BLOCKED","reason":"BLOCK_AND_REVIEW_CHUNK_RECIPE","inputFreeze":frozen,"selectedModel":selected,"tokenAudit":token_audit}
        atomic_json(gate,out/"m8_final_gate.json")
        return gate
    def load_or_encode(array_name: str, metadata_name: str, frame: pd.DataFrame, hashes: pd.Series, texts: list[str]) -> np.ndarray:
        array_path=out/array_name; metadata_path=out/metadata_name
        if array_path.exists() and metadata_path.exists():
            prior=np.load(array_path)
            meta=pd.read_parquet(metadata_path)
            valid=(prior.shape[0] == len(frame) == len(meta) and meta.embeddingRow.tolist() == list(range(len(meta)))
                   and set(meta.modelId.astype(str)) == {str(spec["modelId"])}
                   and set(meta.modelRevision.astype(str)) == {str(spec["revision"])}
                   and meta.inputHash.astype(str).tolist() == hashes.astype(str).tolist())
            if valid:
                return np.asarray(prior,dtype=np.float32)
        return _encode(model,texts,spec)
    title_vec=load_or_encode("article_title_embeddings.npy","article_title_embedding_metadata.parquet",titles,titles.chunkTextHash,titles.chunkText.tolist())
    chunk_vec=load_or_encode("article_body_chunk_embeddings.npy","article_body_chunk_embedding_metadata.parquet",chunks,chunks.chunkTextHash,chunks.chunkText.tolist())
    entity_vec=load_or_encode("culture_entity_embeddings.npy","culture_entity_embedding_metadata.parquet",entities,entities.inputHash,entities.embeddingText.tolist())
    arrays={"article_title_embeddings.npy":title_vec,"article_body_chunk_embeddings.npy":chunk_vec,"culture_entity_embeddings.npy":entity_vec}
    metas={"article_title_embedding_metadata.parquet":_metadata(titles,id_columns=["articleId"],spec=spec,dimension=title_vec.shape[1],hashes=titles.chunkTextHash),"article_body_chunk_embedding_metadata.parquet":_metadata(chunks,id_columns=["articleId","chunkId","blockIndexes"],spec=spec,dimension=chunk_vec.shape[1],hashes=chunks.chunkTextHash),"culture_entity_embedding_metadata.parquet":_metadata(entities,id_columns=["objectType","objectId","sourceArticleIds"],spec=spec,dimension=entity_vec.shape[1],hashes=entities.inputHash)}
    for name,array in arrays.items(): _atomic_npy(array,out/name)
    for name,frame in metas.items(): atomic_parquet(frame,out/name)
    checks={}
    array_metadata = {
        "article_title_embeddings.npy": "article_title_embedding_metadata.parquet",
        "article_body_chunk_embeddings.npy": "article_body_chunk_embedding_metadata.parquet",
        "culture_entity_embeddings.npy": "culture_entity_embedding_metadata.parquet",
    }
    for name,array in arrays.items():
        meta=metas[array_metadata[name]]
        norms=np.linalg.norm(array,axis=1); checks[name]={"rows":int(array.shape[0]),"dimension":int(array.shape[1]),"metadataRows":len(meta),"rowAligned":len(meta)==array.shape[0] and meta.embeddingRow.tolist()==list(range(len(meta))),"nanCount":int(np.isnan(array).sum()),"infCount":int(np.isinf(array).sum()),"zeroVectorCount":int((norms==0).sum()),"normalizedWithinTolerance":bool(np.all(np.abs(norms-1)<=1e-3))}
    sample=np.r_[title_vec[:10],chunk_vec[:10],entity_vec[:5]]; sample_text=titles.chunkText.tolist()[:10]+chunks.chunkText.tolist()[:10]+entities.embeddingText.tolist()[:5]
    repeated=_encode(model,sample_text,spec); cosine=np.sum(sample*repeated,axis=1)/(np.linalg.norm(sample,axis=1)*np.linalg.norm(repeated,axis=1)); determinism={"sampleRows":len(sample_text),"minCosine":float(cosine.min()),"verdict":"DETERMINISM_PASS" if float(cosine.min())>=0.99999 else "DETERMINISM_WITHIN_TOLERANCE"}
    quality={"authority":BENCHMARK_AUTHORITY,"inputFreeze":frozen,"selectedModel":selected,"device":device,"tokenAudit":token_audit,"vectorChecks":checks,"determinism":determinism,"m8Verdict":"M8_EMBEDDING_READY"}
    atomic_json(quality,out/"embedding_quality_report.json"); atomic_json({"selectedModel":selected,"benchmarkAuthority":BENCHMARK_AUTHORITY,"semanticRelationsMaterialized":False},out/"semantic_benchmark_quality_report.json")
    gate={"m8Gate":"M8_EMBEDDING_READY","inputFreeze":frozen,"selectedModel":selected,"vectorChecks":checks,"tokenAudit":token_audit,"determinism":determinism,"manifestHashMismatch":0}
    atomic_json(gate,out/"m8_final_gate.json")
    (out/"m8_completion_report.md").write_text(f"# M8 completion\n\n- Selected local model: {spec['modelId']} @ {spec['revision']}\n- Vectors: title {len(titles)}, body {len(chunks)}, culture entity {len(entities)}\n- Semantic relation artifacts: not generated (M9 boundary).\n",encoding="utf-8")
    files=[]
    for p in sorted(out.iterdir()):
        if p.is_file() and p.name!="artifact_manifest.json": files.append({"path":str(p.relative_to(root)),"bytes":p.stat().st_size,"sha256":sha256_file(p),"rows":int(len(pd.read_parquet(p))) if p.suffix==".parquet" else None})
    manifest={"sourceBranch":"nbM_GUIDE_PY","sourceCommit":os.popen("git rev-parse HEAD").read().strip(),"m7Commit":"76a4d59fe792188453bae72d8632742b267cb1f5","modelId":spec["modelId"],"modelRevision":spec["revision"],"embeddingDimension":int(title_vec.shape[1]),"pooling":spec["pooling"],"normalize":bool(spec["normalize"]),"titleCount":len(titles),"chunkCount":len(chunks),"entityCount":len(entities),"files":files,"generatedAt":_now()}
    atomic_json(manifest,out/"artifact_manifest.json")
    return gate
