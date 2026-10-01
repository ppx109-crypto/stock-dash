"""15분봉 0회차 규칙 · 공통 재료 — 1시간봉 최고 규칙(90 · 94회차)을 15분봉으로 옮김. 회차 스크립트와 m15guard_world가 exec로 씀.

옮기는 법(사용자 계획 docs/RL-15M-PLAN.md):
- 무엇을: 그대로(전 거래일 일봉 추세 문 또는 정배열 문 + 가르침 수급 · 전 거래일 시총 100위 안).
- 언제: 그날 15분봉 EMA 5 · 20 · 60 · 120 · 180이 정배열이 된 봉 다음 시가 · 그날 처음 한 번 · 없으면 11:45 봉(11:45 ~ 12:00)이
  닫힌 뒤 12:00 시가(1시간봉의 '11시 봉 → 12시 시가'와 같은 때).
- 크기 · 순서: 그대로(추세 문 · 3일 연속 4칸 · 그 밖 2칸 · 같은 봉 후보 순서 = 추세 → 3일 연속 → 같은 시각 후보끼리 '수급 약 + 20일 수익 큼' 3무리).
- 팔 때: 그대로이되 봉 수 × 4(추세 문 60봉 → 240봉 = 10거래일 · 자리 바꾸기 7봉 → 28봉).
환경: Q_SPAN(EMA 묶음 'A' 또는 'A4' — A4는 20 · 80 · 240 · 480 · 720 = 1시간봉 A와 같은 시간 길이) · Q_SCALE(봉 수 배수, 기본 4).
"""
import bisect
import json
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
import m15lab as M
import rna
import final_group as FG

HOURLY = os.environ.get("Q_BARS", "15m") == "1h"      # 같은 15분봉 자료를 1시간으로 묶어 1시간봉 규칙과 견줄 때
SCALE = int(os.environ.get("Q_SCALE", "1" if HOURLY else str(M.SCALE)))
SPAN = os.environ.get("Q_SPAN", "A")
NOON = "1100" if HOURLY else "1145"                     # 이 봉이 닫히면 12:00 시가
if "A4" not in rna.SETS:
    rna.SETS["A4"] = tuple(4 * n for n in rna.SETS["A"])
if HOURLY:
    _load = M.load
    M.load = lambda codes=None, home=None: M.to_hours(_load(codes, home))
W = M.setup()
data, ATT, IN = W["data"], W["ATT"], W["IN"]


def door(x):
    if not x:
        return None
    if x["추세문"]:
        return "추세"
    if x["정배열"] and 19 <= x["간격"] < 53 and (x["시장폭"] or 0) >= 50:
        return "정배열"
    return None


def ok(x):
    return door(x) is not None and x["가르침"]


def ctx_now(c, b):
    return np.array([ok(x) for x in ATT[c]]) & IN[c]


def e_align(c, b):
    s = H.states(c, b, SPAN)["정배열"] == 1
    return ctx_now(c, b) & s & ~np.r_[False, s[:-1]]


def e_align_or_noon(c, b):
    al, nn = e_align(c, b), ctx_now(c, b) & M.at(b, NOON)
    days = [t[:8] for t in b["t"]]
    seen, m = set(), np.zeros(len(b["t"]), bool)
    for k in range(len(m)):
        if (al[k] or nn[k]) and days[k] not in seen:
            m[k] = True
            seen.add(days[k])
    return m


def size(c, b, k):
    x = ATT[c][k + 1] if k + 1 < len(b["t"]) else ATT[c][k]
    return 4 if x and (x["추세문"] or x["3일연속"]) else 2


