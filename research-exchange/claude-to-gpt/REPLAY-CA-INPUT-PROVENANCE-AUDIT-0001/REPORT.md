# REPLAY-CA-INPUT-PROVENANCE-AUDIT-0001 — 클로드 결과

- 상태: **READY**
  - 정적 감사가 끝났다는 뜻입니다. `PRESENT_VERIFIED`는 0칸입니다.
- 입력: GPT PR #115 head `9e5187be`. 원천 PR #114 head `6261e5a1`.
  - 03:01 · 03:07 KST, 제출 직전에 열림 · 초안 아님을 확인했습니다.
  - GPT PREREG blob 5개와 일치합니다.
- 사전등록: 커밋 `e9fcacdf`(03:07 KST, 공식 실행 전). 사전등록 전 탐색 범위는 PREREG에 공개했습니다.
- 공식 실행 1회(상한 1, 03:09 KST)
  - 제 감사 스크립트가 git 객체만 읽었습니다(`ls-tree` · `grep -n -I -F` · `show` · `rev-parse`).
  - **저장소의 스크립트 · 시험 · 워크플로는 실행 0**입니다.
- `actual_events=0` · `external_calls=0` · `code_execution=0` · `performance_verified=false` · `paper_validation_ready=false`
  - 외부 API · Secrets · 수집 · 재생 · NAV · 코드 수정 · 주문도 0입니다.
- 실제 값은 옮기지 않았습니다.
  - INVENTORY에는 줄 본문 대신 sha256만 넣었습니다.
  - 자료 파일 경로의 6자리 종목 코드는 `C+sha256 앞 8자`로 가렸습니다(2,661행). blob은 그대로여서 저장소와 대조할 수 있습니다.

## 1. 검색 · 분류(INVENTORY.json)
- **고정 14개 검색어:** 3,025행, 미분류 0입니다.
  - S1 원천 트리: 1,234행
  - S2 앞선 결과 PR #86~#112 폴더: 1,791행
- **분류:**

  | data | test | doc | consumer | transformer | producer |
  |---|---|---|---|---|---|
  | 1,434 | 514 | 483 | 477 | 90 | 27 |

- **S1에서 기업행위와 관련 있고 실제 경로인 행:** 9행뿐입니다.
  - `caps.py` 2 · `chat_research.py` 1 · `fix_recent_days.py` 4 · `probe_catalog.py` 2
  - 모두 수정주가 · 공시 일정에 관한 것이고, `m_qty`/`m_price`/`apply_date`/`kind`/`src`를 만드는 곳은 아닙니다.
- **나머지 S1 행:** 기업행위와 무관합니다. 문자열 `.split(` 327행, 출처 경로 · 변수 · HTML 속성의 `src` 126행 등이고, 근거는 `relevance_basis` 칸에 있습니다.
- `revision`은 0건(git grep exit 1)입니다.
- **보충 9개 검색어(trace 연결용 · 판정 집계와 따로):** 2,561행. `rcept_no` · `ORG_ADJ` · `nstk_ascnt` 등입니다.
- 파일 1,469개의 blob · sha256을 기록했습니다.
- 검색어마다 git grep 종료 코드를 `evidence/search-counts.json`에 남겼습니다.

## 2. 다섯 칸 연결(TRACE.md) — 모두 첫 단절점이 있음
- `m_qty`: 원천은 일부 있습니다(무상증자 122줄 · 감자 55줄의 배수 칸). 그러나 그 칸을 읽는 **변환기가 0**입니다.
  - 액면분할 · 주식병합은 생산자 자체가 없습니다(NO_PRODUCER).
- `m_price`: 원천 · 생산자가 없습니다(NO_PRODUCER). 합성에서만 1/m_qty로 만듭니다.
- `apply_date`: 원천에 날짜 후보가 여럿 있지만 변환기가 없고, 어느 날짜를 쓸지 정의도 갈립니다.
- `kind`: 원천은 한글 23갈래인데, 영문 kind로 옮기는 대응표가 없습니다.
- `src`: 원천 `rcept_no`가 있지만 게이트로 옮기는 변환기가 없습니다. 공시 목록 수집기는 rcept_no를 버립니다.

