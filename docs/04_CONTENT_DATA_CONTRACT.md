# MBN GUIDE Content and Data Contract

Document: `04_CONTENT_DATA_CONTRACT`
Status: `PROPOSED`
Authority: Normative data semantics and PY→FRONT release contract
Contract Version: `0.3.0`
Owner: MBN GUIDE Product Architecture & Documentation Director
Upstream Authority: `00_PRODUCT_CONSTITUTION.md`, `01_PRD.md`, `03_FEATURE_SPEC.md`
Downstream Consumers: PY producer, FRONT consumer, `05~06`
Last Updated: 2026-08-07
Supersedes: Integrated v2.1 entity/pipeline/release sections
Change Rule: Semantic/schema/taxonomy/lifecycle changes require `07` decision, version increment, compatibility statement, and FRONT/PY impact review.

## Contract vocabulary and data lifecycle

Canonical product entities are **Place, Story, Article, CommunityPost, LiveSession, Offer, Partner, TravelerProfile, and SavedItem**. `Story` is the curated product story entity; the v2.1 expression `StoryBundle` is a legacy/reference label, not a second core entity. `CommunityPost` is the product item; a thread may group posts without replacing its moderation contract.

```text
L0 SOURCE → L1 EXTRACTED → L2 RESOLVED → L3 DERIVED INTELLIGENCE → L4 FRONTEND PROJECTION
```

| Level | Meaning | Examples | Promotion rule |
|---|---|---|---|
| L0 SOURCE | Original external/editorial source. | MBN article URL, partner feed, editor source. | Retain source identity and acquisition evidence. |
| L1 EXTRACTED | Candidate/raw material from a source. | Article index/body, mention, raw title. | Never assume product eligibility. |
| L2 RESOLVED | Normalized, identified, or reviewed canonical object. | CanonicalPlace, verified relation. | Ambiguous/unresolved records remain distinct. |
| L3 DERIVED INTELLIGENCE | Versioned model/rule output. | Taxonomy label, semantic relation, recommendation. | Score/confidence is evidence quality, not fact guarantee. |
| L4 FRONTEND PROJECTION | Validated, locale-aware UI data. | Place card/detail, Story feed, release bundle. | Only approved immutable release can be consumed. |

Broken provenance, missing required review, invalid schema, or broken foreign keys prohibit production projection. Editorial text has provenance too; AI is not the only content requiring an audit trail.

## Shared semantics

| Concept | Contract |
|---|---|
| Taxonomy | Canonical categories: `performance`, `exhibition`, `music`, `food`, `beauty-fashion`, `broadcast-media`, `healing`, `activity`; finer culture is versioned tags. |
| Locale | `ko` and `en` are proposed MVP mandatory locales. UI exposes locale availability. Missing content must use S-03 disclosure, not pretend it is translated. |
| Provenance | `source` is `mbn|editor|partner|community|public`; record `referenceId`, human label, retrieval/editorial method, timestamps, and sponsored flag where applicable. Partner/sponsored material is visibly distinct. |
| Confidence | A numeric or categorical signal must name method/version and scope. It is not a truth guarantee or user-facing quality claim by itself. |
| Unknown | The fact is not known or not supplied. Preserve it as `unknown`/absent with reason; do not infer a value. |
| Unavailable | A known entity/action exists but cannot currently be used. Preserve status/reason for S-07. |
| IDs | Stable internal IDs are not provider IDs. Source/provider IDs are namespaced references and cannot replace canonical identity. |

## Core entity contracts

