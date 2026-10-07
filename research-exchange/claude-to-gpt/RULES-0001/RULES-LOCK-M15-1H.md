> **부록 — 하위 에이전트가 기준 커밋 00b98ab1을 읽기만 해서 쓴 추출(코드 실행 · 호출 없음).** 본문 판정은 RULES-LOCK.md · DATA-AVAILABILITY.md가 우선.
> 본 세션 재확인: hourly_a.py:46-63(EMA 씨앗 · 엄격 >) · :96-117 · m15_live.py:28-34 상수 · :51-74 exit_decision · stale · :151(stale은 자리 비키기에만) · 합성 as-is 시험 m15.* · h1.* · ema.*.

# 15분봉(m15_live.py · 22회차 후보) · 1시간봉(hourly_a.py · A그룹) 실제 규칙 — 코드 그대로

- 기준 코드: 커밋 00b98ab1655c84806357f44f2de6f1509ef1447f (BASE 폴더). 읽기만 했고, 아무것도 돌리지 않음.
- 줄 번호는 모두 BASE 안의 파일 기준. "미확인"은 코드만으로 확정할 수 없는 것.

---

## 0. 1시간봉은 몇 회차 규칙이 도는가

- hourly_a.py:1 머리말은 "연구 90회차 최종 규칙(자리 바꾸기 폭<90 + 같은 봉 후보 순서)". paper_trade.py:1은 "90 · 94회차".
- docs/RL-1H-LOG.md 987~991행: **94회차는 90회차 숫자(무리 3 · 20일 수익 · 5일 수급)의 고원 검토**이고, 결론은 "90회차 숫자가 고원 가운데 → 최종". 새 숫자가 아님.
- 코드에 있는 숫자가 90회차 = 94회차 최종과 같음:
  - 무리 3: hourly_a.py:83 `tot[c] += min(int(q * 3), 2)`
  - 20일 수익: hourly_a.py:285 `r20 = closes[-1] / closes[-21] - 1`
  - 5일 수급: hourly_a.py:281-284 `last5 = rows[-5:]` … `/ (sum(vols) / 20)`
  - 자리 바꾸기 7봉 · +4% · 폭 90: hourly_a.py:121
- 결론: **실제로 도는 것 = 90회차 규칙(94회차에서 최종 확정된 그 숫자)**. "94"라는 상수나 갈래는 코드에 없음.

---

## 1. 후보는 어디서 오나 (15분봉 · 1시간봉 같은 후보)

- 두 봇 모두 `hourly-live/plan.json`을 씀: m15_live.py:27 `PLAN = Path("hourly-live") / "plan.json"`, hourly_a.py:33.
- 만드는 곳: `hourly_a.make_plan()` (hourly_a.py:291-343)
  - hourly_a.py:296 `found = final_group.compute(prices, flow_day="next")` — 일봉 A그룹 셈, 수급은 **기준일(오늘) 것까지 포함**(final_group.py:171,192: `flow_before(rows, next_day)` = 날짜 < 다음 날).
  - hourly_a.py:302 `data_guard.daily_ready(prices, day)` — 마지막 날 종가가 있는 종목이 90% 미만이면 후보를 안 만듦(옛 plan이 남음 → 다음 날 장중에 '낡은 후보'로 걸려 새로 안 삼).
  - 후보 칸: hourly_a.py:311-312 `"추세문": final_group.RULE_DOOR in (one.get("갈래") or [])`, `"3일연속": steady`, `"flow5"`, `"r20"`.
  - plan: hourly_a.py:313 `{"base": day, "made": …, "breadth": found.get("breadth"), "candidates": cands, …}`
