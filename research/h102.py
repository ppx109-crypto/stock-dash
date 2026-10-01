"""1시간봉 102회차 — 101회차에서 15분봉 두 거르기가 긴 자료에선 1시간봉 규칙을 나쁘게 함. 어디서 갈리나:
같은 1시간봉 연구 자료를 15분봉 연구 기간(앞 2025-09-17 ~ 2026-03-31 · 뒤 2026-04-01 ~ 2026-08-31)으로 자르고,
Q_CODES=all(362종목) · m15(15분봉 161종목만)로 나눠 '그대로' vs '+ 둘 다'를 봄. 씨앗 16.
"""
import os
import sys
from pathlib import Path
sys.path.insert(0, "/home/user/stock-dash")
exec(open("research/h101.py", encoding="utf-8").read().split('print(f"== 1시간봉 101회차')[0])

PER = (("15분봉 앞", ("2025091700", "2026040100")), ("15분봉 뒤", ("2026040100", "2026090100")))
pick = os.environ.get("Q_CODES", "all")
if pick == "m15":
    keep = {p.name for p in Path(os.environ["M15_HOME"]).iterdir() if p.is_dir()}
    data = {c: b for c, b in data.items() if c in keep or c.startswith("K")}


def run2(tag, fn):
    global sigs, KEYS
    sigs = {c: np.asarray(fn(c, b), bool) for c, b in data.items()}
    KEYS = [(c, k) for c, b in data.items() for k in np.flatnonzero(sigs[c])]
    rk = rk_of(tiers(20, 5, 3))
    res = H.simulate(data, lambda c, b: sigs[c], EX, size, rank=rk, stale_of=stale90, seeds=16, periods=PER)
    print(f"  {tag:30s} " + " | ".join(f"{n} 매매 {r['매매']} 연 {r['연']}({r['폭']}) 골 {r['골']} 행운뺌 {r['행운뺌']}" for n, r in res.items() if r), flush=True)


print(f"== 1시간봉 102회차: 15분봉 기간 · {'15분봉 종목' if pick == 'm15' else '모든 종목'} ({len(data)}종목) ==", flush=True)
run2("그대로", entry_f())
run2("+ 그날 +2% 위 · 시장 −1% 아래 안 삼", entry_f(up=0.02, mkt=-0.01))
run2("+ 둘 다 · 10시 봉 뒤(11:00)", entry_f(noon="10", up=0.02, mkt=-0.01))
print("끝", flush=True)
