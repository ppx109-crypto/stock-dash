"""1시간봉 81회차 — 계좌 브레이크(80회차: 약한 장 큰 낙폭의 절반이 '낙폭 중 새로 산 매매').
계좌가 기준 꼭대기에서 −X% 넘게 빠지면 **N거래일 동안** 새 매수를 멈춤(또는 칸 절반) · N일 뒤엔 그때 계좌를 새 기준으로 다시 삼.
(처음 판: '빠져 있는 동안 계속 멈춤'은 들고 있는 게 없어지면 계좌가 회복할 수 없어 영영 멈춤 → 버림. 또 엔진이 numpy 참을 못 알아듣던 것도 고침.)
계좌 값은 지난 날들의 값만(hlab.simulate brake) — 미래 참조 없음. X = 5 · 7 · 10 · N = 5 · 10 · 20(고원). 바탕: 1시간봉 최고 규칙. 씨앗 16."""
import sys
sys.path.insert(0, "/home/user/stock-dash")
import numpy as np
import hlab as H
exec(open("research/h058.py", encoding="utf-8").read().split('CASES = [')[0])
EX = make_exit()
def cool(X, N, half=False):
    st = {"ref": 0, "until": -1, "n": 0}
    def f(eq):
        n = len(eq)
        if n < st["n"]: st.update(ref=0, until=-1)      # 새 모의(씨앗 · 반)가 시작됨
        st["n"] = n
        if n == 0: return None
        if n <= st["until"]: return 0.5 if half else True
        peak = max(eq[st["ref"]:]) if n > st["ref"] else eq[-1]
        if eq[-1] / peak - 1 <= -X / 100:
            st["until"] = n + N; st["ref"] = n + N - 1
            return 0.5 if half else True
        return None
    return f
def trim(mk):
    got = {}
    for s, (lo, hi) in (("앞", H.EARLY), ("뒤", H.LATE)):
        vals = {k: [] for k in (0, 3)}
        for seed in range(8):
            r = H._one_run(data, sigs, EX, size, lo, hi, 10, seed, None, rank, H.COST, None, None, stale90, None, None, mk() if mk else None)
            if not r: continue
            w = sorted((t["손익"] * t["칸"] / 10 for t in r["목록"]), reverse=True)
            for kk in vals: vals[kk].append(sum(w[kk:]) / 1.5)
        got[s] = {kk: round(float(np.median(v)), 1) if v else None for kk, v in vals.items()}
    return got
print("== 1시간봉 81회차 (계좌 브레이크: −X%면 N일 새 매수 멈춤) ==", flush=True)
cases = [("지금(브레이크 없음)", None)]
for X in (5, 7, 10):
    for N in (5, 10, 20):
        cases.append((f"−{X}%면 {N}일 멈춤", (lambda X=X, N=N: cool(X, N))))
for X, N in ((7, 10), (10, 10)):
    cases.append((f"−{X}%면 {N}일 칸 절반", (lambda X=X, N=N: cool(X, N, True))))
for tag, mk in cases:
    res = H.simulate(data, e_align_or_noon, EX, size, rank=rank, stale_of=stale90, seeds=16, brake=mk() if mk else None)
    tr = trim(mk)
    print(f"  {tag:20s} " + H.line(res), flush=True)
    print(f"      큰 매매 뺀 연: 앞 {tr['앞']} · 뒤 {tr['뒤']}", flush=True)
print("끝", flush=True)