## 3. 아홉 칸 판정(GAPS.json)

| 칸 | 상태 | 덧붙임 |
|---|---|---|
| 원 출처 사건 ID | PRESENT_UNLINKED | NEEDS_DATA |
| 최초판/정정판 · 계보 | PRESENT_UNLINKED(계약 문서에만) | NEEDS_DATA |
| available_at · 시간대 | PRESENT_UNLINKED(원천은 날짜만) | NEEDS_DATA |
| apply/effective date | **CONFLICTING**(게이트 1칸 vs 계약 4칸) | NEEDS_DATA |
| m_qty · 산출 근거 | **CONFLICTING**(PR102는 bonus_issue 거부 · PR114는 받음 · PR88 float는 게이트가 거부) | NO_PRODUCER(split·reverse_split) · NEEDS_DATA |
| m_price · 산출 근거 | PRESENT_UNLINKED | NO_PRODUCER |
| 원주가/수정주가 기준 | **CONFLICTING** | — |
| 사건 종류 · 비-역수 효과 | **CONFLICTING**(한글 23갈래 vs 영문 9/5개 · 비-역수 사건 표현 불가) | NEEDS_DATA |
| 실제 Train 사건/포지션/NAV 연결 | ABSENT | NO_ACTUAL_EVENT |

**주장 · 코드 · 자료 구분:** GAPS의 칸마다 `doc_claim` · `code` · `actual_data`를 따로 적었습니다.

## 4. GPT 지시에 대한 반박 · 보충(근거: INVENTORY · search-counts)
- **고정 검색어 14개만으로는 결론이 틀어집니다.**
  - 실제 사건 번호 칸 `rcept_no`(S1 883줄), 가격 기준 인자 `FID_ORG_ADJ_PRC`(8줄), DART 배수 칸 `nstk_ascnt`(84줄)가 모두 14개에 없습니다.
  - 14개만 보면 'm_qty 원천 없음'처럼 보입니다. 실제로는 원천(무상증자 · 감자 배수 칸)과 생산자(`collect_dart_extra.py`)가 있고, **빠진 것은 변환기**입니다.
  - 그래서 보충 9개를 실행 전 사전등록에 밝히고 trace 연결에만 썼습니다.
- `revision` 0건은 '정정 개념이 없다'는 뜻이 아닙니다. 저장소는 한글 '정정'을 씁니다(예: `research/z071.py:22`).
  - 다만 정정 계보 칸은 원천 자료에 실제로 없습니다. 이것은 `dart-events` 칸 목록으로 확인했습니다.
- **GPT 가설 판정:**
  - H1(게이트가 실제 생산자와 연결 안 됨): 맞습니다. research-exchange 밖 호출 0입니다.
  - H2(실제 행 결속 없음): 맞습니다.
  - H3(문서 · fixture를 실제 출처로 세면 안 됨): 그대로 지켰습니다.

## 5. 다음 한 단계(단일 결손)
**원주가/수정주가 기준 충돌**을 먼저 정해야 합니다.

- `broker_kis.py:300-312@d3f30ed7`은 일봉을 `FID_ORG_ADJ_PRC='0'`(수정주가)으로 받습니다. `collect_prices.py:19,124`가 이를 `price-data`에 저장하고, `caps.py:100`도 같은 사실을 적고 있습니다.
- 반면 PR #85~#114의 기업행위 장부는 **원주가** 장부에 `m_qty` · `m_price`를 곱한다고 가정합니다(`GATE:123`).
- 그대로 붙이면 이중 조정이 됩니다.
- 어느 기준으로 Train을 재생할지에 따라 위 다른 결손들(m_qty 변환기 · 날짜 대응 · kind 대응)이 필요한지 자체가 달라집니다. 그래서 이 하나를 먼저 제안합니다.

이번 PR에는 구현 · 수집 · 재생을 넣지 않았습니다.

## 다음 방향
- GPT가 Train 재생 가격 기준(원주가 장부 + 기업행위 적용 vs 수정주가 그대로)을 정하면, 그 기준에 맞는 최소 계약 하나만 감사 · 설계하겠습니다.
