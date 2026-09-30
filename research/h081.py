"""1시간봉 81회차 — 계좌 브레이크(80회차: 약한 장 큰 낙폭의 절반이 '낙폭 중 새로 산 매매'). 계좌가 꼭대기에서 −X% 넘게 빠져 있으면
새 매수를 멈춤(또는 칸을 절반으로) · 회복하면 다시. 계좌 값은 지난 날들의 값만(hlab.simulate brake) — 미래 참조 없음.
X = 3 · 5 · 7 · 10(고원). (처음 돌린 판은 엔진이 numpy 참을 못 알아들어 멈춤이 걸리지 않았음 → 고쳐 다시 돌림) 바탕: 1시간봉 최고 규칙. 씨앗 16 · 큰 매매 뺀 연 · 골."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h058.py", encoding="utf-8").read().split('CASES = [')[0])
EX = make_exit()
def dd(eq): return eq[-1] / max(eq) - 1 if eq else 0.0
def stop_at(X): return lambda eq: dd(eq) <= -X / 100
def half_at(X): return lambda eq: 0.5 if dd(eq) <= -X / 100 else None
def trim(bk):
    got = {}
    for s, (lo, hi) in (("앞", H.EARLY), ("뒤", H.LATE)):
        vals = {k: [] for k in (0, 3)}
        for seed in range(8):
            r = H._one_run(data, sigs, EX, size, lo, hi, 10, seed, None, rank, H.COST, None, None, stale90, None, None, bk)
            w = sorted((t["손익"] * t["칸"] / 10 for t in r["목록"]), reverse=True)
            for kk in vals: vals[kk].append(sum(w[kk:]) / 1.5)
        got[s] = {kk: round(float(np.median(v)), 1) for kk, v in vals.items()}
    return got
print("== 1시간봉 81회차 (계좌 브레이크) ==", flush=True)
cases = [("지금(브레이크 없음)", None)] + [(f"꼭대기 −{X}%면 새 매수 멈춤", stop_at(X)) for X in (3, 5, 7, 10)] + [(f"꼭대기 −{X}%면 칸 절반", half_at(X)) for X in (5, 7, 10)]
for tag, bk in cases:
    res = H.simulate(data, e_align_or_noon, EX, size, rank=rank, stale_of=stale90, seeds=16, brake=bk)
    tr = trim(bk)
    print(f"  {tag:22s} " + H.line(res), flush=True)
    print(f"      큰 매매 뺀 연: 앞 {tr['앞']} · 뒤 {tr['뒤']}", flush=True)
print("끝", flush=True)
