> **부록 — 하위 에이전트가 기준 커밋 00b98ab1을 읽기만 해서 쓴 추출(코드 실행 · 호출 없음).** 본문 판정은 RULES-LOCK.md · DATA-AVAILABILITY.md가 우선.
> 본 세션 재확인: basket_live.py:29-132(상수 · todays_events · step · 겹침 기록 순서) · collect_events.py:27-63(kind_of 첫 일치 · '유무상증자'→무상증자는 본 세션이 처음에 반대로 잘못 짐작했다가 시험으로 이 문서가 맞음을 확인) · idle_signal.py:25-40 · idle_live.py:41-47 · :368-374 · paper_trade.py:119-128 · 합성 as-is 시험 basket.* · kind_of.*.

# 빈칸 엔진 · 코스닥 인버스 · 사건 바구니 C · 돈 나누기 — 있는 그대로의 규칙

- 기준 코드: 커밋 00b98ab1655c84806357f44f2de6f1509ef1447f (BASE = scratchpad/base, 읽기만 함)
- 시각은 모두 한국 시각.
- 표시: **맞음** = 초안 주장과 같음 · **다름(실제)** = 코드가 다름 · **없음** = 코드에 없음 · **미확인** = 코드만으로 알 수 없음

---

## A. 빈칸 엔진 + 코스닥 과열 인버스 (idle_live.py · research/idle_signal.py)

### A-1. 종목 코드와 역할 (idle_live.py:41-43, idle_signal.py:17)
```
DIP, DOL, INV, K200, Q150 = "069500", "138230", "251340", "069500", "229200"
ROT = ("133690", "138230", "132030", "148070")
CODES = sorted({DIP, DOL, INV, K200, Q150, *ROT})
```
| 코드 | 이름(NAME, :48-49) | 역할 |
|---|---|---|
| 069500 | KODEX 200 | K200: 엔진의 '코스피' 판단값(5일 · 20일선) · DIP: 급락 되돌림 매수 종목(지금 꺼짐) |
| 229200 | KODEX 코스닥150 | Q150: 인버스 신호(10일 수익) · 인버스 익절 폭(60일 표준편차) |
| 251340 | KODEX 코스닥150선물인버스 | INV: 코스닥 과열 인버스 매수 종목 |
| 138230 | KOSEF 미국달러선물 | DOL: 하락 추세 매수 종목 + '원·달러 20일' 판단값 + 돌리기 후보 |
| 133690 | TIGER 미국나스닥100 | 돌리기 후보 |
| 132030 | KODEX 골드선물(H) | 돌리기 후보 |
| 148070 | KOSEF 국고채10년 | 돌리기 후보 |

### A-2. 시각
- `DECIDE_AT, LAST_ORDER = "1510", "1518"` (:40)
- 작업 시작 시 `now.strftime("%H%M") > "1520"` 이거나 주말이면 넘어감 (:267). `IDLE_START`(작업 설정 20261005) 앞이면 넘어감 (:259-262).
- `_wait_until("1510")` (:274) → 저장소 맞추기 → 끄기 스위치 다시 확인 → 장 열림 확인 (:293).
- 주문: `late = now > "1518"` 이면 모든 주문 건너뜀 · 상태는 `dict(state, last_day=day)`만 저장(보유 '지난 날' 숫자도 안 늘어남) (:381, :393-396, :431-432).
- 바구니도 `now <= LAST_ORDER(1518)`일 때만 돎 (:351).
- 작업 일정: `.github/workflows/daily-live.yml` 14:40 · 15:00 시작 → idle_live.py(15:10) 다음 단계에서 daily_live.py(15:20).

### A-3. 쓰는 값 (미래 참조 막는 방식)
- `now_price[code] = client.quote(code)["price"]` — 15:10 직후 현재가 (:296-301). K200 · Q150 · DOL 중 하나라도 못 받으면 `return 1`(주문 없음) (:302-304).
- `history(code, day)` = etf-data 종가 중 `str(d) < day` (어제까지) (:218-221).
- `px[code] = np.array(h + [now_price[code]])` 단, `len(h) >= 25`일 때만 (:305-309). → 마지막 값 = 오늘 15:10 값.
- 시장 폭: `live_breadth` = 전날 시총 150위 종목의 지금 값으로 final_group.compute (:224-245). 실패하면 `breadth = None` → step에 `100.0`을 넘김 → 엔진 끔(팔 것만) (:310-314, :373).
- `decide(..., at_1515=True)`로 부름 (:99) → 15:15용 문턱 사용.

