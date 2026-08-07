# MBN GUIDE Canonical Feature Specification

Document: `03_FEATURE_SPEC`
Status: `PROPOSED`
Authority: Canonical feature, UI-state, analytics, and acceptance contract
Contract Version: `0.2.0`
Owner: MBN GUIDE Product Architecture & Documentation Director
Upstream Authority: `00_PRODUCT_CONSTITUTION.md`, `01_PRD.md`, `02_IA_USER_FLOW.md`
Downstream Consumers: FRONT, PY, `04~06`
Last Updated: 2026-08-07
Supersedes: v2.1 temporary/overloaded feature register
Change Rule: IDs are stable. Meaning, route, required data, event, or acceptance changes require `07` disposition and linked-contract review.

## Feature contract rules

Each registry row is a minimum contract: the actor triggers an eligible action on the named route; required entities/fields are inputs; output is the stated state/navigation/mutation; analytics is emitted only on the stated successful or viewed semantic transition. UI uses the global state and CTA rules below.

| State | Meaning | Minimum behavior |
|---|---|---|
| Loading (`S-04`) | Eligibility/result is pending. | Do not show invented result or CTA. |
| Empty (`S-05`) | Valid query/state returned no eligible content. | Explain scope and offer recovery/filter change. |
| Error (`S-06`) | Request, validation, or provider process failed. | Preserve context, retry when safe, distinguish from empty. |
| Unavailable (`S-07`) | Known content/action is not currently usable. | Explain why; offer a truthful alternative. |

CTA rule: an Offer/Partner CTA may be enabled only when the action is eligible, availability and disclosure are present, and the route can identify the target. `partner_cta_clicked` means an outbound attempt only.

## GUIDE registry

| ID / name | Funnel; user problem / JTBD | Route and trigger | Required inputs → output | Event / payload | Acceptance; dependency |
|---|---|---|---|---|---|
| G-01 Current/Selected Area | DISCOVER; find experiences in this area. | `/guide`; location/manual city trigger. | area permission or manual selection → area context. | `guide_viewed` {city, locale, visitorMode}; optional area-selection event. | Denied permission exposes manual fallback. FRONT consumes state; PY is not required for manual state. |
| G-02 Culture Category Filter | DISCOVER; narrow culture options. | `/guide`; filter interaction. | taxonomy version, selected category → eligible Place set. | `guide_filter_changed` {category, area}. | Empty is distinct from error; filter applies to map/list. FRONT consumes; PY supplies taxonomy/release when data-backed. |
| G-03 Map Place Rendering | DISCOVER; see eligible Places spatially. | `/guide`; area/result change. | map-eligible Place (`lat`,`lng`, status) → markers or list fallback. | `guide_map_rendered` {mode, placeCount}. | Map failure preserves list discovery; unresolved candidate never becomes a pin. FRONT map adapter; PY projection dependency. |
| G-04 Discovery Tray | DISCOVER; browse a usable local set. | `/guide`; initial/filter result. | eligible Place preview fields → ordered tray/list. | `discovery_tray_viewed` {count, category}. | No primary fixture without required context fields; empty/retry supported. FRONT consumes projection. |
| G-05 Place Preview | DISCOVER; decide which place to inspect. | `/guide`; marker/card/link. | Place identity, summary, why/provenance → selected preview. | `map_pin_opened` {placeId, category, provenance}. | Selection preserves source context and can navigate to valid detail; no false availability. FRONT consumes Place. |
| G-06 Place Detail | CONTEXT/TRUST/INTENT; understand place relevance. | `/place/:placeId`; preview/deep link. | resolved Place; typed RelatedArticle and RelatedLive relations; locale → detail state. | `place_detail_viewed` {placeId, entryPoint}. | Identity/provenance survive missing media; RelatedLive needs eligibility/disclosure; relation failure is section empty; unavailable target is S-07. FRONT consumes; PY supplies approved relations. |
| G-07 Save Place | INTENT; preserve a place. | Place detail/preview; save action. | saveable Place ID, profile/store → SavedItem mutation. | `item_saved` {targetType:"place", targetId, collection}. | Idempotent save result is visible; no target snapshot is required. FRONT owns action; PY none. |
| G-08 Share Place | INTENT; share a place. | Place detail; share action. | Place identity and supported share channel/fallback → share attempt result. | `place_share_attempted` {placeId, result}. | Failure is reported without claiming delivery; only Place sharing is canonical now. FRONT adapter; PY none. |

