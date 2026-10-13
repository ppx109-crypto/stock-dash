"""KMF-0022 탐색 1 — 원리로 짠 새 추세봇: 손실은 짧게 끊고 이익은 길게(1계약 · 1분봉 체결 셈).
사용자 2026-10-13: "수익을 늘린다고 mdd가 늘지않는건 12a로 보여줬으니 실행해 · 복사하라고 12a를준게 아닌 할 수 있다고보여준거니
 어느정도 카피는되어도 복사하진말고 너도 지피티와 함께 새봇제작해줘" · 목표(보고만): 신규봇 혼자 MDD ≤ −20p · 합 ≥ +800p.
들기(5분봉 종가 판단 · 그 봉까지 자료만 · 체결 = 다음 분 시가):
  A 돌파: 종가가 앞 N봉 최고(롱) / 최저(숏)를 넘고 · 종가가 VWAP 같은 쪽
  B 되돌림(켬/끔): 큰 추세 쪽으로 · 저가(롱)가 EMA20(5분)에 닿은 뒤 종가가 EMA20 위로 닫힘(숏은 거꾸로)
  거름 ① 뒷북: |종가 − VWAP| ÷ ATR14(5분) > c 이면 안 듦  ② 아침: 09:00 ~ 09:59 범위 ÷ 시가가 앞 20거래일 같은 값의 q 분위 아래면 그날 안 듦
       ③ 큰 추세: EMA(H)(5분 · 날 넘어 이어 셈)의 12봉 기울기 부호가 방향과 다르면 안 듦(H 0 = 끔)
  들기 시간 10:00 ~ 15:00 · 하루 최대 4번 · 하루 −20p 멈춤
나기(1분봉): 재난 멈춤 3 × ATR14(5분) · 조기 손절: 든 뒤 3봉 지나 5분봉 종가가 EMA(F) 거꾸로 · 무익: NP분 지나 평가 ≤ 0
  · 추적: 1분 채널 n분 · 이익이 3 × ATR 넘으면 n/3분으로 줄임 · 15:30 정리 · 편도 0.04p
python3 trend_lab.py"""
import itertools
import json
import sys
from collections import defaultdict, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "research")); sys.path.insert(0, str(ROOT / "research-exchange/claude-to-gpt/KMF-0019/explore"))
import mdd_lab as D  # noqa: E402
K, M17 = D.K, D.M17


def ema(x, s):
    out, e, k = [], None, 2 / (s + 1)
    for v in x:
        e = v if e is None else e + k * (v - e); out.append(e)
    return out


def prep(rows):
    b = M17.prep(rows)
    c = [r[5] for r in b]; h = [r[3] for r in b]; l = [r[4] for r in b]
    tr = [h[0] - l[0]] + [max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])) for i in range(1, len(b))]
    atr = []
    for i in range(len(b)):
        w = tr[max(0, i - 13):i + 1]; atr.append(sum(w) / len(w))
    E = {s: ema(c, s) for s in (10, 20, 48, 96)}
    by = defaultdict(list)
    for r in rows:
        if 540 <= r[1] <= 930:
            by[r[0]].append(r)
    info, hist = {}, []
    for d in sorted(by):
        x = by[d]; am = [r for r in x if r[1] < 600]
        a = (max(r[3] for r in am) - min(r[4] for r in am)) / x[0][2] * 100 if am else None
        info[d] = {"am": a, "hist": list(hist[-20:])}
        if a is not None:
            hist.append(a)
    return b, atr, E, info


