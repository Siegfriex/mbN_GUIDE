# MBN GUIDE FRONT — Legacy Migration Intake & Dependency Audit

> Status: `DECISION_REQUIRED / PRE-IMPLEMENTATION`  
> Front branch verified: `nbM_GUIDE_FRONT`  
> Legacy source: `Siegfriex/bigdata-transportation-front` · `main` · `23ea067a79d8b7bccf06cc69c2a2e600a1e4bbcb`  
> Scope: read-only audit only. No legacy code, history, or data was copied, merged, cherry-picked, or modified.

---

## 1. Executive verdict

**레거시 마이닝은 가능하다. 단, 승인해야 할 방식은 전체 이관이 아닌 `Selective Migration`이다.**

legacy에는 React/Vite/TypeScript/Tailwind 실행 기반, FSD-like 분리, shared UI·storage·HTTP 경계가 있다. 반면 화면·상태·서버·데이터의 대부분은 교통 도메인에 결합되어 있다. 따라서 다음은 금지한다.

```text
전체 repository 복제
merge --allow-unrelated-histories
cherry-pick
legacy src 전체 copy
InteractiveMap 또는 교통 fixture의 이름만 변경
```

허용되는 흐름은 아래뿐이다.

```text
legacy commit 23ea067
  ↓ inventory and dependency-closure audit
REUSE / REWRITE / DROP / HOLD
  ↓
approved technical shell만 새 MBN target path에 이식
  ↓
fixture GUIDE vertical slice로 검증
```

---

## 2. Evidence snapshot

| Item | Observed value | Verdict |
|---|---|---|
| Legacy branch | `main` | 확인됨 |
| Legacy commit | `23ea067a79d8b7bccf06cc69c2a2e600a1e4bbcb` | Master Instruction 기준과 일치 |
| Audit checkout | same SHA, clean worktree | read-only inspection |
| Source size | 3,962 TS/TSX lines, 80+ paths | dependency closure audit 필요 |
| Runtime | React 19, Vite 6, TypeScript, Tailwind 4, Express, Vercel Function, Gemini | technical shell과 product server 혼재 |
| MBN FRONT current import | 없음 | migration not started |

### Audit criteria

| Check | Question | Consequence |
|---|---|---|
| Domain leak | station/subway/bus/bike/route/crowding/Gemini 등 교통 명사가 있는가? | DROP 또는 전면 REWRITE |
| Direct import | 무엇을 import하는가? | domain import면 단독 copy 금지 |
| Transitive closure | import가 route-plan/station/report/chat/server로 이어지는가? | closure 전체가 safe일 때만 REUSE |
| Runtime coupling | env, endpoint, server, package가 제품에 결합되는가? | 최소 runtime으로 재구성 |
| UI independence | 제품 명사 없는 container/toast/storage/HTTP인가? | REUSE 후보 |
| Contract fit | fixture/release adapter와 v2.1 contract에 맞는가? | MBN target path 부여 |

### Transport leak evidence

교통 domain 관련 검색 결과는 App/controller, station/route-plan/report entity, transport map, report widget, Gemini chat/server, settings·archive 등 다수 slice에 존재한다.

```text
station / subway / bus / bike / crowd / route / transit / boarding
carriage / taxi / late-night / Gemini / 통근 / 지하철 / 따릉이 / 막차 / 탈수있나
```

---

## 3. Decision vocabulary

| Decision | Meaning | Front action |
|---|---|---|
| `REUSE` | domain-free 기술 자산 | 최소 변경으로 selective copy 가능 |
| `REWRITE` | 구조·상호작용 패턴만 가치 있음 | source를 참고해 MBN path에서 새 작성 |
| `DROP` | 교통 도메인·Gemini transport·legacy business logic | 이식 금지 |
| `HOLD` | 현재 contract 또는 추가 audit가 필요 | 결정 전 이식 금지 |

**판정 단위는 파일명이 아니라 dependency closure다.** AppShell 하나라도 legacy navigation, transport label, domain route를 함께 끌고 오면 REUSE가 아니다.

---

## 4. File-level migration inventory

### 4.1 Tooling, deployment, runtime

