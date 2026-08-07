# MBN GUIDE FRONT — 의사결정 상태·정합성 보고서

> Report type: `READ-ONLY STATUS / DECISION REPORT`  
> Audit date: 2026-08-07 (Asia/Seoul)  
> Write scope observed: `nbM_GUIDE_FRONT` working tree only  
> Purpose: Product/Data Contract, branch sovereignty, FRONT readiness, legacy migration, PY release consumption의 현재 정합성을 기록한다.  
> Implementation: 없음. 이 보고서는 코드·다른 브랜치·원격 상태를 변경하지 않는다.

---

## 1. Executive verdict

### 결론

**현재 상태는 `DOCUMENT_DESIGN_READY / CONTRACT_PROMOTION_BLOCKED / FRONT_IMPLEMENTATION_NOT_STARTED / PY_RELEASE_NOT_AVAILABLE`다.**

v2.1 명세는 GUIDE / DISCOVER / LIVE 3개 Primary Surface, Article-first 데이터 경로, release manifest, adapter 경계를 상세히 정의한 유효한 **후보 문서**다. 그러나 이 문서는 현재 `nbM_GUIDE_FRONT` 작업 트리의 untracked 파일이고, Product SSOT 권한인 `nbM_GUIDE_DOCS`에는 아직 publish되지 않았다.

따라서 현재 FRONT는 다음 두 작업만 정합하게 시작할 수 있다.

1. Product semantics를 새로 추정하지 않는 **기술 shell / shared primitive / adapter interface** 준비
2. v2.1의 pinned contract version을 가진 **deterministic fixture release** 기반 UX 검증

아래 작업은 아직 시작하면 안 된다.

- DOCS branch 권한을 대신해 Product Contract를 확정·승격하는 일
- PY 역할인 source mining, 본문 parsing, geocoding, embedding, ranking, recommendation 계산
- `releaseId`/manifest 없는 PY 산출물을 실제 data release로 소비하는 일
- map SDK, live provider, commerce partner, 결제 완료 상태를 확정 구현하는 일

---

## 2. Evidence snapshot

### 2.1 Repository and branch

| 항목 | 관측값 | 판단 |
|---|---|---|
| Repository | `https://github.com/Siegfriex/mbN_GUIDE.git` | 확인됨 |
| Authorized branch | `nbM_GUIDE_FRONT` | 확인됨 |
| Local HEAD | `ace484a58a9d53a2bccf312e4b7c947c9850284d` | Initial commit |
| HEAD subject | `Initial commit` | 구현 baseline 없음 |
| Remote `nbM_GUIDE_FRONT` | `ace484a58a9d53a2bccf312e4b7c947c9850284d` | local HEAD와 일치 |
| Remote `nbM_GUIDE_DOCS` | `ace484a58a9d53a2bccf312e4b7c947c9850284d` | FRONT와 같은 initial commit |
| Remote `nbM_GUIDE_PY` | `ace484a58a9d53a2bccf312e4b7c947c9850284d` | FRONT와 같은 initial commit |

원격 세 branch가 같은 SHA를 가리킨다. 이 사실은 branch 분리가 선언되어 있으나, DOCS contract나 PY producer artifact가 원격 history에 아직 publish되지 않았음을 뜻한다.

### 2.2 Baseline tree and working tree

| 범위 | 관측값 | 정합성 영향 |
|---|---|---|
| Committed tree | `LICENSE`, `README.md`만 존재 | React/Vite/FSD/adapter 구현 없음 |
| Committed README | 두 줄의 초기 placeholder | Product SSOT로 사용 불가 |
| Working-tree README | 660행 규모의 기존 4탭 PRD 초안 | v2.1과 navigation 충돌 |
| Working-tree v2.1 | `MBN_GUIDEBOOK_PRODUCT_FUNCTION_SPEC_V2.md`, 1,387행 | 상세 후보 명세이나 untracked |
| `src/`, `package.json`, test config | 없음 | typecheck/lint/build/smoke 실행 불가 |
| `data/90_exports/frontend/<releaseId>` | 없음 | PY release 소비 불가 |