| Entity | Required semantic fields | Key relations and state |
|---|---|---|
| Place | `id`, `name`, `lat`, `lng`, `address`, `category`, `tags`, `availableFrom`, `availableTo`, `summary`, `whyItMatters`, `localeSupport`, `source`, `provenance`, `relatedStoryIds`, `relatedLiveIds`, `offerIds` | A map-projected active Place needs valid coordinates; every primary discovery Place needs localized `whyItMatters`. `available*` may be unknown, never invented. |
| Story | `id`, localized headline/deck/summary, `articleIds`, `placeIds`, `liveIds`, tags, provenance, publish/status metadata | Story links require valid FK validation. Hero media is optional and has its own availability/provenance. |
| Article | `articleId`, `source`, `url`, `rawTitle`, `cleanTitle`, `publishedAt`, `category`, `tags`, `placeIds`, `storyIds` | Also retain source article ID, bracket tokens, collection time, raw/body SHA, parse status/version. Body corpus is not a default FRONT payload. |
| ArticleBodyBlock | `articleId`, `blockIndex`, `blockType`, `cleanText`, `chunkId`, `chunkTextHash`, parser/model version, vector row index when embedded | Block structure is the body-chunk boundary; it preserves a heading with its adjacent explanatory paragraphs where possible. |
| CommunityPost | `id`, author/source class, content/reference, `createdAt`, freshness, `moderationStatus`, visibility, provenance, related target IDs | Readability and writeability are separate. MVP write/public status is proposed, not assumed. |
| LiveSession | `id`/`liveSessionId`, title, description, thumbnail URL, `startsAt`, `endsAt`, stream/outbound URL, disclosure type, partner name, product categories, brand names, `placeIds`, provenance | Broadcast lifecycle is `LIVE|UPCOMING|REPLAY|ENDED`; action/content unavailability is separate. Only the first three are eligible for a contextual live/commerce card. |
| Offer | `id`, type, title, Partner reference, availability, disclosure, target relations, outbound target when eligible | `availability` and `disclosure` are both required before active CTA. `partner_cta_clicked` is outbound attempt only. |
| Partner | `id`, name, disclosure identity, allowed action types, outbound-domain/adapter reference, status, provenance | Partner selection/contract is not confirmed by this schema. |
| TravelerProfile | locale, visitor mode, interests, preference values, persistence status | Profile is user preference, not a new product identity; account model remains open. |
| SavedItem | `id`, targetType, `targetId`, `savedAt`, collection metadata | Stores references, not target snapshots; an unavailable/retired target remains auditable. |

### Place projection invariant

`Place` must not expose provider DTOs or SDK types. A UI projection can contain localized display fields, but must preserve provenance and status. A candidate lacks map eligibility when geocode state is `AMBIGUOUS`, `NOT_FOUND`, or `ERROR`; it must not be pinned merely to fill the map.

### Article and corpus invariant

`rawTitle`, bracket metadata, raw body, clean derived text, parsing status, parser version, source URL, collection time, and hashes serve different audit purposes. `FAILED`, `PARTIAL`, and empty parsing are retained as states, not discarded nulls. Article full text remains a PY/corpus concern unless a separately approved FRONT projection allows a bounded excerpt.

## Local artifact SSOT and external-provider policy

All data, ML, QA, and FRONT release artifacts are local to the PY execution environment. Parquet is the tabular artifact SSOT; DuckDB is an optional local analytical/query layer, not a server database. This contract does not authorize GCS, BigQuery, Cloud Run, Vertex AI, Composer, or a GCP database.

| Artifact class | Local format | Logical location |
|---|---|---|
| Contracts, taxonomy, pipeline/model/recommendation config | YAML | `config/`, `data/00_contracts/` |
| MBN raw acquisition | HTML | `data/10_raw/mbn/` |
| Provider observations permitted for retention | JSON or Parquet | `data/10_raw/providers/`, subject to provider policy |
| Article index/body/body blocks, candidates, canonical entities, relations, rankings | Parquet | `data/20_corpus/`, `30_geo/`, `40_semantic/`, `50_recommendation/` |
| Gold/manual review sets | CSV | Relevant quality or contract path |
| Vectors / vector index | NPY / FAISS | `data/40_semantic/embeddings/`, `data/40_semantic/faiss/` |
| Quality evidence | JSON and report artifacts | `data/80_quality/`, `reports/` |
| Frontend payload | JSON in immutable release directory | `data/90_exports/frontend/<releaseId>/` |

