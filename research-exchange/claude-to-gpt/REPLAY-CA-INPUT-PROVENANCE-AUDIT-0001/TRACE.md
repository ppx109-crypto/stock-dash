# TRACE — PR #114 게이트 입력 5칸의 원천 → 소비 연결

## 읽는 법
- 원천 트리: PR #114 head `6261e5a1`. 인용은 `path:줄@blob 앞 8자리`입니다.
- 연결 칸마다 무엇인지 표시합니다.
  - **[자료]**: 실제 자료가 있음
  - **[코드]**: 실제 코드가 있음
  - **[합성]**: 합성 코드 · fixture만 있음
  - **[문서]**: 주장 · 설계만 있음
  - **없음**: 아무것도 없음
- 합성 소비자(PR #114 게이트)는 모두 다음 파일입니다: `research-exchange/claude-to-gpt/REPLAY-CA-QUANTITY-MUTATION-GATE-0001/code/quantity_mutation_gate.py@58417375`. 아래에서는 `GATE`로 줄입니다.
- 증거는 모두 같은 폴더의 `evidence/quantity-mutation-gate.json@02f65d3c`입니다(합성 · actual_events=0).

## 한눈에

| 칸 | 실제 원천 | 생산자 | 변환기 | 소비자 | 첫 단절점 |
|---|---|---|---|---|---|
| `m_qty` | [자료] 일부 있음 | [코드] 일부 있음 | **없음** | [합성] | 원천 배수 칸 → m_qty |
| `m_price` | 없음 | **없음** | [합성] 1/m_qty | [합성] | 원천 단계(NO_PRODUCER) |
| `apply_date` | [자료] 후보 여럿 | [코드] 있음 | **없음** · 정의 충돌 | [합성] | 원천 날짜 → apply_date |
| `kind` | [자료] 한글 갈래 | [코드] 있음 | **없음** | [합성](키에만 씀) | 한글 갈래 → 영문 kind |
| `src` | [자료] rcept_no | [코드] 있음 | **없음** | [합성] 자유 문자열 | rcept_no → src |

## m_qty
- **원천 [자료]:** `dart-events/` 437파일(값은 읽지 않고 칸 이름 · 줄 수만 셈)
  - 무상증자 122줄 · 75파일, 칸 `nstk_ascnt_ps_ostk`(1주당 신주배정 수)
  - 감자 55줄 · 33파일, 칸 `cr_rt_ostk`(감자 비율)
  - 액면분할 · 주식병합(split/reverse_split): **원천 없음**. `collect_dart_extra.py:33-41@a816aeb5` 주요사항 API 목록에 해당 항목이 없습니다.
- **생산자 [코드]:** `collect_dart_extra.py:36,38,105-119@a816aeb5`(OpenDART 주요사항 → `dart-events/{code}.json`)
- **변환기: 없음.**
  - `nstk_ascnt` · `cr_rt`를 읽는 코드가 0입니다(보충 검색 · `.py/.yml/.html/.js`).
  - [합성] 계약 `PR102 ratio_contract.py:39-56@5c4658bd`가 있습니다. 주식수 · 액면가로 m_qty를 만들되 split/reverse_split만 받습니다.
- **소비자 [합성]:** `GATE:47-48`(QM 판정) · `GATE:93`(격리) · `GATE:123`(수량 × m_qty)
- **첫 단절점:** `dart-events` 줄의 배수 칸 → `m_qty`. 이 사이에 변환기가 없습니다.
- **충돌:** 계약끼리도 맞지 않습니다.
  - PR102(52줄)는 bonus_issue를 `UNKNOWN_DIRECTION_CONTRADICTION`으로 거부하는데, PR114는 bonus_issue m_qty 2를 받습니다.
  - PR88 스키마의 `ratio`는 JSON number(float)인데, `GATE:20-21`이 float를 거부합니다(BLOCKED_INPUT).

## m_price
- **원천: 없음.** 어느 원천 자료에도 가격 배수 칸이 없습니다.
- **생산자: 없음(NO_PRODUCER).**
- **변환기 [합성]:** `PR102 ratio_contract.py:54`, `m_price = 1/m_qty`
- **소비자 [합성]:** `GATE:47-48` · `GATE:123`(가격 × m_price)
- **첫 단절점:** 원천 단계입니다.
- **추가 충돌:** 실제 일봉은 수정주가입니다(아래 GAPS `raw_vs_adjusted_price_basis`). 그래서 m_price를 곱할 원주가 장부가 실제로는 없습니다.

## apply_date
- **원천 [자료]:** 후보 날짜 칸이 여럿 있습니다.
  - 무상증자 `nstk_asstd`(배정기준일) · `nstk_lstprd`(상장예정일)
  - 감자 `crsc_nstklstprd`
  - 합병 `mgsc_nstklstprd` 등
- **생산자 [코드]:** `collect_dart_extra.py:105-119@a816aeb5`
- **변환기: 없음.** 위 칸을 읽는 코드가 0입니다.
- **정의 충돌:**
  - `GATE:35-36,62`는 날짜를 `apply_date` 하나로 받습니다.
  - `PR88 corporate-action.v2.schema.json:74-87@24e3f0d6`은 record · effective · price_basis · listing 네 날짜를 둡니다.
  - `PR86 raw_replay.py:67-69@3a675087`은 effective_date를 필수로 둡니다.
  - 가격 기준일 규칙은 PR94에서 BLOCKED였습니다.
- **첫 단절점:** 원천 날짜 칸 → `apply_date`. 대응 규칙이 정해지지 않았습니다.

## kind
- **원천 [자료]:**
  - `dart-events`의 한글 갈래 이름(`collect_dart_extra.py:33-41`, 23갈래)
  - `event-data`의 제목 갈래(`collect_events.py:29,97@de029767`)
- **생산자 [코드]:** 위 두 수집기
- **변환기: 없음.** 한글 갈래를 영문 kind로 옮기는 대응표가 저장소에 없습니다.
  - [문서] 영문 목록은 따로 있습니다: `PR88 v2 schema:56-67`(9개), `docs/QUANT-REPORT.md:453@4a1db7a2`(5개)
- **소비자 [합성]:** `GATE:35-36`. 의미키에만 쓰고, 판정(QM)에는 쓰지 않습니다.
- **첫 단절점:** 한글 갈래 → 영문 kind
- **비-역수 사건:** 원천에 유상증자 · 감자(유상 가능) · 합병(`mg_rt`) · 회사분할(`dv_rt`)이 있습니다. 이런 사건은 역수 쌍 모델로 표현할 수 없습니다.

## src(출처 사건 번호)
- **원천 [자료]:** `dart-events` 줄마다 `rcept_no` 칸이 있습니다.
- **생산자 [코드]:** `collect_dart_extra.py:115-119`(rcept_no로 중복 제거)
  - `collect_events.py:97-100`은 rcept_no를 **버리고** date · kind · title만 저장합니다.
- **변환기: 없음.**
- **소비자 [합성]:** `GATE:89,98,125`. 자유 문자열 `src`로 provenance만 남기고, 동일성 판정에는 쓰지 않습니다.
- **첫 단절점:** `rcept_no` → `src`
- 정정 계보(root_rcept_no)는 [문서] `PR88 v2 schema:9,22`에만 있습니다. 원천 자료에는 그런 칸이 없습니다.

## Train 연결
- research-exchange 밖에서 `GateLedger` · `apply_batch` · `PayloadLedger` · `FamilyLedger`를 부르는 곳은 0입니다.
- `caps.py:28,97-128@c51002b4`의 주식수 보정(연구용 `CAPS_ADJ`)은 별개의 추정입니다. 주식수 비율 1.8/0.55 문턱을 쓰며, 게이트와 연결되지 않습니다.
- → **NO_ACTUAL_EVENT**