- 일봉 후보 조건(final_group.compute · shortfalls, final_group.py:145-283):
  - 공통: 그날(기준일) 시총 순위 ≤ 100 (rule.py:95 `TOP = 100`, caps.tag는 그날 주식수 × 그날 종가로 순위).
  - 공통 수급(final_group.py:248): `flow["외국인"] > 0 and flow["투신"] > 0 and flow["개인"] < 0` — 5거래일 합(FLOW_DAYS=5), 마지막 수급일이 10 달력일 넘게 낡으면 None(=불통과).
  - 추세 문("추세 규칙"): `vol > calm_edge`이면 탈락(=변동성 ≤ 아래 40% 자리, rule.py:96 `CALM = 0.4`, final_group.py:168 `rule._calm = vols[int(len(vols) * rule.CALM)]` — 전 종목 전 기간 표의 40% 자리), `slope >= 1.46`(rule.py:97, lab.py "추세 기울기" = EMA180의 5거래일 변화율 %, EMA는 SMA로 씨앗 — lab.py:44-55), `60일 전 대비 >= 20`(rule.py:98).
  - 정배열 문("정배열 추세"): 일봉 **단순이동평균** 3>15>20>90>150>200 (final_group.py:36,62-78), 간격 `19 <= gap < 53` (final_group.py:274; gap = SMA3/SMA200−1 %), 시장 폭 `breadth >= 50` (final_group.py:177,276; 폭 = 100위 안 종목 중 SMA50>SMA200 비율 %).
- 3일 연속(hourly_a.py:286-287): 기준일 포함 마지막 3줄 모두 `외국인 > 0 and 투신 > 0`.
- 언제 만드나:
  - 저녁: a-group.yml (workflow_run: "Daily price history" 끝나면) → `python final_group.py` → `python hourly_a.py plan`(a-group.yml:53-64). 사슬 시작은 daily-dart.yml cron `0 9 * * 1-5`(한국 18:00). 실제 기록상 plan 커밋 한국 19:11 · 19:27 · 19:43.
  - 아침 다시 셈: daily-close-check.yml cron `5 22 * * 0-4`(한국 07:05) — 일봉을 바로잡아 바뀐 게 있고 08:30 전이면 `final_group.py` + `hourly_a.py plan` 다시(daily-close-check.yml:61-70).
- 장중 사용 조건(둘 다): `plan.get("base", "") >= day`이면 안 씀(m15_live.py:277, hourly_a.py:438). `data_guard.plan_ready(plan, prev_trading_day)` (data_guard.py:52-60): `base != 어제 거래일`이면 `plan = {**plan, "candidates": []}` → **새로 사지 않고 팔기만**(m15_live.py:296-299, hourly_a.py:457-461).
- 자료 지연: 후보는 **전 거래일 종가 · 전 거래일 수급까지**(장중엔 바뀌지 않음). 15분봉 · 1시간봉 매매 판단에 그날 일봉 값은 안 씀.

---

## 2. 사기(진입)

### 2-1. EMA 정배열 (두 봇 공통 함수)
- hourly_a.py:39 `EMA_A = (5, 20, 60, 120, 180)`
- EMA(hourly_a.py:46-52):
  ```python
  out, k, prev = [], 2.0 / (span + 1), None
  for i, v in enumerate(values):
      prev = v if prev is None else prev + k * (v - prev)
      out.append(prev if i >= span else None)
  ```
  - 씨앗 = **첫 종가 그대로**(SMA 씨앗 아님), adjust 없음(재귀식), 처음 `span`개(인덱스 0 ~ span−1)는 None. 연구 rna.ema(rna.py:20-28)와 같은 셈.
  - 일봉 lab.ema_series(SMA 씨앗)와는 다른 방식 — 장중 EMA는 첫 값 씨앗.
- 정배열(hourly_a.py:55-62): `all(v is not None for v in vals) and all(a > b for a, b in zip(vals, vals[1:]))` — **엄격한 >**, 닫힌 봉 종가만.
- 역사 길이:
  - 15분봉: `history()` (m15_live.py:221-230) = `m15-kis/<code>/*.csv` 중 오늘 앞 날 **전부**(수집 시작 KIS_HOURLY_START=20250917, kis-m15.yml:74) + 오늘 실시간 봉. 하루 26봉(09:00 ~ 15:15). EMA180은 181번째 봉부터 값.
  - 1시간봉: `hlab.load(codes)`(야후 hourly-data, 시험지 잠금 풀고 — hourly_a.py:471-479) + 야후 마지막 봉 뒤는 `kis_history()`(hourly-kis + m15-kis를 1시간으로 묶음, 15시 봉은 14시 봉에 합침 · hourly_a.py:371-405) + 오늘 실시간 봉. 하루 6봉(09 ~ 14시, 14시 봉 = 14:00 ~ 15:30).
  - 매 실행마다 전체 줄로 처음부터 다시 셈(aligned_series(b["c"])).
