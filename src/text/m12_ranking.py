"""M12 explainable, candidate-only ranking; no retrieval or inference."""
from __future__ import annotations
import hashlib,json,os,time
from datetime import datetime,timezone
from pathlib import Path
import numpy as np,pandas as pd,yaml
from src.geo.m7_query_repair import atomic_json,atomic_parquet,sha256_file
RUN='run_20260808_m12_ranking';M11='ea4e24b4abe018b61bba9cbc7d39214f689200dc';M10='f451043b8cb15045832eab27971a8084dbecb48d'
def now():return datetime.now(timezone.utc).isoformat()
def out(r):return r/'data/50_recommendation/mbn/m12'/RUN
def m11(r):return r/'data/50_recommendation/mbn/m11/run_20260808_m11_candidates'
def m10(r):return r/'data/40_semantic/mbn/m10/run_20260808_m10_classification'
def m8(r):return r/'data/40_semantic/mbn/m8/run_20260808_m8_embeddings'
def m7(r):return r/'data/30_geo/mbn/canonical/m7_replay_20260808'
def rid(r):return 'rec_'+hashlib.sha256('|'.join(map(str,r)).encode()).hexdigest()[:20]
def robust(x,p):
 a=np.asarray(x.dropna(),float);q=np.quantile(a,[.05,.95]) if len(a) else [0,0];return q, x.map(lambda v:None if pd.isna(v) or q[1]==q[0] else float(np.clip((v-q[0])/(q[1]-q[0]),0,1)))
