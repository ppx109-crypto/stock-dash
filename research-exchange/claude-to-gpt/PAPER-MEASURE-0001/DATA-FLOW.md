# PAPER-MEASURE-0001 DATA-FLOW — 지금 기록의 분류와 새 연결부

기준: source head `1e6ed49b`(현재 main `149c8015`과 해당 파일 차이 0). 값은 읽어 옮기지 않았고, 키 구조와 개수만 봤습니다.

## 1. 입력 유형 분류표

| 경로 | 분류 | 근거(코드 줄) |
|---|---|---|
| `*-live/paper-orders.json`의 `orders[]`(지금 저장소에는 `idle-live/`만 추적, 2건) | **ORDER_ACCEPTED_NOT_FILL** · 실패 행은 ORDER_INTENT | `paper_trade.py:401-411` — `broker.order()`가 주문번호를 돌려받으면 바로 `status="접수"`로 적음. 체결 조회 없음 |
| 위 `orders[].qty` | 주문 수량(요청 또는 매수가능 수량으로 줄인 값) | `paper_trade.py:403-404` — 체결수량이 아님 |
| 위 `orders[].price` | 판단 때 시세 | `paper_trade.py:411` `prices.get(code)` — 평균체결가가 아님 |
| 위 `orders[].order_no` | 원 주문번호 | `paper_trade.py:177-178` — 주문 응답 `ODNO`를 그대로 저장 |
| 위 `held` | **POSITION_SNAPSHOT**(접수 수량 누계) | `paper_trade.py:405-407` · `basket_live.py:205-207` — 체결 확인 없이 접수 수량을 더하고 뺌 |
| 자리 내주기 매도(`:room:`) | ORDER_ACCEPTED_NOT_FILL | `paper_trade.py:290-298` — 같은 방식으로 `"접수"` |
| `basket-live/paper-orders.json`(저장소 미추적) | ORDER_ACCEPTED_NOT_FILL | `basket_live.py:202-204` — 같은 방식 |
| `idle-live/today.json` `orders[]` | **ORDER_INTENT**(그날 계획) | 필드가 code · side · qty · why뿐 |
| `daily-live/` · `hourly-live/` · `m15-live/` · `idle-live/` `state.json` | **STRATEGY_STATE**(연구 엔진의 가상 체결 · 보유) | 엔진이 "그 봉 시가에 체결"로 적은 모델 값(`paper_trade.py:7`) |
| `reconcile/*.json` · `reconcile/state.json` | 연구 vs 운영 비교(파생 · %) · STRATEGY_STATE | 계좌 몫 % 비교 · 주문 목록 |
| `predash/trades.py` `normalize_kis()` 결과 | **CONFIRMED_FILL**(메모리에만) | `predash/trades.py:18-54` — 취소 제외 · 체결수량 > 0 · 평균가 > 0. `classroom_ui.py:363 · 393 · 899 · 990`에서 화면 표시에만 쓰고 저장하지 않음 |
| `predash/paper.py` | 로컬 학습용 종가 장부(ORDER_INTENT 성격, 증권사와 무관) | `predash/paper.py:1` "never sends broker orders" |
| DERIVED_NAV | **없음** | 일별 평가 · 입출금 · 체결을 합친 파이프라인을 찾지 못함 |

## 2. 왜 기존 paper-orders는 fill이 아닌가
1. "접수"는 주문 API가 주문번호를 돌려줬다는 뜻일 뿐입니다(`paper_trade.py:172-178`). 시장가라도 체결 · 부분체결 · 거부 · 취소 여부는 따로 조회해야 합니다.
2. `qty`는 넣은 수량이고, `price`는 판단 때 시세입니다. 체결수량과 평균체결가가 아닙니다(`paper_trade.py:403 · 411`).
3. 체결 조회 코드(`predash/kis.py` `fills()` → `inquire-daily-ccld`, `CCLD_DVSN=01`)는 있지만 화면용입니다. 결과를 장부에 저장하지 않습니다.
4. KIS 체결 행의 시각도 주문 시각(`ord_tmd`)입니다. 그래서 체결 순서는 확정할 수 없습니다(`predash/trades.py:115-118` 주석과 같은 판단).

## 3. 새 연결부(이 폴더 안에서만)
```
KIS 체결 원문(로컬 · 비공개, 사용자가 직접 받음)
  └─ sanitize_fills.py  ── 키 없음 → 거부 / 출력이 Git 작업트리 안 → 거부 / "접수" 장부 행 → 거부
       └─ 비공개 정규화 원장 ledger.jsonl(저장소 밖) ── fill_uid = HMAC(로컬 키, …), 원 주문 · 지점 번호 없음
            + start.json · prices.json · flows.json · corp_actions.json(모두 로컬)
            └─ build_daily_measurement.py ── public_guard + whitelist_guard 통과해야 씀
                 └─ 공개 비식별 일별 성과(정규화 NAV · TWR · 일/달 손실 · MDD · 비중 · 건수 · bps · 완전성)
```
- 네트워크 0, 표준 라이브러리만 씁니다. 운영 봇 · `paper_trade.py` · 워크플로는 바꾸지 않았습니다.
- 안전한 로컬 실행 순서는 REPORT §5에 있습니다.