- "처음 된 봉"(m15_live.py:124, hourly_a.py:167): `crossed = al[k] and not (k > 0 and al[k - 1])` — 바로 앞 봉(전날 마지막 봉 포함)이 정배열이 아니었고 이 봉에서 정배열. **어제부터 이미 정배열이면 crossed 아님**.

### 2-2. 15분봉 사기 (m15_live.step, m15_live.py:113-137)
- 상수: m15_live.py:30 `NOON = "1045"`, :31 `UP, MKT = 0.02, -0.01`
- 후보마다(그날 아직 '본' 종목이 아니면):
  ```python
  if not (crossed or hm == NOON): continue
  dr = day_ret(b, bar_id)
  if (dr is not None and dr > UP) or (market is not None and market < MKT):
      continue                      # 걸러진 신호는 그날 기회를 쓰지 않음
  today_seen.add(code)
  if code not in pos_all: sigs.append(code)
  ```
- `day_ret`(m15_live.py:77-83): 이 봉 **종가** ÷ 그날 첫 봉 **시가** − 1. 걸러짐: `> 0.02`(엄격).
- 시장 흐름(운영): `market_now()`(m15_live.py:243-254) = universe.json `top100`(161종목 · "2023-09 뒤 하루라도 100위 안") 각각 `client.quote` 현재가 ÷ 오늘 시가 − 1 의 평균, 5종목 미만이면 None(=거르지 않음). **실행 시각(봉 닫힌 뒤 약 3분+)의 값**이고, 이번 실행의 **마지막 봉에만** 적용(m15_live.py:332 `market=market if bar_id == todo[-1] else None`). 걸러짐: `< -0.01`(엄격).
- 두 거르기는 **정배열 신호와 10:45 신호 모두에** 적용(연구 q027 `entry3(al_mkt=-0.01)` = q023.py:10-29와 같음).
- 10:45 봉: 그날 아직 신호가 안 난 후보는 정배열 여부와 **상관없이** 신호(정배열 조건 없음). 거르기에 걸리면 그날 기회를 안 씀 → 10:45 뒤에도 정배열이 '처음 된' 봉이 나오면 살 수 있음.
- 체결 가정: 다음 봉 시가(10:45 봉 → 11:00 시가, 15:15 봉 → 다음 날 09:00 시가).

### 2-3. 1시간봉 사기 (hourly_a.step, hourly_a.py:156-172)
```python
if crossed or hh == "11":
    today_seen.add(code)
    if code not in pos_all:
        sigs.append(code)
```
- **거르기(+2% · 시장 −1%) 없음**. 11시 봉(11:00 ~ 12:00)이 닫히면 남은 후보 모두 신호 → 12:00 시가. 11시 봉에서 모든 후보가 '본 것'이 되므로 12 · 13 · 14시 봉의 정배열은 실제로 쓰일 일이 없음(그 종목 봉이 빠진 경우 제외).
- 실제 사는 때: 09시 봉 → 10:00, 10시 봉 → 11:00, 11시 봉 → 12:00 시가.

### 2-4. 공통 사기 처리
- 그날 한 종목 한 번(seen, m15_live.py:113-137 / hourly_a.py:156-175). 들고 있는 종목도 신호는 '본 것'으로 셈(사지는 않음).
- 실행 시각과 실제 주문: 봉 닫힘 뒤 약 3분(:03 · :18 · :33 · :48)에 실행 → 연습 계좌는 **다음 봉 시가**(오늘 1분봉으로 만든 그 봉의 o)로 적고(m15_live.py:334-338 / hourly_a.py:502-507), 모의 주문은 그때 **시장가**(paper_trade.py:170 `"ORD_DVSN": "01"`).
- 수량(paper_trade.plan_orders, paper_trade.py:317-354): `total = (cash + value) * share`, `money = min(total * 칸 / 10, left)`, `left = (cash + freed) * 0.98`, `qty = floor(money / price)` — price = 그 봉 시가(이론값). 주문 직전 매수가능 수량보다 많으면 줄임(paper_trade.py:159-164). 같은 실행에서 파는 주문이 먼저 나감.

---

## 3. 팔기

