"""1시간봉 43회차(확인 줄) — 42회차 후보(전날 시장 폭 < 70%면 150위 + 자리 바꾸기)의 이득이 어디서 오나.
42회차: 앞 반은 폭 60 → 65에서 22.6 → 52.3으로 뛰었음 → 이득이 '시장 폭 60~65% 날에 산 101~150위 매매' 몇 건에 몰렸을까.
넓혀서 새로 생긴 매매(100위 판엔 없던 것)를 시장 폭 칸 · 순위 칸 · 반기로 나눠 손익을 봄 · 큰 매매 몇 건을 빼도 남나."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h003.py", encoding="utf-8").read().split('print("== 1시간봉 3회차')[0])
stale = lambda p: (p["now"] - p["i"] >= 7) and (data[p["code"]]["c"][p["now"]] / p["price"] - 1) * 100 < 4
IN100 = IN
UW = H.Universe({d: v for d, v in ranks.items() if d >= "20230801"}, top=150)
IN_W = {c: np.where(np.array([bool(x) and (x["시장폭"] if x["시장폭"] is not None else 100) < 70 for x in ATT[c]]), np.array([UW.ok(c, t) for t in data[c]["t"]]), IN100[c]) for c in data}
rdays = sorted(ranks)
print("== 1시간봉 43회차 (폭<70 150위 후보의 이득은 어디서) ==", flush=True)
for tag, st in (("지금 규칙", None), ("자리 바꾸기", stale)):
    IN = IN100; base = H.simulate(data, e_align_or_noon, exit_daily, size, rank=rank, stale_of=st, seeds=1)
    IN = IN_W; wide = H.simulate(data, e_align_or_noon, exit_daily, size, rank=rank, stale_of=st, seeds=1)
    for s in ("앞", "뒤"):
        kb = {(t["code"], t["산 때"]) for t in base[s]["목록"]}
        new = [t for t in wide[s]["목록"] if (t["code"], t["산 때"]) not in kb]
        g = {}
        for t in new:
            k = data[t["code"]]["t"].index(t["산 때"]) - 1
            x = ATT[t["code"]][k]; br = x["시장폭"] if x and x["시장폭"] is not None else -1
            d = H.prev_day(rdays, t["산 때"]); r = ranks.get(d, {}).get(t["code"], 999)
            key = ("폭<60" if br < 60 else "폭60~65" if br < 65 else "폭65~70" if br < 70 else "폭70+") + "·" + ("101~150위" if r > 100 else "100위 안")
            g.setdefault(key, []).append(t["손익"] * t["칸"] / 10)
        w = sorted(t["손익"] * t["칸"] / 10 for t in new)
        print(f"  {tag} · {s}: 연 {base[s]['연']} → {wide[s]['연']} · 새 매매 {len(new)}건 몫 합 {sum(w):+.1f}%p · 큰 3건 뺀 몫 {sum(w[:-3]):+.1f}%p", flush=True)
        print("      " + " · ".join(f"{k} {len(v)}건 {sum(v):+.1f}%p" for k, v in sorted(g.items())), flush=True)
        print(f"      반기(씨앗 0) 100위 {base[s]['반기']} → 넓힘 {wide[s]['반기']}", flush=True)
print("끝", flush=True)