The logical local tree is `data/10_raw`, `20_corpus`, `30_geo`, `40_semantic`, `50_recommendation`, `80_quality`, and `90_exports`; the subdirectories in the supplied local-first plan express artifact ownership, not a cloud deployment topology.

### Provider boundary and retention

`sbsds4` is a Google Maps Platform billing, credential, quota, and alert boundary only. Its initial permitted role is Google Places API (New) Text Search through HTTP from a local notebook/process. Geocoding API is optional and must not be enabled or depended upon until address-to-coordinate resolution is separately required. The project is not an artifact store or pipeline runtime.

Provider data must be classified before storage:

| Provider class | Persistence rule |
|---|---|
| MBN or public/open source whose terms permit retention | Raw response may be retained locally with source policy, hash, and provenance. |
| Google Maps Platform | Do not assume raw responses/content can be permanently archived. Retain only what current provider terms permit; record a policy-aware observation and durable provider identity where allowed. |

`providerRawPath` is therefore not a universal required field. A provider observation records:

```text
articleId
cultureKeyId
provider
queryText
queriedAt
providerEntityId
providerRank
resolutionFeatures
resolutionScore
resolutionStatus
responseRetentionPolicy
```

For a Google Places observation, `provider = GOOGLE_PLACES`, `providerEntityId` is the Place ID, and `responseRetentionPolicy = PROVIDER_RESTRICTED`. Provider IDs are references that may need refresh; they are not CanonicalPlace IDs. A local credential uses a source-tree-external value such as `GOOGLE_MAPS_API_KEY`; `.env`, `.env.*`, `credentials/`, and `secrets/` are excluded from version control. API restriction is Places API (New) initially, with Geocoding API added only by decision. Budget/alert is cost observation, not assumed automatic spend blocking.

## Georesolution, relation, and recommendation contracts

```text
Article evidence → CultureKey → PlaceMention / PlaceCandidate → provider observation → resolution → CanonicalPlace → Place projection
```

| Object/status | Required meaning | UI/promotion rule |
|---|---|---|
| PlaceMention | Extracted surface, context, article ID, method/version, confidence. | Not a Place and never directly rendered as a pin. |
| PlaceCandidate | Grouped mention candidate and region/category hints. | Pending/merged/rejected state remains explicit. |
| ProviderObservation | Query, provider identity/rank, observed time, policy-aware retention state, resolution features/score/status. | Provider DTO/raw response is not the canonical entity and may be retention-restricted. |
| GeocodeResult `RESOLVED` | Valid coordinates and one selected result. | Eligible for canonical review/projection. |
| `AMBIGUOUS` | More than one plausible result or insufficient evidence. | No automatic pin; review queue. |
| `NOT_FOUND` | Provider could not resolve. | May remain an article relation; no coordinates invented. |
| `ERROR` | Provider, transport, or validation failure. | Retry/audit state; never merged into not-found. |
| SemanticRelation | Source/target IDs, method/model/version, rank/distance/score components, reason/evidence, createdAt, staleness. | Relation must pass FK and eligibility validation. |
| Recommendation | Candidate set, ranking version, score decomposition, human-readable reason, context/time, status. | Sponsored candidates are separately labelled; no opaque promotion. |

### CanonicalPlace is provider-independent

`CanonicalPlace` is resolved from article evidence, CultureKey/candidates, permitted provider observations, public-culture observations, and local context. It is not a copied Google response. Its semantic contract includes `canonicalPlaceId`, `canonicalName`, article evidence, source candidate IDs, `providerReferences[]`, resolution status, coordinate source/provenance, and canonical status.

```text
providerReferences[] = {
  provider,
  providerEntityId,
  observedAt,
  responseRetentionPolicy
}
```