### A-4. 신호 (idle_signal.decide, :24-52)
```
k, q, dol = px["069500"], px["229200"], px["138230"]
_ret(a, n) = a[-1] / a[-1-n] - 1      (자료 모자라면 nan)                  # :20-21
engine = used < 0.2 and breadth < 50                                       # :29
dip_th, q_th = (-0.045, 0.095) if at_1515 else (-0.05, 0.10)              # :32  (실제 운영은 -0.045 / 0.095)
dip  = breadth < 50 and _ret(k,5) <= dip_th                                # :34  (used 조건 없음)
ma20 = k[-20:].mean()                                                      # :36  오늘 15:10 값 포함 20개
d20  = _ret(dol, 20)
down = engine and not dip and d20 > 0.02 and k[-1] < ma20                  # :38
rot  = {} ; if engine and not dip and not down:                            # :41-44
    sc  = sorted((_ret(px[c],20), c) for c in ROT if c in px, 내림차순)
    top = [c for r,c in sc if r==r and r > 0][:2]
    rot = {c: 0.5 for c in top}   # 2개면 반반, 1개면 그 1개만 0.5(나머지 반은 현금), 0개면 현금
qinv = _ret(q, 10) >= q_th                                                 # :46-47  엔진 · used · 시장 폭과 무관
```
- idle_live.py:101-103: `DIP_ON = False`(:45) 이면 `sig["급락"] = False`로 덮음 → 급락 되돌림 새 매수 없음.
- `used`(엔진 켬 판단용) = (계좌 평가 − 엔진 장부 평가 − 바구니 장부 평가) / 총액 (:324-325, :349). 즉 '규칙(1일봉 · 15분봉 · 1시간봉 · 장부 밖 보유)'이 쓰는 몫.

### A-5. 하루 판단 step() (idle_live.py:84-201) — 순서 그대로
```
st = state 복사 ; 새 날이면 모든 보유 p["days"] += 1, cool > 0 이면 cool -= 1        # :94-98
sig = decide(px, breadth, used, at_1515=True) ; DIP_ON False면 급락=False            # :99-103

# 1) 인버스 청산 판단 먼저 (:106-116)
for 인버스 보유(장부 수량 >= 1, 오늘 값 있음):
    r = now/산값 - 1 ; take = p["take"] or 0.015
    r >= take → 익절 / r <= -0.015 → 손절 / days >= 10 → 기간 청산

inv_hold = 인버스 보유 and 청산 아님 ; inv_new = qinv and 인버스 보유 없음          # :117-118
if (inv_hold or inv_new) and (엔진 or 급락):                                          # :119-121
    sig = 엔진 False, 급락 False, 하락추세 False, 돌리기 {}      ← 인버스가 엔진보다 먼저(이 날 엔진 보유는 아래에서 팔림)

# 2) 보유 청산 (:122-155)
급락:   (인버스 들거나 삼) → 정리 / r >= +3% 익절 / r <= -3% 손절(cool = 21) / days >= 20
인버스: 위 1)의 결과
달러:   not (엔진 and 하락추세) or 급락 → 팖
돌리기: (엔진 and 하락추세 and not 급락 and code == 138230) → 종류만 '달러'로 바꿔 계속 들고 감(팔고 다시 사지 않음)
        elif not 엔진 or 급락 or 하락추세 → 팖
        elif 주 마지막 거래일 and code not in 오늘 돌리기 고름 → 팖
판 것은 orders에 (code,"sell",장부 수량 전부), exited에 종류 추가

# 3) 돈 (:157-160)
room        = max(0, total*(1-used) - reserve)          # reserve = 1일봉 비켜 둘 돈 + 바구니 평가액(:374)
avail       = (cash + 오늘 판 수량*오늘 값 합) * 0.97     # cash = cash_for_engine(:372)
inv_kept    = 계속 드는 인버스 수량 * 오늘 값
engine_room = max(0, room - inv_kept)

# 4) 엔진 매수 (:162-178)
if 급락 and 급락 미보유: cool == 0 and 오늘 급락 안 팖 → 069500 비중 1.0     (DIP_ON False라 실제로는 안 걸림)
elif 엔진 and 급락 미보유:
    하락추세 and 달러 미보유               → 138230 비중 1.0
    not 하락추세 and (주 끝 or 돌리기 미보유) → 돌리기 고른 코드 중 keep에 없는 것, 비중 0.5씩
for 각 매수: money = min(engine_room * w * 0.97, avail) ; qty = floor(money / 오늘 값)
             qty >= 1 이면 주문, avail -= qty*값                                   # :179-186

# 5) 인버스 매수 (:187-198)
if qinv and 인버스 미보유(keep) and 오늘 인버스 안 팖:
    engine_after = 오늘 산 금액 + keep 중 오늘 안 산 것의 평가
    money = min(max(0, room - engine_after) * 0.97, avail) ; qty = floor(money / INV 값)
    take  = inv_take(px["229200"])  → 상태에 저장(그 매매 내내 씀)
```
- **inv_take** (:58-65): `c = q_closes[:-1]`(오늘 15:10 값 뺌) · 61개 미만이거나 비유한 값이 있으면 0.015 · `r = c[-60:]/c[-61:-1]-1` · `clip(np.std(r) * sqrt(10) * 0.25, 0.015, 0.025)` (모표준편차 ddof=0).
- **주 끝** `week_end(day)` (:77-81): 다음 거래일(평일 · HOLIDAYS 2026-27 고정 목록 :51-53 제외)의 ISO 주가 다르면 참.
- **쉬기(cooldown)**: 급락 손절 뒤 `cool = DIP_COOL + 1 = 21` (:136). 인버스 · 달러 · 돌리기에는 쉬기 없음. 단 '판 날 같은 종류 다시 안 삼'(`exited`)은 급락 · 인버스에 적용(:165, :187). 돌리기 · 달러는 `exited` 검사가 없음(같은 날 판 코드라도 고름에 있으면 다시 살 수 있는 구조이나, 팔리는 조건과 사는 조건이 서로 배타라 사실상 안 생김).
- **days 셈**: 거래일 달력이 아니라 '봇이 새 날 step을 돈 횟수'. 늦게 돈 날(late)은 안 늘어남 → 인버스 10일 · 급락 20일은 '처리한 날' 기준.

