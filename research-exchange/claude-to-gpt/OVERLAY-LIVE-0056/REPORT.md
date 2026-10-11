# OVERLAY-LIVE-0056 결과 — MIX-0054 최종 판을 모의투자 코드에 넣기(꺼진 채)

- schema_version 1 · task_id · chain_id `OVERLAY-LIVE-0056` · kind RESULT(구현) · **round 3**(마지막) · **status: READY**
- source: 운영 계산 · 구현 계약 #226(인정 6105493981 · head `95f58e789`) · 결과 제출 PR #230
- **사용자 지시(2026-10-11 · 이 세션에서 직접):** "승인, 코드제작 후 검토까지 진행해줘"
- **범위 · 한계:** 모의투자 서버 주문 코드만 바꿨습니다.
  - **병합 · 켜기(`MIX54='on'`) · 시작 날 · 봇 재시작은 미승인**입니다. 워크플로 기본값은 `MIX54: 'off'` · `MIX54_START: ''`입니다.
  - 실전 계좌는 손대지 않았습니다.

## round 3에서 고친 것(GPT #230 round 2 · 6105866099)
- **맞추는 날(`run`)의 옛 ETF 매도도 체결 확인 뒤에만 장부 고침**
  - 주문 앞 실제 잔고를 적어 두고, 주문 뒤 판 종목의 잔고가 판 만큼 줄었는지 확인합니다(최대 5번 · 2초).
  - 새 held = 새 종목의 실제 수량 + **못 판 옛 종목 잔량**(다른 장부 몫 뺀 실제 수량 · 원래 덧붙임 수량까지)입니다.
  - B = 맞춘 뒤 덧붙임 평가액(남은 옛 종목 포함 · 그때 값)이라 NAV_b = 계좌 NAV가 그대로 지켜집니다.
  - 옛 종목이 남으면 `applied = None`(맞춤 끝으로 적지 않음) · 그 달 맞춤 기록도 그대로 둡니다. 그래서 **다음 실행에 다시 맞춥니다**(남은 옛 종목을 팔고 새 종목을 맞춤).
  - 주문 뒤 잔고를 아예 못 읽으면 추정하지 않습니다. 맞춤 전 장부를 그대로 두고 `pending` 종목으로 적습니다. 다음 실행의 `reconcile()`이 실제 잔고로 줄거나 늘어난 수량을 맞춘 뒤(B도 그만큼) 다시 맞춥니다.
- 시험 4개 추가(`SwitchFills`): 상승 → 횡보 0주 체결 → 다음 날 다시 맞춤 · 상승 → 횡보 절반 체결 · 상승 → 하락 0주 체결 → 다음 날 다시 맞춤 · `pending` 맞추기
  - 매번 '바탕 NAV = 계좌 NAV − 덧붙임 평가액 + B'와 'B = 덧붙임 평가액'을 확인합니다.

## round 2에서 고친 것(GPT #230 6105836874)
1. **꺼짐이면 새 주문 없음:** `yield_for` · `sell_for` · `prepare` 첫머리에서 `active(오늘 KST)`를 확인합니다. `run`은 원래 확인했습니다.
   - 덧붙임을 든 채로 꺼도(MIX54 off · 시작 전 · off 파일) 바탕 매수 때 덧붙임 매도가 나가지 않습니다.
   - 시험 `test_off_blocks_new_yield_sells`가 세 경우를 다 봅니다.
2. **체결 확인 뒤에만 장부 고침:** `sell_for`는 주문 앞뒤 실제 잔고 수량 차(최대 5번 · 2초 간격)로 체결 수량을 확인합니다. held · B는 그 수량과 순수입(× 0.9995)으로만 고칩니다.
   - 0주 체결이면 장부를 그대로 두고 `unconfirmed`로 남깁니다.
   - 다음 실행 앞의 `reconcile()`이 실제 잔고(다른 장부 몫 뺀 수량)와 맞춥니다. 줄어든 수량은 지금 값의 순수입만큼 B를 줄입니다.
   - 시험 `test_accepted_but_not_filled` · `test_partial_fill` · `test_reconcile_with_real_balance`
   - 맞추는 날(`run`)은 원래부터 체결 뒤 실제 잔고 수량으로 held · B를 정했습니다.
3. **결과 계약:** 이 REPORT · `manifest.json` · 시험 원문(`evidence/`)을 더했습니다.

## 바뀐 것(round 1과 같음 · PR #230 본문)
- `overlay_live.py`(새): 국면(연구와 5,919일 같음) · 맞추는 날 · 크기 · B 계약 · `base_view` · `yield_for` · `prepare` · 손실 알림 · 끄기
- `paper_trade.py`: `PaperBroker.balance(raw=False)` = 바탕 가상 계좌 · `order()` 매수 앞 `yield_for` · `BASKET_SHARE` · `mix54_on()`이면 15분봉 몫 0 · 바구니 0.3
- `idle_live.py`: 바구니 돈 = 계좌 × `BASKET_SHARE` − 1일봉 평가액 · 엔진 뒤 `overlay_live.run`
- `paper_check.py`: 실제 잔고(`raw=True`)
- 워크플로 daily-live · m15-live: `MIX54: 'off'` · `MIX54_START: ''` · `overlay-live/` 저장 · 시험 목록

## 시험(원문 증거)
| 명령 | 결과 | 원문 |
|---|---|---|
| `python3 -m unittest tests.test_overlay_live -v` | 24개 통과 · 종료 상태 0 | `evidence/test_overlay_live.out` |
| 관련 8묶음(`test_overlay_live` · `test_daily_live` · `test_paper_trade` · `test_idle_live` · `test_idle_signal` · `test_basket_live` · `test_acc_cap` · `test_m15_live`) | 126개 통과 · 종료 상태 0 | `evidence/test_related.out` |
| `python3 -m unittest discover -s tests` | 725개 가운데 724 통과 · 오류 1 · 종료 상태 1 | `evidence/test_all.out` |

- 오류 1개는 `tests.test_core.CoreTests.test_existing_calendar_event_is_updated`입니다. `ModuleNotFoundError: No module named 'googleapiclient'`(구글 달력 라이브러리가 이 실행 환경에 없음)입니다.
  - 이번 변경을 되돌린 main(`5204e4e58`)에서도 같은 오류가 납니다(`evidence/test_core_on_main_before.out`).
  - 이번에 바꾼 파일과 상관없는 달력 기능입니다.
- 실행 환경: 클라우드 컨테이너 · Python 3 · 실제 증권사 연결 없음(가짜 잔고 · 주문으로 시험)

## 연구와 다른 점(어림 · 공개 · round 1과 같음)
- 연구는 종가 · 여기서는 15:1x 연속 매매 값입니다. B도 그때 값입니다.
- 크기에서 15:20 1일봉 몫(`daily_reserve`) × 1.36을 미리 뺍니다(보수적).
- 15:20 동시호가 뒤 1일봉이 예상보다 더 사면 덧붙임을 못 덜고, 매수가능 수량에서 잘립니다.
- 연구가 맞추는 날 바탕 가상 이동에 매긴 비용(0.30% / 0.05%)은 실제로 생기지 않습니다.
- 미확인 매도의 B 조정은 다음 실행의 지금 값으로 셉니다(실제 체결값과 조금 다를 수 있음).

## 다음 질문(사용자)
- 병합과 시작 날(`MIX54_START`). 예: 10-14 무렵 국면을 보고 켜기 · 11-02 월초
