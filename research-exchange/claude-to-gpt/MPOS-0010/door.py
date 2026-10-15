"""MPOS-0010 장부 만들기 — 1일봉 장부(z055_d1_raw · 495건) 빈 칸에 새 문 'RM'(GPT #426 G1: 중기 고유(잔차) 강세 + 눌림 → RNA 회복)을 더함.
t 종가까지 자료만: 그날 시총 200위 안 · 시장 = 그날 200위 안 하루 로그 수익 가운데값 ·
  β = 그날까지 120일 이동(공분산 ÷ 시장 분산 · 최소 100일) · 잔차 e = 로그 수익 − β × 시장 ·
  잔차 강세 점수 RM = e를 t−120 ~ t−21(최근 20일 빼고 100일) 합 ÷ (같은 창 e 표준편차 × √100) → 그날 200위 안에서 위 20%(순위 비율 ≥ 0.8) ·
  눌림 · 회복(RNA): z5(t−1) ≤ −K · z5(t) > z5(t−1) · z5(t) < 0 · 종가(t) > 종가(t−1) · z5 = 최근 5일 e 합 ÷ (60일 e 표준편차 × √5)
  → t 다음 거래일 종가에 1칸(빈 칸만 · 기존 문 먼저 · 기존 문 우선 정리 · 들어간 순서 장부 = MPOS-0008 walk 그대로) · 여러 신호면 RM 높은 순.
  나감 하나: 산 날에서 H 거래일째 종가(시간만). 손익 = 판 ÷ 산 − 1 − 0.25%(장부 관례) − 스트레스. 추정 비용은 cost10.py(계좌 NAV로 주문 크기)에서.
빼기: total = 잔차 대신 원 로그 수익(점수 · z5 모두) · nopull = 위 20%에 새로 든 날 바로(눌림 · 회복 없음).
python3 door.py rm K H [rm|total|nopull] [extra] [cut]"""
import json
import math
import os
import sys
from pathlib import Path

TREE = Path("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/m54tree")   # MIX-0054 결과 커밋 9743cb802 그대로
SP = Path("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad")
OUT = SP / "mpos10" / "ledgers"
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


def rm(K, H, mode="rm", extra=0.0, cut=None):
    P, ins, lr, mkt, badwin = frames(cut)
    import nrl
    if mode == "total":
        e = lr
    else:
        Mk = (lr * 0).add(mkt, axis=0)                              # 종목 값이 있는 날만 시장 값(β 표본을 종목 · 시장 같은 날로 맞춤)
        mxy = (lr * Mk).rolling(120, min_periods=100).mean()
        mx = lr.rolling(120, min_periods=100).mean()
        mm = Mk.rolling(120, min_periods=100).mean()
        var = Mk.rolling(120, min_periods=100).var(ddof=0)
        beta = (mxy - mx.mul(mm, axis=0)).div(var, axis=0)
        e = lr - beta.mul(mkt, axis=0)
    past = e.shift(21)
    score = past.rolling(100, min_periods=90).sum() / (past.rolling(100, min_periods=90).std() * 10.0)
    top = score.where(ins).rank(axis=1, pct=True) >= 0.8
    z5 = e.rolling(5, min_periods=5).sum() / (e.rolling(60, min_periods=60).std() * math.sqrt(5))
    if mode == "nopull":
        sig = ins & top & ~top.shift(1, fill_value=False) & ~badwin
    else:
        sig = ins & top & (z5.shift(1) <= -K) & (z5 > z5.shift(1)) & (z5 < 0) & (P > P.shift(1)) & ~badwin
    cal = list(P.index)
    tradeday = set(d for d in nrl.BR if FROM <= d <= TO)
    old = json.load(open(OLD))
    cands = {}
    for t in cal:
        row = sig.loc[t]
        cs = row.index[row.values]
        if len(cs):
            cands[t] = sorted((-float(score.at[t, c]), c) for c in cs)        # 우선순위: 잔차 강세 높은 순 · 같으면 종목 번호
    zv = {t: {} for t in cal}                                       # 계획 나감 신호 없음(시간 나감만)
    Pv = P.to_dict("index")
    if cut:                                                         # 자르기: 기존 장부도 그날까지 아는 것만(그날 뒤 판 날은 '보유 중')
        old = [[c, b, (e if e <= cut else "99999999"), (p if e <= cut else 0.0), s] for c, b, e, p, s in old if b <= cut]
    led, st, meta = walk(cal, tradeday, cands, zv, Pv, old, H, extra)
    return led, st, meta


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


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    K, H = float(sys.argv[2]), int(sys.argv[3])
    mode = sys.argv[4] if len(sys.argv) > 4 else "rm"
    extra = float(sys.argv[5]) if len(sys.argv) > 5 else 0.0
    cut = sys.argv[6] if len(sys.argv) > 6 else None
    led, stat, meta = rm(K, H, mode, extra, cut)
    name = f"rm_{mode}_K{K}_H{H}" + (f"_x{extra}" if extra else "") + (f"_cut{cut}" if cut else "")
    path = OUT / f"{name}.json"
    json.dump(led, open(path, "w"))
    json.dump(meta, open(OUT / f"{name}.meta.json", "w"), ensure_ascii=False)
    if stat["칸 넘은 날"]:
        sys.exit(f"칸 넘음 {stat['넘은 날 예']} → 실패")
    print(json.dumps({"장부": str(path), "줄": len(led), **{k: v for k, v in stat.items()}}, ensure_ascii=False))