### A-6. 돈 입력값 (run(), :315-374)
- `balance = PaperBroker().balance()` → `cash` = **D+2 예수금 `prvs_rcdl_excc_amt`(cash_d2)** 로 바꿔 줌(paper_trade.py:121-128). `value` = 보유 종목 `evlu_amt` 합(broker_kis.py:734-737). `eval_total`은 안 씀.
- `total = cash + value` (:323)
- `held` = 엔진 장부 `idle-live/paper-orders.json`의 held 와 계좌 수량 중 작은 값 (:320)
- `reserve` = `paper_trade.daily_reserve(day, total, 가격)` (:329-330) — C-4 참고.
- 자리 내기: `if reserve > 0 and held and reserve*1.36 > cash*0.98:` → `paper_trade.make_room(broker, balance, reserve, now)` 후 잔고 · 장부 · used 다시 셈 (:331-343). **엔진 보유(held)가 없으면 make_room을 아예 안 부름**(바구니만 있어도 안 팖).
- 바구니 실행 뒤 엔진 현금: `cash_for_engine = max(0, cash - (b_spent*1.36 if b_spent > 0 else b_spent) - reserve*1.36)` (:372). 바구니가 순매도면(b_spent<0) 그만큼 더해 줌.
- step 호출: `reserve = reserve + basket_after`(바구니 주문 뒤 평가액) (:373-374).

### A-7. 주문 (:388-430)
- `sorted(orders, key=lambda o: o[1] != "sell")` → **팔기 먼저** (:389).
- 같은 날 같은 열쇠 `f"{day}:{side}:{code}"` 이미 있으면 건너뜀 (:390-392).
- `broker.order` = 시장가(`ORD_DVSN "01"`, `ORD_UNPR "0"`, paper_trade.py:170-171) · 15:10이라 장중 연속 매매에서 바로 체결. 살 때 먼저 매수가능조회(VTTC8908R `nrcvb_buy_qty`/`max_buy_qty`)로 수량을 줄임(:159-165).
- 장부 held는 **접수 시점**에 바꿈 (:402). 실패한 매수는 상태에서 뺌, 실패한 매도는 상태에 남김 (:414-419).

---

## B. 사건 바구니 C (basket_live.py)

