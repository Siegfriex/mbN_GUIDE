# MBN GUIDE Product Requirements Document

Document: `01_PRD`
Status: `PROPOSED`
Authority: Normative product requirement contract
Contract Version: `0.1.0`
Owner: MBN GUIDE Product Architecture & Documentation Director
Upstream Authority: `00_PRODUCT_CONSTITUTION.md`
Downstream Consumers: `02~06`, FRONT, PY
Last Updated: 2026-08-07
Supersedes: Integrated v2.1 candidate requirement sections
Change Rule: Changes to product goal, target, or requirement require `07` entry and impact review of IA, feature, data, and business contracts.

## Product goal

Enable a user to move from an area-based cultural discovery need to an informed next action without presenting unverified content, availability, partner, or transaction outcomes as facts.

## Product requirements and non-goals

| ID | Type | Requirement / non-goal | Funnel | Product response | Measure |
|---|---|---|---|---|---|
| PR-01 | Requirement | A user can establish current or selected area context. | DISCOVER | GUIDE location/manual selection. | `guide_viewed`, area selection completion |
| PR-02 | Requirement | A user can find culture-relevant Places using taxonomy and map/list fallback. | DISCOVER | GUIDE filter, map rendering, tray. | Place Open Rate |
| PR-03 | Requirement | A user can understand why a Place is relevant before an action CTA. | CONTEXT | Place detail, Story, article/video context. | `context_consumed` |
| PR-04 | Requirement | A user can assess source/trust state. | TRUST | Visible provenance and governed CommunityPost state. | `community_opened`, provenance interaction where instrumented |
| PR-05 | Requirement | A user can preserve an intent for later. | INTENT | Save Place or Story; Saved hub. | Save Rate |
| PR-06 | Requirement | A user can enter a truthfully labelled live/session or outbound action. | ACTION | Live status, Offer disclosure, Partner CTA. | Live Entry Rate, Outbound CTR |
| NG-01 | Non-goal | Do not make a specific genre, MBN program, or foreign visitor identity the product core. | — | Taxonomy and provenance layers. | Qualitative contract review |
| NG-02 | Non-goal | Do not claim booking, purchase, inventory, discount, or revenue completion. | — | Outbound-only CTA semantics. | Safety audit |
| NG-03 | Non-goal | Do not introduce public/writable community before operational readiness. | — | Read-only/Unavailable states. | Moderation readiness decision |

## Target jobs and use cases

| JTBD | Actor | Trigger | Use case | Product response | MVP status |
|---|---|---|---|---|---|
| Find an experience in an unfamiliar area. | Visitor | Current/selected area is known. | Browse categories, map/list, and Place preview. | `G-01~G-05` | MVP |
| Decide whether a place is culturally worthwhile. | Visitor or local explorer | A Place has been opened. | Read why/context and follow linked Story/Article. | `G-06`, `D-02~D-04` | MVP subject to data eligibility |
| Judge the trust/freshness of a recommendation. | All | Context needs corroboration. | View provenance and available community material. | `D-05~D-06` | Curated/read-only proposed |
| Keep a promising option. | All | Place or Story is eligible. | Save and retrieve it later. | `G-07`, `D-07`, `S-02` | MVP |
| Take the next disclosed action. | All | Offer/partner action is eligible. | View status and disclosure, then attempt outbound CTA. | `L-01~L-08` | Contract only; partner/provider unconfirmed |
| Use the product in a preferred language and travel context. | All | First or returning visit. | Select locale, interests, visitor mode, and persistent preferences. | `P-01~P-04` | Proposed boundary |

## Product hypotheses

Hypotheses are not requirements or facts. Each must be evaluated with a declared counter-signal.

| ID | Hypothesis | Candidate signal | Counter-signal / limitation |
|---|---|---|---|
| H-01 | Integrated area-based culture discovery improves discovery engagement. | Guide sessions and Place opens. | It may underperform a simpler map; activity alone is not satisfaction. |
| H-02 | Editorial context improves Place engagement. | `context_consumed` followed by `item_saved`. | Context use may not relate to action. |
| H-03 | Governed community evidence improves intent. | Community open followed by save. | Community may not be trusted or causally responsible. |
| H-04 | Culture-linked live improves the naturalness of action. | Live → Offer → outbound sequence. | CTR may be lower than direct commerce. |
| H-05 | MBN IP/provenance contributes to initial trust or differentiation. | Provenance interaction and survey. | It may add no discovery value. |

## Success metric contract

| Funnel | Metric | Definition | Interpretation limit |
|---|---|---|---|
| DISCOVER | Place Open Rate | `place_detail_viewed / guide_viewed` sessions | Not the sole map-quality metric. |
| CONTEXT | Story Engagement Rate | `story_opened / place_detail_viewed` | Opening is not comprehension. |
| INTENT | Save Rate | `item_saved / eligible detail views` | Save is not a visit or purchase. |
| LIVE | Live Entry Rate | `live_session_opened / active users` | Replay and live must be segmented. |
| ACTION | Outbound CTR | `partner_cta_clicked / offer_opened` | Not a reservation, purchase, or revenue metric. |

## MVP boundary

MVP contains contracts for GUIDE, DISCOVER, LIVE, Save, Locale/Profile, and system states. It can use an approved deterministic fixture release only when it declares `contractVersion` and does not claim empirical source coverage.

The following remain outside MVP unless separately accepted: payment/order completion, verified inventory/discount claims, public community writing, automated translation of user-created content, account merge, a selected map/live/commerce provider, and production recommendation claims.

## Open product decisions

The following are documented as `PROPOSED` in `07_DECISION_LOG`: first prototype geography (Seoul), curated/read-only community MVP, `/settings` preference scope, mandatory `ko/en` MVP locale, and immutable `releaseId` as the FRONT↔PY handoff identity.
