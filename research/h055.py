"""55회차 — 54회차 특징으로 '오르기 전에 사는 규칙'을 만들 수 있나(미래 참조 없이).
54회차: +50% 시작 날은 ① 변동성 큼 · 밴드 폭 · 모임폭 큼(2~3.5배) ② 두 모양 — 이미 세게 오르는 중(추세 기울기 · 60일 수익 · 정배열폭 위 10%) 또는
크게 빠진 뒤(EMA20 이격 · 60일 전고점 대비 아래 10%) ③ 작은 종목(순위 뒤쪽) ④ 거래량 늘어남 ⑤ 흑자 전환. 수급은 거의 상관없음.
규칙의 문턱은 **그 달 첫날 앞 자료로만** 정한 분위(달마다 다시) — 미래 참조 없음. 산 값 = 신호 다음 날 종가(price-data엔 종가만 있어 보수적으로).
결과: 신호 수 · 60일 안 +50% 간 몫(적중) · 20 · 60일 뒤 수익 가운데/평균 · 60일 안 가장 깊은 낙폭 가운데 — 세 시기 따로."""
import sys, json, bisect, pickle
sys.path.insert(0, "/home/user/stock-dash")
from pathlib import Path
import numpy as np
S = "/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad"
data, start = pickle.load(open(f"{S}/h054.pkl", "rb"))
start = set(map(tuple, start))
END = "20260930"
PER = (("2017~19", "20170101", "20200101"), ("2020~22", "20200101", "20230101"), ("2023~26", "20230101", END))
def per(day):
    for n, a, b in PER:
        if a <= day < b: return n
# 달마다 지난 자료로만 분위 문턱
FEATS = ["변동성", "밴드 폭", "모임폭", "추세 기울기", "60일 전 대비", "정배열폭", "EMA20 이격", "60일 전고점 대비", "거래량비", "순위", "20일 전 대비"]
months = sorted({x[1][:6] for x in data})
by_month = {}
for x in data: by_month.setdefault(x[1][:6], []).append(x)
Q = {}          # (feat, month) → np.quantile(past values, qs)
qs = [0.1, 0.3, 0.5, 0.7, 0.9]
past = {f: [] for f in FEATS}
for m in months:
    for f in FEATS:
        arr = np.array(past[f][-400000:], float)
        Q[(f, m)] = np.quantile(arr, qs) if len(arr) > 20000 else None
    for x in by_month[m]:
        for f in FEATS:
            v = x[3].get(f)
            if v is not None: past[f].append(v)
def qbin(f, x):
    """그 달 앞 자료로 정한 분위 칸(0: 아래 10% · 1: 10~30 · 2: 30~50 · 3: 50~70 · 4: 70~90 · 5: 위 10%)."""
    t = Q.get((f, x[1][:6])); v = x[3].get(f)
    if t is None or v is None: return None
    return int(np.searchsorted(t, v, side="right"))
closes = {}
def path(code):
    if code not in closes:
        got = [x for x in json.loads(Path(f"price-data/{code}.json").read_text(encoding="utf-8"))["closes"] if x[0] < END]
        closes[code] = ([x[0] for x in got], np.array([x[1] for x in got], float))
    return closes[code]
def outcome(code, day):
    d, c = path(code); k = bisect.bisect_left(d, day)
    if k + 61 >= len(c): return None
    buy = c[k + 1]                               # 다음 날 종가에 삼
    seg = c[k + 2:k + 62]
    return {"20": (c[k + 21] / buy - 1) * 100, "60": (c[k + 61] / buy - 1) * 100,
            "max": (seg.max() / buy - 1) * 100, "min": (seg.min() / buy - 1) * 100}
def evaluate(tag, cond, gap=20):
    """cond(x) 참인 날에 삼(한 종목은 gap거래일 안 다시 안 셈)."""
    last = {}; res = {n: [] for n, _, _ in PER}
    for x in data:
        p = per(x[1])
        if p is None or not cond(x): continue
        code = x[0]
        d, _ = path(code); k = bisect.bisect_left(d, x[1])
        if code in last and k - last[code] < gap: continue
        last[code] = k
        o = outcome(code, x[1])
        if o: res[p].append(o)
    parts = []
    for n, _, _ in PER:
        r = res[n]
        if not r: parts.append(f"{n} 0건"); continue
        hit = np.mean([o["max"] >= 50 for o in r]) * 100
        parts.append(f"{n} {len(r)}건 적중 {hit:4.1f}% · 60일 가운데 {np.median([o['60'] for o in r]):+5.1f} 평균 {np.mean([o['60'] for o in r]):+5.1f} · 20일 평균 {np.mean([o['20'] for o in r]):+5.1f} · 낙폭 가운데 {np.median([o['min'] for o in r]):+5.1f}")
    print(f"  {tag}\n      " + "\n      ".join(parts), flush=True)
b = qbin
print("== 55회차 (+50% 오르기 전에 사는 규칙 찾기) ==", flush=True)
evaluate("모든 날(기준)", lambda x: True, gap=60)
evaluate("변동성 위 10%", lambda x: b("변동성", x) == 5)
evaluate("모멘텀형: 추세 기울기 위 10% · 변동성 위 30%", lambda x: b("추세 기울기", x) == 5 and (b("변동성", x) or 0) >= 4)
evaluate("모멘텀형 + 거래량비 위 30%", lambda x: b("추세 기울기", x) == 5 and (b("변동성", x) or 0) >= 4 and (b("거래량비", x) or 0) >= 4)
evaluate("모멘텀형 + 작은 종목(순위 뒤 30%)", lambda x: b("추세 기울기", x) == 5 and (b("변동성", x) or 0) >= 4 and (b("순위", x) or 0) >= 4)
evaluate("모멘텀형: 정배열폭 위 10% · 모임폭 위 10%", lambda x: b("정배열폭", x) == 5 and b("모임폭", x) == 5)
evaluate("반등형: EMA20 이격 아래 10% · 60일 전고점 대비 아래 10%", lambda x: b("EMA20 이격", x) == 0 and b("60일 전고점 대비", x) == 0)
evaluate("반등형 + 변동성 위 30%", lambda x: b("EMA20 이격", x) == 0 and b("60일 전고점 대비", x) == 0 and (b("변동성", x) or 0) >= 4)
evaluate("반등형 + 작은 종목", lambda x: b("EMA20 이격", x) == 0 and b("60일 전고점 대비", x) == 0 and (b("순위", x) or 0) >= 4)
evaluate("흑자 전환 · 변동성 위 30%", lambda x: x[3].get("흑자 전환") == 1 and (b("변동성", x) or 0) >= 4)
evaluate("흑자 전환 · 추세 기울기 위 30%", lambda x: x[3].get("흑자 전환") == 1 and (b("추세 기울기", x) or 0) >= 4)
evaluate("밴드 폭 위 10% · 거래량비 위 10%", lambda x: b("밴드 폭", x) == 5 and b("거래량비", x) == 5)
evaluate("20일 전 대비 위 10% · 거래량비 위 10% · 작은 종목", lambda x: b("20일 전 대비", x) == 5 and b("거래량비", x) == 5 and (b("순위", x) or 0) >= 4)
print("끝", flush=True)
