"""MPOS-0011 — 달마다 계좌 위험 크기를 고르는 온라인 학습(RL · 사용자 2026-10-16 "조치하고 RL로 계속 진행해줘").
행동(4): P0(지금 판 그대로) · BASE(덧붙임 끔 = 바탕 d0.5_b0.3) · HALF(P0 절반 + 현금 절반) · CASH(전부 현금 · 수익 0).
문맥(4): 결정 전날까지의 KODEX 200(069500) — 60거래일 수익 부호(오름/내림) × 20거래일 흔들림이 지난 252거래일 흔들림 가운데값보다 큼/작음.
학습(완전 정보 · 지난 달만): 끝난 달 m'마다 네 행동의 달 수익 R_a(m')가 모두 보임 → 같은 문맥의 효용 평균 u = R − λ × max(0, −R) 이 가장 큰 행동.
  창 W(전부 / 같은 문맥의 최근 36개 표본 달) · 같은 문맥 표본 < 6이면 P0 · 동률은 P0 > BASE > HALF > CASH. 결정은 그달 첫 거래일 전에 정해져 그달 내내 유지.
계좌: 날마다 고른 행동의 하루 수익(P0 · BASE = 각 계좌 경로 · HALF = 0.5 × P0 · CASH = 0) · 행동이 바뀌는 달 첫날 전환 비용 근사
  = 0.004 × |주식 노출 차| + 0.0013 × 0.4 × |덧붙임 차|(노출: P0 1 · BASE 1 · HALF 0.5 · CASH 0 / 덧붙임: P0 1 · BASE 0 · HALF 0.5 · CASH 0) · 스트레스 = 2배.
python3 rl11.py run | cut"""
import csv
import json
import math
import os
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, "/home/user/stock-dash/research")
os.environ.setdefault("REG_BOX", "MPOS-0011")
import mix54_run as M  # noqa: E402
import regime_dev as Dv  # noqa: E402

P0_CSV = "/tmp/mix0054-bases/d0.5_b0.3_no15m.csv"
CFG = dict(Dv.R0, **M.OVERLAYS["L0.4_S0.4"])
SNAPDIR = HERE / "inputs"
ARMS = ("P0", "BASE", "HALF", "CASH")
EXPO = {"P0": 1.0, "BASE": 1.0, "HALF": 0.5, "CASH": 0.0}
OVER = {"P0": 1.0, "BASE": 0.0, "HALF": 0.5, "CASH": 0.0}
LAMS, WINS, NMIN = (1.0, 3.0), (None, 36), 6
CELLS = [f"RL_L{int(l)}_W{w or 'ALL'}" for l in LAMS for w in WINS]          # 후보 4
CENTER = "RL_L3_WALL"
ABL = "AB_NOCTX"                                                             # 빼기: 문맥 없음(한 상태) · λ3 · 전부
H1_END, H2_BEG = "202112", "202201"

_load0 = Dv.load


def load_snap():
    root0 = Dv.ROOT
    Dv.ROOT = SNAPDIR
    try:
        return _load0()
    finally:
        Dv.ROOT = root0


Dv.load = load_snap


def paths():
    """P0(덧붙임 계좌) · BASE(바탕) 날마다 NAV — 둘 다 같은 날 목록."""
    Dv.BASE_CSV, Dv.DATA, Dv.FEAT = Path(P0_CSV), None, None
    p0, _ = Dv.account(CFG)
    base = {r["날"]: float(r["NAV"]) for r in csv.DictReader(open(P0_CSV, encoding="utf-8"))}
    ds = [d for d in sorted(p0) if d in base]
    return ds, {d: p0[d] for d in ds}, {d: base[d] for d in ds}


def k200():
    b = json.load(open(SNAPDIR / "etf-data" / "069500.json"))
    return {str(d): float(c) for d, c in b["closes"] if c}