| Legacy path | Purpose / closure | Decision | MBN target | Migration test |
|---|---|---|---|---|
| `package.json` | React/Vite/TS/Tailwind + Express/Gemini scripts | REWRITE | root `package.json` | clean install, client build |
| `package-lock.json` | locks legacy Gemini/Express dependencies | DROP | regenerate | lock reproducibility |
| `vite.config.ts` | React/Tailwind/alias + AI Studio HMR | REWRITE | root config | alias + dev smoke |
| `tsconfig.json` | generic ES2022/bundler baseline | REWRITE | root config | `tsc --noEmit` |
| `index.html` | Vite mount document | REWRITE | root | bootstrap smoke |
| `src/main.tsx` | StrictMode root mount | REWRITE | `src/main.tsx` | root render |
| `src/index.css` | Tailwind plus Apple dark/glass mesh | REWRITE | `src/index.css`, `shared/styles/**` | token/visual check |
| `.gitignore` | generic local ignore rules | HOLD | root | MBN release policy review |
| `vercel.json` | SPA rewrite + legacy `/api/chat` function | REWRITE | root | static SPA preview |
| `.env.example` | Gemini key/model and app URL | DROP | future MBN env only | no Gemini key |
| `server.ts` | Express + Gemini `/api/chat` | DROP | none | server endpoint absent |
| `api/chat.ts` | Vercel Gemini function | DROP | none | no legacy API route |
| `metadata.json` | AI Studio transport metadata | DROP | none | legacy term grep |
| `migrate.ts` | old chat markup rewrite script | DROP | none | absent from target |
| `scripts/phase7-smoke.ts` | static smoke but imports reports/routes/Gemini | REWRITE | future `scripts/mbn-smoke.ts` | MBN route/state smoke |
| legacy `README.md`, `.md`, `docs/**` | transportation product authority | DROP | none | MBN docs only |
| `LICENSE` | license text | HOLD | root | license review |

### 4.2 App, router, and pages

| Legacy path | Direct dependency / purpose | Decision | MBN target | Reason |
|---|---|---|---|---|
| `src/App.tsx` | controller, AI layer, transit map, old nav | DROP | new `src/App.tsx` | complete traffic closure |
| `src/app/model/useAppController.ts` | station/route/report/AI orchestration | DROP | none | monolithic traffic controller |
| `src/app/model/index.ts` | controller barrel | DROP | new barrel later | controller closure |
| `src/app/layouts/AppShell.tsx` | ReactNode + `cn`, Apple mesh classes | REWRITE | `app/layouts/AppShell.tsx` | structure useful; visual contract wrong |
| `src/app/layouts/index.ts` | AppShell barrel | REWRITE | same path | new public export |
| `src/app/router/AppRouter.tsx` | old TabId, Archive/Map/Settings pages | REWRITE | `app/router/AppRouter.tsx` | v2.1 route contract required |
| `src/app/router/index.ts` | router barrel | REWRITE | same path | route export smoke |
| `src/pages/index.ts` | archive/map/settings exports | DROP | new barrel | old IA |
| `src/pages/map-page/index.tsx` | MapWorkspace composition | DROP | `pages/guide-page/index.tsx` new | route/report closure |
| `src/pages/archive-page/index.tsx` | ArchiveCalendar composition | DROP | `pages/saved-page/index.tsx` new | report archive closure |
| `src/pages/settings-page/index.tsx` | transport settings composition | DROP | `pages/settings-page/index.tsx` new | transit preferences |

### 4.3 Shared layer

| Legacy path | Direct dependency / purpose | Decision | MBN target | Reason / test |
|---|---|---|---|---|
| `shared/lib/cn.ts` | no imports; class-string join | REUSE | same path | falsy value unit smoke |
| `shared/lib/time.ts` | Korean-only clock formatter | REWRITE | `shared/lib/date-time.ts` if needed | ko/en fallback |
| `shared/lib/markdown/**` | safe React renderer but Apple colors/chat presentation | HOLD | possible rich-text lib | token/i18n/a11y review |
| `shared/model/usePersistentState.ts` | generic `localStorage` hook | REWRITE | `shared/model/safe-storage.ts` | schema version/migration/private mode |
| `shared/api/http-client.ts` | fetch timeout, JSON/text parsing, typed errors | REUSE | same path | timeout/abort/error test |
| `shared/api/index.ts` | HTTP barrel | REUSE | same path | export smoke |
| `shared/ui/page-container/PageContainer.tsx` | ReactNode + `cn`, semantic main/scroll | REUSE | same path | landmark/scroll smoke |
| `shared/ui/page-container/index.ts` | barrel | REUSE | same path | export smoke |
| `shared/ui/toast/ToastOverlay.tsx` | Lucide + Apple glass/token literals | REWRITE | `shared/ui/toast/**` | portal/focus/mobile/token test |
| `shared/ui/toast/index.ts` | toast barrel | REWRITE | same path | export smoke |
| `shared/config/storage-keys.ts` | `talsu.*` keys | DROP | new config | MBN versioned keys only |
| `shared/config/query-keys.ts` | imports `RoutePlanOptions` | DROP | new entity/feature keys | no route-plan import |
| `shared/config/routes.ts` | map/archive/settings TabId | DROP | new app route contract | GUIDE/DISCOVER/LIVE test |
| `shared/config/z-index.ts` | generic order with legacy names | REWRITE | same path | semantic layer order |
| `shared/config/index.ts` | exports legacy config closure | DROP | new barrel | no legacy exports |