### 2.3 Git environment exception

작업 경로의 `.git`은 읽기 전용 tmpfs mount라서 표준 `git branch --show-current`은 `not a git repository`로 실패한다. 현재 환경에서는 별도 Git metadata 경로 `.mbN_GUIDE_FRONT.git`을 명시할 때만 branch/status를 확인할 수 있다.

```text
git branch --show-current                 → 실패 (read-only placeholder .git)
git --git-dir="$PWD/.mbN_GUIDE_FRONT.git" branch --show-current
                                           → nbM_GUIDE_FRONT
```

이는 repository history의 문제가 아니라 작업 환경의 제약이다. 그러나 Master Instruction의 "모든 write 전 표준 git branch 확인"을 그대로 만족시킬 수 없다는 운영 리스크다.

---

## 3. Contract hierarchy and authority status

### 3.1 권한 모델

```text
nbM_GUIDE_DOCS  = Product/Data Contract authority
nbM_GUIDE_PY    = Data / Algorithm / Release producer
nbM_GUIDE_FRONT = ViewModel / UX consumer
```

### 3.2 현재 권한과 실제 artifact의 차이

| 계약 층 | 권한 branch | 필요한 artifact | 현재 존재 여부 | 상태 |
|---|---|---|---|---|
| Product constitution / PRD | DOCS | approved docs commit | 없음 | BLOCKED |
| IA / routes / feature IDs | DOCS | approved IA + feature spec | 없음 | BLOCKED |
| Data contract | DOCS | Article/Place/Offer/Release schema | 없음 | BLOCKED |
| Source/corpus/geo/embedding | PY | pipeline evidence | 없음 | NOT_STARTED |
| Frontend release | PY | releaseId, manifest, projections, quality report | 없음 | NOT_AVAILABLE |
| UX technical shell | FRONT | React/Vite/FSD baseline | 없음 | NOT_STARTED |
| v2.1 specification | FRONT working tree | candidate design document | 있음, untracked | CANDIDATE_ONLY |

### 3.3 SSOT 정합성 판정

| 비교 | 결과 | 근거 | 조치 |
|---|---|---|---|
| v2.1 vs Front Master Instruction | 대체로 정합 | 3 Primary Surface, Utility layer, fixture/release adapter, provenance, UI 상태 | v2.1을 DOCS authority로 승격할 때 line review |
| v2.1 vs working-tree README | 불일치 | README는 `4탭 GNB`, 지도/매거진/라이브/설정을 명시; v2.1은 GUIDE/DISCOVER/LIVE | DOCS branch에서 하나의 constitution으로 결정 |
| v2.1 vs committed repository | 미정 | committed HEAD에는 v2.1·코드·docs가 없음 | candidate를 commit/publish하기 전 권위 없음 |
| Front Master Instruction vs remote DOCS/PY | 미정 | branch role은 선언됐으나 remote artifact 없음 | DOCS/PY owner의 첫 publish 필요 |
| Product contract vs PY release contract | 설계상 정합, 실행상 미정 | v2.1에 Article/Geo/Recommendation/manifest 정의 | PY release가 나오기 전 검증 불가 |

---

## 4. Product and UX decision status

### 4.1 Navigation and primary surface

| Decision | Candidate decision | Current reality | Status | Required authority |
|---|---|---|---|---|
| Primary surface | `GUIDE / DISCOVER / LIVE` | README는 지도 / 매거진 / 라이브 / 설정 | CONFLICT | DOCS |
| Settings | Utility route `/settings` | README에서는 4번째 GNB | CONFLICT | DOCS |
| Magazine + Community | DISCOVER 내부 `view=magazine|community` | README는 매거진/커뮤니티 혼합 탭이나 4탭 모델 | PARTIAL | DOCS |
| MBN IP | provenance/content trust layer | README는 MBN 추천을 product feature로 폭넓게 서술 | PARTIAL | DOCS |
| 트로트 | `music`의 detail tag | 별도 확정 artifact 없음 | OPEN | DOCS |

### 4.2 Core UX contract

