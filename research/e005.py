"""E 5회차 — 실적을 '발표 시점 사건'으로 다시 봄(사용자 2026-10-02: "이익은 비교를 통하여 가감하였는지 판단해야 하는데 그런 게 없다").

1 ~ 3회차는 '날마다 그때 알려진 최근 실적'을 붙여 봐서, 80일 전에 나온 실적과 어제 나온 실적이 같은 무게였음(효과가 묽어짐).
이번에는 **실적 보고서 접수일마다 한 번** — 그날 알려진 숫자로 '늘었나 줄었나 · 얼마나 놀랍나 · 빨라졌나'를 판정하고 그 뒤 주가를 봄.

판정(영업이익 o · 매출 s, 그 분기 석 달 · 4분기는 사업 − 1~3분기):
  증감      : 작년 같은 분기보다 늘음/줄음 · 흑자 전환 · 적자 전환 · 적자 지속
  놀람(SUE) : (이번 분기 − 작년 같은 분기) ÷ 지난 8분기 그 차이의 표준편차 — 평소 흔들림보다 얼마나 크게 바뀌었나
  가속      : 이번 분기 증가율 − 지난 분기 증가율(빨라짐/느려짐)
  이익률    : 영업이익률이 작년 같은 분기보다 몇 %p 좋아졌나
  매출 동반 : 매출도 늘었나(이익만 는 것과 구분)
  발표 반응 : 접수 전날 종가 → 접수 다음 날 종가, 코스피 대비(시장이 그 숫자를 어떻게 받았나)
주가(코스피 대비 초과): 들어감 = 접수 다음 날 종가. 20 · 60거래일 뒤. 이미 오른 몫 = 접수 21일 전 → 전날.
두 반(2017 ~ 2020 / 2021 ~). 그날 시총 100위 안 종목만(규칙 대상과 같게).
E_DAY=prelim: 날짜를 정식 보고서 접수일 대신 **잠정실적 공시 날**(event-data kind '잠정실적', 분기 끝 뒤 ~ 정식 접수일 사이 첫 날)로.
  숫자는 정식 보고서 값(잠정 숫자와 거의 같음 · 잠정 공시 본문은 받지 않음) — 잠정이 없는 분기는 뺌.
"""
import os
import bisect
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import etools as E
import nrl

ROOT = Path("/home/user/stock-dash")
MID = "20210101"
top = {(r["code"], r["date"]) for r in nrl.inside}
topdays = {}
for r in nrl.inside:
    topdays.setdefault(r["code"], []).append(r["date"])
for v in topdays.values():
    v.sort()
idx = json.loads((ROOT / "market-data/index_KOSPI.json").read_text(encoding="utf-8"))["rows"]
idays = [r["date"] for r in idx]
iclose = np.array([r["종가"] for r in idx], float)


def iat(day, off=0):
    k = bisect.bisect_right(idays, day) - 1 + off
    return iclose[k] if 0 <= k < len(iclose) else None


def in_top(code, day):
    """접수일 근처(앞 5거래일 안)에 그날 시총 100위 안이었나."""
    ds = topdays.get(code) or []
    k = bisect.bisect_right(ds, day)
    return k > 0 and ds[k - 1] >= str(int(day) - 10)


PRELIM = os.environ.get("E_DAY") == "prelim"
QEND = {1: "0331", 2: "0630", 3: "0930", 4: "1231"}


def prelim_days(code):
    try:
        rows = json.loads((ROOT / f"event-data/{code}.json").read_text(encoding="utf-8"))["rows"]
    except (OSError, ValueError, KeyError):
        return []
    return sorted({r["date"] for r in rows if r.get("kind") == "잠정실적"})


events = []
for p in sorted((ROOT / "quarter-data").glob("*.json")):
    code = p.stem
    q = E.series(code)
    if not q:
        continue
    try:
        cl = json.loads((ROOT / f"price-data/{code}.json").read_text(encoding="utf-8"))["closes"]
    except (OSError, ValueError, KeyError):
        continue
    pdays = [d for d, _ in cl]
    pc = np.array([c for _, c in cl], float)
    keys = sorted(q)
    pre_days = prelim_days(code) if PRELIM else []
    for n, key in enumerate(keys):
        v = q[key]
        day = v["날"]
        if PRELIM:
            qend = f"{key[0]}{QEND[key[1]]}"
            cand = [d for d in pre_days if qend < d <= day]
            if not cand:
                continue
            day = cand[0]
        if day < "20170101" or v.get("o") is None or v.get("o0") is None:
            continue
        if not in_top(code, day):
            continue
        k = bisect.bisect_right(pdays, day) - 1          # 접수일(또는 그 앞 마지막 거래일)
        if k < 22 or k + 62 >= len(pc):
            continue
        dk = pdays[k]
        a, b = pc[k - 1], pc[k + 1]
        i0, i1 = iat(pdays[k - 1]), iat(pdays[k + 1])
        if not (a and b and i0 and i1):
            continue
        ear = (b / a - 1) - (i1 / i0 - 1)
        pre = (pc[k - 1] / pc[k - 21] - 1) - ((iat(pdays[k - 1]) or 0) / (iat(pdays[k - 21]) or 1) - 1)
        out = {}
        for h in (20, 60):
            ia, ib = iat(pdays[k + 1]), iat(pdays[k + 1 + h])
            out[h] = (pc[k + 1 + h] / pc[k + 1] - 1) - (ib / ia - 1) if ia and ib else None
        o, o0, s, s0 = v["o"], v["o0"], v.get("s"), v.get("s0")
        # 놀람: 지난 8분기 (o − o0)의 흔들림
        past = [q[x]["o"] - q[x]["o0"] for x in keys[max(0, n - 8):n] if q[x].get("o") is not None and q[x].get("o0") is not None]
        sd = float(np.std(past)) if len(past) >= 4 else None
        sue = (o - o0) / sd if sd else None
        g = E.growth(o, o0)
        prev = q.get(keys[n - 1]) if n else None
        gp = E.growth(prev.get("o"), prev.get("o0")) if prev else None
        accel = g - gp if g is not None and gp is not None else None
        margin = (o / s - o0 / s0) * 100 if s and s0 and s > 0 and s0 > 0 else None
        events.append({"code": code, "day": dk, "turn": E.turn(o, o0), "g": g, "sue": sue, "accel": accel, "margin": margin,
                       "sales_up": (s is not None and s0 is not None and s > s0), "ear": ear, "pre": pre, 20: out[20], 60: out[60]})