Coordinates intended for a durable local canonical dataset require a source and reuse right appropriate to that purpose. A Google observation may assist resolution/cross-checking but does not by itself authorize copying all Google content into a permanent local geographic dataset.

## Contextual Live Recommendation Specification — local-first MVP

**Scope.** GUIDE Place detail, MAGAZINE/Article context, and LIVE broadcast surface. **Non-goals.** Cloud deployment, real-time ad serving, supervised CTR optimization, and user-profile personalization.

This is a contextual relationship engine, not a generic banner system:

```text
Place ↔ Article ↔ LiveSession / Offer
```

The current-context object determines the recommendation. `RelatedArticle` and `RelatedLive` are separate relation types, tables, scores, and presentation contracts. A score from one type must never be reused as the score for another type.

| Surface | Current context | Primary question | Permitted recommendation object |
|---|---|---|---|
| GUIDE Place detail | `placeId` | What content or live offer is relevant to this Place? | RelatedArticle, RelatedLive |
| MAGAZINE article context | `articleId` | What articles, places, and live offers are relevant to this Article? | RelatedArticle, mentioned Place, RelatedLive |
| LIVE | `liveSessionId` or feed | What is broadcasting now or upcoming? | LiveSession, then related Places/Articles |

### Typed relationship inventory

```text
Article ──MENTIONS──> Place
Article ──SIMILAR_TO──> Article
Article ──CONTEXT_MATCH──> LiveSession
Place   ──CONTEXT_MATCH──> LiveSession
LiveSession ──FEATURES──> Product / Brand / Place
```

| Relation table | Required fields | Meaning and safety rule |
|---|---|---|
| `article_place_relation` | `articleId`, `placeId`, `relationType`, `evidenceBlockIndexes`, `confidence`, `resolutionStatus`, `relationReason` | Mention evidence links an Article to a resolved/known Place. Ambiguous/unresolved place candidates cannot become a map relation. |
| `article_article_relation` | `sourceArticleId`, `targetArticleId`, `titleSimilarity`, `bodySimilarity`, `labelSimilarity`, `placeSimilarity`, `finalScore`, `rank`, `relationReason`, `modelVersion` | This is the only RelatedArticle score. It cannot justify a live/commerce card. |
| `article_live_relation` | `articleId`, `liveSessionId`, `titleSimilarity`, `bodySimilarity`, `productCategoryScore`, `placeScore`, `brandScore`, `availabilityScore`, `finalScore`, `rank`, `matchReason`, `disclosureEligible` | Article-context RelatedLive. A row does not override live-card eligibility. |
| `place_live_relation` | `placeId`, `liveSessionId`, `directPlaceScore`, `articleBridgeScore`, `categoryScore`, `geoScore`, `availabilityScore`, `finalScore`, `rank`, `matchReason`, `disclosureEligible` | Place-context RelatedLive. It is never an editorial RelatedArticle. |

### Embedding and evidence policy

Title and body are separate semantic signals. `cleanTitle` alone is embedded for topic/intent and fast retrieval. Body chunks are built from heading plus adjacent paragraphs before any arbitrary-length fallback, and support reranking and evidence. Do not include bracket tokens, boilerplate, share widgets, recommended-news widgets, bylines, legal footers, or ad copy in embedding input. Explicit label/place/brand/category/date metadata is a constraint, boost, and explanation signal; it cannot replace relation evidence.

Required versioned artifacts:

```text
article_title_embeddings.npy
article_title_embedding_metadata.parquet
article_body_chunk_embeddings.npy
article_body_chunk_metadata.parquet
live_embeddings.npy
live_embedding_metadata.parquet
```

Every body-chunk metadata row includes `articleId`, `blockIndex`, `chunkId`, `chunkTextHash`, model/version, and vector row index. For a source article `a` and target `x`, retain local evidence rather than average its whole body:

```text
bodySimilarity(a, x) = 0.70 × max(chunk cosine) + 0.30 × mean(top 3 chunk cosine)
```

This configuration is versioned and manually evaluated; it is not a learned CTR model or a factual relevance guarantee.

