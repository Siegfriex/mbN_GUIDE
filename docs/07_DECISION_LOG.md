# MBN GUIDE Decision Log

Document: `07_DECISION_LOG`
Status: `PROPOSED`
Authority: Decision audit trail for normative product contracts
Contract Version: `0.1.0`
Owner: MBN GUIDE Product Architecture & Documentation Director
Upstream Authority: User-directed product constitution and v2.1 candidate
Downstream Consumers: `00~06`, FRONT, PY
Last Updated: 2026-08-07
Supersedes: Integrated v2.1 open-decision register
Change Rule: Every material product/route/feature/schema/business decision uses the template below. Status is only `PROPOSED`, `ACCEPTED`, `SUPERSEDED`, or `REJECTED`.

## Decision template

```text
Decision ID:
Date:
Status:
Context:
Decision:
Reason:
Rejected Alternatives:
Affected Contracts:
Affected Branches:
Migration Required:
```

## Seed decisions

### GOV-001 — Branch sovereignty

Decision ID: `GOV-001`
Date: 2026-08-07
Status: `ACCEPTED`
Context: The repository has independent DOCS, FRONT, and PY branches.
Decision: Only `nbM_GUIDE_DOCS` may be modified for product/documentation SSOT work; FRONT/PY are read-only references.
Reason: Preserve ownership, auditability, and non-interference.
Rejected Alternatives: Cross-branch edits, merge/cherry-pick/rebase, or treating another branch as product fact.
Affected Contracts: `00~07`.
Affected Branches: `nbM_GUIDE_DOCS`, `nbM_GUIDE_FRONT` (consumer), `nbM_GUIDE_PY` (consumer).
Migration Required: No.

### P-001 — Primary surface model

Decision ID: `P-001`
Date: 2026-08-07
Status: `ACCEPTED`
Context: Product navigation and context need a stable center.
Decision: Primary surfaces are GUIDE → DISCOVER → LIVE; Search/Saved/Language/Profile/Settings are Utility Layer.
Reason: Location discovery, context/trust, and action are the product funnel; utilities are supporting capabilities.
Rejected Alternatives: Four equal GNB tabs; separate Community primary surface.
Affected Contracts: `00`, `01`, `02`, `03`, `06`.
Affected Branches: DOCS, FRONT.
Migration Required: Yes — previous navigation descriptions cannot be treated as canonical.

### P-002 — MBN and culture taxonomy boundary

Decision ID: `P-002`
Date: 2026-08-07
Status: `ACCEPTED`
Context: MBN and individual genres could be mistaken for the product core.
Decision: MBN is a Content/IP/Provenance Layer; culture is the product domain; trot and other genres are taxonomy/tag extensions.
Reason: Maintain culture-first discovery and support expansion without product fragmentation.
Rejected Alternatives: MBN-only dataset/product identity; genre-specific primary IA.
Affected Contracts: `00`, `01`, `04`, `05`.
Affected Branches: DOCS, FRONT, PY.
Migration Required: Yes — source labels and taxonomy semantics must remain separate.

### DOC-001 — v2.1 candidate adoption and SSOT decomposition

Decision ID: `DOC-001`
Date: 2026-08-07
Status: `PROPOSED`
Context: `MBN_GUIDEBOOK_PRODUCT_FUNCTION_SPEC_V2.md` v2.1 is an integrated Product SSOT Candidate, but `docs/00~07` did not exist.
Decision: Adopt its compatible normative content by decomposing it into the eight-document SSOT tree; retain it as reference rather than a parallel authority after acceptance.
Reason: Establish one answer for product, route, feature, data, business, architecture, and decision provenance.
Rejected Alternatives: Keep one integrated document as the continuing SSOT; create implementation-observation documents before implementation.
Affected Contracts: `00~07`.
Affected Branches: DOCS; FRONT/PY are downstream consumers.
Migration Required: Yes — cross-document traceability and references must use `00~07` when accepted.

### DOC-002 — Canonical feature registry and legacy disposition

