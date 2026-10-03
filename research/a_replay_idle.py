"""점검 A11: 운영 코드(idle_live.step)를 지난날(2024 ~)로 날마다 다시 돌려 연구 i013 dump와 보유 날 · 인버스 매매를 맞춤. 인자: i013 I_DUMP 파일."""
import sys, numpy as np
sys.path.insert(0, "/home/user/stock-dash"); sys.path.insert(0, "/home/user/stock-dash/research")
import itools as I, idle_live as L
z = np.load(sys.argv[1]); D = list(z["days"]); n = len(D)
br = I.breadth(); used = z["used"]
px_all = {c: I.px(c) for c in L.CODES}
state = {}; hold = {k: np.zeros(n, bool) for k in ("급락", "달러", "돌리기", "인버스")}
start = D.index(next(d for d in D if d >= "20240102"))
for i in range(start, n - 1):
    d = D[i]
    px = {c: px_all[c][:i + 1][np.isfinite(px_all[c][:i + 1])] for c in L.CODES}
    now = {c: float(px_all[c][i]) for c in L.CODES if np.isfinite(px_all[c][i])}
    held = {c: 1000 for c in state.get("positions", {})}
    prev_used = float(used[i - 1])
    orders, state, why = L.step(state, d, px, breadth=float(np.nan_to_num(br[i], nan=100)), used=prev_used,
                                total=1e9, cash=1e9 * (1 - prev_used), held=held, now_price=now, is_week_end=L.week_end(d))
    for c, p in state["positions"].items():
        hold[p["kind"]][i + 1] = True        # 날 i 종가에 들고 있음 → 연구에선 i + 1 수익
res = {"급락": z["dip"], "인버스": z["qinv"]}
rot = z["rot"]
m = np.zeros(n, bool); m[start + 1:] = True
for k, arr in res.items():
    on = (np.abs(arr) > 1e-12) & m
    print(f"  {k}: 연구 든 날 {on.sum()} · 운영 다시 돌림 든 날 {(hold[k] & m).sum()} · 함께 {(on & hold[k]).sum()} · 연구만 {(on & ~hold[k]).sum()} · 운영만 {(hold[k] & ~on & m).sum()}")
eng = (hold["달러"] | hold["돌리기"]) & m
ron = (np.abs(rot) > 1e-12) & m
print(f"  달러 · 돌리기: 연구 든 날 {ron.sum()} · 운영 {eng.sum()} · 함께 {(ron & eng).sum()} · 연구만 {(ron & ~eng).sum()} · 운영만 {(eng & ~ron).sum()}")
# 매매 목록 견주기(인버스)
qq = px_all["229200"]
qsig = np.nan_to_num(I.ret(qq, 10), nan=0) >= 0.095
sq = np.clip(I.sigma_n(qq, 60) * 0.25 * np.sqrt(10), 0.015, 0.025)
qtr, _ = I.sim_var(qsig, "251340", -np.full(n, 0.015), sq, 10)
rt = [(D[a], D[b]) for a, b, _ in qtr if D[a] >= "20240102"]
# 운영: hold 배열에서 구간
h = hold["인버스"]; lt = []; i = 0
while i < n:
    if h[i]:
        j = i
        while j + 1 < n and h[j + 1]: j += 1
        lt.append((D[i - 1], D[j])); i = j + 1
    else: i += 1
print("  연구 인버스 매매:", rt)
print("  운영 인버스 매매:", lt)
free = np.clip(1 - used, 0, 1)
rt2 = [(D[a], D[b], round(float(free[a]), 2), round(float(1 - used[a - 1]), 2)) for a, b, _ in qtr if D[a] >= "20240102"]
lt_set = {a for a, b in lt}
print("  연구 매매(산 날 · 판 날 · 그날 빈 몫 · 어제 빈 몫) 중 운영에 없는 것:", [x for x in rt2 if x[0] not in lt_set])
