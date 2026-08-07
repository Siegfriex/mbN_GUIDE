# MBN GUIDE Information Architecture and User Flow

Document: `02_IA_USER_FLOW`
Status: `PROPOSED`
Authority: Normative navigation-state contract
Contract Version: `0.1.0`
Owner: MBN GUIDE Product Architecture & Documentation Director
Upstream Authority: `00_PRODUCT_CONSTITUTION.md`, `01_PRD.md`
Downstream Consumers: `03`, `06`, FRONT
Last Updated: 2026-08-07
Supersedes: Integrated v2.1 route section
Change Rule: Route or navigation-state changes require feature/event impact review and a `07` entry.

## Information architecture

```text
Primary surfaces:  GUIDE | DISCOVER | LIVE
Utility layer:     Search | Saved | Language | Profile | Settings
Details:           Place | Story | LiveSession
```

Magazine and Community are views of DISCOVER, not separate primary surfaces. Utility routes must not displace the primary surface hierarchy.

## Canonical route contract

| Route | Surface | Required parameter | Optional query | Screen responsibility | Allowed exits | Relevant IDs |
|---|---|---|---|---|---|---|
| `/guide` | GUIDE | — | area, category, time/context filter | Establish area and render discoverable Places with map/list fallback. | Place, Search, Saved, Settings | G-01~G-05, S-01, S-02, S-04~S-07 |
| `/place/:placeId` | GUIDE detail | `placeId` | entry point, preserved source context | Resolve a Place and present context before eligible action. | Story, Live, Save, Share, Guide | G-06~G-08, D-04, L-06~L-08, S-03~S-07 |
| `/discover` | DISCOVER | — | `view=magazine|community`, theme/filter | Present editorial feed or governed CommunityPost feed. | Story, Place, Saved | D-01, D-03, D-05, D-06, S-01~S-07 |
| `/story/:storyId` | DISCOVER detail | `storyId` | entry point | Explain a Story and its related Places/live context. | Place, Live, Save, Discover | D-02, D-04, D-07, S-03~S-07 |
| `/live` | LIVE | — | category, status | Present LiveSession set by category and truthful status. | Live detail, Place, Saved | L-01, L-02, L-04, S-01~S-07 |
| `/live/:sessionId` | LIVE detail | `sessionId` | entry point | Present a session, chat shell state, related Place, Offer, and eligible CTA. | Place, Saved, Live | L-03, L-05~L-08, S-03~S-07 |
| `/search` | Utility | — | query, scope | Search eligible index/projection; never invent a result. | Detail, Guide, Discover, Live | S-01, S-04~S-07 |
| `/saved` | Utility | — | collection, target filter | Resolve saved targets and their current availability. | Original target, Settings | S-02, S-04~S-07 |
| `/settings` | Utility | — | section | Manage language, interests, visitor mode, and persistence. | Prior route | P-01~P-04, S-04~S-07 |

The canonical route set deliberately contains no separate Community primary route. A community view is `/discover?view=community`.

## Entry, exit, and state preservation

| Entry | Destination | Preserve | Back behavior | Failure behavior |
|---|---|---|---|---|
| Guide marker/card | Place detail | area, category/filter, map viewport, selected source | Restore prior GUIDE state. | Unknown/unavailable `placeId` renders S-07; no substitute Place. |
| Discover Story | Story detail or related Place | discover view/theme, originating story ID | Return to Story then its prior DISCOVER state. | Missing relation is an empty relation section, not a fabricated link. |
| Live card | Live detail | status filter and list position | Return to LIVE hub. | Invalid session uses S-07 with LIVE return route. |
| Related Place | Place or GUIDE | origin type/ID | Preserve origin in history state. | Unresolved Place is S-07; origin remains available. |
| Saved item | Original target | collection/filter | Return to Saved hub. | Retired/unavailable target is labelled; Saved record is not silently deleted. |
| Deep link | Matching detail | path parameter and safe query | Browser/history semantics apply. | Parameter validation failure is S-06 or S-07 depending on cause. |

## Cross-surface user flows

```text
GUIDE → Place preview → Place detail → context/Story/community → Save or eligible Offer
DISCOVER → Story → linked Place → GUIDE or Place detail → Save/live/Offer context
LIVE → Live detail → related Place/context → disclosed Offer → Partner CTA attempt
```

Disallowed flows: Offer-first GUIDE entry; partner CTA from a Story with no contextual Place/Story relationship; writable/real-time Community when its operational state is not ready; a live-looking state without a real LiveSession state.

## Screen state contract

Every route supports the system-state semantics in `03`: Loading, Empty, Error, and Unavailable. A provider failure must retain an alternative where one is contractually possible (for example, GUIDE map failure → list fallback). Loading is not a blank-success state; Empty is not Error; Unavailable identifies a known target/action that cannot currently be used.

## Ownership boundary

This document defines routes, screen responsibility, and state preservation. It does not prescribe component names, folders, router library, map SDK, player provider, or rendering hierarchy. Those choices remain implementation concerns bounded by `06_TECH_ARCHITECTURE_CONSTRAINTS.md`.