## DISCOVER registry

| ID / name | Funnel; user problem / JTBD | Route and trigger | Required inputs → output | Event / payload | Acceptance; dependency |
|---|---|---|---|---|---|
| D-01 Magazine Feed | DISCOVER; find editorial entry points. | `/discover?view=magazine`; route/feed load. | eligible Story metadata → magazine feed. | `discover_viewed` {view:"magazine", theme}. | Empty and loading are explicit; source/provenance available on linked content. FRONT consumes release. |
| D-02 Story Bundle | CONTEXT; understand a cultural theme or article context. | `/story/:storyId`; story card/deep link. | Story/Article relations, typed RelatedArticle and RelatedLive, locale → detail context. | `story_opened` {storyId, source}. | Article-context relations remain typed; a live card requires eligibility/disclosure and cannot inherit editorial recommendation status. FRONT/PY relation contract. |
| D-03 Video Hero | CONTEXT; consume relevant video context. | DISCOVER/Story; hero selection. | approved video media, provenance, playback availability → hero state. | `video_hero_opened` {storyId, mediaId, status}. | Unavailable video preserves Story identity/context; no live implication. FRONT media adapter; PY/content release. |
| D-04 Related Place | CONTEXT → DISCOVER; move from story to place. | Story context; related-place action. | validated Story→Place FK → related-place navigation. | `related_place_opened` {originType:"story", originId, placeId}. | Broken/missing FK is not rendered as a target; back preserves Story. FRONT/PY FK dependency. |
| D-05 Magazine/Community Toggle | TRUST; choose context view. | `/discover`; `view` control/query. | allowed view value → navigation state. | `discover_view_changed` {view}. | Only magazine/community values allowed; Community availability state is explicit. FRONT owns route state. |
| D-06 Community Feed | TRUST; inspect governed social evidence. | `/discover?view=community`; view load. | readable CommunityPost, moderation/freshness/provenance → feed. | `community_opened` {viewMode, targetId?}. | No writable/public implication; unready content is unavailable, not fake engagement. FRONT consumes governed projection; PY/content dependency. |
| D-07 Save Story | INTENT; preserve a story. | Story detail/feed; save action. | saveable Story ID, profile/store → SavedItem mutation. | `item_saved` {targetType:"story", targetId, collection}. | Same idempotent semantics as G-07; unavailable original is labelled in Saved. FRONT owns action. |

## LIVE registry

| ID / name | Funnel; user problem / JTBD | Route and trigger | Required inputs → output | Event / payload | Acceptance; dependency |
|---|---|---|---|---|---|
| L-01 Live Home | DISCOVER/INTENT; find sessions. | `/live`; route load. | LiveSession projection → session hub. | `live_home_viewed` {category, statusFilter}. | Statuses are truthful; empty differs from provider error. FRONT consumes release. |
| L-02 Live Category Filter | DISCOVER; narrow sessions. | `/live`; filter interaction. | live taxonomy/filter → filtered sessions. | `live_filter_changed` {category, status}. | Invalid filter cannot create hidden session state. FRONT owns selection; PY/content provides labels. |
| L-03 Live Detail | CONTEXT/ACTION; inspect a session. | `/live/:sessionId`; card/deep link. | resolved LiveSession, typed related Articles/Places → detail state. | `live_session_opened` {sessionId, status}. | `LIVE`/`UPCOMING`/`REPLAY`/`ENDED` labels persist; invalid or action-unavailable target is S-07. FRONT/PY session projection. |
| L-04 Live Status | TRUST; know what can actually be watched. | Live home/detail; status presentation. | broadcast lifecycle, schedule/replay availability → visible status. | `live_status_viewed` {sessionId?, status}. | Never present replay/upcoming/ended as live or invent viewers. FRONT consumes status. |
| L-05 Chat Shell | TRUST; understand chat capability state. | Live detail; chat affordance. | session chat policy/status → shell, unavailable, or read-only state. | `chat_shell_viewed` {sessionId, capability}. | No fabricated messages or real-time claim. Provider/moderation dependency remains open. |
| L-06 Related Place | CONTEXT; connect session to place. | Live detail; related-place action. | validated LiveSession→Place FK → navigation. | `related_place_opened` {originType:"live", originId, placeId}. | Missing FK renders no target; return preserves Live context. FRONT/PY FK dependency. |
| L-07 Offer Card | ACTION; understand a possible offer. | Live/Place detail; eligible offer expansion. | Offer availability, disclosure, Partner reference → offer state. | `offer_opened` {offerId, offerType, availability}. | Absent availability/disclosure means no active CTA; unavailable/coming-soon is explicit. FRONT/PY or partner projection. |
| L-08 Partner CTA | ACTION; attempt next action safely. | Eligible Offer; CTA press. | eligible Offer, disclosed outbound target → outbound attempt. | `partner_cta_clicked` {offerId, partner, outboundType}. | Result is attempt/open failure only, never booking/purchase/revenue. FRONT adapter; business/provider dependency. |

