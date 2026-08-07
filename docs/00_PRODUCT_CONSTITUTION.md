# MBN GUIDE Product Constitution

Document: `00_PRODUCT_CONSTITUTION`
Status: `PROPOSED`
Authority: Normative product contract; highest authority within `docs/00~07`
Contract Version: `0.1.0`
Owner: MBN GUIDE Product Architecture & Documentation Director
Upstream Authority: User-approved product constitution; `MBN_GUIDEBOOK_PRODUCT_FUNCTION_SPEC_V2.md` v2.1 candidate
Downstream Consumers: `01~07`, FRONT, PY
Last Updated: 2026-08-07
Supersedes: No previously accepted split SSOT; v2.1 remains a reference candidate, not a parallel authority
Change Rule: A change requires impact review of `01~06` and a `07_DECISION_LOG` entry.

## Product definition

MBN GUIDE is a location-based culture commerce platform that helps people discover Korean culture, places, and content around their current or intended area; understand its context through related articles, video, and community material; then take an honestly represented next action such as viewing live content, an offer, a reservation, or an external CTA.

This is a product definition, not evidence that every source, partner, provider, or conversion path exists.

## Problem domain and intended response

| Problem | Product response | Contract boundary |
|---|---|---|
| Discovery information is fragmented across maps, social, articles, and video. | Location-aware place discovery and cross-links. | A map/provider is not selected here. |
| A place list lacks cultural meaning or fit. | `whyItMatters`, story, article/video context, and provenance. | Context requires declared sources or editorial provenance. |
| Interest does not naturally reach a next action. | Live/session, offer, and partner CTA after context and trust. | CTA is an attempt, never proof of purchase, booking, stock, or revenue. |

## Target and JTBD

**Primary.** Visitors to Korea and domestic travel/business visitors in an unfamiliar area: “I want to quickly find a cultural experience I can enjoy here.”

**Secondary.** Local explorers: “I want to find a cultural experience near me that I did not already know.”

**Expansion.** Culture and fandom audiences across K-pop, trot, music, food, beauty/fashion, exhibition, performance, broadcast content, and other taxonomy tags.

`locale` and visitor mode are user attributes. They do not make this an expatriate-only product or a set of separate apps.

## Product structure

```text
GUIDE → DISCOVER → LIVE
  discovery   context/trust   action
```

| Surface | Responsibility | Primary product nouns |
|---|---|---|
| GUIDE | Discover culture and places by current or selected area. | Place, category, map/list, discovery tray |
| DISCOVER | Build context and trust through editorial, video, and governed community material. | Story, Article, CommunityPost |
| LIVE | Connect context to a live/replay/upcoming session, offer, or partner action. | LiveSession, Offer, Partner |

Search, Saved, Language, Profile, and Settings are Utility Layer capabilities. They support the three surfaces and do not become primary content destinations.

## Funnel

```text
DISCOVER → CONTEXT → TRUST → INTENT → ACTION
```

Every feature must declare at least one stage, user problem, required data, consuming screen, and success event/metric. A feature that cannot do so is outside MVP.

## MBN role

MBN is a content/IP and provenance layer, not the sole data source or the whole product domain. Its eligible assets are MBN Video, Article, Program, Talent, Recommendation, and Live. MBN provenance must be visible where applicable; it must not be reduced to a product-coupled boolean.

## Non-negotiable principles

1. A primary discovery Place requires meaningful localized `whyItMatters`, not coordinates alone.
2. Context and trust precede commerce CTA; a CTA cannot masquerade as a completed transaction.
3. Sponsored/partner material is distinguishable from organic/editorial material.
4. Live, upcoming, replay, and unavailable are distinct states. No fake chat, viewer count, stock, or availability is allowed.
5. Community exposure follows moderation and policy readiness. It is not assumed to be writable or public.
6. Missing locale content, source evidence, relation, or provider result is represented as a state; it is not silently fabricated.
7. Product contracts define semantics, not a React component tree, notebook filenames, provider choice, or a working implementation.

## Authority and reality

```text
00 Product Constitution
  → 01 PRD
  → 02 IA / User Flow
  → 03 Feature Spec
  → 04 Content / Data Contract
  → 06 Technical Architecture Constraints
  → implementation
```

`00~07` are normative contracts. `08_CODE_BASED_FSD`, `09_CURRENT_IMPLEMENTATION`, and `10_DELIVERY_QA` are reserved for post-implementation observed evidence and must not be created during this phase. If code later differs, the difference is recorded as fact; upper contracts are not silently rewritten to match it.

## Documentation gates

| Gate | Required contract | Initial migration assessment |
|---|---|---|
| P0 Product | definition, target, surfaces, MBN role, commerce role | `PASS` |
| P1 IA | route, entry/exit, cross-surface flow | `PASS_WITH_FINDINGS` — Profile/Settings boundary remains proposed |
| P2 Feature | canonical ID, state, acceptance, analytics | `FAIL` before canonicalization; must be re-evaluated after approval of `03` |
| P3 Data | entity, taxonomy, provenance, confidence, unknown rules | `FAIL` before normalization; must be re-evaluated after approval of `04` |
| P4 Business safety | disclosure and no false transaction claims | `PASS_WITH_FINDINGS` — sponsored/organic governance remains proposed |

**Implementation gate: CLOSED.** A document draft is not implementation authorization. P0–P4 require an accepted cross-document audit before the gate opens.

## Branch sovereignty

Only `nbM_GUIDE_DOCS` may be modified for this contract. `nbM_GUIDE_FRONT` and `nbM_GUIDE_PY` may be read to evaluate contract alignment, but are not evidence of current product reality and must not be changed, merged, cherry-picked, rebased, or switched to without explicit user direction.

## Cross-document trace

| Need | Authority |
|---|---|
| Goals, JTBD, product hypotheses | `01_PRD` |
| Route and navigation state | `02_IA_USER_FLOW` |
| Canonical feature, event, acceptance contract | `03_FEATURE_SPEC` |
| Entity, lifecycle, release semantics | `04_CONTENT_DATA_CONTRACT` |
| Revenue hypotheses and safety | `05_BUSINESS_MONETIZATION_HYPOTHESIS` |
| Dependency and pipeline constraints | `06_TECH_ARCHITECTURE_CONSTRAINTS` |
| Decision status and conflict disposition | `07_DECISION_LOG` |