### 4.4 Widgets and reusable UI patterns

| Legacy path | Purpose / closure | Decision | MBN target | Condition |
|---|---|---|---|---|
| `widgets/bottom-navigation/BottomNavigation.tsx` | 3 tabs but old Map/Archive/Settings `TabId` | REWRITE | `widgets/bottom-navigation/**` | GUIDE/DISCOVER/LIVE only |
| `widgets/top-app-bar/TopAppBar.tsx` | old brand/user/reset header | REWRITE | `widgets/app-chrome/**` | Search/Saved/Profile utility contract |
| `features/complete-onboarding/ui/OnboardingOverlay.tsx` | multi-step overlay with train/bike/crowding | DROP | new onboarding later | TravelerProfile only |
| `widgets/settings-form/**` | station and transit preference form | DROP | new traveler settings | no transport fields |
| `widgets/archive-calendar/**` | saved report calendar | DROP | new saved hub | SavedItem target relation |
| `widgets/map-workspace/**` | route/map/report composition | DROP | new Guide workspace | Place view model only |
| `widgets/transit-map-panel/**` | 627-line SVG transport map | DROP | future `shared/map` + Guide widget | MapAdapter/list fallback, no rename-copy |
| `components/InteractiveMap.tsx` | transit-map compatibility export | DROP | none | no legacy facade |
| `widgets/report-sheet/**` | boarding/carriage/deadline/recovery views | DROP | new place detail sheet | Why→context→evidence→CTA |
| `widgets/ai-chat-panel/**` | AI traffic chat overlay | DROP | optional culture brief panel later | only after DOCS/PY contract |

### 4.5 Entities, features, data, server

| Legacy path | Purpose | Decision | MBN treatment |
|---|---|---|---|
| `entities/station/**` | station types/fixture | DROP | new `entities/place/**` from DOCS/PY |
| `entities/route-plan/**` | route plans/carriage survival | DROP | no route generator; future recommendation consumer only |
| `entities/report/**` | traffic reports/saved report store | DROP | new CultureBrief/SavedItem/Offer contracts |
| `entities/user-preferences/**` | transit user preferences | DROP | new TravelerProfile; storage pattern only |
| `entities/chat-message/**` | chat message type | HOLD | only if CultureBrief UX is approved |
| `features/generate-route-plan/**` | route calculation/preset | DROP | FRONT never ranks or recommends |
| `features/save-report/**` | report persistence/dedupe | DROP | new `save-item/**` by target type/id |
| `features/send-ai-chat/**` | Gemini schema/API/responder/fallback | DROP | no FRONT LLM transport |
| `features/toggle-map-layer/**` | transit map layers | DROP | future generic filter only if DOCS specifies |
| `src/data.ts`, `src/types.ts` | legacy facade/data exports | DROP | entity-owned MBN contracts |

---

## 5. Dependency-closure approval

### Initial direct REUSE closure

Only the following source closure is eligible for direct selective copy after normal attribution/license review.

```text
src/shared/lib/cn.ts
src/shared/api/http-client.ts
src/shared/api/index.ts
src/shared/ui/page-container/PageContainer.tsx
src/shared/ui/page-container/index.ts
```

These files have no observed transport import. `http-client` is generic infrastructure only; it does not authorize a new FRONT endpoint, PY computation, or unpinned release consumption.

### Rewrite-reference closure

The following may be inspected for structure but must be newly authored in MBN target paths.

```text
package.json, vite.config.ts, tsconfig.json, index.html, src/main.tsx
src/index.css, AppShell.tsx, AppRouter.tsx, usePersistentState.ts
ToastOverlay.tsx, z-index.ts, BottomNavigation.tsx, TopAppBar.tsx
vercel.json, scripts/phase7-smoke.ts
```

