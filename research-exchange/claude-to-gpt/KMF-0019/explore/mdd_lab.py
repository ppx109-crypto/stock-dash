"""KMF-0019 탐색 2 — KMF-0017 MDD 줄이기 여러 판(전체 자료 한 번에 · 판정은 나중 시험 2만).
장 안 규칙: 하루 멈춤 DS · 횡보 봇 멈춤 폭 s(ATR 배수) · 봇 빼기(R/W).
날 단위 규칙(그림자 셈 — 봇은 매일 그림자로 돌고, 실제로 들지 말지는 '앞 날까지' 결과로만 정함):
  none · ddN(X,N): 실제 누적이 고점에서 X 넘게 내려가면 그 뒤 N일 쉼(쉬는 날도 그림자는 셈)
  streak(k): 그림자 손해 날이 k번 이어지면 다음 1일 쉼 · wk(X): 이번 주 실제 손익 ≤ −X 이면 그 주 남은 날 쉼
  mo(X): 이번 달 실제 손익 ≤ −X 이면 그달 남은 날 쉼
python3 mdd_lab.py"""
import itertools
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import loss_lab as L  # noqa: E402
K, M13, M14, M15, M16, M17 = L.K, L.M13, L.M14, L.M15, L.M16, L.M17


def signals(b, T, R, W, lock=(40, 15)):
    n = len(b); want = [None] * n; i = 0
    while i < n:
        d = b[i][0]; j = i
        while j < n and b[j][0] == d:
            j += 1
        pos, entry, real, peak, halt, done, last, pend = 0, 0.0, 0.0, 0.0, False, False, 0, None
        for k in range(i, j):
            o, h, l, c, m = b[k][2], b[k][3], b[k][4], b[k][5], b[k][1]
            if pend is not None and not done and m <= K.FLAT_AT:
                tgt, pm = pend
                if tgt != pos:
                    if pos:
                        real += pos * (o - entry) - K.COST; pos = 0
                    if tgt and K.ENTRY_FROM <= pm <= K.ENTRY_TO and real > K.DAY_STOP:
                        pos, entry = tgt, o; real -= K.COST
            pend = None
            if pos and not done:
                sp = entry + pos * (K.DAY_STOP - real + K.COST)
                if (l <= sp) if pos > 0 else (h >= sp):
                    px = min(o, sp) if pos > 0 else max(o, sp)
                    real += pos * (px - entry) - K.COST; pos = 0; done = True
            if done or m >= K.FLAT_AT:
                continue
            mtm = real + (pos * (c - entry) - K.COST if pos else 0.0)
            peak = max(peak, mtm)
            if lock and peak >= lock[0] and mtm <= peak - lock[1]:
                halt = True
            tgt = 0 if halt else (T[k] or R[k] or W[k])
            if tgt != last:
                want[k] = tgt; last = tgt
            pend = (tgt, m)
        i = j
    return want


def throttle(days, rule):
    """그림자 날 손익 → 실제 날 손익(앞 날까지만 보고 정함)."""
    out, eq, peak, rest, streak = {}, 0.0, 0.0, 0, 0
    wk_key = mo_key = None; wk = mo = 0.0
    kind = rule[0]
    for d, p in sorted(days.items()):
        dt = date(int(d[:4]), int(d[4:6]), int(d[6:]))
        wkk, mok = dt.isocalendar()[:2], d[:6]
        if wkk != wk_key:
            wk_key, wk = wkk, 0.0
        if mok != mo_key:
            mo_key, mo = mok, 0.0
        trade = True
        if kind == "dd" and rest > 0:
            trade = False; rest -= 1
        if kind == "streak" and streak >= rule[1]:
            trade = False; streak = 0
        if kind == "wk" and wk <= -rule[1]:
            trade = False
        if kind == "mo" and mo <= -rule[1]:
            trade = False
        a = p if trade else 0.0
        out[d] = a; eq += a; wk += a; mo += a
        streak = streak + 1 if p < 0 else 0
        if eq > peak:
            peak = eq
        if kind == "dd" and trade and peak - eq >= rule[1]:
            rest = rule[2]; peak = eq          # 쉰 뒤 새로 셈
    return out


def summ(days):
    vals = sorted(days.items()); mon = defaultdict(float)
    for d, p in vals:
        mon[d[:6]] += p
    top = sorted(days.values(), reverse=True)
    return {"합계": round(sum(days.values()), 2), "MDD": L.mdd(days)[0], "하루 최악": round(min(days.values()), 2),
            "가장 나쁜 달": round(min(mon.values()), 2), "손해 달": sum(1 for p in mon.values() if p < 0),
            "앞": round(sum(p for d, p in vals if d < "20260601"), 2), "뒤": round(sum(p for d, p in vals if d >= "20260601"), 2),
            "177일": round(sum(p for d, p in vals if d not in M17.TOP10_KMF16), 2), "자기위10뺀": round(sum(top[10:]), 2)}


if __name__ == "__main__":
    b = M17.prep(K._rows_before(M17.END))
    T = M16.intent(b, M13.signals(b, M13.grid()[0]))
    W = M16.intent(b, M15.signals(b, M15.grid()[0]))
    Rs = {}
    for s in (3.0, 2.0, 1.5):
        cfg = dict(M14.grid()[0]); cfg["s"] = s
        Rs[s] = M16.intent(b, M14.signals(b, cfg))
    zero = [0] * len(b)
    rules = [("none",)] + [("dd", x, n) for x in (15, 25, 40) for n in (1, 3, 5)] + [("streak", 2), ("streak", 3), ("wk", 15), ("wk", 25), ("mo", 25), ("mo", 40)]
    res = []
    for ds, rkey, useW in itertools.product((25, 15, 10, 7), ("R3", "R2", "R1.5", "R없음"), (1, 0)):
        K.DAY_STOP = -float(ds)
        R = zero if rkey == "R없음" else Rs[float(rkey[1:])]
        want = signals(b, T, R, W if useW else zero)
        days, _ = K.simulate(b, want)
        for rule in rules:
            s = summ(throttle(days, rule))
            res.append({"판": f"DS{ds}_{rkey}_W{useW}_{'_'.join(map(str, rule))}", **s})
    K.DAY_STOP = -25.0
    print("판 수", len(res))
    ok = sorted([r for r in res if r["MDD"] >= -33], key=lambda r: -r["합계"])
    print("MDD −33 이내(1,100만 원의 −15%) 상위 15:")
    for r in ok[:15]:
        print(json.dumps(r, ensure_ascii=False))
    ok15 = sorted([r for r in res if r["MDD"] >= -15], key=lambda r: -r["합계"])
    print("MDD −15p 이내 상위 10:")
    for r in ok15[:10]:
        print(json.dumps(r, ensure_ascii=False))
    print("기준:", json.dumps([r for r in res if r["판"] == "DS25_R3_W1_none"][0], ensure_ascii=False))
    Path(__file__).with_name("mdd_lab_out.json").write_text(json.dumps(res, ensure_ascii=False, indent=0))
