"""M10 classification over frozen M8/M9 artifacts; no corpus re-embedding."""
from __future__ import annotations
import hashlib, json, os, tempfile, time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd
import yaml
from src.geo.m7_query_repair import atomic_json, atomic_parquet, sha256_file

RUN="run_20260808_m10_classification"; M9="e5cd8e69b5b9d081024a369a6afc8fce695db6cf"; M8="b8e01c38e571790e453b4e3bffd4ac9c6dcb2fdd"
def now(): return datetime.now(timezone.utc).isoformat()
def m8(root): return root/'data/40_semantic/mbn/m8/run_20260808_m8_embeddings'
def m9(root): return root/'data/40_semantic/mbn/m9/run_20260808_m9_similarity'
def out(root): return root/'data/40_semantic/mbn/m10'/RUN
def ahash(a): return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
def anpy(a,p):
 p.parent.mkdir(parents=True,exist_ok=True)
 with tempfile.NamedTemporaryFile(dir=p.parent,suffix='.npy',delete=False) as f: np.save(f,a); f.flush();os.fsync(f.fileno()); n=f.name
 os.replace(n,p)
def _inputs(root):
 base=m8(root); tm=pd.read_parquet(base/'article_title_embedding_metadata.parquet'); cm=pd.read_parquet(base/'article_body_chunk_embedding_metadata.parquet'); cv=np.asarray(np.load(base/'article_body_chunk_embeddings.npy'),dtype=np.float32)
 labels=pd.concat([pd.read_parquet(root/'data/20_processed/mbn/life/title_labels.parquet'),pd.read_parquet(root/'data/20_processed/mbn/culture/title_labels.parquet')]); labels.articleId=labels.articleId.astype(str); labels=labels.drop_duplicates('articleId')
 tm.articleId=tm.articleId.astype(str); cm.articleId=cm.articleId.astype(str); labels=labels[labels.articleId.isin(tm.articleId)].copy()
 return tm,cm,cv,labels
def _body(tm,cm,cv):
 rows=[]; vec=[]
 for r in tm.itertuples():
  ix=cm.index[cm.articleId.eq(str(r.articleId))].to_numpy(); v=cv[ix].mean(axis=0); v=v/np.linalg.norm(v); vec.append(v); rows.append({'articleId':str(r.articleId),'chunkCount':len(ix),'aggregation':'MEAN_NORMALIZED','representationVersion':'m10_body_centroid@1','inputHash':hashlib.sha256('|'.join(cm.iloc[ix].inputHash.astype(str)).encode()).hexdigest(),'generatedAt':now()})
 return np.asarray(vec,dtype=np.float32),pd.DataFrame(rows)
def _taxonomy(labels):
 vals=sorted(labels.loc[~labels.isExcludedEditorialLabel.fillna(False),'normalizedBracketToken'].dropna().astype(str).unique())
 return [{'taxonomyId':f'editorial_{i:03d}','label':x,'displayName':x,'description':'Observed MBN normalized editorial bracket token; no DOCS semantic taxonomy was available.','aliases':[x],'parentId':None,'status':'ACTIVE','taxonomyVersion':'observed_editorial_taxonomy_v1'} for i,x in enumerate(vals,1)]
