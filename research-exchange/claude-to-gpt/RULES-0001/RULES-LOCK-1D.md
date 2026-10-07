> **부록 — 하위 에이전트가 기준 커밋 00b98ab1을 읽기만 해서 쓴 추출(코드 실행 · 호출 없음).** 본문 판정은 RULES-LOCK.md · DATA-AVAILABILITY.md가 우선.
> 본 세션 재확인: daily_live.py:42-50 size_of · :54-79 exit_decision · lab.py:30 · :58-65 · :283 · :291(EMA180 기울기) · final_group.py:37 · :274(19.0 ≤ 간격 < 53.0) · 합성 as-is 시험 d1.* 18건.

# 1일봉 새 82회차 — 운영 코드 그대로의 규칙 (기준 커밋 00b98ab1655c84806357f44f2de6f1509ef1447f)

모든 경로는 `BASE=<기준점 폴더>/` 아래입니다.
읽기만 했고, 증권사 · 네트워크를 건드리는 코드는 돌리지 않았습니다.
`%` 단위: 코드의 문턱은 대부분 **퍼센트 숫자**(1.46, 20.0, 19.0, 53.0, 50.0)이고 소수(0.0146)가 아닙니다.

---

## 0. 실행 틀 · 시각 (daily_live.py `run`)

| 항목 | 위치 | 코드 그대로 |
|---|---|---|
| 상수 | daily_live.py:32-37 | `SLOTS = 10` · `POOL = 150` · `DECIDE_AT, LAST_ORDER, SETTLE_AT = "1520", "1528", "1532"` · `VOL_BIG, FRESH_DAYS = 2.0, 10` · `COST = 0.25` · `KIN = 0.6` |
| 시작일 | :299-302 | `start = os.getenv("DAILY_START", ...)`; `if start and day < start: return 0` (workflow에서 `DAILY_START: '20261002'`) |
| 하루 한 번 | :303, :313 | `if state.get("last_day") == day: return 0` (git 맞춤 뒤 한 번 더 봄) |
| 주말 · 늦은 실행 | :306 | `if now.weekday() >= 5 or now.strftime("%H%M") > "1600": return 0` |
| 판단 시각 | :309 | `_wait_until(DECIDE_AT)` — 15초마다 보며 KST 15:20까지 기다림 |
| 저장소 맞춤 | :311 | `_pt.sync_repo()` (LIVE_GIT_SYNC=1이면 `git pull --rebase`) |
| 늦음 판정 | :316 | `late = datetime.now(KST).strftime("%H%M") > LAST_ORDER` — **15:20 기다림 + git 맞춤 직후 한 번만** 셈. 그 뒤 시세 150여 개 조회 · 계산이 길어져도 다시 보지 않음 → 주문은 15:28 넘어서도 나갈 수 있음(paper_trade에도 시각 막음 없음) |
| 장 열린 날 | :326 | `I.market_open_today(client, day)` — 특별 장시간 날(collect_kis_intraday.py:61 `SPECIAL_HOURS`: 20261119 수능 · 20270104)은 쉼 |
| 예약 | .github/workflows/daily-live.yml:8-9 | `cron: '40 5 * * 1-5'`(KST 14:40) · `cron: '0 6 * * 1-5'`(KST 15:00, 첫 예약 밀림 대비). `concurrency: group: daily-live, cancel-in-progress: false` → 둘째는 첫째 뒤에 돌고 `last_day == day`면 끝 |
| 같은 작업 안 순서 | daily-live.yml | 먼저 `idle_live.py`(빈칸 엔진 · 사건 바구니, 15:10 판단) → 그다음 `daily_live.py` |
| CAPS_ADJ | daily-live.yml env | 설정 없음 → caps.py:28 `ADJ = os.getenv("CAPS_ADJ", "0") == "1"` = False → **raw DART 주식수** |
| 확정 기록 | :396-405 | `_wait_until(SETTLE_AT)`(15:32) → `client.quote(code)["price"]`를 '종가'로 써서 `settle` → `state["last_day"] = day` → 저장 |

### "15:32 종가 대체"의 정체
daily_live.py:397-403
```python
close = {}
for code in {x["code"] for x in sells + buys} | set(held):
    try:
        close[code] = client.quote(code)["price"]          # 15:32 현재가 = 장 끝난 뒤라 종가로 봄
    except broker_kis.BrokerError:
        close[code] = now_price.get(code)                   # 실패하면 15:20 값으로 대신
fills = settle(state, day, sells, buys, close)
```
- 연습 장부(daily-live/state.json)는 **모의 주문 체결 여부와 상관없이** 이 값으로 사고판 것으로 적음. 모의 주문의 체결 조회는 이 파일 어디에도 없음.
- 15:32 조회가 실패하면 15:20 값이 '종가'로 적힘.
- 늦어서(`late`) 주문을 안 넣은 날도 장부에는 적음(:394-395 "연습 계좌에만 적음").
→ 초안의 "15:32 close substitution is not fill evidence"는 **맞음(CONFIRMED)**.

---

## 1. 대상(유니버스)