### 3-1. 판단 함수 (두 봇 같은 몸, 숫자만 다름)
m15_live.py:51-70 (1시간봉 hourly_a.py:96-116, 60봉):
```python
now = (close / pos["price"] - 1) * 100
if pos["kind"] == "추세":
    if now >= 13: 전량 "익절"
    if now <= -5: 전량 "손절"
    if pos["bars"] >= HOLD_TREND(240 | 60): 전량 "기간 청산"
    before = (prev_closes_max / pos["price"] - 1) * 100 if prev_closes_max is not None else -99
    if now >= 5 and before < 5 and pos["칸"] == pos["처음칸"]:
        return max(1, pos["처음칸"] // 2)   # 절반 익절
    return 0
if now <= -10: 전량 "손절"
peak = (pos["peak"] / pos["price"] - 1) * 100
if peak >= 8 and now <= 1: 전량 "본전 지키기"
return 0
```
- 모두 **봉 종가**로만 판단(장중 고가 · 저가 안 봄) → 다음 봉 시가에 팖. 같은 봉에서 익절 · 손절이 '둘 다' 닿는 경우는 생기지 않음(종가 하나). 차례: +13 → −5 → 기간 → 절반.
- `peak` = 산 값(시가)과 그 뒤 종가들의 최고(이 봉 포함, m15_live.py:103).
- `prev_closes_max` = 산 봉 종가부터 바로 앞 봉까지 종가 최고(m15_live.py:100,108). 산 봉 자체에선 None → −99.
- '처음칸' = 실제로 받은 칸(take). 절반 = 4칸 → 2칸, 2칸 → 1칸, 1칸 → 1칸(=전량).
- 종류(kind): 산 때 `"추세" if c.get("추세문") else "정배열"`(m15_live.py:166). 추세 문 + 정배열 문 둘 다면 추세.
- 일봉 정배열 깨짐(정배열 매매만):
  - 15분봉: 그날 첫 실행에서(`state["break_day"] != day`) 전날까지 일봉으로 `final_group.lines_now(closes)["정배열"]`이 False면 매도 예약, decided = `plan.base + "1515"` → **그날 09:00 시가**(m15_live.py:204-216, 300-305). 일봉 SMA 3>15>20>90>150>200 기준.
  - 1시간봉: 저녁 make_plan에서 오늘 종가로 같은 셈, decided = `day + "14"` → 다음 날 09:00 시가(hourly_a.py:325-334). 아침 다시 셈 때도 한 번 더 봄(이미 매도 예약이면 건너뜀).
- 봉 세기: 체결 때 `"bars": -1`(m15_live.py:197, hourly_a.py:235) → 산 봉이 닫히면 0. 즉 **산 봉은 0, 그 뒤 닫힌 봉마다 +1** (연구 `k - p["i"]`와 같음). 240봉 = 산 봉 뒤 240번째 닫힌 봉 종가에서 판단 → 그다음 봉 시가.
- 매도 예약이 있는 종목은 판단을 건너뜀(m15_live.py:105-106).

### 3-2. 자리 바꾸기(묵은 매매) — 따로 파는 규칙이 아님
- m15_live.py:73-74 / hourly_a.py:119-121:
  ```python
  pos["bars"] >= STALE_BARS(28 | 7) and (close / pos["price"] - 1) * 100 < 4 and (breadth if breadth is not None else 100) < 90
  ```
  - close = 그 종목 마지막 처리 봉 종가(`last_close`), breadth = `plan["breadth"]`(전 거래일 일봉 시장 폭 %).
- **새 신호가 칸이 모자랄 때만** 씀(m15_live.py:149-160): `free < need`이면 묵은 매매를 (last_close/산 값) 낮은 것부터 전량 팔기 예약, `free >= need`가 될 때까지.

### 3-3. 체결 (fill, m15_live.py:175-201 / hourly_a.py:213-240)
- 앞 봉에서 정한 것(`decided < bar_id`)을 이 봉 시가로. 비용 0.30%를 팔 때 한 번에 뺌(연습 계좌 기록용).
- 모의 매도 수량(paper_trade.py:331-337): 다 팔렸으면 그 규칙 장부 수량 전부, 일부면 `max(1, round(have * 칸 / (칸 + remain)))`.

---

## 4. 칸 · 크기 · 순서