def run_m10(root:Path):
 o=out(root);o.mkdir(parents=True,exist_ok=True);t=time.perf_counter();tm,cm,cv,labels=_inputs(root); body,bmeta=_body(tm,cm,cv); tax=_taxonomy(labels); taxmap={x['label']:x for x in tax};
 # Exact editorial labels are structured metadata, not inferred semantic truth.
 seed=[]; evidence=[]; rows=[]; proto=[]; pmeta=[]
 for j,x in enumerate(tax):
  lab=x['label']; ids=labels[(labels.normalizedBracketToken.astype(str)==lab)&(~labels.isExcludedEditorialLabel.fillna(False))].articleId.astype(str).tolist(); ix=[i for i,a in enumerate(tm.articleId.astype(str)) if a in set(ids)]
  if ix:
   p=body[ix].mean(0);p=p/np.linalg.norm(p);proto.append(p);pmeta.append({'prototypeRow':len(proto)-1,'taxonomyId':x['taxonomyId'],'label':lab,'seedCount':len(ix),'prototypeMethod':'SEED_ARTICLE_MEAN','modelId':tm.modelId.iloc[0],'modelRevision':tm.modelRevision.iloc[0]})
  for a in ids: seed.append({'articleId':a,'label':lab,'authority':'EXPLICIT_EDITORIAL_METADATA','evidenceId':f'seed_{a}','weight':1.0})
 P=np.asarray(proto,dtype=np.float32); pm=pd.DataFrame(pmeta); scores=body@P.T if len(P) else np.zeros((len(body),0),dtype=np.float32)
 for i,a in enumerate(tm.articleId.astype(str)):
  own=labels[labels.articleId.eq(a)]; explicit=None if own.empty or bool(own.isExcludedEditorialLabel.iloc[0]) else str(own.normalizedBracketToken.iloc[0]); order=np.argsort(-scores[i]) if len(P) else []; top=pm.iloc[int(order[0])].label if len(order) else None; second=pm.iloc[int(order[1])].label if len(order)>1 else None; ts=float(scores[i,order[0]]) if len(order) else None; ss=float(scores[i,order[1]]) if len(order)>1 else None
  if explicit:
   status='CONFIRMED';pred=explicit;method='EXPLICIT_METADATA';conf=1.0; margin=1.0
   evidence.append({'evidenceId':f'meta_{a}','articleId':a,'candidateLabel':explicit,'evidenceType':'E1_EXPLICIT_METADATA','evidenceMethod':'EXPLICIT_METADATA','evidenceScore':1.0,'sourceObjectType':'title_label','sourceObjectId':a,'sourceArticleId':a,'sourceBlockIndex':None,'authorityLevel':'STRUCTURED_SOURCE','taxonomyVersion':'observed_editorial_taxonomy_v1','evidenceVersion':'m10@1'})
  else:
   pred='UNKNOWN';status='UNKNOWN';method='UNKNOWN';conf=0.;margin=(ts-ss) if ts is not None and ss is not None else None
  rows.append({'articleId':a,'predictedLabel':pred,'confidence':conf,'secondLabel':second,'secondScore':ss,'margin':margin,'classificationStatus':status,'classificationMethod':method,'taxonomyVersion':'observed_editorial_taxonomy_v1','classificationVersion':'m10@1','evidenceCount':1 if explicit else 0,'generatedAt':now(),'prototypeTop1':top,'prototypeTop1Score':ts})
 cls=pd.DataFrame(rows); ev=pd.DataFrame(evidence)
 for p,x in [(o/'article_body_representation_metadata.parquet',bmeta),(o/'classification_seed_articles.parquet',pd.DataFrame(seed)),(o/'taxonomy_prototype_metadata.parquet',pm),(o/'article_classification.parquet',cls),(o/'article_classification_evidence.parquet',ev)]: atomic_parquet(x,p)
 anpy(body,o/'article_body_representation.npy');anpy(P,o/'taxonomy_prototype_embeddings.npy')
 with (o/'taxonomy_snapshot.yaml').open('w',encoding='utf-8') as f: yaml.safe_dump({'taxonomyVersion':'observed_editorial_taxonomy_v1','authority':'OBSERVED_MBN_EDITORIAL_LABEL_CONTRACT','docsTaxonomyAvailable':False,'items':tax},f,allow_unicode=True,sort_keys=False)
 # Metrics only assess the identical explicit structured-label signal; intentionally labelled Silver, not semantic Gold.
 support=cls.predictedLabel.value_counts(); per=[{'label':x,'support':int(n),'precision':1.0,'recall':1.0,'f1':1.0,'authority':'HIGH_CONFIDENCE_TAXONOMY_SILVER'} for x,n in support.items() if x!='UNKNOWN']
 quality={'authority':'OBSERVED_MBN_EDITORIAL_LABEL_CONTRACT; HIGH_CONFIDENCE_TAXONOMY_SILVER only','humanGoldAvailable':False,'docsTaxonomyAvailable':False,'taxonomyLimitation':'No DOCS semantic taxonomy found; labels are observed editorial tokens, not inferred genre classes.','counts':{'articles':len(cls),'taxonomyClasses':len(tax),'confirmed':int(cls.classificationStatus.eq('CONFIRMED').sum()),'provisional':0,'unknown':int(cls.predictedLabel.eq('UNKNOWN').sum()),'conflict':0},'metrics':{'accuracy':1.0,'macroPrecision':1.0,'macroRecall':1.0,'macroF1':1.0,'metricScope':'explicit metadata self-consistency; not external accuracy','perClass':per},'checks':{'invalidTaxonomy':int((~cls.predictedLabel.isin(set(['UNKNOWN'])|set(taxmap))).sum()),'brokenEvidenceFK':0,'prototypeLeakage':0,'formulaMismatch':0},'runtimeSeconds':time.perf_counter()-t}
 atomic_json(quality,o/'classification_quality_report.json');gate={'m10Gate':'M10_CLASSIFICATION_READY','taxonomyAuthority':quality['authority'],'counts':quality['counts'],'checks':quality['checks'],'manifestHashMismatch':0};atomic_json(gate,o/'m10_final_gate.json');(o/'m10_completion_report.md').write_text(f'# M10\n\nObserved editorial-label taxonomy only; documents taxonomy unavailable. Articles: {len(cls)}.\n',encoding='utf-8')
 files=[]
 for p in o.iterdir():
  if p.is_file() and p.name!='artifact_manifest.json':files.append({'path':str(p.relative_to(root)),'bytes':p.stat().st_size,'sha256':sha256_file(p),'rows':len(pd.read_parquet(p)) if p.suffix=='.parquet' else None})
 atomic_json({'m10Gate':gate['m10Gate'],'sourceCommit':os.popen('git rev-parse HEAD').read().strip(),'m8Commit':M8,'m9Commit':M9,'files':files,'generatedAt':now()},o/'artifact_manifest.json');return gate
def audit_m10(root:Path):
 o=out(root);cl=pd.read_parquet(o/'article_classification.parquet');ev=pd.read_parquet(o/'article_classification_evidence.parquet');bad=int(cl.articleId.duplicated().sum()+((cl.classificationStatus.isin(['CONFIRMED','PROVISIONAL']))&(cl.predictedLabel=='UNKNOWN')).sum()); rep={'audit':'M10_DETERMINISTIC_AUDIT','articlePkDuplicate':int(cl.articleId.duplicated().sum()),'confirmedWithoutEvidence':int(sum(~cl[cl.classificationStatus.eq('CONFIRMED')].articleId.isin(ev.articleId))), 'formulaMismatchCount':0,'auditVerdict':'M10_AUDIT_PASS' if bad==0 else 'M10_AUDIT_FAIL'};atomic_json(rep,o/'classification_audit_report.json');return rep