### Forbidden import closure

If a candidate import reaches any path below, migration fails until the dependency is fully removed.

```text
entities/station
entities/route-plan
entities/report
features/generate-route-plan
features/send-ai-chat
widgets/transit-map-panel
widgets/report-sheet
api/chat.ts
server.ts
```

---

## 6. Target recomposition

```text
src/
├─ app/{layouts,router,providers,model}
├─ pages/{guide,discover,live,place,story,live-detail,search,saved,settings}-page/
├─ widgets/{app-chrome,bottom-navigation,map-discovery-workspace,place-detail-sheet,magazine-feed,live-commerce-hub}/
├─ features/{filter-places,select-place,save-item,share-item,select-language,open-partner-cta}/
├─ entities/{place,article,story-bundle,live-session,offer,recommendation}/
└─ shared/{api,config,i18n,lib,styles,ui,types}/
```

Constraints:

- Place/Article/StoryBundle/LiveSession/Offer/Recommendation은 legacy rename이 아니라 DOCS/PY contract 기반 신규 entity다.
- MapAdapter는 legacy SVG map wrapper가 아니다. provider 미결 전에는 list fallback과 mock canvas만 사용한다.
- Recommendation은 PY projection consumer다. FRONT가 similarity·taxonomy·ranking score를 계산하지 않는다.
- Saved는 legacy archive rename이 아니라 `SavedItem(targetType, targetId)` utility다.
- Bottom navigation은 GUIDE/DISCOVER/LIVE만 소유한다.

---

## 7. Execution gates

### M-0 — Legacy intake

| Required output | Status |
|---|---|
| fixed source SHA | PASS |
| file/dependency inventory | PASS: this report |
| REUSE/REWRITE/DROP/HOLD decision | PASS: Sections 3–5 |
| source provenance | PASS |

M-0은 source copy 승인 자체가 아니라 decision evidence다.

### M-1 — Technical shell extraction

Allowed:

```text
tooling baseline audit
approved direct REUSE closure
new AppShell/router/shared UI from REWRITE references
safe storage, HTTP boundary, static Vercel boundary
```

Forbidden:

```text
Place/MBN/PY data
transport feature import
Gemini endpoint
legacy page/widget/entity copy
```

Gate: `npm ci`, typecheck, client build, legacy-term grep 0, no `api/chat.ts`/`server.ts`/transport import.

### M-2 — MBN recomposition

Requires a DOCS commit SHA and `contractVersion`. Then FRONT may build GUIDE/DISCOVER/LIVE routing, ko/en fallback, universal states, fixture/release adapter interfaces, Saved/Profile persistence, and warm culture-first tokens.

### M-3 — First vertical slice

```text
/guide → category filter → fixture Place list/map fallback
       → discovery tray → /place/:placeId → whyItMatters → save
```

This validates the consumer contract. It must not copy `InteractiveMap.tsx`, geocode an address, generate a score, or claim a PY release exists.

---

## 8. Decision register

| ID | Decision | Recommended owner | Status | Blocks |
|---|---|---|---|---|
| L-DEC-01 | approve Selective Migration | FRONT owner | PENDING | M-1 |
| L-DEC-02 | approve initial REUSE closure | FRONT owner | PENDING | any source copy |
| L-DEC-03 | promote v2.1 Product/Data Contract to DOCS | DOCS owner | PENDING | M-2 semantics |
| L-DEC-04 | pin fixture `contractVersion` | DOCS + FRONT | PENDING | F2/M-2 |
| L-DEC-05 | define first PY release scope | PY + DOCS | REQUIRED | releaseAdapter |
| L-DEC-06 | select map provider | Product/infra | OPEN | real map SDK |
| L-DEC-07 | resolve `.git` wrapper/worktree policy | workspace owner | REQUIRED | protocol automation |

### Recommended approval scope

```text
REUSE: cn.ts, http-client.ts/API barrel, PageContainer/barrel
REWRITE: tooling, shell, router, toast, persistence, config, nav, Vercel, smoke
DROP: all transport domain/map/AI/server/data/widgets/pages/entities/features
```

---

## 9. Final finding

**레거시 마이닝은 가능하지만 legacy를 기반 앱으로 복제하는 것은 부적합하다.** `23ea067`에서 직접 재사용 가능한 closure는 작고 명확하다. 성공 기준은 코드 복사량이 아니라 MBN GUIDE Product/Data Contract를 침범하지 않는 기술 shell의 재사용이다.