### RelatedArticle algorithm

Candidate set: union title-vector top 30 Articles, body-chunk-vector top 30 Article IDs, and direct candidates sharing an active resolved `placeId`; exclude the source Article, invalid Article status, duplicate URL, excluded/legal-only editorial type, and prohibited source scope.

```text
ArticleArticleScore =
  0.35 × TitleSimilarity
+ 0.40 × BodySimilarity
+ 0.15 × PlaceSimilarity
+ 0.05 × LabelSimilarity
+ 0.05 × RecencyScore
```

`PlaceSimilarity` is high for the same resolved Place and medium for the same canonical region/category. `LabelSimilarity` is a weak signal and cannot be the sole reason. Apply MMR after ranking to prevent near-duplicates:

```text
MMR(candidate) = λ × ArticleArticleScore - (1 - λ) × maxSimilarityToAlreadySelected
```

Initial `λ = 0.75` is configurable and must be evaluated in the local notebook/workflow. `relationReason` uses saved evidence only, for example same resolved place, supported body topic, or canonical region/category; it is not unsupported free-form generation.

### Article-to-Live algorithm

A LiveSession is eligible for a commerce/live card only when all are true:

```text
status ∈ {LIVE, UPCOMING, REPLAY}
AND disclosureType ∈ {AD, PARTNER, AFFILIATE, OWNED}
AND streamUrl OR outboundUrl exists
AND title AND thumbnailUrl exist
```

Candidates are the union of exact normalized brand/product-category/resolved-place matches, nearest live title/description vectors, and top body-chunk evidence matches. Remove ineligible sessions before ranking.

```text
ArticleLiveScore =
  0.20 × TitleSimilarity
+ 0.35 × BodySimilarity
+ 0.15 × ProductCategoryScore
+ 0.15 × PlaceScore
+ 0.10 × BrandScore
+ 0.05 × AvailabilityScore
```

Brand score requires explicit brand evidence. Availability orders `LIVE > UPCOMING > REPLAY`; `ENDED` is excluded. MAGAZINE Article context renders at most three cards under **관련 라이브**, with **광고 · 제휴 콘텐츠** disclosure, status, start time, partner name, thumbnail, saved `matchReason`, and only a Live detail or eligible partner outbound target. It never states MBN editorial endorsement.

### Place-to-Live algorithm

Candidates are direct Place IDs listed by sessions, sessions bridged through Articles with that Place relation, and sessions compatible with canonical region/category. Remove ineligible sessions before ranking.

```text
PlaceLiveScore =
  0.40 × DirectPlaceScore
+ 0.20 × ArticleBridgeScore
+ 0.15 × CategoryScore
+ 0.10 × GeoScore
+ 0.15 × AvailabilityScore
```

Geo score uses same neighborhood/city context, not raw distance alone. GUIDE Place detail renders at most two cards under **이 장소와 관련된 라이브**, includes **광고 · 제휴 콘텐츠** disclosure, and saves a place/category/region evidence reason. A non-eligible relation remains data/audit evidence and is not a CTA.

### LIVE feed independence

LIVE is the broadcast source-of-truth surface, not a contextual ad widget. Its initial feed ranks inventory independently from any currently open Article or Place:

```text
LiveTabScore =
  0.45 × BroadcastStatusScore
+ 0.20 × ScheduledRecency
+ 0.15 × CategoryPriority
+ 0.10 × PartnerPriority
+ 0.10 × ContentRelationCoverage
```

The LIVE surface exposes Live now, Upcoming, Replay, filters, detail, related Places/Articles, and an eligible product/reservation CTA. Only after a session is selected may it show `LiveSession → Related articles → Related places → Open in map`.

### Surface non-confusion rules

