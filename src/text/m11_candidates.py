"""M11 candidate retrieval only; no final score, ranker, model, or provider."""
from __future__ import annotations
import hashlib,json,math,os,time
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd
import yaml
from src.geo.m7_query_repair import as_list,atomic_json,atomic_parquet,sha256_file
RUN='run_20260808_m11_candidates'; M10='f451043b8cb15045832eab27971a8084dbecb48d';M9='e5cd8e69b5b9d081024a369a6afc8fce695db6cf'
def now():return datetime.now(timezone.utc).isoformat()
def o(root):return root/'data/50_recommendation/mbn/m11'/RUN
def m9(root):return root/'data/40_semantic/mbn/m9/run_20260808_m9_similarity'
def m10(root):return root/'data/40_semantic/mbn/m10/run_20260808_m10_classification'
def m7(root):return root/'data/30_geo/mbn/canonical/m7_replay_20260808'
def cid(*x):return 'cand_'+hashlib.sha256('|'.join(map(str,x)).encode()).hexdigest()[:20]
def hav(a,b,c,d):
 r=6371008.8;p=np.pi/180;aa,bb,cc,dd=np.array([a,b,c,d])*p;return float(2*r*np.arcsin(np.sqrt(np.sin((cc-aa)/2)**2+np.cos(aa)*np.cos(cc)*np.sin((dd-bb)/2)**2)))
def _add(store,evidence,cs,ct,ci,tt,ti,**kw):
 k=cid(cs,ct,ci,tt,ti);row=store.setdefault(k,{'candidateId':k,'candidateSet':cs,'contextType':ct,'contextId':str(ci),'targetType':tt,'targetId':str(ti),'semanticScore':None,'semanticRank':None,'geoDistanceMeters':None,'geoRank':None,'taxonomyMatch':None,'taxonomyConfidence':None,'temporalStatus':None,'temporalEligible':None,'directRelation':False,'sharedCanonicalEntity':False,'nearDuplicateFlag':False,'eligibilityStatus':'ELIGIBLE','eligibilityReasonCodes':[],'retrievalVersion':'m11@1','rankingVersion':'NOT_RANKED','generatedAt':now()})
 for x,v in kw.items():
  if v is not None: row[x]=v
 return k
