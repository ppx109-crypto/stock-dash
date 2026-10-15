"""MPOS-0008 장부 만들기 — 1일봉 장부(z055_d1_raw · 495건)에 새 문을 더하거나(G2) 칸을 2배로 나눔(G1).
G2 'RV'(시장 대비 과매도 → RNA 회복 확인 · GPT #420 G2 + 사용자 H3):
  t 종가까지 자료만: 그날 시총 200위 안(z001.universe · 옛 시총 = 바구니와 같음) · 60일선 기울기 +(MA60(t) > MA60(t−5)) ·
  z(t−1) ≤ −K · z(t) > z(t−1) · z(t) < 0 · 종가(t) > 종가(t−1)  →  t 다음 거래일(b) 종가에 1칸 삼(빈 칸만 · 기존 문 먼저).
  z = 5일 '시장 대비' 로그 수익 합 ÷ (60일 시장 대비 하루 수익 σ × √5) · 시장 = 그날 200위 안 종목 하루 로그 수익 가운데값.
  나감(하나): u ≥ b 종가에 z(u) ≥ 0 이면 u 다음 거래일 종가에 팖 · 최대 보유(하나): b에서 H 거래일째 종가.
  기존 문 우선(GPT #421 지적 2): 그날 기존 칸 + 새 보유 > 10 이면 가장 늦게 든 새 보유부터 그날 종가에 팖(그날 기존 장부 상태만 봄) → 날마다 칸 ≤ 10.
  장부 순서(GPT #421 지적 1): 새 문 줄은 **들어간 순서**(산 날 · 그날 z 순위 · 같으면 종목 번호) · 기존 495줄 뒤에 붙음 → z100 같은 날 사기 순서 = 기존 문 → 새 문 순위.
  손익 = 판 값 ÷ 산 값 − 1 − 0.25%(기존 장부와 같은 왕복 뺌) − 스트레스(판 손익 깎기 · z100에선 계획 청산 때 남은 몫에만 걸림 = 계좌 상한으로 먼저 덜어낸 몫엔 안 걸림).
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
    cands = {}
    for t in cal:
        row = sig.loc[t]
        cs = row.index[row.values]
        if len(cs):
            cands[t] = sorted((float(key.at[t, c]), c) for c in cs)            # 우선순위: z 낮은 순 · 같으면 종목 번호
    zv = z.to_dict("index")
    Pv = P.to_dict("index")
    return walk(cal, tradeday, cands, zv, Pv, old, H, extra)


def walk(cal, tradeday, cands, zv, Pv, old, H, extra=0.0):
    """순수 셈(합성 시험용). 새 문 매매를 **들어간 순서**(산 날 · 그날 우선순위)로 장부에 둠 — 판 날 · 손익은 나중에 채우나 순서는 바꾸지 않음.
    하루 순서(z100 15:20과 같음): ① 새 문 계획 나감(어제 종가 z ≥ 0 · H째) ② 기존 문 우선 정리: 그날 기존 칸 + 새 보유 > 10 이면
    가장 늦게 들어간 새 보유부터 그날 종가에 팖(그날 기존 장부 상태만 봄 · 앞날 기존 진입은 안 봄) ③ 빈 칸에 새로 삼(어제 신호)."""
    nan = lambda x: x is None or (isinstance(x, float) and math.isnan(x))
    occ, held_old = {}, {}
    for c, b, e, p, s in old:
        for d in cal:
            if b <= d < e:
                occ[d] = occ.get(d, 0) + s
            if b <= d <= e:
                held_old.setdefault(d, set()).add(c)
    new, opened = [], []                                          # opened: 장부 줄 번호(들어간 순서)
    st = {"신호": 0, "빈 칸 없음": 0, "겹침": 0, "값 없음": 0, "기존 문 우선 정리": 0, "칸 넘은 날": 0, "넘은 날 예": []}
    want = {}

    def close(j, d, why):
        r = new[j]
        pb, ps = Pv[r[1]][r[0]], Pv[d][r[0]]
        r[2], r[3] = d, (ps / pb - 1) * 100 - 0.25 - extra * 100
        r.append(why)
        opened.remove(j)

    for i in range(1, len(cal)):
        t, b = cal[i - 1], cal[i]
        for j in list(opened):                                    # ① 계획 나감
            c, ib = new[j][0], new[j][5]
            zt = zv[t].get(c)
            if (i - 1 >= ib and not nan(zt) and zt >= 0) or i - ib >= H:
                want[j] = True
            if want.get(j) and not nan(Pv[b].get(c)):
                close(j, b, "계획")
        over = occ.get(b, 0) + len(opened) - SLOTS               # ② 기존 문 우선
        for j in sorted(opened, reverse=True):
            if over <= 0:
                break
            if not nan(Pv[b].get(new[j][0])):
                close(j, b, "기존 문 우선")
                st["기존 문 우선 정리"] += 1
                over -= 1
        if occ.get(b, 0) + len(opened) > SLOTS:
            st["칸 넘은 날"] += 1
            st["넘은 날 예"] = (st["넘은 날 예"] + [b])[:5]
        if b not in tradeday:
            continue
        cs = cands.get(t, [])                                     # ③ 사기
        st["신호"] += len(cs)
        free = SLOTS - occ.get(b, 0) - len(opened)
        mine = {new[j][0] for j in opened}
        for rank, (_, c) in enumerate(cs):
            if c in mine or c in held_old.get(b, ()):
                st["겹침"] += 1
                continue
            if free <= 0:
                st["빈 칸 없음"] += 1
                continue
            if nan(Pv[b].get(c)):
                st["값 없음"] += 1
                continue
            new.append([c, b, "99999999", 0.0, 1, i, t, rank])     # 종목 · 산 날 · 판 날 · 손익 · 칸 · (보조: 산 날 번호 · 신호 날 · 그날 순위)
            opened.append(len(new) - 1)
            mine.add(c)
            free -= 1
    st["새 매매"] = len(new)
    st["못 판"] = len(opened)
    led = old + [r[:5] for r in new]
    meta = [{"id": k, "신호 날": r[6], "산 날": r[1], "그날 순위": r[7], "나감": (r[8] if len(r) > 8 else "끝까지 보유")} for k, r in enumerate(new)]
    return led, st, meta


def occupancy_ok(led, cal):
    """장부만으로 날마다 1일봉 칸 합(산 날 ≤ d < 판 날) ≤ 10 인지."""
    bad = [d for d in cal if sum(s for c, b, e, p, s in led if b <= d < e) > SLOTS + 1e-9]
    return bad


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
        stat["칸 넘은 날"] = 0
    else:
        K, H = float(sys.argv[2]), int(sys.argv[3])
        mode = sys.argv[4] if len(sys.argv) > 4 else "rv"
        extra = float(sys.argv[5]) if len(sys.argv) > 5 else 0.0
        cut = sys.argv[6] if len(sys.argv) > 6 else None
        led, stat, meta = g2(K, H, mode, extra, cut)
        name = f"g2_{mode}_K{K}_H{H}" + (f"_x{extra}" if extra else "") + (f"_cut{cut}" if cut else "")
    path = OUT / f"{name}.json"
    json.dump(led, open(path, "w"))
    if sys.argv[1] != "g1":
        json.dump(meta, open(OUT / f"{name}.meta.json", "w"), ensure_ascii=False)
        if stat["칸 넘은 날"]:
            sys.exit(f"칸 넘음 {stat['넘은 날 예']} → 실패")
    print(json.dumps({"장부": str(path), "줄": len(led), **{k: v for k, v in stat.items()}}, ensure_ascii=False))
