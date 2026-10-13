"""시간대 짧은 추세 봇 탐색(전체 자료 · 5분봉 · −25p · 1계약): 창(30분 + 30분)마다 앞 30분 움직임 방향으로 뒤 30분 들기.
 앞 30분 움직임이 q × ATR(5분봉 앞 20봉) 넘을 때만 · 수급 거름(전날 개인 순매수 z 부호와 같은 방향만) 켬/끔 · 늦은 창은 되돌림(반대로) 켬/끔.
 들기 판단 = 앞 30분 마지막 5분봉 종가 · 체결 = 다음 봉 시가 · 정리 판단 = 뒤 30분 마지막 5분봉 종가."""
import sys, json, itertools
from collections import defaultdict
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "research"))
import kmf as K, kmf4 as K4
K.DAY_STOP = -25.0
sys.path.insert(0, str(ROOT / "research-exchange/claude-to-gpt/KMF-0014/explore"))
import short_lab as S
rows = K._rows_before("20261013")
b = K4.day_start_aligned(rows, 5)
c = np.array([r[5] for r in b]); o = np.array([r[2] for r in b]); h = np.array([r[3] for r in b]); l = np.array([r[4] for r in b])
pc = np.r_[c[0], c[:-1]]; trr = np.maximum(np.maximum(h - l, np.abs(h - pc)), np.abs(l - pc))
atr = np.full(len(c), np.nan)
for i in range(20, len(c)):
    atr[i] = trr[i - 20:i].mean()
idx = {(r[0], r[1]): i for i, r in enumerate(b)}
inv = {r["date"]: r for r in json.load(open(Path(__file__).parent / "investor_KSP.json"))["rows"]}
idates = sorted(inv)
bias = {}
for d in sorted({r[0] for r in b}):
    prev = [x for x in idates if x < d]
    if len(prev) < 21:
        continue
    hist = [inv[x]["개인"] for x in prev[-21:-1]]
    z = (inv[prev[-1]]["개인"] - np.mean(hist)) / (np.std(hist) or 1)
    bias[d] = 1 if z > 0 else -1


def sig(cfg):
    want = [None] * len(b)
    for d in sorted({r[0] for r in b}):
        for h0, mode in cfg["wins"]:
            s0, s1, e1 = idx.get((d, h0 + 4)), idx.get((d, h0 + 29)), idx.get((d, h0 + 59))
            if s0 is None or s1 is None or e1 is None or np.isnan(atr[s1]):
                continue
            a = c[s1] - o[s0]
            if abs(a) < cfg["q"] * atr[s1] or a == 0:
                continue
            side = int(np.sign(a)) * (1 if mode == "mom" else -1)
            if cfg["flow"] and bias.get(d) != side:
                continue
            if want[s1] is None or want[s1] == 0:
                want[s1] = side
            want[e1] = 0
    return want


MOM_ALL = [545, 575, 605, 695, 785, 815]          # 앞 · 뒤 반 모두 +인 창(진단 ②)
REV = [845, 875]                                   # 앞 · 뒤 반 모두 −인 창
def main():
  res = {}
  for wset, rev, q, flow in itertools.product(("all6", "am3", "pm2"), (0, 1), (0.0, 0.5, 1.0, 1.5), (0, 1)):
      wins = {"all6": MOM_ALL, "am3": [545, 575, 605], "pm2": [785, 815]}[wset]
      w = [(x, "mom") for x in wins] + ([(x, "rev") for x in REV] if rev else [])
      cfg = {"wins": w, "q": q, "flow": flow}
      days, tr = K.simulate(b, sig(cfg))
      r = S.report(days, tr)
      res[f"{wset}_rev{rev}_q{q}_flow{flow}"] = r
  json.dump(res, open(Path(__file__).parent / "window_lab.json", "w"), ensure_ascii=False)
  for k, v in sorted(res.items(), key=lambda kv: -kv[1]["ex10"]):
      print(k, {x: v[x] for x in ("total", "ex10", "trades", "pos_m", "worst_m", "mdd")})


if __name__ == "__main__":
    main()