| UX decision | v2.1 candidate | Master Instruction | 정합성 | 구현 상태 |
|---|---|---|---|---|
| GUIDE 핵심 | area/category/filter/pin/tray | 동일 | PASS | NOT_STARTED |
| Place detail 순서 | Why → context/evidence → save/share → CTA | 동일 | PASS | NOT_STARTED |
| DISCOVER | Magazine/Community toggle | 동일 | PASS | NOT_STARTED |
| Community MVP | curated/read-only 가능 | 동일 | PASS | NOT_STARTED |
| LIVE states | live/upcoming/replay/unavailable | 동일 | PASS | NOT_STARTED |
| Fake UI 금지 | fake chat/count/commerce 금지 | 동일 | PASS | NOT_STARTED |
| i18n | `ko`, `en`, 명시 fallback | 동일 | PASS | NOT_STARTED |

### 4.3 UI state contract

v2.1은 `loading`, `empty`, `error`, `denied`, `unavailable`, `disabled`를 정의하고 있다. Master Instruction의 `IDLE / LOADING / SUCCESS / EMPTY / ERROR / UNAVAILABLE` 및 commerce 상태와 의미는 일치한다.

단, 실제 component/state machine이 없으므로 상태 계약의 **문서 정합성은 PASS**, 구현 검증은 **NOT_STARTED**다.

---

## 5. Data intelligence and release-consumption status

### 5.1 v2.1 설계 계약 평가

| 영역 | v2.1 계약 | Master Instruction / producer 분리와의 정합성 | 현재 실행 상태 |
|---|---|---|---|
| Article corpus | ArticleIndex/ArticleBody, SHA, parser status | PASS: FRONT가 parser를 소유하지 않음 | NOT_STARTED in PY |
| Place resolution | mention → candidate → geocode → canonical → Place | PASS: FRONT geocoding 금지 | NOT_STARTED in PY |
| Geo failure | RESOLVED/AMBIGUOUS/NOT_FOUND/ERROR | PASS: 실패를 map pin으로 승격하지 않음 | NOT_STARTED in PY |
| Embedding/relation | model/revision/dimension/top-k trace | PASS: FRONT embedding 금지 | NOT_STARTED in PY |
| Recommendation | retrieval → ranking, score/reason/version | PASS: FRONT score 생성 금지 | NOT_STARTED in PY |
| Generation provenance | editorial/rule/retrieval/LLM/hybrid | PASS: whyItMatters 출처 추적 | NOT_STARTED in PY/DOCS |
| Release bundle | releaseId, manifest, SHA, quality report | PASS: FRONT는 projection consumer | NOT_AVAILABLE |

### 5.2 Release consumption verdict

**현재 소비 가능한 PY release는 없다.**

필수 release path와 artifact는 아래와 같지만 committed tree, working tree, 원격 PY branch 어느 곳에도 존재하지 않는다.

```text
data/90_exports/frontend/<releaseId>/
├─ manifest.json
├─ places.json
├─ articles.json
├─ stories.json
├─ recommendations.json
├─ taxonomy.json
└─ quality_report.json
```

그러므로 현재 FRONT는 `releaseAdapter`를 실제 data source로 연결할 수 없다. 사용 가능한 유일한 정합한 대안은 `contractVersion`을 명시한 `fixtureAdapter`이며, 이를 empirical release 또는 PY 결과로 표현해서는 안 된다.

### 5.3 P5–P9 Data Intelligence Gates

| Gate | 현재 | 판단 | FRONT 영향 |
|---|---|---|---|
| P5 Source readiness | source scope/index/body artifact 없음 | BLOCKED | Article 기반 UI에는 fixture만 사용 |
| P6 Geo readiness | place candidate/geocode artifact 없음 | BLOCKED | map SDK 대신 list/map mock fallback만 허용 |
| P7 Semantic readiness | embedding/relation artifact 없음 | BLOCKED | "관련" 추천은 curated fixture만 허용 |
| P8 Recommendation readiness | candidate/ranking/reason artifact 없음 | BLOCKED | algorithmic recommendation UI 금지 |
| P9 Release readiness | manifest/SHA/quality report 없음 | BLOCKED | releaseAdapter/preview promotion 금지 |

