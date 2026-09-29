"""1시간봉 3회차 — 봉 단위 계좌 모의 첫 판(hlab.simulate). 일봉 규칙(A그룹 꼴: 추세 문 또는 정배열 문 + 가르침 수급)의 '무엇을'은 그대로 두고
'언제 사나'만 바꿔 계좌로 견줌. 파는 법은 일봉 규칙을 봉에 옮김(봉 종가로 판단 → 다음 봉 시가에 팜):
- 추세 문으로 산 것: +5%에 처음 닿은 봉 뒤 절반 · +13% 전량 · −5% · 60봉(10거래일)
- 정배열 문으로 산 것: 다음 날 일봉 정배열이 깨지면(전날 종가로 앎) 다음 날 시가 · −10% · 한때 +8% 뒤 +1% 아래
칸: 추세 문 또는 3일 연속이면 4칸, 아니면 2칸(10칸 계좌). 씨앗 8번 가운데. 연 = 복리 없는 한 해 몫."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H

data = H.load()
codes = [c for c in data if not c.startswith("K")]
ranks, trend = H.cached_tables("20220101")
CTX = H.daily_context(codes, ranks, trend)
ATT = {c: H.attach(data[c], CTX[c], sorted(CTX[c])) for c in codes if c in CTX}
uni = H.Universe({d: v for d, v in ranks.items() if d >= "20230801"}, top=100)
data = {c: data[c] for c in ATT}
IN = {c: np.array([uni.ok(c, t) for t in data[c]["t"]]) for c in data}

def door(x):
    if not x: return None
    if x["추세문"]: return "추세"
    if x["정배열"] and 19 <= x["간격"] < 53 and (x["시장폭"] or 0) >= 50: return "정배열"
    return None
def ok(x): return door(x) is not None and x["가르침"]
def daystart(b): return np.r_[True, np.array([b["t"][i][:8] != b["t"][i - 1][:8] for i in range(1, len(b["t"]))])]
def hour_is(b, hh): return np.array([t[8:] == hh for t in b["t"]])

def ctx_now(c, b):     # 이 봉 시점에 아는 재료(전 거래일 것) · 종목 모음 안
    return np.array([ok(x) for x in ATT[c]]) & IN[c]
def e_morning(c, b):   # 다음 봉 = 다음 날 09시 시가. 그날 재료(= 오늘 종가로 앎)가 켜지면
    a = ATT[c]; ds = daystart(b); n = len(b["t"])
    m = np.zeros(n, bool)
    for k in range(n - 1):
        if ds[k + 1] and ok(a[k + 1]) and IN[c][k + 1]:
            m[k] = True
    return m
def e_noon(c, b): return ctx_now(c, b) & hour_is(b, "11")
def e_align(c, b):
    s = H.states(c, b, "A")["정배열"] == 1
    return ctx_now(c, b) & s & ~np.r_[False, s[:-1]]
def e_align_or_noon(c, b):
    al = e_align(c, b); nn = e_noon(c, b); days = [t[:8] for t in b["t"]]
    seen = set(); m = np.zeros(len(b["t"]), bool)
    for k in range(len(m)):
        if al[k] and days[k] not in seen:
            m[k] = True; seen.add(days[k])
        elif nn[k] and days[k] not in seen:
            m[k] = True; seen.add(days[k])
    return m

def size(c, b, k):
    x = ATT[c][k + 1] if k + 1 < len(b["t"]) else ATT[c][k]
    return 4 if x and (x["추세문"] or x["3일연속"]) else 2
def rank(c, b, k):
    x = ATT[c][k + 1] if k + 1 < len(b["t"]) else ATT[c][k]
    return (0 if x and x["추세문"] else 1, 0 if x and x["3일연속"] else 1)

def exit_daily(c, b, p, k):
    now = (b["c"][k] / p["price"] - 1) * 100
    x0 = ATT[c][p["i"]]
    kind = door(x0) or "정배열"
    held = k - p["i"]
    if kind == "추세":
        if now >= 13 or now <= -5 or held >= 60: return "all"
        before = b["c"][p["i"]:k].max() if k > p["i"] else -1
        if now >= 5 and (before / p["price"] - 1) * 100 < 5 and p["칸"] == p["처음칸"]:
            return max(1, p["처음칸"] // 2)
        return 0
    if now <= -10: return "all"
    if (p["peak"] / p["price"] - 1) * 100 >= 8 and now <= 1: return "all"
    if k + 1 < len(b["t"]):
        nx = ATT[c][k + 1]
        if nx is not None and not nx["정배열"]: return "all"
    return 0

print("== 1시간봉 3회차 (봉 단위 계좌 · 파는 법 = 일봉 규칙) ==", flush=True)
for tag, e in (("아침 09시 시가(일봉 신호 다음 날)", e_morning), ("12시 시가", e_noon),
               ("1시간봉 A 정배열 된 봉 다음", e_align), ("정배열 된 봉 다음, 없으면 12시", e_align_or_noon)):
    res = H.simulate(data, e, exit_daily, size, rank=rank)
    print(f"  {tag:28s} " + H.line(res), flush=True)
    print(f"      반기(씨앗 0, 계좌 몫 %): 앞 {res['앞']['반기'] if res['앞'] else '-'} · 뒤 {res['뒤']['반기'] if res['뒤'] else '-'}", flush=True)
print("끝", flush=True)