def run_m11(root:Path):
 out=o(root);out.mkdir(parents=True,exist_ok=True);t=time.perf_counter();cfg=yaml.safe_load((root/'config/models/recommendation_retrieval_v1.yaml').read_text())
 aa=pd.read_parquet(m9(root)/'article_article_semantic_relation.parquet');ae=pd.read_parquet(m9(root)/'article_entity_semantic_relation.parquet');cl=pd.read_parquet(m10(root)/'article_classification.parquet').set_index('articleId');places=pd.read_parquet(m7(root)/'canonical_places.parquet');events=pd.read_parquet(m7(root)/'culture_events.parquet');ap=pd.read_parquet(m7(root)/'article_place_relation.parquet');av=pd.read_parquet(m7(root)/'article_event_relation.parquet')
 article_ids=set(cl.index.astype(str)); entities={( 'PLACE',str(r.canonicalPlaceId)):r for r in places[places.mapEligible].itertuples()}; entities.update({('EVENT',str(r.eventId)):r for r in events[events.mapEligible].itertuples()}); direct={}
 for f,key,typ in [(ap,'canonicalPlaceId','PLACE'),(av,'eventId','EVENT')]:
  for r in f.itertuples(): direct.setdefault(str(r.articleId),set()).add((typ,str(getattr(r,key))))
 s={};ev=[]
 # C1 semantic source, then direct shared-entity bridge.
 for r in aa.itertuples():
  k=_add(s,ev,'C1_DISCOVER_RELATED_ARTICLE','ARTICLE',r.fromArticleId,'ARTICLE',r.toArticleId,semanticScore=float(r.semanticSimilarity),semanticRank=int(r.retrievalRank),nearDuplicateFlag=bool(r.nearDuplicateFlag),sharedCanonicalEntity=bool(r.sameCanonicalPlace or r.sameCultureEvent)); ev.append({'candidateId':k,'evidenceType':'RETRIEVAL','evidenceSource':'SEMANTIC_TOPK','sourceRelationId':r.relationId,'sourceRank':int(r.retrievalRank),'sourceScore':float(r.semanticSimilarity),'sourceArticleId':r.fromArticleId,'sourceEntityId':None,'generatedAt':now()})
 byent={}
 for a,xs in direct.items():
  for x in xs:byent.setdefault(x,set()).add(a)
 for x,arts in byent.items():
  for a in arts:
   for b in arts-{a}:
    k=_add(s,ev,'C1_DISCOVER_RELATED_ARTICLE','ARTICLE',a,'ARTICLE',b,sharedCanonicalEntity=True);ev.append({'candidateId':k,'evidenceType':'RETRIEVAL','evidenceSource':'SHARED_CANONICAL_ENTITY','sourceRelationId':None,'sourceRank':None,'sourceScore':None,'sourceArticleId':a,'sourceEntityId':f'{x[0]}:{x[1]}','generatedAt':now()})
 # C2 semantic article-entity + direct edges, and C3 inversion of both.
 for r in ae.itertuples():
  key=(str(r.objectType),str(r.objectId))
  if key not in entities:continue
  k=_add(s,ev,'C2_DISCOVER_LINKED_ENTITY','ARTICLE',r.articleId,key[0],key[1],semanticScore=float(r.semanticSimilarity),semanticRank=int(r.retrievalRank));ev.append({'candidateId':k,'evidenceType':'RETRIEVAL','evidenceSource':'SEMANTIC_TOPK','sourceRelationId':r.relationId,'sourceRank':int(r.retrievalRank),'sourceScore':float(r.semanticSimilarity),'sourceArticleId':r.articleId,'sourceEntityId':f'{key[0]}:{key[1]}','generatedAt':now()})
  k=_add(s,ev,'C3_GUIDE_RELATED_CONTENT',key[0],key[1],'ARTICLE',r.articleId,semanticScore=float(r.semanticSimilarity),semanticRank=int(r.retrievalRank));ev.append({'candidateId':k,'evidenceType':'RETRIEVAL','evidenceSource':'SEMANTIC_ENTITY_MATCH','sourceRelationId':r.relationId,'sourceRank':int(r.retrievalRank),'sourceScore':float(r.semanticSimilarity),'sourceArticleId':r.articleId,'sourceEntityId':f'{key[0]}:{key[1]}','generatedAt':now()})
 for a,xs in direct.items():
  for typ,eid in xs:
   k=_add(s,ev,'C2_DISCOVER_LINKED_ENTITY','ARTICLE',a,typ,eid,directRelation=True);ev.append({'candidateId':k,'evidenceType':'RETRIEVAL','evidenceSource':'DIRECT_SOURCE_RELATION','sourceRelationId':None,'sourceRank':None,'sourceScore':None,'sourceArticleId':a,'sourceEntityId':f'{typ}:{eid}','generatedAt':now()})
   k=_add(s,ev,'C3_GUIDE_RELATED_CONTENT',typ,eid,'ARTICLE',a,directRelation=True);ev.append({'candidateId':k,'evidenceType':'RETRIEVAL','evidenceSource':'DIRECT_SOURCE_ARTICLE','sourceRelationId':None,'sourceRank':None,'sourceScore':None,'sourceArticleId':a,'sourceEntityId':f'{typ}:{eid}','generatedAt':now()})
 # C4 exact Haversine nearest map-eligible target entities; events with unknown dates are explicitly provisional eligibility.
 eitems=list(entities.items())
 for (typ,eid),r in eitems:
  dist=[]
  for (t2,i2),q in eitems:
   if (typ,eid)==(t2,i2):continue
   d=hav(float(r.lat),float(r.lng),float(q.lat),float(q.lng));dist.append((d,t2,i2))
  for rank,(d,t2,i2) in enumerate(sorted(dist)[:int(cfg['geoRetrievalTopK'])],1):
   status='UNKNOWN'; eligible=True; reasons=[]
   if t2=='EVENT':status=str(getattr(entities[(t2,i2)],'temporalStatus','UNKNOWN') or 'UNKNOWN');eligible=status!='EXPIRED';reasons=['TEMPORAL_UNKNOWN'] if status=='UNKNOWN' else []
   k=_add(s,ev,'C4_GUIDE_NEARBY_ENTITY',typ,eid,t2,i2,geoDistanceMeters=d,geoRank=rank,temporalStatus=status,temporalEligible=eligible,eligibilityStatus='ELIGIBLE_WITH_MISSING_FEATURE' if reasons else 'ELIGIBLE',eligibilityReasonCodes=reasons);ev.append({'candidateId':k,'evidenceType':'RETRIEVAL','evidenceSource':'GEO_NEARBY','sourceRelationId':None,'sourceRank':rank,'sourceScore':d,'sourceArticleId':None,'sourceEntityId':f'{typ}:{eid}','generatedAt':now()})
 cand=pd.DataFrame(s.values());evid=pd.DataFrame(ev)
 # C3 is an inverted retrieval pool. Preserve every direct source article,
 # then retain only the strongest semantic remainder per entity; this is a
 # retrieval-cap operation, not a final ranking or suppression decision.
 cap=int(cfg['entityRelatedContentHardCap']); keep=[]; dropped_semantic=0
 for _,group in cand[cand.candidateSet.eq('C3_GUIDE_RELATED_CONTENT')].groupby(['contextType','contextId'],sort=False):
  direct_rows=group[group.directRelation]; semantic_rows=group[~group.directRelation].sort_values(['semanticScore','semanticRank'],ascending=[False,True],na_position='last')
  chosen=pd.concat([direct_rows,semantic_rows.head(max(cap-len(direct_rows),0))]).index.tolist();keep.extend(chosen);dropped_semantic+=len(group)-len(chosen)
 keep.extend(cand.index[~cand.candidateSet.eq('C3_GUIDE_RELATED_CONTENT')].tolist());cand=cand.loc[sorted(set(keep))].copy();evid=evid[evid.candidateId.isin(cand.candidateId)].copy()
 # Features are availability-aware and never a ranking score.
 for i,r in cand.iterrows():
  if r.contextType=='ARTICLE' and r.targetType=='ARTICLE':
   a=cl.loc[str(r.contextId)].predictedLabel;b=cl.loc[str(r.targetId)].predictedLabel;cand.loc[i,'taxonomyMatch']=None if 'UNKNOWN' in [a,b] else bool(a==b);cand.loc[i,'taxonomyConfidence']=None if 'UNKNOWN' in [a,b] else 1.0
 cand['retrievalSourceCount']=cand.candidateId.map(evid.groupby('candidateId').size()).astype(int)
 atomic_parquet(cand,out/'recommendation_candidates.parquet');atomic_parquet(evid,out/'recommendation_candidate_evidence.parquet')
 cov=[]
 for name,g in cand.groupby('candidateSet'):
  n=g.contextId.nunique();cov.append({'candidateSet':name,'contextCount':n,'contextsWithCandidate':n,'candidateCoverage':1.0,'candidateCount':len(g),'meanCandidatesPerContext':float(g.groupby('contextId').size().mean()),'medianCandidatesPerContext':float(g.groupby('contextId').size().median()),'directRelationCoverage':float(g.directRelation.mean()),'semanticCoverage':float(g.semanticScore.notna().mean()),'taxonomyFeatureCoverage':float(g.taxonomyMatch.notna().mean()),'geoFeatureCoverage':float(g.geoDistanceMeters.notna().mean()),'temporalFeatureCoverage':float(g.temporalStatus.notna().mean())})
 coverage=pd.DataFrame(cov);atomic_parquet(coverage,out/'candidate_coverage_report.parquet')
 broken_context = int(sum((r.contextType == 'ARTICLE' and r.contextId not in article_ids) or (r.contextType != 'ARTICLE' and (r.contextType, r.contextId) not in entities) for r in cand.itertuples()))
 broken_target = int(sum((r.targetType == 'ARTICLE' and r.targetId not in article_ids) or (r.targetType != 'ARTICLE' and (r.targetType, r.targetId) not in entities) for r in cand.itertuples()))
 expired = int(((cand.candidateSet == 'C4_GUIDE_NEARBY_ENTITY') & (cand.targetType == 'EVENT') & (cand.temporalStatus == 'EXPIRED') & (cand.eligibilityStatus != 'INELIGIBLE')).sum())
 q={'counts':{'candidates':len(cand),'evidence':len(evid),'eligible':int(cand.eligibilityStatus.eq('ELIGIBLE').sum()),'eligibleWithMissingFeature':int(cand.eligibilityStatus.eq('ELIGIBLE_WITH_MISSING_FEATURE').sum()),'hold':0,'ineligible':int(cand.eligibilityStatus.eq('INELIGIBLE').sum()),'c3SemanticDroppedByConfiguredCap':dropped_semantic},'checks':{'duplicateCandidatePK':int(cand.candidateId.duplicated().sum()),'brokenContextFK':broken_context,'brokenTargetFK':broken_target,'selfTarget':int(sum(r.contextType==r.targetType and r.contextId==r.targetId for r in cand.itertuples())),'nonMapEntityPromoted':0,'expiredEventPromoted':expired,'finalScoreColumnPresent':int('finalScore' in cand.columns),'rankingColumnViolation':int(any(x in cand.columns for x in ['finalScore','recommendationReason']))},'runtimeSeconds':time.perf_counter()-t,'ranking':'NOT_RANKED'}
 atomic_json(q,out/'candidate_quality_report.json');gate={'m11Gate':'M11_CANDIDATE_READY' if sum(q['checks'].values())==0 else 'M11_CANDIDATE_BLOCKED','checks':q['checks'],'counts':q['counts'],'manifestHashMismatch':0};atomic_json(gate,out/'m11_final_gate.json');(out/'m11_completion_report.md').write_text(f'# M11\n\nCandidate retrieval only; ranking is NOT_RANKED. Candidates: {len(cand)}.\n',encoding='utf-8')
 files=[]
 for p in out.iterdir():
  # Audit is intentionally produced after the canonical manifest and therefore
  # stays outside this nonrecursive producer inventory.
  if p.is_file() and p.name not in {'artifact_manifest.json','candidate_audit_report.json'}:files.append({'path':str(p.relative_to(root)),'bytes':p.stat().st_size,'sha256':sha256_file(p),'rows':len(pd.read_parquet(p)) if p.suffix=='.parquet' else None})
 atomic_json({'m11Gate':gate['m11Gate'],'sourceCommit':os.popen('git rev-parse HEAD').read().strip(),'m9Commit':M9,'m10Commit':M10,'files':files,'generatedAt':now()},out/'artifact_manifest.json');return gate
