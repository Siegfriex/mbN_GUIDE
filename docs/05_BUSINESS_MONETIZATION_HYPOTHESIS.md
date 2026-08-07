# MBN GUIDE Business and Monetization Hypothesis

Document: `05_BUSINESS_MONETIZATION_HYPOTHESIS`
Status: `PROPOSED`
Authority: Normative business-safety boundary and hypothesis register
Contract Version: `0.1.0`
Owner: MBN GUIDE Product Architecture & Documentation Director
Upstream Authority: `00_PRODUCT_CONSTITUTION.md`, `01_PRD.md`, `04_CONTENT_DATA_CONTRACT.md`
Downstream Consumers: `03`, `06`, FRONT, PY, future business/partner owners
Last Updated: 2026-08-07
Supersedes: Integrated v2.1 monetization section
Change Rule: A commercial claim, disclosure rule, partner state, or conversion definition change requires `07` decision and legal/operational review where applicable.

## Business safety contract

Commerce is downstream of context and trust. The current product fact is limited to: an Offer can exist; it can declare availability and disclosure; an outbound CTA can exist; and a user can attempt that CTA.

The following are prohibited until separately evidenced and contracted: real inventory, price/discount truth, reservation success, purchase completion, order status, settlement, revenue, fake urgency, or implied partner endorsement. `partner_cta_clicked` is not purchase, booking, conversion revenue, or attribution proof.

| Item | Required handling |
|---|---|
| Offer | Show type, availability, disclosure, and known limitations consistently in card/detail/live contexts. |
| Partner | Keep partner identity/status/provenance separate from organic/editorial context. No partner is implied by an outbound URL alone. |
| Sponsored content | Mark sponsored/partner provenance visibly and keep it out of organic ranking semantics unless an accepted policy defines treatment. |
| Unavailable action | Use unavailable/coming-soon or a non-transactional alternative; do not manufacture stock or waitlist promises. |
| Measurement | Report outbound attempts/CTR with denominator and limits; never relabel them as completed commerce. |

## Business hypotheses

| ID | Hypothesis | Candidate measurement | Explicit limitation |
|---|---|---|---|
| BM-H01 | A disclosed outbound partner CTA can create useful next-action intent after culture context. | Outbound CTR after `offer_opened`. | Click is not a completed transaction. |
| BM-H02 | Live/session context can improve relevance of an Offer. | Live→Offer→CTA sequence rate. | No causal or revenue conclusion without experiment/partner data. |
| BM-H03 | Clearly marked branded content can coexist with editorial trust. | Disclosure interaction, retention/survey. | Requires policy, moderation, and research; not an accepted revenue claim. |
| BM-H04 | Sponsored discovery may be viable when provenance and ranking separation are explicit. | Sponsored exposure/CTA quality metrics. | Cannot weaken organic relevance or be inserted without disclosure policy. |
| BM-H05 | A qualified outbound lead may have value to a partner. | Partner-confirmed downstream data, if lawfully available. | No lead/revenue claim exists before partner instrumentation and consent. |

## Open dependencies

Commerce partner, live provider, contract/settlement model, inventory availability source, reservation confirmation, and user consent/legal obligations are not selected. Their absence is a product state, not a prompt to simulate a checkout.

## Promotion questions before commercial expansion

Before any claim beyond outbound attempt, decide and record: partner identity and legal basis; source of offer truth; display/refresh SLA; disclosure wording/location; sponsored ranking treatment; cross-domain consent and attribution; cancellation/refund/support ownership; moderation and consumer-protection obligations. A decision may be proposed without enabling the feature.