---

## 6. FRONT architecture and migration readiness

### 6.1 Legacy baseline

| 항목 | 관측값 | 판단 |
|---|---|---|
| Source repository | `Siegfriex/bigdata-transportation-front` | 접근 가능한 기술 기준선 |
| Source branch / SHA | `main` / `23ea067a79d8b7bccf06cc69c2a2e600a1e4bbcb` | Master Instruction 기준과 일치 |
| Reuse policy | shell, responsive layout, router pattern, shared UI, toast/sheet, persistence, HTTP/schema, Vercel boundary | 정합 |
| Exclusion policy | station/subway/bus/bike/crowding/route risk/transit map/Gemini 교통 prompt/copy | 정합 |
| Current import | 없음 | NOT_STARTED |

### 6.2 FSD readiness

| FSD layer | Contracted responsibility | Current files | Status |
|---|---|---|---|
| `app` | provider/router/global layout | 없음 | NOT_STARTED |
| `pages` | URL 해석/widget composition | 없음 | NOT_STARTED |
| `widgets` | Guide/Detail/Discover/Live 큰 화면 블록 | 없음 | NOT_STARTED |
| `features` | save/filter/select/CTA 등 행동 | 없음 | NOT_STARTED |
| `entities` | Place/Story/Live/Offer ViewModel/schema | 없음 | NOT_STARTED |
| `shared` | UI primitive/i18n/analytics/map base | 없음 | NOT_STARTED |

### 6.3 Adapter readiness

| Adapter | Required mode | Current state | Decision |
|---|---|---|---|
| Place/Story/Live/Offer repository | fixture + release, future live API | 없음 | F2에서 interface만 먼저 생성 가능 |
| Map adapter | mock/list fallback, future provider | 없음 | P6 전 SDK 선정 금지 |
| Partner CTA adapter | unavailable/coming soon/outbound | 없음 | P4 contract를 준수해 shell만 가능 |
| Safe storage | local profile/saved item | 없음 | F1/F2에서 구현 가능 |
| i18n adapter | ko/en and explicit fallback | 없음 | F1에서 구현 가능 |
| Analytics adapter | contract event payload | 없음 | F1 interface, F7 verification |

---

## 7. Branch sovereignty and safety audit

| Rule | Evidence | Verdict |
|---|---|---|
| Write only FRONT | 현재 working tree write는 FRONT 경로에만 존재 | PASS (observed scope) |
| Other branch mutation | remote DOCS/PY SHA는 initial commit, 이 audit 중 write 0 | PASS (this audit) |
| Automatic merge/cherry-pick/rebase | 실행 없음 | PASS (this audit) |
| FRONT algorithm reimplementation | source/corpus/geo/embedding/ranking code 없음 | PASS |
| Fake commerce/live | UI code 없음 | N/A; contract는 금지 규칙 PASS |
| Provenance preservation | v2.1 release manifest/provenance contract 존재 | DESIGN_PASS / IMPLEMENTATION_NOT_STARTED |
| Standard branch check | `.git` read-only mount로 표준 명령 실패 | ENVIRONMENT_EXCEPTION |

### Environment decision required

다음 중 하나를 선택하지 않으면 Master Instruction의 Git protocol을 완전히 자동화할 수 없다.

1. 작업 환경에서 실제 writable `.git` worktree를 제공한다.
2. `.mbN_GUIDE_FRONT.git`을 사용하는 wrapper/alias를 Front branch의 승인된 운영 절차로 명문화한다.

현재는 2번의 수동 우회로 branch를 확인했으며, 그 결과는 `nbM_GUIDE_FRONT`다. 이 보고서는 이를 branch authority 증빙으로 사용하지만 표준 workflow PASS로 표기하지 않는다.

---

## 8. Decision register