def exit_rule(c, b, p, k):
    now = (b["c"][k] / p["price"] - 1) * 100
    kind = door(ATT[c][p["i"]]) or "정배열"
    held = k - p["i"]
    if kind == "추세":
        if now >= 13 or now <= -5 or held >= 60 * SCALE:
            return "all"
        before = b["c"][p["i"]:k].max() if k > p["i"] else -1
        if now >= 5 and (before / p["price"] - 1) * 100 < 5 and p["칸"] == p["처음칸"]:
            return max(1, p["처음칸"] // 2)
        return 0
    if now <= -10:
        return "all"
    if (p["peak"] / p["price"] - 1) * 100 >= 8 and now <= 1:
        return "all"
    if k + 1 < len(b["t"]):
        nx = ATT[c][k + 1]
        if nx is not None and not nx["정배열"]:
            return "all"
    return 0


def stale90(p):
    if not ((p["now"] - p["i"] >= 7 * SCALE) and (data[p["code"]]["c"][p["now"]] / p["price"] - 1) * 100 < 4):
        return False
    x = ATT[p["code"]][p["now"]]
    return (x["시장폭"] if x and x["시장폭"] is not None else 100) < 90


# 같은 시각 후보 순서(1시간봉 90회차): 사는 날 앞까지의 일봉 가격 · 거래량 · 수급으로만
ROWS = {}
for _c in data:
    px = json.load(open(f"price-data/{_c}.json", encoding="utf-8"))["closes"]
    vv = json.load(open(f"volume-data/{_c}.json", encoding="utf-8"))["날"]
    fl = sorted(FG.flow_rows(_c), key=lambda x: x["date"])
    lim = H.day_limit()
    if lim:
        px = [x for x in px if x[0] < lim]
        vv = [x for x in vv if str(x[0]) < lim]
        fl = [x for x in fl if x["date"] < lim]
    ROWS[_c] = ([x[0] for x in px], [float(x[1]) for x in px], [str(x[0]) for x in vv], [float(x[1]) for x in vv],
                [x["date"] for x in fl], fl)


def raw(c, k, rn=20, fn=5):
    b = data[c]
    day = b["t"][k + 1][:8] if k + 1 < len(b["t"]) else b["t"][k][:8]
    pd_, pc, vd, vol, fd, fl = ROWS[c]
    i = bisect.bisect_left(pd_, day) - 1
    j = bisect.bisect_left(vd, day) - 1
    f = bisect.bisect_left(fd, day) - 1
    r = pc[i] / pc[i - rn] - 1 if i >= rn and pc[i - rn] > 0 else np.nan
    av = np.mean(vol[j - 19:j + 1]) if j >= 20 else np.nan
    s = sum((x.get("외국인") or 0) + (x.get("투신") or 0) for x in fl[max(0, f - fn + 1):f + 1]) if f >= fn - 1 else np.nan
    return (s / av if av == av and av > 0 else np.nan, r)


def tiers(sig, rn=20, fn=5, n=3):
    keys = [(c, k) for c, m in sig.items() for k in np.flatnonzero(m)]
    sc = {z: raw(*z, rn, fn) for z in keys}
    bybar, T = {}, {}
    for (c, k) in sc:
        bybar.setdefault(data[c]["t"][k], []).append((c, k))
    for t, L in bybar.items():
        if len(L) == 1:
            T[L[0]] = n - 1
            continue
        tot = np.zeros(len(L))
        for col, good_high in ((0, False), (1, True)):
            v = np.array([sc[z][col] for z in L], float)
            v = np.where(np.isnan(v), np.nanmedian(v) if np.any(~np.isnan(v)) else 0, v)
            q = np.argsort(np.argsort(v)) / (len(v) - 1)
            if not good_high:
                q = 1 - q
            tot += np.minimum((q * n).astype(int), n - 1)
        for z, x in zip(L, tot):
            T[z] = int(x)
    return T


def rank_of(T):
    def r(c, b, k):
        x = ATT[c][k + 1] if k + 1 < len(b["t"]) else ATT[c][k]
        return (0 if x and x["추세문"] else 1, 0 if x and x["3일연속"] else 1, -T.get((c, k), 0))
    return r


SIGS = {c: np.asarray(e_align_or_noon(c, b), bool) for c, b in data.items()}
RANK = rank_of(tiers(SIGS))