### B-1. 상수 (:29-30)
```
SLOTS, HOLD, GAP, TH, TOP = 5, 20, 20, -0.02, 200
KINDS = ("자사주취득", "무상증자")
```
- 갈래 이름은 collect_events.py:27-32 `kind_of(제목)`: 공백 뺀 제목에 `"자기주식취득"`이 들어 있으면 '자사주취득', `"무상증자"`면 '무상증자'(위에서부터 처음 맞는 것). 부분 문자열 맞춤이라 예: '자기주식취득신탁계약체결결정'도 자사주취득, '유무상증자결정'도 무상증자로 잡힘(유상증자 표식 '유상증자'는 '유무상증자'에 붙어 있지 않음). 자기주식처분 · 소각은 다른 갈래.
- 공시 자료: event-data/*.json, events.yml 평일 19:20 이어 받기.

### B-2. 사건 날짜 (:65-67, :169-177)
```
t0     = data_guard.prev_trading_day(client, day)   # 지수 0001 일봉에서 오늘보다 앞선 마지막 날
days   = etf-data 069500 종가 날짜 중 < day + [day]    # idle_live.py:352
before = days[days.index(t0) - 1]                    # t0 앞 거래일
ev     = sorted({(c,k) for c, rows in events for d,k in rows if before < d <= t0 and k in KINDS})
```
- 갈래만 거름(제목 · 금액 등 다른 조건 없음). 주말 · 휴일 접수분도 다음 거래일 t0 사건으로 들어감.
- t0를 못 알거나 days에 없으면: 새로 사지 않고 팔기만.

### B-3. 반응 (reactions, :47-62)
```
rows   = t0 종가가 있는 모든 종목(study.load_prices 의 price-data 우주)
caps.tag(rows, 200)              # 시총 = t0 종가 × t0까지 접수된 주식 수, 주식 수 모르면 순위 없음
inside = 순위 <= 200 인 코드
raw    = {c: P_t0 / P_before - 1  for c in inside if P_before 있음}
if len(raw) < 40: return {}, inside          # 표본 40 미만 → 그날 반응 전부 없음
mid    = statistics.median(raw.values())     # 200위 안 전체(사건 종목 포함) 가운데값
react  = {c: raw[c] - mid}
```

### B-4. 사건 걸러 사기 (step, :70-132)
```
# 팔기 먼저 판단
for 바구니 보유: 장부 수량 < 1 → 상태에서 지움(자리 내줌 등)
                 n = days_since(산 날) ; n >= 20 → 장부 수량 전부 시장가 매도      # 산 날 = 0
freed = 판 수량 × 오늘 값 ; left = (avail + freed) * 0.97 ; slot = capital / 5

for (code, kind) in ev:
    prev = last["code:kind"]
    if prev and days_since(prev) - days_since(t0) < 20: 건너뜀(last 안 바꿈)         # :98
    if code not in inside: 건너뜀(last 안 바꿈)
    r = react.get(code) ; None이면 건너뜀(last 안 바꿈)                                # 결측 처리
    last["code:kind"] = t0                         # ← 문턱 검사 '앞'에서 기록(:106)
    if kind == "자사주취득" and not r < -0.02: 건너뜀                                  # 엄격 < , 반응 = 가운데값 뺀 값
    이미 바구니 보유 → 건너뜀
    code in others(1일봉 · 15분봉 · 1시간봉 · 엔진 장부에 수량 > 0) → 건너뜀
    len(pos) >= 5 → 건너뜀
    qty = floor(min(slot*0.97, left) / 15:10 값) ; < 1 이면 건너뜀
    left -= qty*값 ; 매수 ; pos[code] = {day, price, kind, react}
last 중 days_since(d) > 40 지움
```
- 20거래일 겹침: 같은 종목 · 같은 갈래끼리만(키 `code:kind`), 069500 거래일 달력 기준, '마지막으로 센 사건'과만 견줌. **반응이 −2% 위라 안 산 자사주 사건도 last에 기록**되어 다음 20거래일 동안 같은 종목 자사주 사건을 막음. 200위 밖 · 반응 없음 사건은 기록 안 함.
- 무상증자도 200위 안 + 반응값 존재(표본 40 이상, 전날 값 있음)가 필요(반응 크기와는 무관).
- 익절 · 손절 없음. 청산은 20거래일째 15:10 시장가, 또는 make_room 강제 매도뿐.

### B-5. 바구니 돈 (idle_live.py:359-368)
```
d1_value  = Σ 1일봉 장부 held × 계좌 현재가(없으면 0)
b_capital = max(0, total * SHARES["1d"](0.5) - d1_value)     # 바구니 자신 보유는 안 뺌 → 한 칸 = 이 값/5 (날마다 바뀜)
others    = DAILY_BOOK ∪ M15_BOOK ∪ BOOK(1시간봉) ∪ IDLE_BOOK 의 held>0 코드
avail     = max(0, cash - reserve*1.36)                       # cash = D+2 예수금(make_room 뒤 값)
```
- 바구니 run 실패(예외) 시 엔진은 그대로 돎(:369-371).
- 주문: 팔기 먼저(:196), 열쇠 `day:side:code`, 시장가, 장부는 접수 때 바꿈(:205). 반환 `spent` = Σ 산 금액 − 판 금액(15:10 값), `val` = 주문 뒤 바구니 평가.

### B-6. 차례
- 15:10 안 순서: (필요 시) make_room → **바구니** → **엔진/인버스** → 15:20 1일봉. 문서 표현 "규칙 > 바구니 > 엔진"(idle_live.py:17, basket_live.py:13).
- 규칙 쪽(daily_live · m15_live · hourly_a)은 바구니 · 엔진이 든 종목을 피하는 검사가 **없음**(같은 종목을 규칙이 나중에 살 수 있음 · 장부는 따로).

---

## C. 돈 나누기 · 차례 · 현금 다툼 (paper_trade.py)

### C-1. 몫
```
SHARES = {"1h": env PAPER_SHARE_1H "0.0", "1d": env PAPER_SHARE_1D "0.5", "15m": env PAPER_SHARE_15M "0.5"}   # :36-37
SLOTS = 10                                                                                               # :40
MKT_MARGIN = env PAPER_MKT_MARGIN "1.36"                                                                 # :49
```
- 작업 설정 파일들에 PAPER_SHARE_* 덮어쓰기 없음 → 실제 1d 0.5 · 15m 0.5 · 1h 0. (m15-live.yml:75 주석 '15분봉 몫 20%'는 낡은 글.)
- 1시간봉: hourly_a.py:513 `execute(...)`(strategy 기본 "1h") → share 0 → total 0 → 매수 0 · 장부에 있는 것 매도만.

### C-2. 장부 (book_path, :256-257)
`{"1h": hourly-live/paper-orders.json, "1d": daily-live/paper-orders.json, "15m": m15-live/paper-orders.json, "idle": idle-live/paper-orders.json}` + 바구니 `basket-live/paper-orders.json`(:29).

### C-3. plan_orders (:317-354)
```
held  = 그 규칙 장부 held 와 계좌 수량 중 작은 값
cash  = balance["cash"]  (= D+2 예수금)
total = (cash + value) * share
팔기: 그 규칙 보유가 있으면, 남은 칸 <= 0 이면 전부, 아니면 max(1, round(have * 판칸/(판칸+남은칸)))
left  = (cash + 판 수량×prices 합) * 0.98
사기: money = min(total * 칸 / 10, left) ; qty = floor(money / prices[code]) ; left -= qty*price
```
- `prices`: 1일봉 = 15:20 현재가(now_price, daily_live.py:390) · 15분봉 = 그 봉 시가(m15_live.py:339-346) · 1시간봉 = 그 봉 시가.
- 초안식 `floor(total*share*slots/10/price)`는 대체로 맞으나 **현금(left) 상한**과 칸(1일봉 2~4칸 등)이 있음.

### C-4. daily_reserve (:216-253) — 엔진 · 바구니가 15:10에 비켜 둘 돈
```
near-now.json(m15-live, hourly-live) 중 date == 오늘 and at[11:16] >= "14:30" 인 것들
last = at 가장 늦은 것 ; picks = last["picks_daily"]
없으면 0
share   = total * 0.5
held    = Σ 1일봉 장부 held × 가격(계좌가 위에 15:10 현재가 덮음)
want    = min(len(picks)*4/10, 1.0) * share         # 후보마다 4칸으로 봄
reserve = max(0, min(want, share - held))
```
예외 나면 0.

### C-5. make_room (:260-314)
```
make_room(need): _give_room(엔진 장부, partial=False) → _give_room(바구니 장부, partial=True)
_give_room:
  if need*1.36 <= cash*0.98 or 장부 보유 없음: 그대로
  순서 = 상태의 산 날(day) 오래된 것 → 코드
  partial(바구니)이면: 한 번이라도 판 뒤 need*1.36 <= est*0.98 되면 멈춤 (est = cash + 판 수량×잔고 현재가)
  엔진은 전부 팖(partial=False)
  판 것은 장부 · 상태에서 지움, 2초 쉰 뒤 잔고 다시 받음
```
- 주의: 바구니 단계의 cash는 엔진을 판 뒤 다시 받은 잔고의 D+2 예수금 기준.
- 부르는 곳: ① execute(strategy in SHARES) — 1일봉 15:20, 15분봉 각 봉, 1시간봉(need 0) — `need = Σ total*칸/10`(살 것만, 값 있는 것) ② idle_live 15:10, `need = reserve`(엔진 보유 있을 때만).
- 1일봉 15:20 make_room 매도는 마감 동시호가라 15:30에야 돈이 풀림 → 그래서 15:10 reserve가 있음(:217-218 설명).

### C-6. 주문 형태 · 마감 시각
- 모두 시장가 `ORD_DVSN "01"` 현금 주문(:170), 매수는 매수가능 수량으로 줄임.
- 엔진/바구니 15:10(장중 연속, 15:18 넘으면 안 넣음) · 1일봉 15:20 판단, `LAST_ORDER 1528`(daily_live.py:34) → 마감 동시호가 → 종가 체결 · 15분봉 09:03~15:48 작업, 봉 시가.
- 장부 held 변경은 접수 때: paper_trade.py:405, idle_live.py:402, basket_live.py:205.

---

## D. F5 (공매도 비중 낮음 위 20)
- 운영 코드(research/ 밖) 구현 **없음**. research/ 밖 '공매도' 등장은 자료 모으기뿐: broker_kis.py:658-669(공매도 일별추이 조회), collect_short_credit.py, probe_short_credit.py, tests/test_short_credit.py, short-credit-history.yml. 'F5' 문자열은 research/ 밖에 없음.
- 연구에만: research/z054.py:73 `sim_factor`(달 첫 거래일 t 자료로 200위 안 점수 위 N=20 → t+1 종가 똑같은 비중 · 다음 달 첫 거래일+1까지 · 상한가 하루 미룸), :151 `("F5 공매도 비중 낮음 위 20", -X["공매도20"], 20)`, 점수 정의 research/z001.py:166 `X["공매도20"] = F["공매도비중"].rolling(20, min_periods=15).mean()`. 그 밖 z047 · z048 · z049 · z050 · z052 · z056 · z067.

---

## 초안(GPT) 대조

| 초안 주장 | 판정 | 실제 |
|---|---|---|
| E2 = 자사주 매입/취득 | 맞음(말만 다름) | 제목에 '자기주식취득' 포함(신탁계약 체결 제목도 걸림). '매입'이라는 말은 코드에 없음 |
| 반응 = 사건일 수익 − 200위 가운데값 < −0.02 (원수익 −2% 아님) | 맞음 | basket_live.py:58-62, :107 엄격 `<` |
| 200위 기준 · 최소 표본 40 | 맞음 | 표본 = 200위 안에서 전날 값 있는 종목 수 < 40 → 그날 반응 모두 없음 |
| 결측 처리 | 맞음(세부) | 반응 없으면 조용히 건너뜀 · 겹침 기록(last)도 안 남김 |
| E3 = 무상증자 | 맞음 | 반응 크기 무관. 단 200위 안 + 반응값 존재 필요. '유무상증자'도 포함 |
| E4 = E2 OR E3, 종목 · 갈래별 20거래일 겹침 막기 | 맞음 + 세부 다름 | 갈래별 키. **문턱을 못 넘긴 자사주 사건도 last에 기록돼 다음 20거래일 막음** · 069500 거래일 달력 · 마지막으로 센 사건과만 견줌 |
| 다음 거래일 15:10 진입 | 맞음 | 시장가 연속 매매, 15:18 넘으면 안 함(그 사건은 다음 날 t0가 바뀌어 사라짐) |
| 최대 5칸 | 맞음 | 한 칸 = (총액×0.5 − 1일봉 평가)/5, ×0.97, 현금 상한 |
| 산 날 0 기준 20거래일째 청산, TP/SL 없음 | 맞음 | n >= 20 |
| 돈 = 1일봉 안 쓰는 돈 | 맞음 | 바구니 자기 보유는 안 뺌(칸 크기 고정 아님, 날마다 다시 셈) |
| 엔진 강제 매도 | 맞음 | make_room: 엔진 전부 → 바구니 오래된 것부터 모자란 만큼. 15:10 idle에서는 엔진 보유가 있을 때만 부름 |
| 계좌 중복 차례 | 일부 다름 | 바구니만 다른 장부 보유 종목을 피함. 규칙 봇은 바구니/엔진 보유를 안 피함 |
| 엔진 켬 = 쓴 몫 < 20% and 시장 폭 < 50 | 맞음 | 쓴 몫 = 엔진 · 바구니 뺀 보유 평가/총액 |
| 급락 되돌림 | 꺼짐 | DIP_ON = False(:45). 보유분 청산 규칙만 남음 |
| 하락 추세 → 달러선물 | 맞음 | 138230 20일 > +2% and 069500(15:10 값) < 20일 평균(오늘 포함) |
| 돌리기 20일 위 2개 반반, 주 끝 다시 고름 | 맞음 + 세부 | 양수만 · 1개면 0.5만 · 첫 진입은 아무 날이나(돌리기 미보유면) · 주 중엔 바꾸지 않음 |
| 코스닥 인버스: 229200 10일 ≥ +9.5% → 251340 | 맞음 | 엔진 · used · 시장 폭과 무관, 엔진 몫(room)에서 돈 |
| 인버스 익절 D11b / 손절 −1.5% / 10일 | 맞음 | clip(0.25·σ60·√10, 1.5%, 2.5%), 산 날 고정. 10일은 '처리한 날' 수 |
| 인버스 들거나 사는 날 엔진 쉼 | 맞음 | 이 때 엔진 보유(달러 · 돌리기)는 '엔진 끔'으로 팔림 |
| 15:10 판단 · 15:18 뒤 주문 안 함 | 맞음 | 시작이 15:20 넘으면 그날 안 돎 |
| room = total*(1−used) − reserve | 맞음 + 세부 | reserve 자리에 '1일봉 비켜 둘 돈 + 바구니 평가'가 들어감 |
| avail = (현금 + 판 돈)×0.97 | 맞음 | 현금 = D+2 예수금 − 바구니 산 돈×1.36 − 비켜 둘 돈×1.36 |
| 팔기 먼저 | 맞음 | 엔진 · 바구니 · plan_orders 모두 |
| 장부는 접수 때 바꿈 | 맞음 | paper_trade.py:405 등 |
| 잔고 필드 | 확인 | cash = cash_d2(prvs_rcdl_excc_amt), value = 종목 evlu_amt 합, eval_total 안 씀 |
| F5 운영 구현 | 없음 | 연구(z054 등)에만 |

## 미확인
- 한투 모의 서버가 15:10 시장가를 실제로 몇 원에 체결하는지(장부는 15:10 현재가로 적음) — 증권사 응답이라 코드로 알 수 없음.
- daily_reserve가 읽는 near-now.json의 picks_daily가 1일봉 15:20 실제 후보와 얼마나 맞는지 — 작동 기록이 필요.
- px에 069500 · 229200 · 138230 중 하나가 25일 미만이면 decide에서 KeyError가 날 수 있음(etf-data 상태에 달림) — 실제 자료로 확인 안 함.

## 연구(research/z021.py events, :30-48)와 맞대 봄
- 연구도 `last[k] = j`를 문턱(pick, :110) **앞**에서 기록 → '문턱 못 넘긴 자사주 사건도 20일 막음'은 연구와 같음.
- 작은 차이: 연구는 반응이 nan(전날 값 없음)이어도 last를 기록한 뒤 dropna로 버림 · 운영은 반응 없으면 last를 안 남김. 또 연구는 그날 200위 가운데값을 표본 수 하한 없이 계산 · 운영은 40 미만이면 그날 전부 버림.
- 연구 칸 크기 = 바구니 평가(현금+보유)/5 · 운영 = (총액×0.5 − 1일봉 평가)/5.

## 다음 방향
- 위 작은 차이(반응 결측 시 last 기록 여부 · 표본 40 하한)가 성적에 주는 영향을 자르기 시험과 함께 재 볼지 결정.
- 규칙 봇이 바구니 · 엔진 보유 종목을 겹쳐 살 때 한 종목 40% 한도가 지켜지는지 따로 점검.
