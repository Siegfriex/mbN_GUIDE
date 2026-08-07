# MBN GUIDE Content and Data Contract

Document: `04_CONTENT_DATA_CONTRACT`
Status: `PROPOSED`
Authority: Normative data semantics and PY→FRONT release contract
Contract Version: `0.1.0`
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
| CommunityPost | `id`, author/source class, content/reference, `createdAt`, freshness, `moderationStatus`, visibility, provenance, related target IDs | Readability and writeability are separate. MVP write/public status is proposed, not assumed. |
| LiveSession | `id`, status, localized title/deck/summary, host reference, scheduled/replay fields, `placeIds`, `offerIds`, provenance | Status is `live|upcoming|replay|unavailable`; no inferred live state. |
| Offer | `id`, type, title, Partner reference, availability, disclosure, target relations, outbound target when eligible | `availability` and `disclosure` are both required before active CTA. `partner_cta_clicked` is outbound attempt only. |
| Partner | `id`, name, disclosure identity, allowed action types, outbound-domain/adapter reference, status, provenance | Partner selection/contract is not confirmed by this schema. |
| TravelerProfile | locale, visitor mode, interests, preference values, persistence status | Profile is user preference, not a new product identity; account model remains open. |
| SavedItem | `id`, targetType, `targetId`, `savedAt`, collection metadata | Stores references, not target snapshots; an unavailable/retired target remains auditable. |

### Place projection invariant

`Place` must not expose provider DTOs or SDK types. A UI projection can contain localized display fields, but must preserve provenance and status. A candidate lacks map eligibility when geocode state is `AMBIGUOUS`, `NOT_FOUND`, or `ERROR`; it must not be pinned merely to fill the map.

### Article and corpus invariant

`rawTitle`, bracket metadata, raw body, clean derived text, parsing status, parser version, source URL, collection time, and hashes serve different audit purposes. `FAILED`, `PARTIAL`, and empty parsing are retained as states, not discarded nulls. Article full text remains a PY/corpus concern unless a separately approved FRONT projection allows a bounded excerpt.

## Georesolution, relation, and recommendation contracts

```text
Article → PlaceMention → PlaceCandidate → GeocodeResult → CanonicalPlace → Place projection
```

| Object/status | Required meaning | UI/promotion rule |
|---|---|---|
| PlaceMention | Extracted surface, context, article ID, method/version, confidence. | Not a Place and never directly rendered as a pin. |
| PlaceCandidate | Grouped mention candidate and region/category hints. | Pending/merged/rejected state remains explicit. |
| GeocodeResult `RESOLVED` | Valid coordinates and one selected result. | Eligible for canonical review/projection. |
| `AMBIGUOUS` | More than one plausible result or insufficient evidence. | No automatic pin; review queue. |
| `NOT_FOUND` | Provider could not resolve. | May remain an article relation; no coordinates invented. |
| `ERROR` | Provider, transport, or validation failure. | Retry/audit state; never merged into not-found. |
| SemanticRelation | Source/target IDs, method/model/version, rank/distance/score components, reason/evidence, createdAt, staleness. | Relation must pass FK and eligibility validation. |
| Recommendation | Candidate set, ranking version, score decomposition, human-readable reason, context/time, status. | Sponsored candidates are separately labelled; no opaque promotion. |

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

Release rules: do not overwrite an existing release when parser/model/taxonomy/ranking changes; do not promote `FAIL`; do not silently coerce schema mismatch in UI; do not ignore broken FK; keep deterministic fixtures explicitly marked with their contract version and non-empirical status.

## PY responsibility boundary

PY may implement article intake/body corpus, title parsing, taxonomy, georesolution, embeddings, semantic relations, recommendation, and release generation. DOCS owns the meaning of inputs/outputs, taxonomy, provenance, confidence, unknown/unavailable rules, and versioning. Exact provider, crawler, model, notebook name, source scope, and execution evidence are not asserted here.
