"""F 6회차(첫 판) — 새 투자자 칸(금융투자 · 보험 · 은행 · 기타법인 · 외국인 등록/비등록 · 종금 · 기타단체)과 앞으로 수익.
investor-full에 받아진 종목만(수집 중) · 그날 시총 100위(nrl.inside) · 전날까지 5일 순매수 ÷ 20일 평균 거래량.
[1] 하나씩 그날 위 20% / 아래 20% (시장 넘는 수익 = 그날 100위 평균 대비)  [2] 1일봉 후보 문 + 가르침 안에서 새 칸 부호."""
import bisect
import glob
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import nrl

rule = nrl.rule
FULL = {}
for p in glob.glob("investor-full/*.json"):
    body = json.loads(Path(p).read_text(encoding="utf-8"))
    cols = body["cols"]
    rows = [r for r in body["rows"] if r[0] >= "20160101"]
    days = [r[0] for r in rows]
    acc = {c: np.concatenate([[0.0], np.cumsum([(r[i] or 0) for r in rows])]) for i, c in enumerate(cols) if c not in ("date", "종가")}
    FULL[body["code"]] = (days, acc)
NEW = ("금융투자", "보험", "은행", "종금", "기타단체", "기타법인", "외국인등록", "외국인비등록", "사모", "연기금", "투신", "외국인", "기관", "개인")
VOL = {}


def vol20(code, day):
    if code not in VOL:
        try:
            v = json.loads(Path(f"volume-data/{code}.json").read_text(encoding="utf-8"))["날"]
        except (OSError, ValueError, KeyError):
            v = []
        ds = [x[0] for x in v]
        VOL[code] = (ds, np.concatenate([[0.0], np.cumsum([x[1] for x in v])]))
    ds, a = VOL[code]
    k = bisect.bisect_left(ds, day)
    return (a[k] - a[k - 20]) / 20 if k >= 20 else None


def power(r, col, n=5):
    got = FULL.get(r["code"])
    if not got:
        return None
    days, acc = got
    k = bisect.bisect_left(days, r["date"])          # 전날까지
    if k < n:
        return None
    v = vol20(r["code"], r["date"])
    return (acc[col][k] - acc[col][k - n]) / v if v else None


# 앞으로 20 · 60일 수익과 그날 100위 평균
rows = [r for r in nrl.inside]
fw = {}
for r in rows:
    c = nrl.lanes[r["code"]]["closes"]
    i = r["i"]
    for h in (20, 60):
        fw[(r["code"], r["date"], h)] = c[i + 1 + h] / c[i + 1] - 1 if i + 1 + h < len(c) and c[i + 1] else None
mean = {}
for r in rows:
    for h in (20, 60):
        v = fw[(r["code"], r["date"], h)]
        if v is not None:
            mean.setdefault((r["date"], h), []).append(v)
mean = {k: float(np.mean(v)) for k, v in mean.items()}
ex = lambda r, h: (None if fw[(r["code"], r["date"], h)] is None else fw[(r["code"], r["date"], h)] - mean[(r["date"], h)])
have = [r for r in rows if r["code"] in FULL]
MID = rule.MID
print(f"== F 6회차(첫 판): 받아진 {len(FULL)}종목 · 그날 100위 줄 {len(have)}/{len(rows)} ==", flush=True)


def show(name, picked):
    out = [f"  {name:28s}"]
    for side, test in (("앞", lambda d: d < MID), ("뒤", lambda d: d >= MID)):
        sel = [r for r in picked if test(r["date"])]
        a = [ex(r, 20) for r in sel if ex(r, 20) is not None]
        b = [ex(r, 60) for r in sel if ex(r, 60) is not None]
        if not a:
            out.append(f"| {side} 없음")
            continue
        out.append(f"| {side} {len(a):5d}건 20일 {np.mean(a) * 100:+5.2f} 60일 {np.mean(b) * 100:+5.2f} 가운데 {np.median(a) * 100:+5.2f} 이김 {np.mean(np.array(a) > 0) * 100:4.1f}")
    print(" ".join(out), flush=True)


print("\n[1] 하나씩 · 그날(받아진 종목 안) 위 20% / 아래 20%", flush=True)
byday = {}
for r in have:
    byday.setdefault(r["date"], []).append(r)
for col in NEW:
    top, bot = [], []
    for d, rs in byday.items():
        vals = [(power(r, col), r) for r in rs]
        vals = [(v, r) for v, r in vals if v is not None]
        if len(vals) < 10:
            continue
        vals.sort(key=lambda x: x[0])
        q = max(1, len(vals) // 5)
        bot += [r for _, r in vals[:q]]
        top += [r for _, r in vals[-q:]]
    show(f"{col} 위 20%", top)
    show(f"{col} 아래 20%", bot)
print("\n[2] 1일봉 후보 문 + 가르침(지금 규칙의 사는 조건) 안에서 새 칸 부호", flush=True)
door = [r for r in have if nrl.BASE_HOLD(r)]
show("지금 사는 조건 전부", door)
for col in NEW[:10]:
    pos = [r for r in door if (power(r, col) or 0) > 0]
    neg = [r for r in door if (power(r, col) or 0) < 0]
    show(f"+ {col} 순매수", pos)
    show(f"+ {col} 순매도", neg)
print("끝", flush=True)