## PROFILE registry

| ID / name | Funnel; user problem / JTBD | Route and trigger | Required inputs → output | Event / payload | Acceptance; dependency |
|---|---|---|---|---|---|
| P-01 Language | CONTEXT; read available content in a chosen locale. | `/settings`; language control. | supported locale → locale preference/fallback state. | `locale_changed` {locale}. | `ko/en` remains proposed MVP policy; absent translation is labelled, not silently substituted. FRONT/i18n; content locale data. |
| P-02 Interests | DISCOVER; express culture preference. | `/settings`; interest selection. | taxonomy IDs → profile interests. | `interests_updated` {count}. | Values conform to versioned taxonomy. FRONT persistence; PY uses only if an accepted recommendation contract does. |
| P-03 Visitor Mode | DISCOVER; tune context without changing product identity. | `/settings`; mode selection. | supported mode → TravelerProfile value. | `visitor_mode_updated` {mode}. | Does not split routes or products; manual edit is possible. FRONT persistence. |
| P-04 Local Preference Persistence | INTENT; retain settings safely. | `/settings`; preference mutation/reload. | valid preference set → persisted/local recovery state. | `profile_preferences_persisted` {storageMode}. | Storage/account model remains open; failure is visible and safe. FRONT storage adapter. |

## SYSTEM registry

| ID / name | User problem / route scope | Input → output | Event / acceptance | Dependency |
|---|---|---|---|---|
| S-01 Search | Find an eligible item across permitted projections. `/search`. | query + scoped index → results/empty/error. | `search_submitted` {queryLength, scope}; never claim a result not in index. | FRONT search boundary; PY/release index if data-backed. |
| S-02 Saved Hub | Return to saved intent. `/saved`. | SavedItem references + target state → grouped hub. | `saved_hub_viewed` {collection}; target retirement is visible. | FRONT persistence and target projections. |
| S-03 Locale Fallback | Understand missing translation on any localized surface. | requested locale + locale support → translated/original/unavailable disclosure. | `locale_fallback_shown` {requested, served, reason}; no silent language impersonation. | FRONT/i18n, content locale contract. |
| S-04 Loading | Know content is pending. All routes. | pending request → bounded loading state. | `loading_presented` may be sampled; no success semantics before data resolves. | FRONT request boundary. |
| S-05 Empty | Recover from a valid zero-result state. All relevant routes. | valid query/collection → empty recovery state. | `empty_state_viewed` {scope, reason}; distinguish from error. | FRONT plus source/release scope. |
| S-06 Error | Recover from failure. All routes. | failure classification → error/retry state. | `error_presented` {scope, class}; retain safe context. | FRONT/provider adapter. |
| S-07 Unavailable | Understand why known content/action cannot be used. All detail/action routes. | known target/status → reason and alternative. | `unavailable_presented` {targetType, reason}; no replacement target is implied. | FRONT plus entity status. |

## Legacy mapping and conflict disposition

| v2.1 expression | Canonical treatment |
|---|---|
| `G-06 Culture layer toggle` | Removed from canonical registry; non-MVP candidate. `G-06` is Place Detail. |
| `P-01 complete onboarding` | User flow composed from P-01~P-04; not an independent feature. |
| `P-02 select language` | P-01 Language. |
| `G-03 select place` | Distributed across G-03 rendering, G-05 preview, G-06 detail. |
| `D-01 toggle discover view` | D-05. |
| `D-03 open community evidence` | D-06. |
| `L-01 open live session` | L-03. |
| `L-02 open culture brief` | Context module; no independent canonical ID. |
| `I-01 save item` | G-07, D-07, and S-02 by target/state. |
| `I-02 share item` | G-08 for Place only; Story/Live sharing is not expanded yet. |
| `A-01 open partner CTA` | L-08. |
| `U-01 manage profile` | P-01~P-04. |

The formal disposition and affected branches are recorded in `07_DECISION_LOG.md` (DOC-002).