### 1-a 자료 확인 (data_guard)
- daily_live.py:332 `ready, last, why = data_guard.daily_ready(prices, data_guard.prev_trading_day(client, day))`
- `prev_trading_day`(data_guard.py:19-26): KOSPI 지수(0001) 일봉에서 `str(r.get("date")) < day and r.get("종가")`인 가장 늦은 날. 실패면 None.
- `daily_ready`(data_guard.py:34-49): `edge = _minus(expect, 30)`; `pool = [d for d in lasts.values() if d >= edge]`; `have = sum(d >= expect for d in pool)`; `if rate < share: return False` (`SHARE = 0.9`) → **90% 이상이면 됨(≥, 포함)**. expect가 None이면 가장 많은 종목의 마지막 날.
- daily_live.py:334-336 `if not last or last >= day: return 1` → 이날은 **팔기까지 전부 쉼**.
- daily_live.py:379-380 `if not ready: cands = []` → 새로 사지 않고 팔기만.

### 1-b 시세를 받을 묶음(POOL=150)
- prices = `study.load_prices()` (study.py:27-40): price-data/*.json 전부(507개 파일), `c and float(c) > 0`인 줄만, **120줄 이상** 종목만. 수정주가.
- daily_live.py:337 `yest = [... for c, v in prices.items() if v["rows"][-1][0] == last]` — 마지막 줄이 '어제 거래일'인 종목만.
- daily_live.py:338 `caps.tag(yest, POOL)` → 어제 종가 × `known_by(code, 어제)`의 raw 주식수로 순위.
- daily_live.py:339 `pool = {r["code"] for r in yest if (r.get(caps.RANK) or 999) <= POOL} | set(state.get("positions", {}))`
- daily_live.py:346 `if len(quotes) < len(pool) * 0.8: return 1` → 시세 80% 못 받으면 하루 전부 쉼.
- daily_live.py:349-350 `live = {c: {"name": ..., "rows": prices[c]["rows"] + [(day, quotes[c]["price"])]} for c in quotes if c in prices}` → **오늘 줄 = 15:20 현재가**를 붙임.

### 1-c 100위 판정 (매수 조건)
- final_group.py:172-173 `today = [row for row in latest if row["date"] == day]`; `caps.tag(today, rule.TOP)` — **live 묶음(어제 150위 + 보유) 안에서만** 오늘 순위를 매김.
- caps.py:151-169 `tag`: `count = known_by(row["code"], row["date"])` — 접수일 `when > day`면 멈춤 → **그날(오늘) 접수분까지 포함**한 가장 최근 DART 주식수(raw). `row[SIZE] = count * row["price"]`(오늘 15:20 값). 주식수가 없거나 값 0이면 순위 없음. `here.sort(key=lambda one: -one[SIZE])`; `enumerate(here, 1)` → 1부터. 같은 시총이면 입력 순서(코드 오름차순) 유지.
- `top` 인자는 `tag` 안에서 쓰이지 않음(모두 순위 매김).
- 판정: final_group.py:256-258 `rank_gap = ([] if place is not None and place <= rule.TOP else [...])`, rule.py:95 `TOP = 100` → **순위 ≤ 100(포함)**, 순위 모름이면 탈락.
- 제외: 명시적 제외 목록(ETF · 우선주 · 관리종목 등) **없음**. 실질 제외 = price-data 507종목 밖, 120줄 미만, 어제 종가 없음(150위 밖이 됨), 주식수 자료(share-data 499개) 없음, 시세 조회 실패, lab.build 행이 안 나오는 종목(아래).
- lab.build(lab.py:281-282, 317-321): `if len(closes) <= warmup + max(horizons): continue` (warmup=120, horizons=(0,) → 121줄 이상), 그날 EMA 5·20·40·60 중 하나라도 None이면 그 줄 없음.

---

## 2. 공통 문(두 갈래 모두)

### 2-a 수급(스승님 조건) — final_group.py
- 호출: :192 `flow = flow_before(flow_rows(row["code"]), next_day if flow_day == "next" else (flow_day or day))` → daily_live는 flow_day를 안 주므로 `day`=오늘.
- `flow_rows`(:220-227): investor-data/{code}.json, 칸 `('date','개인','외국인','기관','투신','연기금','사모','종가')`. 값은 **순매수 수량(주)** (broker_kis.py:432-433 `prsn_ntby_qty`, `frgn_ntby_qty`, `ivtr_ntby_qty`). 파일 없으면 `[]`.
- `flow_before`(:230-241):
  ```python
  before = [r for r in rows if r.get("date", "") < day][-days:]      # days = FLOW_DAYS = 5, 오늘 제외
  if len(before) < days: return None
  if any(r.get(k) is None for r in before for k in ("외국인", "투신", "개인")): return None
  if (datetime.strptime(day, "%Y%m%d") - last).days > FLOW_STALE: return None   # FLOW_STALE = 10 (달력 일)
  return {"외국인": sum(...), "투신": sum(...), "개인": sum(...)}
  ```
  → **오늘 미포함, 오늘보다 앞선 마지막 5줄**(어제 자료가 아직 없으면 그 앞 5줄 — 마지막 줄이 10달력일 안이면 그대로 씀; '어제 거래일이 꼭 들어 있어야' 하는 검사는 없음).
- `flow_gap`(:244-251): `if flow is None: 실패`; 통과 = `flow["외국인"] > 0 and flow["투신"] > 0 and flow["개인"] < 0` (모두 엄격 부등호). 자료 없음 → **탈락**.
- 두 갈래 모두에 붙음(:279-282).

### 2-b 45일 목표가 내림 거르기 — daily_live.py:215-231 `target_cut`
```python
got = study.target_timeline(code)
if not got: return False                                   # 목표가 자료 없으면 거르지 않음(통과)
def at(d):
    k = bisect.bisect_left(days, d)                        # d보다 '앞' 날짜만(d 당일 제외)
    if k == 0: return None
    return got[k - 1][1] if days[k - 1] >= study._months_before(d, 3) else None   # 마지막 목표가 날이 3달 안이어야
then = (datetime.strptime(day, "%Y%m%d") - timedelta(days=back_days)).strftime("%Y%m%d")   # 45 달력일 앞
a, b = at(day), at(then)
return bool(a and b and a["목표가"] < b["목표가"])          # 엄격히 '내림'만, 둘 중 하나라도 없으면 False
```
- `study.target_timeline`(study.py:56-84): opinion-data/{code}.json, `target > 0`인 줄만 날짜순. 줄마다 `seen[member or date] = row`(증권사별 가장 최근 것), `edge = _months_before(row["date"], 3)`; `live = [r for r in seen.values() if r["date"] >= edge]`; 가운데값(짝수면 가운데 둘 평균). → **각 목록 날짜 기준 3달 안 증권사별 마지막 목표가의 중앙값**.
- `_months_before`(study.py:87-93): 달만 빼고 일은 그대로 문자열(예: 20260531 → 20260231, 존재하지 않는 날짜여도 문자열 비교).
- 적용: daily_live.py:358-362 — picks 가운데 `target_cut`이면 후보에서 빼고 `near` 목록으로.
- 데이터 지연: 오늘 낸 목표가는 `bisect_left`라 안 씀(전날까지).

### 2-c 그 밖 매수 막음
- 상한가: daily_live.py:132 `if (rate.get(code) or 0) >= 29.5: continue` (rate = 현재가 응답 `prdy_ctrt`, 15:20 등락률%).
- 닮음(상관): §6 참고.

---

## 3. ① 추세 문 (RULE_DOOR "추세 규칙")

daily_live는 `rule.holds`를 직접 부르지 않고 final_group.shortfalls(:254-283)로 같은 조건을 봄:
```python
if vol is None or vol > calm_edge:            → 탈락    # 통과 = vol <= calm_edge
if slope is None or slope < rule.SLOPE:       → 탈락    # 통과 = slope >= 1.46
if sixty is None or sixty < rule.SIXTY:       → 탈락    # 통과 = sixty >= 20.0
```
(rule.py:172-177 `trend_leg`도 같은 뜻: `(row.get("변동성") or 99) > _calm` 탈락, `(row.get("추세 기울기") or -99) >= SLOPE and (row.get("60일 전 대비") or -99) >= SIXTY`.)
상수: rule.py:96-98 `CALM = 0.4` · `SLOPE = 1.46` · `SIXTY = 20.0`.

### 3-a 변동성 `변동성` = lab.rolling_std(closes, 20) (lab.py:96-107)
```python
moves = [None] + [(closes[i] / closes[i - 1] - 1) * 100 ...]       # 일간 등락률 %
chunk = [m for m in moves[i - window + 1:i + 1] if m is not None]  # 오늘(i) 포함 최근 20개
if len(chunk) >= window // 2:                                      # 10개 이상
    out[i] = math.sqrt(sum((m - mean) ** 2 for m in chunk) / (len(chunk) - 1))   # ddof = 1
```
- 오늘 등락 = 15:20 현재가 ÷ 어제 종가.

### 3-b '조용함' 문턱 calm_edge — **오늘 단면이 아님**
- daily_live.py:351-352 `calm = (_load(Path("study") / "a_group.json", {}) or {}).get("calm_edge")`; `found = final_group.compute(live, calm=calm)`.
- final_group.py:168 `rule._calm = calm if calm is not None else vols[int(len(vols) * rule.CALM)]`.
- a_group.json의 값은 전날 저녁 A group 작업(`final_group.py` main, a-group.yml ← Daily price history ← Daily DART refresh cron `0 9 * * 1-5` = KST 18:00)이 만든 것:
  - final_group.py:153-156, 165, 168: 모든 price-data 종목을 BATCH=40씩 `lab.build(part, horizons=(0,))`, **모든 날짜의 모든 줄**의 `변동성`을 모아 `vols.sort()` → `vols[int(len(vols) * 0.4)]` (보간 없음, 아래쪽 순위 자리).
  - 즉 **507종목 × 전 기간(각 종목 121번째 줄부터) 종목-날 변동성의 40% 자리** — 오늘 100위 안 단면도, 오늘 전체 단면도 아님.
  - final_group.py:216 `"calm_edge": round(rule._calm, 3)` → **소수 셋째 자리로 반올림**한 값이 다음 날 문턱(현재 파일 값 2.148, 2026-10-07 19:07 만듦).
- a_group.json이 없거나 calm_edge가 없으면: live 묶음(약 150종목)의 전 기간 변동성(오늘 15:20 줄 포함)으로 즉석 계산.
- 비교: `vol > calm_edge` 탈락 → **같으면 통과(≤)**.

### 3-c 180일선 기울기 `추세 기울기` — **EMA**, SMA 아님
- lab.py:30 `AXES = {..., "추세": 180}`, :283 `emas = {span: ema_series(closes, span) ...}`, :291 `slopes[name] = slope_series(line)`, :345 `**{f"{name} 기울기": slopes[name][i] ...}` → 키 `"추세 기울기"`.
- `ema_series`(lab.py:44-55): 처음 180개 단순평균으로 시작, `alpha = 2 / (span + 1)`, 그 뒤 `value = close * alpha + value * (1 - alpha)` — **종목 자료 첫날부터 누적**(시작점에 따라 값이 조금 달라짐).
- `slope_series`(lab.py:58-65): `out[i] = (now / before - 1) * 100` with `before = line[i - 5]` (SLOPE_STEP = 5줄 = 5거래일), 오늘(15:20 값) 포함.
- 통과: `slope >= 1.46` (퍼센트).

### 3-d 60일 수익 `60일 전 대비`
- lab.py:355-356 `((price / closes[i - 60] - 1) * 100 if i >= 60 and closes[i - 60] else None)` — 60줄 앞 종가 대비, 오늘 값 = 15:20 현재가. 통과 `>= 20.0`.

---

## 4. ② 정배열 문 (LINES_DOOR "정배열 추세")

final_group.py:36-38 `LINES = (3, 15, 20, 90, 150, 200)` · `SPREAD = (19.0, 53.0)` · `BREADTH = 50.0`

### 4-a 정배열 `lines_now`(final_group.py:62-78)
- `if len(closes) < max(LINES) + 50: return None` → **250줄 미만이면 계산 안 함 → 정배열 문 탈락** ("상장 기간이 짧아").
- `sma`(:50-59): 단순이동평균, 오늘(15:20 값) 포함, 앞 span−1개 None.
- `aligned(k)`: `all(means[a][k] is not None and means[b][k] is not None and means[a][k] > means[b][k] for a, b in zip(LINES, LINES[1:]))` → **3>15>20>90>150>200 모두 엄격 >**.
- `"된 지"`: 오늘부터 거꾸로 정배열이 이어진 날 수(오늘 포함) — **크기(3칸) 판정에는 쓰이지 않음**(§5-c).
- `"간격"`: `(means[3][last] / means[200][last] - 1) * 100`.

### 4-b 간격 범위 — 위쪽은 **미포함**
final_group.py:274 `if gap is None or not SPREAD[0] <= gap < SPREAD[1]:` 탈락 → 통과 = **`19.0 <= 간격 < 53.0`** (퍼센트). (연구 nrl.py:108 `LO <= f["간격"] < HI`와 같음.)

### 4-c 시장 폭(breadth) — final_group.py:174-179
```python
shape = {row["code"]: lines_now([c for _, c in prices[row["code"]]["rows"]][:row["i"] + 1]) for row in today}
inside = [row for row in today if caps.inside(row, rule.TOP) and shape.get(row["code"])]
breadth = (sum(shape[row["code"]]["50>200"] for row in inside) / len(inside) * 100 if inside else 0.0)
```
- `"50>200"`: `means[50][last] > means[200][last]` (엄격 >, SMA, 오늘 15:20 값 포함).
- 분모 = **live 묶음 안 오늘 순위 1~100 가운데 250줄 이상 있는 종목**.
- 판정: :276 `if breadth < BREADTH:` 탈락 → **통과 = breadth >= 50.0**(반올림 전 값으로 비교; 출력만 `round(breadth, 1)`).

### 4-d 갈래 정하기
- :195 `doors = [door for door, gaps in missing.items() if not gaps]` (순서: 추세 규칙 → 정배열 추세).
- daily_live.py:363 `"추세문": final_group.RULE_DOOR in (one.get("갈래") or [])` → 둘 다 통과면 **추세로 취급**(kind "추세", 4칸, 추세 팔기).

---

## 5. 크기(칸)

daily_live.py:43-51
```python
def size_of(c):
    if c.get("추세문"):   return 4
    if c.get("3일연속"):  return 4
    if (c.get("거래량비") or 0) >= VOL_BIG and (c.get("정배열일수") or 999) <= FRESH_DAYS:   # 2.0, 10
        return 3
    return 2
```
(연구 nrl.py:202-203 `BASE_SIZE`와 같은 꼴.)

### 5-a 3일 연속 `steady3`(daily_live.py:195-198)
```python
rows = [r for r in final_group.flow_rows(code) if r.get("date", "") < day][-3:]
return len(rows) == 3 and all((r.get("외국인") or 0) > 0 and (r.get("투신") or 0) > 0 for r in rows)
```
- 오늘 제외, 앞선 마지막 3줄, 날마다 외국인 > 0 **그리고** 투신 > 0 (엄격). None은 0으로 봐 실패. 낡음 검사 없음.

### 5-b 거래량비 `volume_ratio`(daily_live.py:201-212) — 연구(lab.volume_line)와 조금 다름
```python
past = [row[k] for row in body.get("날") or [] if str(row[0]) < day and row[k]][-20:]   # 오늘 전, 0/None 아닌 줄의 마지막 20개
if len(past) < 20: return None                                                         # 정확히 20개 필요
m = statistics.median(past)
return today_volume / m if m else None
```
- `today_volume` = 15:20 현재가 응답 `acml_vol`(누적 거래량, **마감 동시호가 몫 빠짐**). 없으면 None.
- None → `size_of`에서 `or 0` → 3칸 안 됨.
- 연구 lab.volume_line(lab.py:240-271)은 `line[max(0, k - 20):k]` 범위 중 0 아닌 값이 **10개 이상**이면 되고 오늘 값은 종가 기준 거래량.
- daily_live.py:363-364에서 `one`의 값을 덮어씀(`{**one, ..., "거래량비": volume_ratio(...)}`).

### 5-c 정배열일수 — **EMA 5>20>60>120 네 선**이 이어진 날 수(SMA 6선 아님)
- final_group.py:191 `"정배열일수": row.get("정배열일수")` ← lab.py:365 `"정배열일수": lined[i]`
- lab.py:33 `FAN = (5, 20, 60, 120)`, :301-305 `lined = run_length([all(emas[order[k]][i] and emas[order[k + 1]][i] and emas[order[k]][i] > emas[order[k + 1]][i] for k in range(3)) ...])`
- `run_length`(lab.py:127-133): 참이면 +1(오늘 포함), 거짓이면 0.
- **`or 999` 버릇**: 오늘 EMA 네 선 정배열이 아니면 값 0 → `0 or 999` = 999 → `<= 10` 거짓 → 3칸 불가. 1~10이면 3칸 가능. (SMA 6선 정배열 '된 지'와는 다른 값.)

### 5-d 칸이 모자랄 때
daily_live.py:136 `take = min(size_of(c), free)` → **남은 칸만큼 일부 배정 허용**.

---

## 6. 후보 순서 · 고르기 · 다시 사기

daily_live.py:121-142
```python
free = SLOTS - sum(left.values())                     # 팔고 남은 칸(값 못 받은 보유도 칸 그대로 셈)
holding = [c for c, k in left.items() if k > 0]
for c in sorted(cands, key=lambda c: -(c.get("추세 기울기") or -99))[:max(free, 0)]:
    if free <= 0: break
    if code in holding: continue                      # 이미 든 것(일부만 판 것 포함)
    if (rate.get(code) or 0) >= 29.5: continue        # 상한가
    if not kin_ok(code, holding): continue            # 닮음
    take = min(size_of(c), free); free -= take; holding.append(code)
```
- 순서: `추세 기울기` 내림차순. 이 값은 final_group.py:186 `_round(row.get("추세 기울기"))` → **소수 둘째 자리 반올림 값**으로 정렬(문턱 판정은 반올림 전 값). 기울기 None 또는 정확히 0.0이면 `or -99` → 맨 뒤.
- 같은 값: Python 정렬은 안정 → picks 순서(final_group.py:213 같은 열쇠로 정렬, 그 앞은 코드 오름차순) → **코드 오름차순**.
- **'빈 칸 수만큼 위 후보만'**: 정렬 뒤 `[:max(free, 0)]` — 칸 수(예: 6)만큼의 후보만 봄. 그중 보유 · 상한가 · 닮음으로 빠진 자리는 아래 후보로 채우지 않음.
- 하루 매수 종목 수 제한: **없음**(rule.PER_DAY=2는 이 경로에서 안 씀).
- 닮음(상관) 거르기: daily_live.py:82-99 `kin_checker` + lab.py:1219-1250
  - `lab.moves`: 일간 수익률(소수), 첫 값 0.0, 앞 종가 0이면 0.0. 오늘 = 15:20 값.
  - `kinship`: 후보는 오늘 index i, 보유 종목은 **산 날 index**(`bisect.bisect_right(days[h], str(b)) - 1`; 오늘 새로 담은 것은 오늘 index)로 끝나는 최근 60개 수익률의 Pearson 상관(`top / wide`, 평균 뺀 곱합 ÷ 제곱합 루트 곱). `i < 60 or j < 60`이면 0.0, 분모 0이면 0.0.
  - 통과: `all(lab.kinship(...) < kin for h in holding if h in idx)` → **상관 < 0.6** (0.6이면 탈락). live에 없는 보유 종목은 검사 안 함.
- 다시 사기: 오늘 **전량** 판 종목은 `left`가 0이라 `holding`에 없음 → **같은 날 다시 살 수 있음**(시험 tests/test_daily_live.py `test_sold_today_can_be_bought_again_like_research`). 일부만 판 종목은 못 삼. 쉬는 기간(cooldown) **없음**.
- 하한가면 팔기 취소: daily_live.py:116-117 `if n and (rate.get(code) or 0) <= -29.5: why, n = None, 0`.

---

## 7. 팔기 — daily_live.py:54-79 `exit_decision`

평가 값 `close` = **15:20 현재가**(daily_live.py:110 `price = now_price.get(code)`; 값 없으면 그 보유는 판단 안 하고 칸 그대로 :111-113).
`now = (close / pos["price"] - 1) * 100` — 산 값은 15:32 기록 '종가'.
`q = dict(p, days=p.get("days", 0) + 1)` (:114) → 산 날 다음 거래일이 1.

### 7-a ① 추세(위에서부터 처음 걸리는 하나)
1. `if now >= 13:` 전량 `pos["칸"]`
2. `if now <= -5:` 전량
3. `if pos["days"] >= 10:` 전량 (산 날 뒤 10번째 '처리된' 거래일 종가)
4. 절반: `before = (pos["max_close"] / pos["price"] - 1) * 100` (어제까지 기록 종가의 최고, 산 날 종가 포함) —
   `if now >= 5 and before < 5 and pos["칸"] == pos["처음칸"] and pos["칸"] >= 2: return min(2, pos["칸"] - 1)`
   → 4칸이면 2칸, 3칸 2칸, 2칸 1칸, 1칸 안 나눔. 한 번 판 뒤(`칸 != 처음칸`)엔 다시 안 함. 일부 배정으로 처음부터 1칸이면 절반 없음.
- 추세 보유는 정배열 깨짐으로 팔지 않음.

### 7-b ② 정배열
1. `if now <= -10:` 전량
2. `peak = (max(pos["peak"], close) / pos["price"] - 1) * 100` (기록 최고 종가와 **오늘 15:20 값** 중 큰 것); `if peak >= 8 and now <= 1:` 전량
3. `if aligned_now is False:` 전량 — `aligned[code] = bool(form and form.get("정배열"))`(daily_live.py:368-372, SMA 3>15>20>90>150>200, 오늘 15:20 값 포함). **250줄 미만이라 form이 None이어도 False → 깨짐으로 팜**. live에 없는 종목은 None → 이 이유로는 안 팖.
- 기간 제한 **없음**, 익절 문턱 없음.

---

## 8. 칸 · 돈 계산(모의투자, paper_trade.py)

- 장부 칸: daily_live.py:32 `SLOTS = 10`; 1칸 = 1일봉 몫의 10%.
- 몫: paper_trade.py:36 `SHARES = {..., "1d": float(os.getenv("PAPER_SHARE_1D", "0.5")), ...}` → 0.5.
- 총액: :327 `total = (cash + float(balance.get("value") or 0)) * share` — `cash`는 :126-127 D+2 예수금(`cash_d2`, 있으면), `value`는 **계좌 전체 평가액**(다른 규칙 보유 포함). 즉 1일봉 몫 = 모의 계좌 전체 총액 × 0.5.
- 매수 수량: :348-349 `money = min(total * x["칸"] / SLOTS, left)`; `qty = math.floor(money / price)` — `price` = **15:20 현재가**(daily_live.py:390 `now_price`). `left = (cash + freed) * 0.98`(:340), `freed` = 같은 차례 매도 수량 × 15:20 값. 1주 미만이면 건너뜀. 주문 직전 `buyable`(매수가능 수량)보다 많으면 줄임(:159-164).
- 매도 수량: :335-336 `remain = 판 뒤 남은 칸`; `qty = have if remain <= 0 else max(1, round(have * x["칸"] / (x["칸"] + remain)))` (Python `round` = 은행가 반올림). `have` = 1일봉 장부 held와 계좌 수량 중 작은 값.
- 주문: 시장가 `ORD_DVSN "01"`, 매도를 먼저 목록에 넣음(:331-337 → :341-353). 같은 열쇠(`f"{bar_id}:{type}:{code}:{decided}"`, bar_id = day+"1520")면 다시 안 넣음.
- make_room(:260-314): 1일봉 매수 필요액 `need = Σ total*칸/10`(:381)에 대해 `if need * MKT_MARGIN <= cash * 0.98 or not held: 그대로`(MKT_MARGIN 1.36). 아니면 빈칸 엔진 보유를 **전부** 팔고, 그래도 모자라면 사건 바구니를 오래된 것부터 모자란 만큼. 이 매도도 접수만 하고 2초 쉰 뒤 잔고 다시 받음.
- 15:10 빈칸 엔진이 미리 비켜 두는 돈: `daily_reserve`(:216-253) — 후보마다 4칸으로 보고 `min(len(picks) * 4 / SLOTS, 1.0) * share`까지(1일봉 판단 자체에는 영향 없음).

---

## 9. 장부 상태 바뀜

- state.json 꼴: `{"positions": {code: {...}}, "closed": [...], "last_day": "YYYYMMDD"}`
- positions(daily_live.py:174-175): `code, name, kind('추세'|'정배열'), price(산 날 15:32 값), peak, max_close, last_close, 칸, 처음칸, days(0), bought(day), why`
- closed(:159-160): `code, name, kind, 산 날, 판 날, 칸, 산 값, 판 값, 손익(=round((c / p["price"] - 1) * 100 - COST, 2)), 까닭`; `state["closed"] = closed[-1000:]`
- settle 순서(:152-169): 보유마다 `days += 1` → 팔 것이고 `c`가 있으면 `part = min(x["칸"], p["칸"])` 기록, 칸 빼고 0이면 지움 → 남으면 `peak`, `max_close`, `last_close`를 `c`로 올림(둘 다 같은 식으로 올라감; 쓰는 곳만 다름). 그 뒤 매수 추가(같은 코드면 덮어씀 = 같은 날 다시 산 경우).
- `c`가 없으면(15:32 · 15:20 값 모두 없음): 매도는 장부에 안 적히고(칸 그대로, 모의 주문은 이미 나갔을 수 있음), 매수는 장부에 안 생김.
- 모의 주문 장부(daily-live/paper-orders.json): :405 `book["held"][code] = max(0, book["held"].get(code, 0) + (qty if side == "buy" else -qty))` — **'접수'만으로 held를 바꿈**. 체결 확인 · 미체결 정정 코드 없음. 실패면 `status "실패 · ..."`, held 그대로.
- 연습 장부와 모의 주문은 따로 움직임: 주문이 거절 · 미체결이어도 state.json은 산 것으로 적힘.
- `days`는 이 작업이 실제로 처리한 날에만 1씩 늘어남(작업이 하루 통째로 쉬면 그날은 안 늘어남 → 10거래일 청산이 밀릴 수 있음).

---

## 10. 하루 판단 의사코드(코드 그대로의 순서)

```text
run(now):
  day = 오늘(KST)
  if DAILY_START and day < DAILY_START: return
  if state.last_day == day: return
  if 주말 or 지금 > 16:00: return
  wait until 15:20 ; git pull(LIVE_GIT_SYNC) ; state 다시 읽기 ; if state.last_day == day: return
  late = (지금 > "1528")                          # 여기서 한 번만
  증권사 인증(최대 3번, 65초 쉼) ; if 오늘 장 안 열림 or 특별 장시간 날: return
  prices = price-data(120줄 이상)
  last = KOSPI 지수로 본 어제 거래일 ; ready = (last까지 종가 있는 종목 비율 >= 0.9, 30일 넘게 멈춘 종목 제외)
  if not last or last >= day: return 1             # 팔기도 안 함
  yest = 마지막 줄 날짜 == last 인 종목 ; 어제 종가 × raw 주식수로 순위
  pool = {순위 <= 150} ∪ 보유
  quotes = 15:20 현재가(실패 종목 건너뜀) ; if len(quotes) < 0.8*len(pool): return 1
  live = pool 종목의 일봉 + (day, 15:20 값)
  calm = a_group.json.calm_edge(전날 저녁, 507종목 전 기간 변동성 40% 자리, 소수 3자리)
  compute(live, calm):
     today 줄마다 lab.build 특징(변동성 · EMA180 5일 기울기% · 60일% · EMA4선 정배열일수)
     오늘 순위 = live 안에서 (오늘 접수분까지 raw 주식수 × 15:20 값) 내림차순
     shape = SMA(3,15,20,90,150,200,50) on 오늘 값 포함 (250줄 미만이면 None)
     breadth = 순위<=100 & shape있음 가운데 SMA50 > SMA200 비율 ×100
     flow = 오늘 앞 5줄 합(외국인, 투신, 개인), 모자람 · None · 10달력일 넘게 낡음 → None
     추세문 = 순위<=100 and 변동성<=calm and 기울기>=1.46 and 60일>=20 and 외>0 and 투>0 and 개<0
     정배열문 = 순위<=100 and shape and SMA 엄격 정배열 and 19<=간격<53 and breadth>=50 and 수급 같음
     picks = 둘 중 하나라도 통과 ; 기울기(소수 2자리) 내림차순
  cands = picks 가운데 not target_cut(45달력일 앞보다 중앙 목표가 엄격히 낮음; 자료 없으면 통과)
         + 추세문, 3일연속(앞 3줄 매일 외>0 & 투>0), 거래량비(15:20 누적 ÷ 앞 20개 중앙값, 20개 필요)
  칸 = 4 if 추세문 else 4 if 3일연속 else 3 if 거래량비>=2 and 0<EMA정배열일수<=10 else 2
  aligned[보유] = SMA 6선 정배열(오늘 값 포함, shape 없으면 False)
  if not ready: cands = []
  decide:
     보유마다(15:20 값 없으면 그대로):
        days+1 ; exit_decision(15:20 값)
        추세: >=+13 전량 → <=-5 전량 → days>=10 전량 → (+5 처음 & 칸==처음칸 & 칸>=2) min(2,칸-1)
        정배열: <=-10 전량 → (최고(기록최고,오늘)>=+8 & 지금<=+1) 전량 → 정배열 아님 전량
        등락률 <= -29.5 이면 팔기 취소
     free = 10 - 남은 칸 합 ; holding = 남은 칸>0 종목
     for c in 기울기순 상위 free개:
        if free<=0 break ; if c in holding skip ; if 등락률>=29.5 skip
        if 보유(산 날 창) 누구와든 60일 상관 >= 0.6 skip
        take = min(칸, free) ; free -= take ; holding += c
  디스코드(판단)
  if (sells or buys) and not late: paper_trade.execute(시장가, 1d 몫 0.5, 수량 floor, 접수로 held 갱신, make_room)
  elif late: 주문 없이 알림
  wait until 15:32 ; close = 15:32 현재가(실패면 15:20 값)
  settle(close) ; last_day = day ; state.json · today.json · alerts.json 저장 ; 디스코드(체결)
```

---

## 11. GPT 초안 대조

| 초안 주장 | 판정 | 실제(코드) |
|---|---|---|
| common: top100 | **CONFIRMED** (단서) | 순위 ≤ 100. 단, 순위는 'live 묶음(어제 150위+보유)' 안에서 오늘 15:20 값 × 오늘까지 접수된 **raw** DART 주식수로 매김(caps.py:151-169, final_group.py:173) |
| foreign 5d sum>0, 투신 5d sum>0, 개인 sum<0 up to previous trading day | **CONFIRMED** (단서) | `date < day` 마지막 5줄, 엄격 부등호, 자료 없음/모자람/None → 탈락, 마지막 줄이 10달력일 넘게 낡으면 탈락. '어제'가 꼭 들어 있는지는 안 봄. 단위는 순매수 **수량** |
| trend: 20d volatility in universe bottom 40% | **DIFFERENT** | 문턱 = 전날 저녁 a_group.json `calm_edge` = **507종목 × 전 기간 종목-날 변동성을 모은 것의 40% 자리**(`vols[int(len*0.4)]`, 보간 없음, 소수 3자리 반올림). 오늘 단면 · 100위 안이 아님. 통과 `vol <= edge`. 변동성 = 오늘 포함 20개 일간 %등락의 표본표준편차(ddof=1, 10개 이상) |
| trend: SMA180 5-trading-day change >= 0.0146 | **DIFFERENT** | **EMA180**(lab.ema_series, 처음 180개 SMA로 시작) 5줄 변화 `(ema[i]/ema[i-5]-1)*100 >= 1.46` — 단위는 % (뜻으로는 0.0146과 같음) |
| trend: 60-trading-day return >= 0.20 | **CONFIRMED** | `(price / closes[i-60] - 1) * 100 >= 20.0`, 오늘 = 15:20 값 |
| aligned: SMA3>SMA15>SMA20>SMA90>SMA150>SMA200 | **CONFIRMED** | 모두 엄격 >, 250줄 미만이면 None → 탈락 |
| aligned: 0.19 <= SMA3/SMA200-1 <= 0.53 | **DIFFERENT** | 위쪽 **미포함**: `19.0 <= gap < 53.0` (final_group.py:274) |
| aligned: top100 share SMA50>SMA200 >= 0.50 | **CONFIRMED** (단서) | `breadth >= 50.0`(%); 분모 = 순위≤100이면서 250줄 이상 종목, SMA50 > SMA200 엄격, 오늘 15:20 값 포함 |
| sizing: trend OR 3일 연속 외국인>0 & 투신>0 → 4 | **CONFIRMED** | `date < day` 마지막 3줄 정확히 3개, 날마다 엄격 > 0 |
| else 거래량/prior-20 median >= 2 AND aligned age <= 10 → 3 | **DIFFERENT(부분)** | 거래량 = **15:20 누적 거래량**(마감 동시호가 빠짐), 앞 20개(0 아닌 값) 정확히 20개 필요. '정배열 나이' = **EMA 5>20>60>120 네 선** 연속일수(lab `정배열일수`), SMA 6선 아님; 0이면 `or 999`로 실패 → 실제 조건 `1 <= 일수 <= 10` |
| else 2 | **CONFIRMED** | |
| partial allocation of free slots allowed | **CONFIRMED** | `take = min(size_of(c), free)` |
| trend exits order: >=+13 → <=-5 → held>=10 → first>=+5 partial min(2, slots-1) | **CONFIRMED** (단서) | 절반은 `칸 == 처음칸 and 칸 >= 2`일 때만, '처음' = 어제까지 기록 종가 최고 < +5. 평가 값은 15:20 값. 하한가(등락률 ≤ −29.5)면 모든 팔기 취소 |
| aligned exits: <=-10 OR (peak>=+8 AND now<=+1) OR alignment broken | **CONFIRMED** (단서) | 순서 그대로. peak에 오늘 15:20 값 포함. 기간 제한 없음. 정배열 계산 불가(250줄 미만)도 '깨짐'으로 팜 |
| 15:20 provisional price | **CONFIRMED** | 판단 · 수량 · 평가 모두 15:20 현재가 |
| orders until 15:28 | **DIFFERENT(부분)** | 15:28은 15:20 기다림+git 맞춤 직후 **한 번만** 검사(`late`). 그 뒤 시세 조회 · 계산 · make_room이 길어져도 다시 안 봄 → 15:28 뒤 주문도 가능. 늦으면 주문 없이 장부만 적음 |
| "15:32 close substitution is not fill evidence" | **CONFIRMED** | settle은 15:32 현재가(실패 시 15:20 값)로 장부를 적고, 모의 주문 체결은 확인하지 않음. 주문 장부 held도 '접수'로 바뀜 |
| (초안에 없음) | **NOT IN DRAFT** | 45일 목표가 내림 거르기 · 자료 확인(90%) · 시세 80% · 상한가 매수 막음(≥29.5) · 하한가 매도 막음(≤−29.5) · 상관 < 0.6 · '빈 칸 수만큼 위 후보만' · 같은 날 전량 매도 종목 다시 사기 · 둘 다 통과면 추세 취급 |

---

## 12. 미확인

- **15:20 현재가의 실제 뜻**: 15:20부터 마감 동시호가라 `stck_prpr`가 15:20 직전 체결가인지 예상 체결가인지는 증권사 동작이라 코드로 확인 불가.
- **15:32 값 = 공식 종가인가**: 동시호가 연장(VI 등)이나 늦은 반영이 있으면 다를 수 있음. 코드에는 확인 장치 없음.
- **모의 주문 실제 체결 여부**: 이 경로(daily_live · paper_trade)에 체결 조회 코드가 없어 장부와 실제 체결의 차이는 코드로 알 수 없음(reconcile.py 등 별도 작업은 이번 범위 밖).
- **a_group.json이 15:20에 늘 전날 것인지**: 저녁 작업 사슬(DART 18:00 → 일봉 → A group)이 실패하면 그 앞 날 값이 쓰임. 낡음 검사 없음. 실제 실패 이력은 확인 안 함.
- **수급 · 목표가 · 거래량 자료가 15:20에 '어제'까지 차 있는지**: 코드는 낡음을 10달력일(수급 5일 합)만 보고, 3일 연속 · 거래량 · 목표가는 안 봄. 실제 채움 정도는 확인 안 함.
- **raw 주식수의 쪼개기 · 무상증자 직후 오차**: CAPS_ADJ가 꺼져 있어 다음 보고서 접수 전까지 순위가 틀릴 수 있음 — 실제 영향 종목은 확인 안 함.

## 다음 방향
- 초안을 고칠 곳: 변동성 문턱(전 기간 모음 · 전날 값), EMA180 기울기, 간격 위쪽 미포함(<53), 3칸의 '정배열 나이'(EMA 네 선 · 0이면 실패), 15:28 한 번 검사.
- 연구(lab.volume_line)와 운영(volume_ratio)의 거래량비 차이(10개 vs 20개, 종가 거래량 vs 15:20 누적)는 자르기 시험 · 15분봉 확인 대상으로 따로 보는 것이 좋겠습니다.