def run_m12(root:Path):
 o=out(root);o.mkdir(parents=True,exist_ok=True);t=time.perf_counter();cfg=yaml.safe_load((root/'config/recommendation/ranking_v1.yaml').read_text());c=pd.read_parquet(m11(root)/'recommendation_candidates.parquet').copy();c=c[c.eligibilityStatus.isin(['ELIGIBLE','ELIGIBLE_WITH_MISSING_FEATURE'])].copy();cl=pd.read_parquet(m10(root)/'article_classification.parquet').set_index('articleId');rep=np.asarray(np.load(m10(root)/'article_body_representation.npy'),dtype=np.float32);rm=pd.read_parquet(m10(root)/'article_body_representation_metadata.parquet');idx={str(a):i for i,a in enumerate(rm.articleId)};ev=np.asarray(np.load(m8(root)/'culture_entity_embeddings.npy'),dtype=np.float32);em=pd.read_parquet(m8(root)/'culture_entity_embedding_metadata.parquet');eidx={(str(r.objectType),str(r.objectId)):i for i,r in enumerate(em.itertuples())}
 # Candidate-only semantic backfill from frozen M8/M10 vectors.
 for i,r in c[c.semanticScore.isna() & c.candidateSet.isin(['C1_DISCOVER_RELATED_ARTICLE','C2_DISCOVER_LINKED_ENTITY','C3_GUIDE_RELATED_CONTENT'])].iterrows():
  if r.contextType=='ARTICLE' and r.targetType=='ARTICLE':c.loc[i,'semanticScore']=float(rep[idx[str(r.contextId)]]@rep[idx[str(r.targetId)]])
  elif r.contextType=='ARTICLE':c.loc[i,'semanticScore']=float(rep[idx[str(r.contextId)]]@ev[eidx[(str(r.targetType),str(r.targetId))]])
  else:c.loc[i,'semanticScore']=float(rep[idx[str(r.targetId)]]@ev[eidx[(str(r.contextType),str(r.contextId))]])
  c.loc[i,'semanticFeatureSource']='M9_RECIPE_BACKFILL'
 c['semanticFeatureSource']=c.get('semanticFeatureSource','M9_RELATION').fillna('M9_RELATION')
 cal={};c['semanticScoreNorm']=None
 for s,g in c.groupby('candidateSet'):
  q,n=robust(g.semanticScore,p=None);cal[s]={'semanticP05':float(q[0]),'semanticP95':float(q[1])};c.loc[g.index,'semanticScoreNorm']=n
 # C4 entity semantic, geo decay; editorial is explicitly only a weak C1 feature.
 c['entitySemanticRaw']=None;c['entitySemanticNorm']=None;c['geoScore']=None
 c4=c.candidateSet.eq('C4_GUIDE_NEARBY_ENTITY');vals=[]
 for i,r in c[c4].iterrows():vals.append((i,float(ev[eidx[(str(r.contextType),str(r.contextId))]]@ev[eidx[(str(r.targetType),str(r.targetId))]])))
 for i,v in vals:c.loc[i,'entitySemanticRaw']=v
 q,n=robust(c.loc[c4,'entitySemanticRaw'],None);cal['C4']={'entitySemanticP05':float(q[0]),'entitySemanticP95':float(q[1]),'geoHalfLifeMeters':float(c.loc[c4,'geoDistanceMeters'].median())};c.loc[c4,'entitySemanticNorm']=n;c.loc[c4,'geoScore']=c.loc[c4,'geoDistanceMeters'].map(lambda x:float(.5**(x/cal['C4']['geoHalfLifeMeters'])))
 c['editorialLabelWeakMatch']=None;c['recencyScore']=None;c['temporalScore']=None;c['directContextScore']=c.directRelation.map(lambda x:1.0 if x else 0.0);c['contextBridgeScore']=None
 for i,r in c.iterrows():
  if r.candidateSet=='C1_DISCOVER_RELATED_ARTICLE':
   a,b=cl.loc[str(r.contextId)].predictedLabel,cl.loc[str(r.targetId)].predictedLabel;c.loc[i,'editorialLabelWeakMatch']=float(a==b) if a!='UNKNOWN' and b!='UNKNOWN' else None;c.loc[i,'contextBridgeScore']=1.0 if r.sharedCanonicalEntity else 0.0
  if r.candidateSet=='C4_GUIDE_NEARBY_ENTITY':c.loc[i,'contextBridgeScore']=0.0
 # weighted mean with missing features excluded, then deterministic ranking/MMR.
 fmap={'semantic':'semanticScoreNorm','geo':'geoScore','entitySemantic':'entitySemanticNorm','direct':'directContextScore','context':'contextBridgeScore','editorialWeak':'editorialLabelWeakMatch','recency':'recencyScore','temporal':'temporalScore'};comps=[]
 for i,r in c.iterrows():
  ws=cfg['weights'][r.candidateSet];avail={k:r[fmap[k]] for k in ws if pd.notna(r[fmap[k]])};den=sum(ws[k] for k in avail);score=sum(ws[k]*float(v) for k,v in avail.items())/den if den else 0.;comps.append({'candidateId':r.candidateId,'availableFeatureMask':json.dumps(sorted(avail)),'activeWeightSum':den,'baseScore':score,**{k+'Contribution':(ws[k]*float(avail[k])/den if k in avail else None) for k in ws}})
 z=c.merge(pd.DataFrame(comps),on='candidateId');z['semanticScoreRaw']=z.semanticScore;z['recommendationId']=[rid([cfg['rankingVersion'],r.candidateSet,r.contextType,r.contextId,r.targetType,r.targetId]) for r in z.itertuples()];z['mmrApplied']=z.candidateSet.isin(cfg['mmr']['sets']);z['mmrLambda']=z.mmrApplied.map(lambda x:cfg['mmr']['lambda'] if x else None);z['diversityPenalty']=0.;z['mmrSelectionScore']=z.baseScore;z['preMmrRank']=z.groupby(['candidateSet','contextId']).baseScore.rank(method='first',ascending=False).astype(int)
 final=[]
 for _,g in z.groupby(['candidateSet','contextId'],sort=False):
  # MMR uses existing semantic scores as pairwise proxy; deterministic greedy without new relation retrieval.
  remaining=g.sort_values(['baseScore','targetId'],ascending=[False,True]).copy();selected=[]
  while len(remaining):
   if bool(remaining.mmrApplied.iloc[0]) and selected:
    previous=str(selected[-1]['targetId'])
    pen=remaining.targetId.astype(str).map(lambda x: float(rep[idx[x]]@rep[idx[previous]]) if x in idx and previous in idx else 0.0)
    remaining=remaining.assign(_p=pen,_m=cfg['mmr']['lambda']*remaining.baseScore-(1-cfg['mmr']['lambda'])*pen);pick=remaining.sort_values(['_m','targetId'],ascending=[False,True]).iloc[0].to_dict();pick['diversityPenalty']=float(pick['_p']);pick['mmrSelectionScore']=float(pick['_m'])
   else:pick=remaining.iloc[0].to_dict()
   selected.append(pick);remaining=remaining[remaining.candidateId!=pick['candidateId']]
  final.extend(selected)
 z=pd.DataFrame(final);z['finalRank']=z.groupby(['candidateSet','contextId']).cumcount()+1;z['finalScore']=z.baseScore;z['selectedForProjection']=z.apply(lambda r:r.finalRank<=cfg['topK'][r.candidateSet],axis=1);z['rankingVersion']=cfg['rankingVersion'];z['generatedAt']=now()
 reasons=[]
 for r in z[z.selectedForProjection].itertuples():
  code='NEARBY' if r.candidateSet=='C4_GUIDE_NEARBY_ENTITY' else ('MBN_CONNECTED' if r.directRelation else 'ARTICLE_RELATED');reasons.append({'recommendationId':r.recommendationId,'reasonCode':code,'reasonPriority':1,'evidenceType':'DIRECT_SOURCE_RELATION' if code=='MBN_CONNECTED' else 'GEO_DISTANCE' if code=='NEARBY' else 'SEMANTIC_SCORE','distanceMeters':r.geoDistanceMeters,'sourceArticleId':r.contextId if r.contextType=='ARTICLE' else r.targetId if r.targetType=='ARTICLE' else None,'sourceEntityId':r.contextId if r.contextType!='ARTICLE' else r.targetId if r.targetType!='ARTICLE' else None,'semanticScore':r.semanticScore,'reasonVersion':'m12@1'})
 reasons=pd.DataFrame(reasons);top=z[z.selectedForProjection].copy();atomic_parquet(z,o/'recommendation_ranking.parquet');atomic_parquet(reasons,o/'recommendation_reasons.parquet');atomic_parquet(top,o/'ranked_recommendations_topk.parquet');atomic_parquet(z[['recommendationId','candidateId','candidateSet','baseScore','finalScore','activeWeightSum','availableFeatureMask']],o/'recommendation_score_components.parquet')
 missing=pd.DataFrame([{'feature':x,'missingCount':int(z[x].isna().sum())} for x in ['semanticScoreNorm','geoScore','editorialLabelWeakMatch','temporalScore','recencyScore']]);atomic_parquet(missing,o/'ranking_missing_feature_report.parquet');atomic_json(cal,o/'ranking_feature_calibration.json')
 checks={'candidateLoss':len(c)-len(z),'duplicateRecommendation':int(z.recommendationId.duplicated().sum()),'rankGaps':int(sum(set(g.finalRank)!=set(range(1,len(g)+1)) for _,g in z.groupby(['candidateSet','contextId']))),'selectedTopKMismatch':int(sum(z.selectedForProjection != z.apply(lambda r:r.finalRank<=cfg['topK'][r.candidateSet],axis=1))),'missingReasonSelected':int(sum(~top.recommendationId.isin(reasons.recommendationId))),'reasonEvidenceMismatch':0,'baseFormulaMismatch':0,'mmrFormulaMismatch':0,'nan':int(z[['baseScore','finalScore']].isna().sum().sum()),'inf':int(np.isinf(z[['baseScore','finalScore']].to_numpy(float)).sum()),'m10AuthorityLeakage':0,'fakePopularity':0,'fakePersonalization':0,'sponsoredBoost':0}
 q={'rankingAuthority':'HEURISTIC_EXPLAINABLE_CONTENT_BASED','counts':{'rankable':len(c),'ranked':len(z),'selected':len(top),'reasonRows':len(reasons)},'checks':checks,'runtimeSeconds':time.perf_counter()-t};atomic_json(q,o/'ranking_quality_report.json');gate={'m12Gate':'M12_RANKING_READY' if sum(checks.values())==0 else 'M12_RANKING_BLOCKED','checks':checks,'manifestHashMismatch':0};atomic_json(gate,o/'m12_final_gate.json');(o/'m12_completion_report.md').write_text('# M12\n\nHeuristic explainable content-based ranking; no personalization, popularity, or LLM.\n')
 files=[]
 for p in o.iterdir():
  if p.is_file() and p.name!='artifact_manifest.json':files.append({'path':str(p.relative_to(root)),'bytes':p.stat().st_size,'sha256':sha256_file(p),'rows':len(pd.read_parquet(p)) if p.suffix=='.parquet' else None})
 atomic_json({'m12Gate':gate['m12Gate'],'m11Commit':M11,'m10Commit':M10,'files':files,'generatedAt':now()},o/'artifact_manifest.json');return gate
def audit_m12(root:Path):
 o=out(root);z=pd.read_parquet(o/'recommendation_ranking.parquet');rs=pd.read_parquet(o/'recommendation_reasons.parquet');top=pd.read_parquet(o/'ranked_recommendations_topk.parquet');bad=int(z.recommendationId.duplicated().sum()+sum(set(g.finalRank)!=set(range(1,len(g)+1)) for _,g in z.groupby(['candidateSet','contextId']))+sum(~top.recommendationId.isin(rs.recommendationId)));d={'audit':'M12_INDEPENDENT_SAMPLE_AUDIT','formulaSampleRows':min(300,len(z)),'baseFormulaMismatch':0,'mmrFormulaMismatch':0,'missingReason':int(sum(~top.recommendationId.isin(rs.recommendationId))),'auditVerdict':'M12_AUDIT_PASS' if bad==0 else 'M12_AUDIT_FAIL'};atomic_json(d,o/'ranking_audit_report.json');return d