| Rule | GUIDE | MAGAZINE | LIVE |
|---|---|---|---|
| Primary object | Place | Article | LiveSession |
| RelatedArticle ranking | Place-linked first | Article→Article similarity | Live→Article relation after selection |
| RelatedLive ranking | Place→Live | Article→Live | Feed ranking, not contextual-widget ranking |
| Disclosure | Required for partner/affiliate live/offer | Required | Required for partner/affiliate offer |
| Full broadcast player | No | No | Yes |
| Map emphasis | Primary | Linked/secondary | Related-place secondary |

Never label Article similarity as a live recommendation, live recommendation as editorial recommendation, or an unverified outbound URL as advertising.

### Local-first delivery and QA

1. Validate Article index/labels, block-parse bodies, and extract place/product/brand/category/outbound evidence with block indexes; build a small manual gold set.
2. Produce title and body-chunk embeddings, `article_article_relation`, and review 15–20 manual queries for relevance/diversity.
3. Define/ingest a small local LiveSession catalog with explicit product/brand/place/disclosure metadata; generate both Live relation tables and review every commerce card.
4. Build a static immutable release with:

```text
manifest.json
places.json
articles.json
stories.json
live_sessions.json
offers.json
article_place_relations.json
article_article_relations.json
article_live_relations.json
place_live_relations.json
recommendations.json
taxonomy.json
quality_report.json
```

Required quality metrics: `articleBodyParseRate`, `placeExtractionPrecision@sample`, `resolvedPlaceRate`, `bodyEmbeddingValidRate`, `embeddingDimensionConsistency`, `relatedArticleTopKRelevance`, `relatedArticleDiversity`, `articleLiveEligibleCoverage`, `articleLiveManualPrecision@K`, `placeLiveManualPrecision@K`, `disclosureCoverage`, and `brokenOutboundUrlCount`.

Primary-feature done requires separate versioned title/body artifacts; separate relation tables/scores; disclosure and saved match reason on every displayed live card; GUIDE ranked from Place context; MAGAZINE ranked from Article context; independently ranked LIVE inventory; no unverified advertising link; and zero broken Article/Place/Live foreign keys in the static release.

## Generated and editorial text provenance

`whyItMatters`, Story summaries, and culture briefs may be editorial, rule-derived, retrieval-derived, or model-generated. Each must record source/article IDs where applicable, generation method, generator/model/prompt version when applicable, timestamp, review status, locale, and confidence if produced. Confidence decides review priority; it does not assert factuality. Text without required source/review evidence cannot be promoted to production Place projection.

## Immutable PY→FRONT release contract

PY is the producer of a validated release; FRONT is the consumer. The handoff is a pinned immutable `releaseId`, never “latest file,” a working directory, or a failed release.

| Manifest field | Requirement |
|---|---|
| `releaseId` | Immutable identity for the bundle consumed by FRONT. |
| `sourceCommit` | Producer source commit/revision; distinct from this DOCS branch. |
| `contractVersion`, `schemaVersion`, `taxonomyVersion`, `pipelineVersion` | Exact compatible versions. |
| `generatedAt`, record counts, quality status | Reproducibility and scope evidence. |
| File SHA-256 | Bundle integrity for every declared file. |
| Validation report | Schema, enum, locale/provenance, FK, quality, and promotion verdict. |

Release rules: build and retain the immutable bundle locally; do not overwrite an existing release when parser/model/taxonomy/ranking changes; do not promote `FAIL`; do not silently coerce schema mismatch in UI; do not ignore broken FK; keep deterministic fixtures explicitly marked with their contract version and non-empirical status. How FRONT receives a validated local release is a FRONT-track decision, not a reason to make the release cloud storage.

## PY responsibility boundary

PY may implement article intake/body corpus, title parsing, taxonomy, local georesolution, local embeddings/FAISS or cosine relations, local recommendation, local DuckDB/Pandas QA, and local release generation. DOCS owns the meaning of inputs/outputs, taxonomy, provenance, confidence, unknown/unavailable rules, provider-retention boundary, and versioning. Exact model, crawler, notebook filename, source scope, and execution evidence are not asserted here.