- SLOTS = 10 (m15_live.py:28, hourly_a.py:38). 두 봇 따로(각자 state.json).
- 크기 hourly_a.py:92-93: `4 if c.get("추세문") or c.get("3일연속") else 2`.
- 칸 셈(m15_live.py:143-145): `held = 들고 있는 칸 + 사기 예약 칸`, `free = 10 - held + 팔기 예약 칸`.
- 순서(m15_live.py:141-142):
  ```python
  tiers = A.order_tiers({c: cands[c] for c in allsig})        # 15분봉: 그 봉 신호 전부(들고 있는 종목 포함)
  sigs.sort(key=lambda c: (0 if 추세문 else 1, 0 if 3일연속 else 1, -tiers[c], A.tie(c, bar_id)))
  ```
  - 1시간봉(hourly_a.py:178): `tiers = order_tiers({c: cands[c] for c in sigs})` — **안 든 종목 신호만**으로 무리를 셈(연구 h095 · q_rule은 그 봉 신호 전부로 셈 → 1시간봉 운영만 조금 다름. 15분봉은 x009에서 고쳤다고 주석 m15_live.py:140).
  - order_tiers(hourly_a.py:65-84): 후보 1개면 2. 아니면 flow5(낮을수록 좋음) · r20(높을수록 좋음) 각각 순위 q∈[0,1] → `min(int(q*3), 2)` 더함(0 ~ 4), None은 가운데 값으로.
  - 같은 무리 안: `sha256(f"{code}|{bar}")` 문자열 순(hourly_a.py:87-89).
- 살 때: `take = min(need, free)` — **칸이 조금만 남아도 줄여서 삼**(m15_live.py:164). `free <= 0`이면 "못 삼".
- 하루 사는 수 제한: **없음**(칸만 제한). 같은 종목 그날 한 번. 판 뒤 다른 날 다시 살 수 있음.
- 계좌 몫(paper_trade.py:36-37): `SHARES = {"1h": 0.0, "1d": 0.5, "15m": 0.5}`(환경변수로 덮어쓸 수 있음). m15-live.yml:3 · m15_live.py:1의 "20% 몫"은 옛 글.
- 모의 주문 스위치:
  - intraday.yml:36-38 `HOURLY_PAPER_TRADING: 'off'`, `M15_PAPER_TRADING: 'on'`, `M15_PAPER: 'on'` → intraday_runner.py:107-112가 봇마다 `PAPER_TRADING`으로 바꿔 넣음.
  - hourly-a-live.yml:80 `PAPER_TRADING: 'off'` / m15-live.yml:76-77 `M15_PAPER: 'on'`, `PAPER_TRADING: 'on'`.
  - paper_trade.enabled(paper_trade.py:181-192): PAPER_TRADING=='on' · PAPER_START(20261002) 지남 · hourly-live/paper-off 없음 · 모의 키 있음.
  - **1시간봉은 주문 안 함**(PAPER_TRADING off, 게다가 몫 0.0). hourly_a.run_live는 paper_trade.execute를 부르기는 함(hourly_a.py:510-515) → enabled()에서 걸러짐.
  - 15분봉은 m15_live.py:341 `M15_PAPER == "on"`일 때만 execute.

---

## 5. 시각 · 자료

- 실제 주 실행기: intraday.yml cron `20 23 * * 0-4`(한국 08:20, 오전 창 0855 ~ 1200), `41 2 * * 1-5`(한국 11:41, 오후 창 1200 ~ 1600) → intraday_runner.py.
  - 15분봉: :03 · :18 · :33 · :48 (09:03 ~ 15:48) (intraday_runner.py:27).
  - 1시간봉: 0903 · 1003 · 1103 · 1203 · 1303 · 1403 · 1533 (intraday_runner.py:28), 같은 시각이면 15분봉 먼저.
  - 늦게 떴으면 봇마다 가장 최근 회차 한 번만 따라잡음. 봇은 밀린 닫힌 봉을 차례로 처리(todo).
- 뒷받침 예약(상주 작업이 돌면 건너뜀): m15-live.yml `3,18,33,48 0-6 * * 1-5`(한국 09:03 ~ 15:48), hourly-a-live.yml `1 0`(09:01) · `1 1,2,3,4,5`(10:01 ~ 14:01) · `31 6`(15:31).
- 봉 닫힘: 15분봉 `close_at` = 시작 + 15분, 15:15 봉은 15:30(m15_live.py:38-41). 1시간봉 CLOSE_AT 09→1000 … 14→1530(hourly_a.py:41).
- 오늘 봉: 한투 1분봉(collect_kis_hourly.broker_kis_rows, TR FHKST03010230, ENDS 153000 · 133000 · 113000 · 093000) → 15분봉 `collect_kis_m15.to_bars`(1분봉 시각 = 그 분 끝, `slot = (h*60+m-1)//15*15`, 09:00 ~ 15:15 칸만, 15:15 칸에 15:30 마감 동시호가 포함) / 1시간봉 `collect_kis_hourly.to_hours` + 15시를 14시에 합침(hourly_a.py:353-368).
- 지난 봉: m15-kis(kis-m15.yml, 한국 17:20 · 20:20 · 23:20 · 02:20 · 05:20 수집).
- 장 열림 확인: collect_kis_intraday.market_open_today(장 시간이 다른 날은 쉼).

