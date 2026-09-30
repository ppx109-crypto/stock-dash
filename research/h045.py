"""1시간봉 45회차(확인 줄) — 새 종목 수급이 다 들어온 뒤(178/180) 종목 넓히기 다시: 100 · 150 · 200 · 300위 · 약한 장(폭<70)에서만 150 · 200 · 300위
× 지금 규칙 / 자리 바꾸기. 씨앗 8개마다 '큰 매매 k건(0 · 3 · 5) 뺀 연수익' 가운데 값까지(43 · 44회차 방식)."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h003.py", encoding="utf-8").read().split('print("== 1시간봉 3회차')[0])
stale = lambda p: (p["now"] - p["i"] >= 7) and (data[p["code"]]["c"][p["now"]] / p["price"] - 1) * 100 < 4
IN100 = IN
def uni_in(top, weak_only):
    U = H.Universe({d: v for d, v in ranks.items() if d >= "20230801"}, top=top)
    out = {}
    for c in data:
        w = np.array([U.ok(c, t) for t in data[c]["t"]])
        if weak_only:
            weak = np.array([bool(x) and (x["시장폭"] if x["시장폭"] is not None else 100) < 70 for x in ATT[c]])
            w = np.where(weak, w, IN100[c])
        out[c] = w
    return out
def trimmed(st):
    sigs = {c: np.asarray(e_align_or_noon(c, b), bool) for c, b in data.items()}
    got = {}
    for s, (lo, hi) in (("앞", H.EARLY), ("뒤", H.LATE)):
        vals = {k: [] for k in (0, 3, 5)}
        for seed in range(8):
            r = H._one_run(data, sigs, exit_daily, size, lo, hi, 10, seed, None, rank, H.COST, None, None, st)
            w = sorted((t["손익"] * t["칸"] / 10 for t in r["목록"]), reverse=True)
            for k in vals: vals[k].append(sum(w[k:]) / 1.5)
        got[s] = {k: round(float(np.median(v)), 1) for k, v in vals.items()}
    return got
print("== 1시간봉 45회차 (수급 다 들어온 뒤 종목 넓히기 다시) ==", flush=True)
print(f"  모의 종목 {len(data)}", flush=True)
for name, top, weak in (("100위", 100, False), ("150위", 150, False), ("200위", 200, False), ("300위", 300, False),
                        ("폭<70이면 150위", 150, True), ("폭<70이면 200위", 200, True), ("폭<70이면 300위", 300, True)):
    IN = IN100 if top == 100 else uni_in(top, weak)
    for tag, st in (("지금 규칙", None), ("자리 바꾸기", stale)):
        res = H.simulate(data, e_align_or_noon, exit_daily, size, rank=rank, stale_of=st)
        tr = trimmed(st)
        print(f"  {f'{name} · {tag}':22s} " + H.line(res), flush=True)
        print(f"      큰 매매 뺀 연(가운데): 앞 {tr['앞']} · 뒤 {tr['뒤']}", flush=True)
print("끝", flush=True)
