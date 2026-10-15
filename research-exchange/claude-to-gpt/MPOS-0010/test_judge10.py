"""판정 함수 경계 합성 시험(MPOS-0010): gt · mechanism · judge 관문이 0 · 양수 · 음수 · 결측을 구분하는지 · 추정 비용 뒤 관문."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mpos10 as M  # noqa: E402


def T(net, front=0.1, back=0.1, year=0.3):
    return {"전체": {"추정비용뒤": net}, "앞반": {"추정비용뒤": front, "추정비용뒤_2배금액": front}, "뒤반": {"추정비용뒤": back, "추정비용뒤_2배금액": back}, "한해몰림": year}


def mech(c, tot, nop, lc=39, lt=40, ln=40):
    return M.mechanism({M.CENTER: {"손실": lc}, "AB_TOTAL": {"손실": lt}, "AB_NOPULL": {"손실": ln}},
                       {M.CENTER: T(c), "AB_TOTAL": T(tot), "AB_NOPULL": T(nop)})["지지"]


def run():
    ok = []
    g = M.gt
    ok += [("gt 0 > −0.1", g(0.0, -0.1) is True), ("gt 0 > 0 거짓", g(0.0, 0.0) is False), ("gt None · nan 거짓", not g(None, 1) and not g(1, None) and not g(math.nan, -1))]
    ok += [("반례: 중심 −0.10 · TOTAL 0 · NOPULL −0.2 → 미지지", mech(-0.10, 0.0, -0.2) is False), ("중심 0 · 대조 음수 → 지지", mech(0.0, -0.1, -0.2) is True),
           ("대조 결측 → 미지지", mech(0.3, None, -0.2) is False), ("손실 달 많음 → 미지지", mech(0.3, 0.1, 0.1, lc=41) is False)]
    base = {"최악날": -5.0, "최악달": -5.0, "앞손실": 10, "뒤손실": 10, "손실": 20, "MDD": -10.0, "연_거래일": 40.0}
    R = {"P0": dict(base, 손실=40, 앞손실=20, 뒤손실=20)}
    for c in M.ALL:
        R[c] = dict(base)
    Ts = {c: T(0.2) for c in M.ALL}
    ok.append(("judge: 모두 통과 6칸", len(M.judge(R, Ts, {"지지": True})[1]) == 6))
    Ts[M.CENTER] = T(0.2, front=0.0)
    ok.append(("judge: 앞 반 추정 비용 뒤 0 → 탈락", M.CENTER not in M.judge(R, Ts, {"지지": True})[1]))
    Ts[M.CENTER] = T(0.2, year=None)
    ok.append(("judge: 한 해 몰림 결측 → 탈락", M.CENTER not in M.judge(R, Ts, {"지지": True})[1]))
    ok.append(("judge: 기전 미지지 → 모두 탈락", M.judge(R, {c: T(0.2) for c in M.ALL}, {"지지": False})[1] == []))
    R2 = dict(R)
    R2["RM_K1.0_H10"] = dict(base, 손실=41)
    ok.append(("judge: 이웃 하나 ③ 실패 → 그 이웃의 이웃 탈락", "RM_K1.0_H20" not in M.judge(R2, {c: T(0.2) for c in M.ALL}, {"지지": True})[1]))
    R3 = dict(R)
    R3[M.CENTER] = dict(base, 최악달=-6.0)
    R3["P0"] = dict(R["P0"], 최악달=-5.5)
    ok.append(("judge: 최악 달이 P0보다 나쁨 → 탈락(⑥깊이)", M.CENTER not in M.judge(R3, {c: T(0.2) for c in M.ALL}, {"지지": True})[1]))
    Ts = {c: T(0.2) for c in M.ALL}
    Ts[M.CENTER] = dict(T(0.2), 앞반={"추정비용뒤": 0.2, "추정비용뒤_2배금액": -0.01})
    ok.append(("judge: 기준 금액은 + 이지만 2배 금액에서 − → 탈락", M.CENTER not in M.judge(R, Ts, {"지지": True})[1]))
    for n, v in ok:
        print("PASS" if v else "FAIL", n)
    return all(v for _, v in ok)


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
