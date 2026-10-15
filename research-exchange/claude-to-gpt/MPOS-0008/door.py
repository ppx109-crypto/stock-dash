"""MPOS-0008 장부 만들기 — 1일봉 장부(z055_d1_raw · 495건)에 새 문을 더하거나(G2) 칸을 2배로 나눔(G1).
G2 'RV'(시장 대비 과매도 → RNA 회복 확인 · GPT #420 G2 + 사용자 H3):
  t 종가까지 자료만: 그날 시총 200위 안(z001.universe · 옛 시총 = 바구니와 같음) · 60일선 기울기 +(MA60(t) > MA60(t−5)) ·
  z(t−1) ≤ −K · z(t) > z(t−1) · z(t) < 0 · 종가(t) > 종가(t−1)  →  t 다음 거래일(b) 종가에 1칸 삼(빈 칸만 · 기존 문 먼저).
  z = 5일 '시장 대비' 로그 수익 합 ÷ (60일 시장 대비 하루 수익 σ × √5) · 시장 = 그날 200위 안 종목 하루 로그 수익 가운데값.
  나감(하나): u ≥ b 종가에 z(u) ≥ 0 이면 u 다음 거래일 종가에 팖 · 최대 보유(하나): b에서 H 거래일째 종가.
  손익 = 판 값 ÷ 산 값 − 1 − 0.25%(기존 장부와 같은 왕복 뺌) − 비용 더함(스트레스).
  빼기(ablation): raw = 시장 빼지 않음(z를 원수익으로) · noconf = 회복 확인 없이 z(t) ≤ −K 날 바로.
G1 '2N': 같은 1일봉 엔진(ntools.once · 씨앗 · 순서 · 나감 그대로)을 slots=20으로 돌리고 칸 ÷ 2(돈 = 계좌 × 몫 × 칸 ÷ 20).
python3 door.py g2 K H [raw|noconf|rv] [extra_cost] [cut] → 장부 json 경로 · python3 door.py g1 → 장부 json 경로"""
import json
import math
import os
import sys
from pathlib import Path

TREE = Path("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/m54tree")   # MIX-0054 결과 커밋 9743cb802 그대로
SP = Path("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad")
OUT = SP / "mpos8" / "ledgers"
OLD = SP / "z055_d1_raw.json"
FROM, TO, SLOTS, TOP = "20170201", "20260930", 10, 200
os.chdir(TREE)
sys.path[:0] = [str(TREE), str(TREE / "research"), str(TREE / "research" / "mix0053")]


def frames(cut=None):
    import numpy as np
    import pandas as pd
    import nrl
    import z001 as Z
    import caps
    caps.ADJ = False
    P = pd.DataFrame({c: dict(v["rows"]) for c, v in nrl.prices.items()}).sort_index()
    P = P[P.index >= "20160101"]
    if cut:
        P = P[P.index <= cut]
    C, *_ = Z.load()
    if cut:
        C = C[C.index <= cut]
    inside, _ = Z.universe(C)
    ins = inside.reindex(index=P.index, columns=P.columns).fillna(False).astype(bool)
    r = P / P.shift(1) - 1
    bad = (r.abs() > 0.35)                                        # 하루 ±35% 넘는 값(가격 제한 30% 밖) = 자료 의심 → 60일 창에서 신호 막음
    lr = np.log(P / P.shift(1)).where(~bad)
    mkt = lr.where(ins).median(axis=1)
    badwin = bad.astype(float).rolling(60, min_periods=1).max() > 0
    return P, ins, lr, mkt, badwin


def zscore(lr, mkt, raw):
    rel = lr if raw else lr.sub(mkt, axis=0)
    return rel.rolling(5, min_periods=5).sum() / (rel.rolling(60, min_periods=60).std() * math.sqrt(5))


