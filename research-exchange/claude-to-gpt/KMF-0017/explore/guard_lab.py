"""KMF-0017 탐색: KMF-0016 신호는 그대로 두고 '하루 지키기'만 더함(전체 자료 · 1계약). 모두 그 봉 종가까지 값으로 정하고 다음 봉 시가에 실행.
 stop  : 하루 멈춤 −10 · −15 · −20 · −25(지금)
 am    : 추세 봇의 새 들기를 hh:mm 전에는 안 받음(횡보 봇은 그대로) · 0 = 끔
 lock  : 그날 손익(실현 + 들고 있는 것 종가 평가)이 +L 넘은 뒤 최고치에서 G 넘게 내려오면 정리하고 그날 끝 · 0 = 끔
 loss2 : 그날 진 거래가 n번이면 그날 끝 · 0 = 끔"""
import sys, json, itertools
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "research"))
import kmf as K, kmf16 as M16
sys.path.insert(0, str(ROOT / "research-exchange/claude-to-gpt/KMF-0014/explore"))
import short_lab as S
b = M16.prep(K._rows_before(M16.END))
T = M16.intent(b, M16.M13.signals(b, M16.M13.grid()[0]))
R = M16.intent(b, M16.M14.signals(b, M16.M14.grid()[0]))
TOP10 = set(json.load(open(Path(__file__).parent / "top10_kmf16.json"))["top10"])
COST = K.COST


def run(stop=-25.0, am=0, lock=(0, 0), loss2=0):
    """KMF-0016 합치기 + 지키기(체결 = 다음 봉 시가 · 멈춤은 봉 안 고저 · 지키기 판단은 봉 종가)."""
    days, trades = {}, []
    n = len(b); i = 0
    while i < n:
        d = b[i][0]; j = i
        while j < n and b[j][0] == d:
            j += 1
        real, pos, entry, done, halt, peak, losses, pend = 0.0, 0, 0.0, False, False, 0.0, 0, None
        for k in range(i, j):
            o, h, l, c, m = b[k][2], b[k][3], b[k][4], b[k][5], b[k][1]
            if pend is not None and not done and m <= K.FLAT_AT:
                tgt, pm = pend
                if tgt != pos:
                    if pos:
                        p = pos * (o - entry) - COST; real += p; trades.append((d, pm, pos, entry, o))
                        losses += (p - COST) < 0; pos = 0
                    if tgt and K.ENTRY_FROM <= pm <= K.ENTRY_TO and real > stop and not halt:
                        pos, entry = tgt, o; real -= COST
            pend = None
            if halt and pos == 0:
                done = True
            if pos:
                sp = entry + pos * (stop - real + COST)
                if (l <= sp) if pos > 0 else (h >= sp):
                    px = min(o, sp) if pos > 0 else max(o, sp)
                    real += pos * (px - entry) - COST; trades.append((d, m, pos, entry, px)); pos = 0; done = True
            if k == j - 1 or m >= K.FLAT_AT:
                if pos:
                    real += pos * (c - entry) - COST; trades.append((d, m, pos, entry, c)); pos = 0
                break
            if done:
                continue
            mtm = real + (pos * (c - entry) - COST if pos else 0.0)
            peak = max(peak, mtm)
            if (lock[0] and peak >= lock[0] and mtm <= peak - lock[1]) or (loss2 and losses >= loss2):
                halt = True
            if halt:
                pend = (0, m)
                continue
            t = T[k]
            if am and m < am and t != pos:
                t = 0                                   # 오전엔 추세 봇의 새 들기 · 뒤집기 안 받음(이미 든 추세 자리는 유지)
            pend = (t if t else R[k], m)
        days[d] = real
        i = j
    return days, trades


def score(days, trades):
    r = S.report(days, trades)
    r["rest177"] = round(sum(v for d, v in days.items() if d not in TOP10), 1)
    r["top10_fixed"] = round(sum(v for d, v in days.items() if d in TOP10), 1)
    return r


def main():
  base = score(*run())
  print("기준(지키기 없음):", {k: base[k] for k in ("total", "rest177", "top10_fixed", "ex10", "pos_m", "worst_m", "mdd")})
  res = {}
  for stop, am, lock, loss2 in itertools.product((-25.0, -20.0, -15.0, -10.0), (0, 660, 720), ((0, 0), (20, 10), (30, 15), (40, 20)), (0, 2, 3)):
      r = score(*run(stop, am, lock, loss2))
      res[f"s{int(-stop)}_am{am}_L{lock[0]}-{lock[1]}_n{loss2}"] = r
  json.dump(res, open(Path(__file__).parent / "guard_lab.json", "w"), ensure_ascii=False)
  print("조합", len(res))
  for k, v in sorted(res.items(), key=lambda kv: -kv[1]["rest177"])[:20]:
      print(k, {x: v[x] for x in ("total", "rest177", "top10_fixed", "ex10", "pos_m", "worst_m", "mdd")})


if __name__ == "__main__":
    main()