def run(rows, b, atr, E, info, N, c_, q, H, F, NP, n, useB, maxn=4, ds=20.0):
    bi = {(r[0], r[1]): k for k, r in enumerate(b)}
    days = {}; i, nr = 0, len(rows)
    while i < nr:
        d = rows[i][0]; j = i
        while j < nr and rows[j][0] == d:
            j += 1
        inf = info.get(d, {}); gate = True
        if q and inf.get("am") is not None and len(inf["hist"]) >= 10:
            hs = sorted(inf["hist"]); gate = inf["am"] >= hs[int(q * (len(hs) - 1))]
        pos, entry, emin, real, cnt, stopped, pend, mfe, ea, ekb = 0, 0.0, 0, 0.0, 0, False, None, 0.0, 1.0, 0
        pv, vv = 0.0, 0.0; lo1, hi1 = deque(maxlen=120), deque(maxlen=120); nb = 0
        for k in range(i, j):
            _, m, o, h, l, c = rows[k][:6]; v = (rows[k][6] if len(rows[k]) > 6 else 1.0) or 1.0
            if m >= 540:
                pv += (h + l + c) / 3 * v; vv += v
            if pend is not None and not stopped and m <= K.FLAT_AT:
                tgt, a0 = pend
                if tgt != pos:
                    if pos:
                        real += pos * (o - entry) - K.COST; pos = 0
                    if tgt and real > -ds and cnt < maxn:
                        pos, entry, emin, mfe, ea = tgt, o, m, 0.0, a0; real -= K.COST; cnt += 1
            pend = None
            if pos:
                for sp, end in ((entry - pos * 3 * ea, False), (entry + pos * (-ds - real + K.COST), True)):
                    if pos and ((l <= sp) if pos > 0 else (h >= sp)):
                        real += pos * ((min(o, sp) if pos > 0 else max(o, sp)) - entry) - K.COST; pos = 0
                        stopped = stopped or end
            if not pos and real <= -ds:
                stopped = True
            if pos and (m >= K.FLAT_AT or k == j - 1):
                real += pos * (c - entry) - K.COST; pos = 0
            if pos and not stopped and m < K.FLAT_AT:
                mfe = max(mfe, pos * ((h if pos > 0 else l) - entry))
                nn = max(5, n // 3) if mfe >= 3 * ea else n
                ch = list(lo1)[-nn:] if pos > 0 else list(hi1)[-nn:]
                if len(ch) >= 5 and ((pos > 0 and c < min(ch)) or (pos < 0 and c > max(ch))):
                    pend = (0, 0)
                if NP and m - emin >= NP and pos * (c - entry) <= 0:
                    pend = (0, 0)
            kb = bi.get((d, m))
            if kb is not None:
                nb += 1; cc = b[kb][5]
                if pos and pend is None and m - emin >= 15 and (cc - E[F][kb]) * pos < 0:
                    pend = (0, 0)
                if not pos and pend is None and gate and not stopped and 600 <= m <= 900 and cnt < maxn and nb > N:
                    vw = pv / vv if vv else cc
                    box = b[kb - N:kb]; bh = max(x[3] for x in box); bl = min(x[4] for x in box)
                    tr_ = 0 if not H else (1 if E[H][kb] > E[H][kb - 12] else -1)
                    side = 1 if (cc > bh and cc > vw) else (-1 if (cc < bl and cc < vw) else 0)
                    if not side and useB and tr_:
                        e20 = E[20][kb]
                        if tr_ > 0 and b[kb][4] <= e20 < cc and cc > vw:
                            side = 1
                        elif tr_ < 0 and b[kb][3] >= e20 > cc and cc < vw:
                            side = -1
                    if side and c_ and abs(cc - vw) / max(atr[kb], 1e-9) > c_:
                        side = 0
                    if side and H and tr_ != side:
                        side = 0
                    if side:
                        pend = (side, atr[kb])
            lo1.append(l); hi1.append(h)
        days[d] = real
        i = j
    return days


if __name__ == "__main__":
    rows = K._rows_before(M17.END)
    b, atr, E, info = prep(rows)
    res = []
    grid = list(itertools.product((8, 12, 16), (1.0, 1.5, 2.5, 0), (0, 0.2, 0.33), (0, 48, 96), (10, 20), (60, 90), (30, 60), (0, 1)))
    for N, c_, q, H, F, NP, n, useB in grid:
        days = run(rows, b, atr, E, info, N, c_, q, H, F, NP, n, useB)
        res.append({"판": f"N{N}_c{c_}_q{q}_H{H}_F{F}_NP{NP}_n{n}_B{useB}", **D.summ(days)})
    (Path(__file__).with_name("trend_lab_out.json")).write_text(json.dumps(res, ensure_ascii=False, indent=0))
    print("판 수", len(res))
    ok = [x for x in res if x["MDD"] >= -20]
    print("MDD ≤ −20:", len(ok), "· 그중 +800 이상:", sum(1 for x in ok if x["합계"] >= 800))
    for x in sorted(ok, key=lambda x: -x["합계"])[:8]:
        print("  ", json.dumps(x, ensure_ascii=False))
    print("비 상위")
    for x in sorted(res, key=lambda x: -x["합계"] / max(1, -x["MDD"]))[:8]:
        print("  ", round(x["합계"] / max(1, -x["MDD"]), 1), json.dumps(x, ensure_ascii=False))