print(f"== E 5회차: 실적 사건 {len(events)}개 · 날짜 = {'잠정실적 공시 날' if PRELIM else '정식 보고서 접수일'}(그날 시총 100위 안 · 2017~) ==", flush=True)


def show(name, sel):
    line = [f"  {name:34s}"]
    for side, test in (("앞", lambda d: d < MID), ("뒤", lambda d: d >= MID)):
        x = [e for e in sel if test(e["day"])]
        a = [e[20] for e in x if e[20] is not None]
        b = [e[60] for e in x if e[60] is not None]
        if len(a) < 15:
            line.append(f"| {side} {len(a)}건(적음)")
            continue
        line.append(f"| {side} {len(a):4d}건 반응 {np.mean([e['ear'] for e in x]) * 100:+5.2f} 앞서오름 {np.mean([e['pre'] for e in x]) * 100:+5.2f} "
                    f"20일 {np.mean(a) * 100:+5.2f} 60일 {np.mean(b) * 100:+5.2f} 이김 {np.mean(np.array(a) > 0) * 100:4.1f}")
    print(" ".join(line), flush=True)


show("전체", events)
print("\n[1] 영업이익 증감 판정(작년 같은 분기 대비)", flush=True)
for t in ("흑전", "늘음", "줄음", "적전", "적지"):
    show(t, [e for e in events if e["turn"] == t])
print("\n[2] 늘음 안에서 증가 폭", flush=True)
for lo, hi, nm in ((0, 20, "+0~20%"), (20, 50, "+20~50%"), (50, 100, "+50~100%"), (100, 1e9, "+100%↑")):
    show(nm, [e for e in events if e["turn"] == "늘음" and e["g"] is not None and lo <= e["g"] < hi])
print("\n[3] 놀람 크기(SUE) 다섯 무리", flush=True)
s = [e for e in events if e["sue"] is not None]
qs = np.quantile([e["sue"] for e in s], [0.2, 0.4, 0.6, 0.8])
print(f"  경계 {', '.join(f'{x:.2f}' for x in qs)}", flush=True)
for j in range(5):
    lo = -np.inf if j == 0 else qs[j - 1]
    hi = np.inf if j == 4 else qs[j]
    show(f"SUE 무리 {j + 1}", [e for e in s if lo <= e["sue"] < hi])
print("\n[4] 가속(이번 분기 증가율 − 지난 분기 증가율) · 늘음 안에서", flush=True)
show("늘음 · 빨라짐", [e for e in events if e["turn"] == "늘음" and (e["accel"] or 0) > 0])
show("늘음 · 느려짐", [e for e in events if e["turn"] == "늘음" and e["accel"] is not None and e["accel"] <= 0])
print("\n[5] 이익률 · 매출 동반", flush=True)
show("이익률 +2%p↑", [e for e in events if (e["margin"] or 0) >= 2])
show("이익률 −2%p↓", [e for e in events if e["margin"] is not None and e["margin"] <= -2])
show("영업이익↑ · 매출↑", [e for e in events if e["turn"] in ("늘음", "흑전") and e["sales_up"]])
show("영업이익↑ · 매출↓", [e for e in events if e["turn"] in ("늘음", "흑전") and not e["sales_up"]])
print("\n[6] 숫자 × 시장 반응(발표 반응 = 접수 전날 → 다음 날, 코스피 대비)", flush=True)
hi_s = qs[3]
lo_s = qs[0]
show("놀람 위 20% · 반응 +", [e for e in s if e["sue"] >= hi_s and e["ear"] > 0])
show("놀람 위 20% · 반응 −", [e for e in s if e["sue"] >= hi_s and e["ear"] <= 0])
show("놀람 아래 20% · 반응 +", [e for e in s if e["sue"] < lo_s and e["ear"] > 0])
show("놀람 아래 20% · 반응 −", [e for e in s if e["sue"] < lo_s and e["ear"] <= 0])
show("늘음 · 반응 +3%↑", [e for e in events if e["turn"] in ("늘음", "흑전") and e["ear"] >= 0.03])
show("줄음 · 반응 −3%↓", [e for e in events if e["turn"] in ("줄음", "적전", "적지") and e["ear"] <= -0.03])
print("끝", flush=True)