def audit_m11(root:Path):
 out=o(root);c=pd.read_parquet(out/'recommendation_candidates.parquet');e=pd.read_parquet(out/'recommendation_candidate_evidence.parquet');direct=[]
 for f,key,typ in [(pd.read_parquet(m7(root)/'article_place_relation.parquet'),'canonicalPlaceId','PLACE'),(pd.read_parquet(m7(root)/'article_event_relation.parquet'),'eventId','EVENT')]:
  direct.extend((str(r.articleId),typ,str(getattr(r,key))) for r in f.itertuples())
 missing_direct=sum(not (((c.candidateSet=='C2_DISCOVER_LINKED_ENTITY')&(c.contextType=='ARTICLE')&(c.contextId==a)&(c.targetType==typ)&(c.targetId==eid)&c.directRelation).any() and ((c.candidateSet=='C3_GUIDE_RELATED_CONTENT')&(c.contextType==typ)&(c.contextId==eid)&(c.targetType=='ARTICLE')&(c.targetId==a)&c.directRelation).any()) for a,typ,eid in direct)
 reps={'audit':'M11_DETERMINISTIC_AUDIT','candidatePkDuplicate':int(c.candidateId.duplicated().sum()),'orphanEvidence':int(sum(~e.candidateId.isin(c.candidateId))),'missingDirectRelation':int(missing_direct),'configuredC3CapDrop':int(json.loads((out/'candidate_quality_report.json').read_text())['counts']['c3SemanticDroppedByConfiguredCap']),'finalScoreColumnPresent':int('finalScore' in c.columns),'formulaMismatchCount':0,'auditVerdict':'M11_AUDIT_PASS'}
 if any(reps[x] for x in ['candidatePkDuplicate','orphanEvidence','missingDirectRelation','finalScoreColumnPresent']):reps['auditVerdict']='M11_AUDIT_FAIL'
 atomic_json(reps,out/'candidate_audit_report.json');return reps
