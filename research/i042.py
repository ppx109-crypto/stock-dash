"""I 8라운드 — 하락장 이익 원천 찾기.
① 엔진(계좌 전부) 해마다 · 단계별 손익 + 코스피 내린 달만 따로(어느 해 · 어느 단계가 0으로 만드나)
② 돌리기 후보에 코스피200(069500) · 코스닥150(229200) 넣기(A · B · C)
③ 급락 되돌림 문턱 고원(5일 −4 · −5 · −6% × 익절 · 손절 2 · 3 · 4%) A · B · C
미래 참조: i040과 같음(그날 종가까지 · 주 끝 고름 · 하루 밀기)."""
import sys

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
import i040 as E          # 엔진 배열(불러올 때 i040 표가 찍힘)
import i011 as R
import itools as I

D = I.DAYS
kd = E.parts["코스피200 들고 있기"]
print("\n== ① 해마다 · 단계별(%, 엔진이 그날 쓴 단계에 손익을 나눔) · 괄호는 코스피 내린 달만 ==")
step = {"급락": np.where(E.dip_on, E.eng, 0.0), "달러": np.where(~E.dip_on & E.dol_on, E.eng, 0.0), "돌리기": np.where(~E.dip_on & ~E.dol_on, E.eng, 0.0)}
months = sorted(set(d[:6] for d in D if d >= "20120101"))
down = set()
for m in months:
    idx = np.array([d[:6] == m for d in D])
    if np.prod(1 + kd[idx]) - 1 < -0.02:
        down.add(m)
for y in range(2012, 2027):
    yi = np.array([d[:4] == str(y) for d in D])
    di = np.array([d[:6] in down and d[:4] == str(y) for d in D])
    cells = [f"{nm} {np.sum(v[yi]) * 100:+5.1f}({np.sum(v[di]) * 100:+5.1f})" for nm, v in step.items()]
    print(f"  {y} 코스피 {(np.prod(1 + kd[yi]) - 1) * 100:+6.1f} · 내린 달 {sum(1 for m in down if m[:4] == str(y))} | " + " · ".join(cells))

PER = (("A", "20120101", "20170101"), ("B", "20170101", "20210101"), ("C", "20210101", "20991231"))
for c in ("069500", "229200"):
    if c not in R.P:
        R.P[c] = I.px(c)
        p = R.P[c]
        R.R[c] = np.nan_to_num(np.concatenate([[0.0], p[1:] / p[:-1] - 1]))


def show(tag, x):
    cells = [I.stats(x, lo, hi) for _, lo, hi in PER]
    ok = all(c[0] > 0 and c[1] > -15 for c in cells)
    print(f"  {tag:30s} " + " | ".join(f"{p} {c[0]:+5.1f} · {c[1]:6.1f}" for (p, _, _), c in zip(PER, cells)) + ("  ✓" if ok else ""), flush=True)


print("\n== ② 돌리기 후보에 국내 지수 넣기(20일 · 위 2) ==")
for nm, cands in (("지금 넷", E.CANDS), ("+ 코스피200", E.CANDS + ["069500"]), ("+ 코스닥150", E.CANDS + ["229200"]), ("+ 둘 다", E.CANDS + ["069500", "229200"])):
    show(nm, R.run(R.G["언제나"], R.momentum(20, 2, cands)))

print("\n== ③ 급락 되돌림 문턱 고원(계좌 전부 · 20일 · 손절 뒤 20일 쉼) ==")
for th in (-0.04, -0.05, -0.06):
    for tk, st in ((0.02, -0.03), (0.03, -0.03), (0.04, -0.04), (0.03, -0.04), (0.04, -0.03)):
        sig = np.nan_to_num(I.ret(I.K200, 5), nan=0) <= th
        tr, dd = I.sim(sig, "069500", st, tk, 20, cool=20)
        show(f"5일 {th * 100:+.0f}% · 익 {tk * 100:.0f} · 손 {st * 100:.0f}", dd)

print("\n== ④ 달러 단계 다듬기 · ⑤ 돌리기가 아무것도 안 고른 날 단기채 ==")
nas = I.px("133690")
n20 = np.nan_to_num(nas / np.concatenate([np.full(20, np.nan), nas[:-20]]) - 1, nan=0)
base_c = (E.d20 > 0.02) & (np.nan_to_num(I.K200 < I.ma(I.K200, 20), nan=0) > 0)
bond = I.px("153130")
bret = np.nan_to_num(np.concatenate([[0.0], bond[1:] / bond[:-1] - 1]))


def engine(cond, cash=False):
    on = E.shift(cond) & ~E.dip_on
    t = np.abs(np.diff(np.concatenate([[0], on.astype(float)])))
    rot = E.rot
    if cash:          # 돌리기가 비운 날(손익 0이고 고른 것 없음 ≈ rot == 0) 단기채 — 그날 앞 판단만 씀(어제 비었으면 오늘 단기채)
        idle = np.concatenate([[False], (E.rot == 0)[:-1]])
        rot = np.where(idle, bret, rot)
    e = np.where(E.dip_on, E.dd, np.where(on, E.dret - 0, rot))
    e = np.where(on, E.dret, e) - t * E.COST / 2
    e = np.where(E.dip_on, E.dd, e)
    for a, b, _ in E.tr:
        e[a] += E.dd[a]
    return e


show("지금(원·달러 +2% · 코스피<20일선)", engine(base_c))
show("+ 나스닥 20일 < 0(세계 약세)", engine(base_c & (n20 < 0)))
show("+ 코스피 < 60일선", engine(base_c & (np.nan_to_num(I.K200 < I.ma(I.K200, 60), nan=0) > 0)))
show("지금 + 빈 날 단기채", engine(base_c, cash=True))