Decision ID: `DOC-002`
Date: 2026-08-07
Status: `ACCEPTED`
Context: v2.1 reuses IDs with conflicting meanings and uses temporary `I-*`, `A-*`, and `U-*` namespaces.
Decision: Use the constitutional G-01~G-08, D-01~D-07, L-01~L-08, P-01~P-04, S-01~S-07 registry in `03`. `G-06` means Place Detail; Save maps to G-07/D-07/S-02; Place share maps to G-08; partner CTA maps to L-08.
Reason: Stable IDs preserve traceability from problem to route, data, event, and acceptance.
Rejected Alternatives: Preserve overloaded v2.1 IDs; introduce additional canonical `I-*`, `A-*`, or `U-*` namespaces.
Affected Contracts: `02`, `03`, `04`, `06`.
Affected Branches: DOCS, FRONT, PY.
Migration Required: Yes — consumers must map legacy labels per `03`; `G-06 Culture layer toggle` is a non-MVP candidate, not a canonical feature.

### GOV-002 — Normative versus observed documentation

Decision ID: `GOV-002`
Date: 2026-08-07
Status: `ACCEPTED`
Context: No implementation evidence is in scope and all branches initially point at the same initial commit.
Decision: `00~07` are normative pre-implementation contracts. `08~10` are created only after implementation and contain observed facts/evidence.
Reason: Prevent plans, provider choices, or reference code from being recorded as current reality.
Rejected Alternatives: Create code/FSD/current-implementation documents now; infer implementation facts from sibling branches.
Affected Contracts: `00`, `06`, future `08~10`.
Affected Branches: DOCS, FRONT, PY.
Migration Required: No.

### EXP-001 — First prototype geography

Decision ID: `EXP-001`
Date: 2026-08-07
Status: `PROPOSED`
Context: A bounded initial geography may make a prototype tractable.
Decision: Use Seoul as the first prototype geography while retaining an expandable area schema.
Reason: Suggested v2.1 boundary; no validated source/coverage evidence is asserted.
Rejected Alternatives: Nationwide launch scope; geography fixed in type/route semantics.
Affected Contracts: `01`, `02`, `04`, `06`.
Affected Branches: DOCS, FRONT, PY.
Migration Required: No until accepted.

### EXP-002 — Community MVP exposure

Decision ID: `EXP-002`
Date: 2026-08-07
Status: `PROPOSED`
Context: Community trust value requires moderation, abuse, policy, and operations readiness.
Decision: Limit MVP community to curated/read-only material; do not authorize public writing.
Reason: Preserve truthful trust signals and avoid unsupported moderation claims.
Rejected Alternatives: Open write/public community at MVP; fake read/write activity.
Affected Contracts: `01`, `02`, `03`, `04`, `05`.
Affected Branches: DOCS, FRONT, PY.
Migration Required: No until accepted.

### EXP-003 — Locale, profile, and release handoff

Decision ID: `EXP-003`
Date: 2026-08-07
Status: `PROPOSED`
Context: MVP locale scope, preference location, and FRONT↔PY artifact identity need product owner confirmation.
Decision: Make `ko/en` required MVP locales, manage profile preferences through `/settings`, and require immutable `releaseId` manifest consumption.
Reason: v2.1 recommendation supports explicit locale disclosure and reproducible handoff, but provider/account implementation is not selected.
Rejected Alternatives: Silent locale substitution; scattered profile routes; latest/working-directory data consumption.
Affected Contracts: `02`, `03`, `04`, `06`.
Affected Branches: DOCS, FRONT, PY.
Migration Required: Yes if an unpinned release or incompatible locale behavior exists later.

### EXP-004 — External provider and commerce selection

Decision ID: `EXP-004`
Date: 2026-08-07
Status: `PROPOSED`
Context: Map provider, live provider, commerce partner, and account model are not confirmed.
Decision: Keep each behind an adapter and expose only truthful unavailable/coming-soon/outbound-attempt semantics.
Reason: Product contract must survive provider choice and must not claim a partnership/transaction.
Rejected Alternatives: Name a provider/partner as current fact; embed provider DTOs or checkout semantics in domain objects.
Affected Contracts: `03`, `04`, `05`, `06`.
Affected Branches: DOCS, FRONT, PY.
Migration Required: No until a provider/partner decision is accepted.

## Open decision queue

All open questions are represented by `PROPOSED` decisions above. Before implementation-gate opening, the product owner must accept, reject, or supersede the relevant decision and trigger the stated impact review. No absence of a decision authorizes an implementation assumption.