def g2(K, H, mode="rv", extra=0.0, cut=None):
    P, ins, lr, mkt, badwin = frames(cut)
    import nrl
    z = zscore(lr, mkt, mode == "raw")
    ma = P.rolling(60, min_periods=60).mean()
    trend = ma > ma.shift(5)
    if mode == "noconf":
        sig = ins & trend & (z <= -K) & ~badwin
        key = z
    else:
        sig = ins & trend & (z.shift(1) <= -K) & (z > z.shift(1)) & (z < 0) & (P > P.shift(1)) & ~badwin
        key = z.shift(1)
    cal = list(P.index)
    tradeday = set(d for d in nrl.BR if FROM <= d <= TO)
    old = json.load(open(OLD))
    occ, held_old = {}, {}
    for c, b, e, p, s in old:
        for d in cal:
            if b <= d < e:
                occ[d] = occ.get(d, 0) + s
            if b <= d <= e:
                held_old.setdefault(d, set()).add(c)
    zv, Pv = z.to_dict("index"), None
    new, opened = [], []                                          # opened: [code, b_idx, sell_idx or None, 팔기 정함]
    stat = {"신호": 0, "빈 칸 없음": 0, "겹침": 0, "값 없음": 0}
    for i in range(1, len(cal)):
        t, b = cal[i - 1], cal[i]
        # 1) 나감: 어제(t) 종가에 z ≥ 0 이거나 오늘이 b+H째 → 오늘 b 종가에 팖(값 없으면 다음 값 있는 날)
        for pos in opened:
            c, ib = pos[0], pos[1]
            zt = zv[t].get(c)
            if (i - 1 >= ib and zt is not None and not math.isnan(zt) and zt >= 0) or i - ib >= H:
                pos[3] = True                                     # 한 번 팔기로 정하면 값 있는 날까지 이어 감
            if pos[3] and not math.isnan(P.iat[i, P.columns.get_loc(c)]):
                pos[2] = i
        for pos in [x for x in opened if x[2] == i]:
            c, ib = pos[0], pos[1]
            pb, ps = P.iat[ib, P.columns.get_loc(c)], P.iat[i, P.columns.get_loc(c)]
            new.append([c, cal[ib], b, round((ps / pb - 1) * 100 - 0.25 - extra * 100, 4), 1])
            opened.remove(pos)
        if b not in tradeday:
            continue
        # 2) 사기: t 신호 → b 종가 · 빈 칸만
        row = sig.loc[t]
        cands = sorted((key.at[t, c], c) for c in row.index[row.values])
        stat["신호"] += len(cands)
        free = SLOTS - occ.get(b, 0) - len(opened)
        mine = {x[0] for x in opened}
        for _, c in cands:
            if c in mine or c in held_old.get(b, ()):
                stat["겹침"] += 1
                continue
            if free <= 0:
                stat["빈 칸 없음"] += 1
                continue
            if math.isnan(P.at[b, c]):
                stat["값 없음"] += 1
                continue
            opened.append([c, i, None, False])
            mine.add(c)
            free -= 1
    for c, ib, *_ in opened:                                       # 끝까지 안 판 것: 판 날 없음(z100이 끝날까지 값으로 평가)
        new.append([c, cal[ib], "99999999", 0.0, 1])
    stat["새 매매"] = len(new)
    return old + new, stat


def g1():
    import ntools as T
    got = T.once("MPOS-0008 G1 2N", slots=2 * SLOTS)
    rows = [(t["code"], t["산 날"], t["판 날"], t["손익"], (t.get("자리") or 1) / 2) for s in ("앞", "뒤") if got.get(s) for t in got[s]["매매목록"]]
    return rows, {s: {k: v for k, v in (got.get(s) or {}).items() if k != "매매목록" and not isinstance(v, (list, dict))} for s in ("앞", "뒤")}


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    if sys.argv[1] == "g1":
        led, stat = g1()
        name = "g1_2n"
    else:
        K, H = float(sys.argv[2]), int(sys.argv[3])
        mode = sys.argv[4] if len(sys.argv) > 4 else "rv"
        extra = float(sys.argv[5]) if len(sys.argv) > 5 else 0.0
        cut = sys.argv[6] if len(sys.argv) > 6 else None
        led, stat = g2(K, H, mode, extra, cut)
        name = f"g2_{mode}_K{K}_H{H}" + (f"_x{extra}" if extra else "") + (f"_cut{cut}" if cut else "")
    path = OUT / f"{name}.json"
    json.dump(led, open(path, "w"))
    print(json.dumps({"장부": str(path), "줄": len(led), **{k: v for k, v in stat.items()}}, ensure_ascii=False))
