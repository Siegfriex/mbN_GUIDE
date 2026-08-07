# MBN GUIDE Technical Architecture Constraints

Document: `06_TECH_ARCHITECTURE_CONSTRAINTS`
Status: `PROPOSED`
Authority: Normative implementation-boundary and handoff constraint
Contract Version: `0.3.0`
Owner: MBN GUIDE Product Architecture & Documentation Director
Upstream Authority: `00_PRODUCT_CONSTITUTION.md`, `02_IA_USER_FLOW.md`, `03_FEATURE_SPEC.md`, `04_CONTENT_DATA_CONTRACT.md`
Downstream Consumers: FRONT, PY
Last Updated: 2026-08-07
Supersedes: Integrated v2.1 architecture constraint section
Change Rule: A constraint change requires data/feature impact review and a `07` decision. This document never records an unverified implementation as current fact.

## Scope and non-scope

This contract sets ownership and dependency boundaries only. It does not select a framework, React component tree, map SDK, live provider, crawler, ranking model, or production deployment. The reference repository `Siegfriex/bigdata-transportation-front` may inform a responsibility model but does not define this product's implementation or current state.

All MBN GUIDE PY artifacts and execution stay local: notebooks are the control plane; Parquet/JSON/HTML/CSV/NPY/FAISS, PyTorch, DuckDB, Pandas, local Python, and local reports are the runtime/storage boundary. GCP is not a data store, pipeline runtime, model runtime, scheduler, or database for this product. GCS, BigQuery, Cloud Run, Vertex AI, Composer, and GCP databases are out of scope.

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

### Local execution and Google provider boundary

```text
local notebook / Python process
  → local artifacts, ML, QA, and release
  → HTTP only when a provider query is needed
  → Google Maps Platform project sbsds4
```

`sbsds4` is restricted to Maps Platform billing, API credential, quota, and billing alerts for local calls. The initial provider is Places API (New) Text Search; a query uses only the FieldMask needed for pilot resolution (provider Place ID, display name, formatted address, location, and types). Geocoding API is optional and separately enabled only after an address-to-coordinate need is demonstrated. API secrets never belong in repository files or notebooks: local environment/secrets paths are ignored, the key is restricted to the enabled API, and optional source-IP restriction depends on the stability of the local public egress address. Budget alerts warn; they are not treated as automatic cost shutoff.

| Milestone | Input semantics | Output semantics | Required gate |
|---|---|---|---|
| M1 Article intake | Approved source policy and acquisition scope. | Stable Article index/source references and acquisition evidence. | Source scope/policy; no crawl is authorized by this document. |
| M2 Normalized corpus | Extracted index/body with retention/status. | Parsed body/title metadata, hashes, parser/version trace. | Parse-quality evidence. |
| M3 Georesolution | Normalized text and taxonomy context. | Mention/candidate/geocode/canonical states, including failures. | Resolved/ambiguous/not-found/error separation. |
| M4 Semantic relation | Approved eligible corpus/entities. | Versioned relations with evidence, rank/distance/score trace and staleness. | FK/eligibility/review checks. |
| M5 Recommendation | Valid candidates and contextual policy. | Explainable ranked candidate projection. | No broken target; sponsored separation. |
| M6 Validated release | Approved L4 projections. | Immutable release bundle, manifest, hashes, validation/promotion verdict. | `PASS` only for promotion. |

Raw source, corpus, geo, semantic/vector, recommendation, quality, and frontend projection zones must remain logically separate. Missing, ambiguous, failed, stale, or rejected records are retained as quality evidence and cannot be erased to overstate readiness.

The local directory contract is:

```text
notebooks/                 # control plane
config/                    # pipeline, sources, models, taxonomy, recommendation YAML
data/00_contracts/
data/10_raw/{mbn,providers}/
data/20_corpus/{article_index,article_body,article_body_block}/
data/30_geo/{culture_key,place_candidate,provider_observation,canonical_place,culture_event}/
data/40_semantic/{embeddings,faiss,relations}/
data/50_recommendation/{candidates,rankings}/
data/80_quality/
data/90_exports/frontend/<releaseId>/
reports/  src/  tests/
```

This is a local artifact ownership layout, not a claim that the paths or notebook names already exist on `nbM_GUIDE_PY`.

### Pilot integration boundary

A pilot control-plane notebook may orchestrate the sequence “local article selection → MBN HTTP → local raw HTML → local body/body-block Parquet → local Gold CSV → CultureKey extraction → provider HTTP only for mappable candidates → local resolution → CanonicalPlace/Event → map object/reverse relation → local QA report.” A recommended name such as `03aPilotLabeledArticleBodyAndCultureEntity.ipynb` is not a DOCS-mandated filename.

The initial PY module boundaries are collection, parsing, text extraction, geo provider/mapper/resolver, local IO/hashing, and validation. `GooglePlace` must not be coupled directly to `CanonicalPlace`: Google DTO → mapper → ProviderCandidate/Observation → local resolver → CanonicalPlace.

### Local-first contextual-relation implementation constraints

The initial relation workflow is local and evidence-first. It does not authorize cloud deployment, real-time ad serving, supervised CTR training, or user-profile personalization.

1. Keep Article title vectors and ArticleBodyBlock vectors in separate versioned artifacts; never concatenate title/body into one undifferentiated embedding input.
2. Persist model/version, body block/chunk identity, text hash, vector row index, score components, candidate eligibility, rank, and evidence-based reason for every emitted relation.
3. Materialize `article_article_relation`, `article_live_relation`, and `place_live_relation` separately. Do not share `finalScore`, candidate pool, or display semantics across relation types.
4. Filter LiveSession eligibility before Article→Live or Place→Live ranking. `ENDED`, missing disclosure, missing title/thumbnail, and missing stream/outbound target cannot produce a live/commerce card.
5. Rank the LIVE feed from broadcast inventory status/schedule/category/partner/content coverage independently; contextual Place/Article ranks are detail-level relations only.
6. Keep scoring weights configurable and versioned; manual relevance/diversity/commerce-card review is required before a static release. A score is not a production quality claim.
7. The static release must declare relation files and quality metrics in its manifest, including foreign-key, embedding-dimension, eligibility, disclosure, and outbound-URL checks.
8. Provider rate limits are a first-class local concurrency constraint. Use locally controlled async/thread/process execution appropriate to the request type; never use cloud scale as a substitute for provider-policy compliance.
9. Provider responses follow the retention policy in `04`: raw MBN/public responses may be locally retained only when allowed; Google response persistence is not assumed, and observation/reference data is sufficient for resolution audit.

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
