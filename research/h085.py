"""1시간봉 85회차 — 자료 점검 빈틈 ④ '조합 방식': 한투 · DART 자료를 거르기 대신 **같은 시각 후보의 순서**로 씀.
지금 순서: 추세 문 → 3일 연속 → 무작위. 무작위 자리를 자료 점수로 바꿈(추세 문 · 3일 연속 먼저는 그대로).
점수는 사는 봉 시가 전에 아는 값(64회차 재료와 같음)이고, 같은 시각 후보끼리 크기만 견주므로 문턱이 없음(문턱 미래 참조 없음).
보는 점수: 외국인+투신 5일 세기 · 프로그램 5일 세기 · 간격(추세 세기) · 20일 수익 · 목표가 여유 · 20일 변동성 · 시총 순위 · 여럿을 같은 날 순위로 합친 점수.
점수마다 거꾸로 순서도 봄(좋은 점수라면 거꾸로는 나빠야 함). 씨앗 16."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
from pathlib import Path
import numpy as np
src = open("research/h064.py", encoding="utf-8").read()
exec(src.split("# ---------- 1. 매매 모으기")[0].replace("== 1시간봉 64회차 (약한 장 진 매매 샅샅이 분해) ==", "== 1시간봉 85회차 (자료 점수로 후보 순서) =="))
exec(src.split("# ---------- 2. 자료 읽기 ----------")[1].split("ROWS = []")[0].replace("CODES = sorted({c for c, _ in trades})", "CODES = sorted(data)"))
EX = make_exit()
F = {}
for c, b in data.items():
    for k in np.flatnonzero(sigs[c]):
        if k + 1 < len(b["t"]): F[(c, k)] = feats(c, k + 1)
print(f"  신호 {len(F)}개 재료 계산 끝", flush=True)
def g(c, k, nm):
    v = F.get((c, k), {}).get(nm, np.nan)
    return np.nan if v is None else v
def flow(c, k): return g(c, k, "외국인 5일/거래량") + g(c, k, "투신 5일/거래량")
SC = {"수급 세기(외국인+투신 5일)": flow, "프로그램 5일 세기": lambda c, k: g(c, k, "프로그램 5일/거래량"),
      "간격(추세 세기)": lambda c, k: g(c, k, "간격(3일선/200일선)"), "20일 수익": lambda c, k: g(c, k, "20일 수익"),
      "목표가 여유": lambda c, k: g(c, k, "목표가 여유(%)"), "20일 변동성": lambda c, k: g(c, k, "20일 변동성"),
      "시총 순위(작을수록 큼)": lambda c, k: -g(c, k, "시총 순위")}
# 합친 점수: 같은 날 신호끼리 수급 · 프로그램 · 간격 순위 평균(그날 안에서만 견줌)
byday = {}
for (c, k) in F: byday.setdefault(data[c]["t"][k][:8], []).append((c, k))
COMBO = {}
for day, L in byday.items():
    parts = []
    for fn in (flow, SC["프로그램 5일 세기"], SC["간격(추세 세기)"]):
        v = np.array([fn(c, k) for c, k in L], float); v = np.where(np.isnan(v), np.nanmedian(v) if np.any(~np.isnan(v)) else 0, v)
        parts.append(np.argsort(np.argsort(v)) / max(len(v) - 1, 1))
    for (c, k), s_ in zip(L, np.mean(parts, axis=0)): COMBO[(c, k)] = s_
SC["합친 점수(수급 · 프로그램 · 간격)"] = lambda c, k: COMBO.get((c, k), np.nan)
def rank_by(fn, sign=1):
    def r(c, b, k):
        x = ATT[c][k + 1] if k + 1 < len(b["t"]) else ATT[c][k]
        v = fn(c, k); v = 0.0 if v != v else v
        return (0 if x and x["추세문"] else 1, 0 if x and x["3일연속"] else 1, -sign * v)
    return r
def trim(rk):
    got = {}
    for s, (lo, hi) in (("앞", H.EARLY), ("뒤", H.LATE)):
        vals = {k: [] for k in (0, 3)}
        for seed in range(8):
            r = H._one_run(data, sigs, EX, size, lo, hi, 10, seed, None, rk, H.COST, None, None, stale90)
            w = sorted((t["손익"] * t["칸"] / 10 for t in r["목록"]), reverse=True)
            for kk in vals: vals[kk].append(sum(w[kk:]) / 1.5)
        got[s] = {kk: round(float(np.median(v)), 1) for kk, v in vals.items()}
    return got
cases = [("지금(추세 문 → 3일 연속 → 무작위)", rank)]
for nm, fn in SC.items():
    cases.append((f"{nm} 큰 것 먼저", rank_by(fn, 1)))
    cases.append((f"{nm} 작은 것 먼저", rank_by(fn, -1)))
for tag, rk in cases:
    res = H.simulate(data, e_align_or_noon, EX, size, rank=rk, stale_of=stale90, seeds=16)
    tr = trim(rk)
    print(f"  {tag:34s} " + H.line(res), flush=True)
    print(f"      큰 매매 뺀 연: 앞 {tr['앞']} · 뒤 {tr['뒤']}", flush=True)
print("끝", flush=True)