---

## 6. 겹침

- 15분봉은 자기 state(m15-live/state.json)만 봄: `if code not in pos_all`(m15_live.py:132). 1일봉(daily-live) · 1시간봉 보유는 안 봄 → **같은 종목을 1일봉과 동시에 들 수 있음**. daily_live.py에도 15분봉 보유를 보는 곳 없음(rg로 확인).
- 15분봉과 1시간봉은 같은 후보라 자주 겹침(1시간봉은 주문 안 하니 실제 계좌 겹침은 15분봉 · 1일봉).
- 모의 계좌는 하나를 나눠 씀: 규칙마다 장부(held)가 따로이고 팔 때 `min(장부 수량, 계좌 수량)`만 팖(paper_trade.py:324-325). 몫은 `(현금 + 계좌 전체 평가) × 0.5`라 다른 규칙 보유도 총액에 들어감.

---

## 7. 의사코드

### 15분봉 (m15_live.run_live · 한 번 실행)
```
plan ← hourly-live/plan.json;  if plan.base >= 오늘: 끝
todo ← 오늘 닫힌 봉 중 state.last_bar 뒤
if 장 안 열림: 끝
if plan.base != 어제 거래일: candidates = []           # 팔기만
if 오늘 첫 실행:
    for 정배열 매매: if 전날까지 일봉 SMA(3,15,20,90,150,200) 정배열 아님: 팔기 예약(decided=base+"1515")
market ← mean(현재가/오늘시가−1 over universe.top100) (값 ≥5개일 때)   # todo와 후보가 있을 때만
for bar in todo:
    fill(bar 시가)                                            # decided < bar 인 예약
    # 보유 판단
    for p in 보유: bars += 1; peak = max(peak, close)
        if 팔기 예약 없음: n = exit_decision(p, close, 앞 종가 최고); if n: 팔기 예약
    # 신호
    for c in 후보, 오늘 안 본 종목:
        al = EMA5>20>60>120>180 (엄격, 첫 값 씨앗, 처음 span개 None)
        crossed = al[k] and not al[k−1]
        if not (crossed or bar == 10:45): continue
        if day_ret(c, bar) > 0.02 or (bar == todo[-1] and market < −0.01): continue   # 그날 기회 안 씀
        본 것에 넣음; if 안 들고 있음: 신호
    정렬(추세문, 3일연속, −무리(신호 전부로), 해시)
    for 신호: need = 4 if 추세문 or 3일연속 else 2
        if free < need: 묵은 매매(bars≥28 · 수익<4% · 폭<90) 수익 낮은 것부터 전량 팔기 예약
        if free ≤ 0: 못 삼; else take=min(need,free) 사기 예약
fill(지금 막 시작한 봉 시가)   # 또는 09:03이면 09:00 시가로 어제 예약 체결
모의 주문(M15_PAPER=on, PAPER_TRADING=on): 시장가, 몫 0.5
```
exit_decision(추세): +13 전량 → −5 전량 → bars≥240 전량 → (+5 처음 · 안 나눔) max(1,처음칸//2)
exit_decision(정배열): −10 전량 → (peak≥+8 그리고 지금≤+1) 전량 · 일봉 정배열 깨짐 → 다음 09:00

### 1시간봉 (hourly_a.run_live)
```
같은 짜임. 차이:
- 봉: 09 · 10 · 11 · 12 · 13 · 14(14:00~15:30)
- 신호: crossed 또는 11시 봉(거르기 없음) → 12:00 시가
- 무리: 안 든 종목 신호만으로 셈
- 기간 60봉 · 자리 바꾸기 7봉
- 일봉 정배열 깨짐: 저녁 plan에서(오늘 종가) → 다음 날 09:00
- 모의 주문 없음(PAPER_TRADING off · 몫 0.0)
```

---

## 8. GPT 초안 견주기

| 초안 주장 | 판정 | 실제 |
|---|---|---|
| EMA5>EMA20>EMA60>EMA120>EMA180 | **맞음** | 엄격 >, 닫힌 봉 종가, 첫 값 씨앗(SMA 아님), 처음 span개 None(hourly_a.py:46-62) |
| 닫힌 봉에서 '처음 된' 것 vs 대신 사기 구분 | **맞음(보충)** | crossed = 이 봉 정배열 · 앞 봉(전날 포함) 아님. 대신 사기(10:45 / 11시)는 **정배열을 요구하지 않음** — 이미 정배열이든 아니든 삼 |
| 15m: 10:45 봉 뒤 이론 체결 11:00 | **맞음** | NOON="1045" → 다음 봉 1100 시가 |
| 15m: 그날 첫 시가 대비 > +0.02 이면 안 삼 | **맞음(보충)** | 이 봉 **종가** / 그날 첫 봉 시가 − 1 > 0.02. 대신 사기뿐 아니라 **정배열 신호에도** 적용 |
| 15m: 시장 평균 < −0.01 이면 안 삼 | **맞음(보충)** | 운영 값 = 161종목(universe top100) 현재가/오늘 시가 평균, 실행 순간 값, 마지막 봉에만, 5종목 미만이면 안 거름. 연구는 같은 시각 봉의 그날 수익 평균(전 거래일 100위 안만). 걸러진 신호는 그날 기회를 안 씀 |
| 15m 추세: ≥0.13 · ≤−0.05 · ≥240봉 전량 | **맞음** | % 단위(13 · −5), 종가 기준, 산 봉 = 0봉 |
| 첫 ≥0.05 절반 max(1, original_slots//2) | **맞음(보충)** | 처음칸 = 실제 받은 칸, 조건 `칸 == 처음칸`이고 앞 종가 최고 < +5% |
| 정배열: −0.10 / 고점 0.08 → 지금 0.01 | **맞음** | `now <= -10`, `peak >= 8 and now <= 1`(이상 · 이하 포함) |
| 전날 일봉 정배열 깨짐 → 다음 09:00 | **맞음(보충)** | 일봉 **SMA** 3>15>20>90>150>200(final_group.lines_now). 15m은 그날 첫 실행에서 전날 종가로 → 그날 09:00 시가 |
| stale ≥28봉 · 수익 <0.04 · 전날 폭 <0.90 | **맞음(다름 하나)** | 숫자는 맞음(폭은 % 90). 다만 **스스로 파는 규칙이 아님** — 새 신호가 칸이 모자랄 때만 수익 낮은 것부터 비킴 |
| 1H: 11:00 봉 뒤 → 12:00 | **맞음** | 단 1H에는 +2% · 시장 −1% 거르기 **없음** |
| 1H: 추세 최대 60봉, stale 7봉 | **맞음** | hourly_a.py:105, 121 |

### 초안에 없는 차이 · 주의
1. 1시간봉 같은 봉 순서 무리를 **안 든 종목 신호만**으로 셈(hourly_a.py:178) — 연구(그 봉 신호 전부)와 다름. 15분봉은 신호 전부(m15_live.py:141).
2. 15분봉 몫은 50%(paper_trade.py:36-37). m15-live.yml:3 · :75 · m15_live.py:1의 "20%"는 낡은 주석.
3. 1시간봉은 모의 주문 없음(몫 0.0 · PAPER_TRADING off). 알림 · 연습 계좌만.
4. 밀린 봉을 몰아 처리할 때 시장 −1% 거르기는 마지막 봉에만, 모의 주문은 모두 지금 시장가.
5. 칸이 모자라면 줄여서 삼(take = min(need, free)).
6. 하루 매수 수 제한 없음.

### 미확인
- 한투 1분봉 · 야후 1시간봉 값이 액면분할 등으로 수정된 값인지: 코드로 확인 불가(자료 출처 성질).
- m15-kis에 빠진 날이 있으면 EMA가 그 틈을 그냥 잇는데, 실제로 빈 날이 있는지는 자료를 안 돌려 미확인.
- 저녁 plan의 정확한 생성 시각: 앞 작업(DART → 일봉) 걸리는 시간에 따름. 기록상 한국 19시대.