| ID | Decision required | Recommended decision | Owner | Status | Blocked work |
|---|---|---|---|---|---|
| DEC-F-01 | v2.1을 Product/Data SSOT로 승격할지 | DOCS branch에 review 후 publish | DOCS owner | PENDING | semantic source of truth |
| DEC-F-02 | README 4탭 PRD 처리 | v2.1 constitution 승인 후 README를 derived public overview로 정렬 | DOCS owner | REQUIRED | navigation implementation |
| DEC-F-03 | Fixture contract version | v2.1 schema를 pin한 deterministic fixture release 생성 | FRONT + DOCS approval | PENDING | F2 domain UX |
| DEC-F-04 | PY first release scope | ArticleIndex/Body → Place/Geo → manifest의 최소 release 목표 확정 | PY + DOCS | REQUIRED | releaseAdapter |
| DEC-F-05 | Map provider | P6 전에는 mock/list fallback; provider 선정은 별도 결정 | Product/infra | OPEN | real map SDK |
| DEC-F-06 | Partner/live provider | P4의 unavailable/coming-soon contract로 우선 표현 | Product/business | OPEN | real commerce/live |
| DEC-F-07 | Git environment protocol | writable `.git` 또는 approved wrapper | Repository/workspace owner | REQUIRED | compliant write/verify automation |

---

## 9. Recommended next sequence

### Immediate: no product-code dependency

1. DOCS owner가 v2.1 candidate를 검토해 `nbM_GUIDE_DOCS`의 commit으로 승인·publish한다.
2. 승인된 DOCS commit SHA와 `contractVersion`을 결정 로그에 기록한다.
3. README의 4탭 서술을 primary constitution으로 사용하지 않도록 정리한다. FRONT는 이를 직접 수정하지 않는다.
4. workspace owner가 Git environment decision(실제 `.git` 또는 wrapper)을 확정한다.

### FRONT can proceed after DOCS pin, before PY release

1. legacy `23ea067`에서 기술 shell만 선별 이식한다.
2. `fixtureAdapter`와 `releaseAdapter` interface를 분리한다.
3. `ko/en`, universal UI states, GNB 3 Primary Surface, route shell을 만든다.
4. deterministic fixture release를 `DEMO / FIXTURE`로 명확히 표시해 GUIDE → Place → DISCOVER → LIVE UX를 검증한다.
5. no fake commerce/live/chat, no algorithm reimplementation rule을 smoke/grep gate에 넣는다.

### PY release가 준비된 뒤

1. manifest/SHA/schema/quality report를 검증한다.
2. exact `releaseId`를 FRONT config에 pin한다.
3. `releaseAdapter`에서 ViewModel transformation만 수행한다.
4. missing locale, broken FK, unresolved geo, unavailable offer를 success data로 변환하지 않는다.
5. preview에서 release provenance와 UI state를 함께 검증한 뒤 promotion한다.

---

## 10. Final status matrix

| Area | Decision status | Contract status | Artifact status | Implementation status | Overall |
|---|---|---|---|---|---|
| Product constitution | v2.1 candidate exists | conflict with README | not published to DOCS | none | PENDING |
| IA/routes | v2.1 candidate exists | 3-surface model defined | not published to DOCS | none | PENDING |
| UX safety | defined | Master-aligned | no UI | none | DESIGN_PASS |
| Data intelligence | defined in v2.1 | producer/consumer separation aligned | PY artifacts absent | FRONT consumer absent | BLOCKED |
| Release provenance | defined | manifest contract aligned | no release bundle | no adapter | BLOCKED |
| Front shell/FSD | defined | Master-aligned | legacy baseline available | no source import | READY_TO_START_AFTER_PIN |
| Cross-branch governance | roles defined | remote branches exist | all at initial commit | no promotion/merge | PARTIAL |
| Verification | requirements defined | Master-aligned | no Node project | not runnable | NOT_STARTED |

**최종 판단:** DOCS/PY의 실제 산출물은 아직 없지만, FRONT가 소비해야 할 경계와 금지사항은 v2.1 candidate에 충분히 정의되어 있다. 계약이 DOCS branch에 pin되면, PY release를 기다리지 않고 fixture 기반의 기술 shell과 UX 구현을 시작할 수 있다. 실제 releaseAdapter 및 empirical recommendation·map projection은 P5~P9와 release manifest PASS 이후에만 시작해야 한다.
