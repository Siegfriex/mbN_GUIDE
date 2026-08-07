# MBN GUIDE Technical Architecture Constraints

Document: `06_TECH_ARCHITECTURE_CONSTRAINTS`
Status: `PROPOSED`
Authority: Normative implementation-boundary and handoff constraint
Contract Version: `0.2.0`
Owner: MBN GUIDE Product Architecture & Documentation Director
Upstream Authority: `00_PRODUCT_CONSTITUTION.md`, `02_IA_USER_FLOW.md`, `03_FEATURE_SPEC.md`, `04_CONTENT_DATA_CONTRACT.md`
Downstream Consumers: FRONT, PY
Last Updated: 2026-08-07
Supersedes: Integrated v2.1 architecture constraint section
Change Rule: A constraint change requires data/feature impact review and a `07` decision. This document never records an unverified implementation as current fact.

## Scope and non-scope

This contract sets ownership and dependency boundaries only. It does not select a framework, React component tree, folder names, map SDK, live provider, storage backend, crawler, geocoder, ranking model, notebook filename, or production deployment. The reference repository `Siegfriex/bigdata-transportation-front` may inform a responsibility model but does not define this product's implementation or current state.

## FRONT responsibility constraints

| Layer responsibility | Must hold | Must not hold |
|---|---|---|
| Route/page boundary | Route parameter validation, screen composition, loading boundary, navigation contract. | Raw API/storage calls, provider URL construction, business eligibility ownership. |
| Widget/composition boundary | Compose entity and feature view models into screen sections. | Raw DTO, global fixture, partner URL, or direct provider dependency. |
| Feature/action boundary | Orchestrate user actions, eligibility checks, adapters, and analytics events. | App shell ownership, direct route-object assembly, feature-internal coupling. |
| Entity/domain boundary | Domain schema, mapper, selector, repository contract, deterministic fixture boundary. | UI open/close state, page layout, SDK/provider types. |
| Shared boundary | Generic UI, analytics client, i18n core, safe storage/HTTP primitives, map base adapter. | Product nouns or product-specific business rules. |

Normative rules:

1. Pages do not directly own API or storage access.
2. Widgets do not own raw DTOs, fixtures, or external URLs.
3. External map, media/live, content, and partner dependencies sit behind adapters.
4. Provider/SDK types do not leak into Place, Story, Offer, or other domain contracts.
5. Mock, live, and provider implementations remain separable; a deterministic fixture must declare its contract version and non-empirical status.
6. A feature may activate an outbound CTA only under `03` and `04` eligibility semantics.

## PY/data pipeline constraints

PY is an independent data-product producer, not a FRONT pre-processing script.

```text
DOCS semantic contract → PY pipeline → validated immutable release → FRONT repository/adapter
```

| Milestone | Input semantics | Output semantics | Required gate |
|---|---|---|---|
| M1 Article intake | Approved source policy and acquisition scope. | Stable Article index/source references and acquisition evidence. | Source scope/policy; no crawl is authorized by this document. |
| M2 Normalized corpus | Extracted index/body with retention/status. | Parsed body/title metadata, hashes, parser/version trace. | Parse-quality evidence. |
| M3 Georesolution | Normalized text and taxonomy context. | Mention/candidate/geocode/canonical states, including failures. | Resolved/ambiguous/not-found/error separation. |
| M4 Semantic relation | Approved eligible corpus/entities. | Versioned relations with evidence, rank/distance/score trace and staleness. | FK/eligibility/review checks. |
| M5 Recommendation | Valid candidates and contextual policy. | Explainable ranked candidate projection. | No broken target; sponsored separation. |
| M6 Validated release | Approved L4 projections. | Immutable release bundle, manifest, hashes, validation/promotion verdict. | `PASS` only for promotion. |

Raw source, corpus, geo, semantic/vector, recommendation, quality, and frontend projection zones must remain logically separate. Missing, ambiguous, failed, stale, or rejected records are retained as quality evidence and cannot be erased to overstate readiness.

### Local-first contextual-relation implementation constraints

The initial relation workflow is local and evidence-first. It does not authorize cloud deployment, real-time ad serving, supervised CTR training, or user-profile personalization.

1. Keep Article title vectors and ArticleBodyBlock vectors in separate versioned artifacts; never concatenate title/body into one undifferentiated embedding input.
2. Persist model/version, body block/chunk identity, text hash, vector row index, score components, candidate eligibility, rank, and evidence-based reason for every emitted relation.
3. Materialize `article_article_relation`, `article_live_relation`, and `place_live_relation` separately. Do not share `finalScore`, candidate pool, or display semantics across relation types.
4. Filter LiveSession eligibility before Article→Live or Place→Live ranking. `ENDED`, missing disclosure, missing title/thumbnail, and missing stream/outbound target cannot produce a live/commerce card.
5. Rank the LIVE feed from broadcast inventory status/schedule/category/partner/content coverage independently; contextual Place/Article ranks are detail-level relations only.
6. Keep scoring weights configurable and versioned; manual relevance/diversity/commerce-card review is required before a static release. A score is not a production quality claim.
7. The static release must declare relation files and quality metrics in its manifest, including foreign-key, embedding-dimension, eligibility, disclosure, and outbound-URL checks.

## Release consumption constraints

FRONT pins a declared `releaseId`, contract version, schema version, and taxonomy version. It does not discover a “latest” directory, read a PY working directory, upgrade a failed release, silently coerce a mismatch, or ignore a broken FK. A new parser/model/taxonomy/ranking version creates a new release identity; it never overwrites a released artifact.

## Dependency and delivery boundaries

| Gate | Required before implementation claim | Failure handling |
|---|---|---|
| P0 Product | Accepted product definition and scope. | Do not settle product-oriented technical names as facts. |
| P1 IA | Accepted route/state contract. | Do not build navigation/detail behavior. |
| P2 Feature | Accepted canonical features, events, acceptance. | Do not implement only happy paths. |
| P3 Data | Accepted entity/taxonomy/provenance/release semantics. | Keep only labelled deterministic fixtures; no empirical claim. |
| P4 Business safety | Accepted disclosure/no-false-transaction boundary. | Offer remains unavailable/coming-soon; no checkout claim. |

Following P0–P4, source readiness, georesolution, semantic/recommendation, and release readiness are operational evidence gates owned by PY and its future validation artifacts. Documentation does not mark them passed without such evidence.