def context_fn(k, cut=None):
    """결정 날 d(그달 첫 거래일)의 문맥 = d 전 거래일까지 KODEX 200만."""
    days = sorted(x for x in k if not cut or x <= cut)
    idx = {d: i for i, d in enumerate(days)}
    lr = [None] + [math.log(k[days[i]] / k[days[i - 1]]) for i in range(1, len(days))]

    def sd(xs):
        m = sum(xs) / len(xs)
        return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))

    def ctx(d):
        prev = [x for x in days if x < d]
        if not prev:
            return None
        i = idx[prev[-1]]
        if i < 272:
            return None
        trend = k[days[i]] > k[days[i - 60]]
        v20 = sd(lr[i - 19:i + 1])
        hist = sorted(sd(lr[j - 19:j + 1]) for j in range(i - 251, i + 1))
        return (trend, v20 > hist[len(hist) // 2])
    return ctx


def decide(month, past, lam, win, ctx_of, use_ctx=True):
    """past: [(달, 문맥, {행동: 달 수익})] — 결정 달보다 앞선 끝난 달만. 돌려줌 (행동, 까닭)."""
    c = ctx_of(month)
    if c is None:
        return "P0", "문맥 없음"
    pool = [p for p in past if p[0] < month and (not use_ctx or p[1] == c)]
    if win:
        pool = pool[-win:]
    if len(pool) < NMIN:
        return "P0", "표본 모자람"
    best, bu = None, None
    for a in ARMS:
        u = sum(r[a] - lam * max(0.0, -r[a]) for _, _, r in pool) / len(pool)
        if bu is None or u > bu + 1e-15:
            best, bu = a, u
    return best, "학습"


def simulate(cell, ds, p0, base, k, cost_k=1.0, cut=None):
    lam = 3.0 if cell == ABL else float(cell.split("_")[1][1:])
    w = cell.split("_")[2][1:] if cell != ABL else "ALL"
    win = None if w == "ALL" else int(w)
    use_ctx = cell != ABL
    if cut:
        ds = [d for d in ds if d <= cut]
    ctx = context_fn(k, cut)
    first = {}
    for d in ds:
        first.setdefault(d[:6], d)
    r0 = {ds[j]: p0[ds[j]] / p0[ds[j - 1]] - 1 for j in range(1, len(ds))}
    rb = {ds[j]: base[ds[j]] / base[ds[j - 1]] - 1 for j in range(1, len(ds))}
    mon_days = {}
    for d in ds[1:]:
        mon_days.setdefault(d[:6], []).append(d)
    past, nav, cur, log, choice = [], {ds[0]: 1.0}, "P0", {}, {}
    v = 1.0
    for m in sorted(mon_days):
        if use_ctx:
            a, why = decide(m, past, lam, win, lambda mm: ctx(first[mm]))
        else:
            a, why = decide_noctx(m, past, lam, win, ctx(first[m]))
        cost = cost_k * (0.004 * abs(EXPO[a] - EXPO[cur]) + 0.0013 * 0.4 * abs(OVER[a] - OVER[cur]))
        rs = {x: 1.0 for x in ARMS}
        for i, d in enumerate(mon_days[m]):
            day = {"P0": r0[d], "BASE": rb[d], "HALF": 0.5 * r0[d], "CASH": 0.0}
            if i == 0:                                              # 판단(전달 끝 종가) 다음 날: 첫날은 전달 행동 그대로 · 첫날 종가에 바꿈(대리 검토 결함 1)
                v *= (1 + day[cur]) * (1 - cost)
            else:
                v *= 1 + day[a]
            nav[d] = v
            for x in ARMS:
                rs[x] *= 1 + day[x]
        choice[m] = (a, why)
        past.append((m, ctx(first[m]), {x: rs[x] - 1 for x in ARMS}))   # 그달이 끝난 뒤에만 학습에 들어감
        cur = a
    return nav, choice


def decide_noctx(m, past, lam, win, c_now):
    if c_now is None:
        return "P0", "문맥 없음"
    pool = [p for p in past if p[0] < m]
    if win:
        pool = pool[-win:]
    if len(pool) < NMIN:
        return "P0", "표본 모자람"
    best, bu = None, None
    for a in ARMS:
        u = sum(r[a] - lam * max(0.0, -r[a]) for _, _, r in pool) / len(pool)
        if bu is None or u > bu + 1e-15:
            best, bu = a, u
    return best, "학습"


def mstats(navs):
    ds = sorted(navs)
    r = {ds[j]: navs[ds[j]] / navs[ds[j - 1]] - 1 for j in range(1, len(ds))}
    mo = {}
    for d, x in r.items():
        mo[d[:6]] = mo.get(d[:6], 1) * (1 + x)
    full = {m: v - 1 for m, v in mo.items() if "201703" <= m <= "202608"}
    assert len(full) == 114, len(full)
    pk = mdd = 0
    for d in ds:
        pk = max(pk, navs[d])
        mdd = min(mdd, navs[d] / pk - 1)
    return dict(달수=len(full), 손실=sum(v < 0 for v in full.values()), 영=sum(v == 0 for v in full.values()), 이익=sum(v > 0 for v in full.values()),
                앞손실=sum(full[m] < 0 for m in full if m <= H1_END), 뒤손실=sum(full[m] < 0 for m in full if m >= H2_BEG),
                최악달=min(full.values()) * 100, 최악날=min(r.values()) * 100, 연_거래일=((navs[ds[-1]] / navs[ds[0]]) ** (250 / len(ds)) - 1) * 100,
                MDD=mdd * 100, 달=dict(sorted(full.items())))


def gt(a, b):
    return a is not None and b is not None and not (isinstance(a, float) and math.isnan(a)) and not (isinstance(b, float) and math.isnan(b)) and a > b


def nei(c):
    if c == ABL:
        return []
    l, w = c.split("_")[1], c.split("_")[2]
    return [f"RL_{x}_{w}" for x in ("L1", "L3") if x != l] + [f"RL_{l}_{x}" for x in ("WALL", "W36") if x != w]


def judge(R, mech):
    b = R["P0"]

    def acct(c):
        x = R[c]
        return (x["최악날"] >= -15 and x["최악달"] >= -15 and x["앞손실"] <= b["앞손실"] and x["뒤손실"] <= b["뒤손실"] and x["손실"] < b["손실"]
                and x["연_거래일"] >= 30.702 and x["최악달"] >= b["최악달"])

    def gate(c):
        x = R[c + "_X"]
        return x["최악날"] >= -15 and x["최악달"] >= -15 and x["손실"] < b["손실"] and x["연_거래일"] >= 30.702 and mech["지지"]
    why = {c: {"①": R[c]["최악날"] >= -15 and R[c]["최악달"] >= -15, "②": R[c]["앞손실"] <= b["앞손실"] and R[c]["뒤손실"] <= b["뒤손실"],
               "③": R[c]["손실"] < b["손실"], "④": R[c]["연_거래일"] >= 30.702, "⑥깊이": R[c]["최악달"] >= b["최악달"],
               "⑤": all(acct(n) for n in nei(c)), "관문": gate(c)} for c in CELLS}
    ok = [c for c in CELLS if all(why[c].values())]
    rank = sorted(ok, key=lambda c: (-math.floor(R[c]["최악달"] / 5), R[c]["손실"], -math.floor(R[c]["MDD"] / 2), -R[c]["연_거래일"], c))
    return ok, rank, why


def mechanism(R):
    """기전(결과 전 고정): 가운데(λ3 · 전부)가 문맥 없음보다 손실 달 ≤ 이고 연 > 이면 '문맥 지지'."""
    c, a = R[CENTER], R[ABL]
    return {"손실달_이하": c["손실"] <= a["손실"], "연_큼": gt(c["연_거래일"], a["연_거래일"]), "지지": c["손실"] <= a["손실"] and gt(c["연_거래일"], a["연_거래일"])}


def boot(R, c, reps=2000, blk=6, seed=20261016):
    MON = sorted(R["P0"]["달"])
    a, p = [R[c]["달"][m] for m in MON], [R["P0"]["달"][m] for m in MON]
    rnd, n, dl = random.Random(seed), len(MON), []
    for _ in range(reps):
        idx = []
        while len(idx) < n:
            s = rnd.randrange(n - blk + 1)
            idx += range(s, s + blk)
        idx = idx[:n]
        dl.append(sum(a[i] < 0 for i in idx) - sum(p[i] < 0 for i in idx))
    dl.sort()
    return {"손실달차_90": [dl[int(.05 * (reps - 1))], dl[int(.95 * (reps - 1))]], "묶음": blk, "횟수": reps, "씨앗": seed}


LOCK = {P0_CSV: "6bacf87ea66e8cde576e7d8b3cd533e2b18ccd78ed8afdb7e79d5ebb72824531",
        "/home/user/stock-dash/research/regime_dev.py": "9b8c18720c489707ca6fc0ab71e888cc6a5dab5e54bcd4d6eb20265cd58fe0bc",
        "/home/user/stock-dash/research/mix54_run.py": "b77ba1c1a68d7d6e242f30f4a3ed3c6fc654dd57e3a6dc44ab96852faf7bbd6e",
        "/tmp/rev-full.pkl": "540114ff96929ceb3e9d6420887e5f5457df4ab65c4457377b9bec13a1fa06a6"}


def verify():
    import hashlib
    h = lambda f: hashlib.sha256(open(f, "rb").read()).hexdigest()
    got = {f: h(f) for f in LOCK}
    for f in ("rl11.py", "test_rl11.py"):
        got[f] = h(HERE / f)
    lk = json.load(open(HERE / "inputs_lock.json"))
    for f in lk:
        got["inputs/" + f] = h(SNAPDIR / f)
    bad = [f for f, v in LOCK.items() if got[f] != v] + [f for f, v in lk.items() if got["inputs/" + f] != v]
    if (HERE / "lock.json").exists():
        bad += [f for f, v in json.load(open(HERE / "lock.json")).items() if got.get(f) != v]
    if bad:
        sys.exit(f"잠금 불일치 → 중단: {bad}")
    return got


def run():
    lock = verify()
    ds, p0, base = paths()
    k = k200()
    R = {"P0": mstats(p0)}
    b = R["P0"]                                                     # 기준 상수와 같은지(대리 검토 결함 5)
    assert b["손실"] == 40 and abs(b["최악달"] + 14.0434) < 1e-3 and abs(b["연_거래일"] - 34.1129) < 1e-3, (b["손실"], b["최악달"], b["연_거래일"])
    C = {}
    for c in CELLS + [ABL]:
        nav, ch = simulate(c, ds, p0, base, k)
        R[c] = mstats(nav)
        C[c] = {m: list(v) for m, v in ch.items()}
        R[c + "_X"] = mstats(simulate(c, ds, p0, base, k, cost_k=2.0)[0])
        R[c + "_H"] = mstats(simulate(c, ds, p0, base, k, cost_k=0.5)[0])    # 보고만(비용 반)
    mech = mechanism(R)
    ok, rank, why = judge(R, mech)
    count = {c: {a: sum(1 for v in C[c].values() if v[0] == a) for a in ARMS} for c in C}
    out = {"P0": R["P0"], "cells": R, "고른 행동 수(달)": count, "고른 행동(달마다)": C, "기전": mech, "잣대": why, "자격": ok, "순위": rank,
           "고른 것": rank[0] if rank else None, "판정": "SELECTED" if rank else "NO_IMPROVEMENT", "묶음 이어뽑기(보고만)": {c: boot(R, c) for c in CELLS},
           "0인 달(보고 · '모든 달 양수'와 다름)": {c: R[c]["영"] for c in CELLS + [ABL]}, "잠금": lock}
    json.dump(out, open(HERE / "result.json", "w"), ensure_ascii=False, indent=1)
    for c in ["P0"] + CELLS + [ABL]:
        print(c, json.dumps({kk: (round(v, 3) if isinstance(v, float) else v) for kk, v in R[c].items() if kk != "달"}, ensure_ascii=False), count.get(c, ""))
    print("기전", mech, "자격", ok, "순위", rank)


def cut():
    """자르기(대리 검토 결함 2 · 3): 달 끝 2개 + 달 중간 3개 날까지 자료만으로 — KODEX 200 자름 + **P0 · BASE 경로도 regime_dev 자르기(Dv.CUT)로 다시 셈**
    (z100 바탕 csv는 MIX-0054 결과 그대로 · 그 미래 참조 검사는 MIX-0054 · MPOS-0002 ~ 0006) → 그날까지 고른 행동 · 날마다 NAV 차이 0."""
    lock = verify()
    ds, p0, base = paths()
    k = k200()
    recs, bad = [], 0
    for ct in ("20211231", "20240628", "20211215", "20240614", "20200303"):
        Dv.CUT, Dv.DATA, Dv.FEAT = ct, None, None
        cds, cp0, cbase = paths()
        Dv.CUT, Dv.DATA, Dv.FEAT = "", None, None
        for c in CELLS + [ABL]:
            full_nav, full_ch = simulate(c, ds, p0, base, k)
            nav, ch = simulate(c, cds, cp0, cbase, k, cut=ct)
            same_ch = all(ch[m] == full_ch[m] for m in ch if m <= ct[:6])
            dd = [d for d in nav if d <= ct]
            same_nav = all(nav[d] == full_nav[d] for d in dd)
            ok = same_ch and same_nav and bool(dd)
            bad += not ok
            recs.append({"칸": c, "자른 날": ct, "달": len([m for m in ch if m <= ct[:6]]), "날": len(dd), "판정": "PASS" if ok else "FAIL"})
            print(json.dumps(recs[-1], ensure_ascii=False))
    json.dump({"잠금": lock, "줄": recs}, open(HERE / "receipt_cut.json", "w"), ensure_ascii=False, indent=1)
    if bad:
        sys.exit(3)


if __name__ == "__main__":
    {"run": run, "cut": cut}[sys.argv[1]]()
