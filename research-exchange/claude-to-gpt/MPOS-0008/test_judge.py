"""판정 함수 경계 합성 시험(GPT #421 round 2): gt · mechanism · judge의 G2 관문이 0 · 양수 · 음수 · 결측(None · nan)을 구분하는지.
python3 test_judge.py"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mpos8 as M  # noqa: E402


def T(stress, front=0.1, back=0.1, year=0.3):
    return {"전체": {"스트레스평균": stress}, "앞반": {"스트레스평균": front}, "뒤반": {"스트레스평균": back}, "한해몰림": year}


def R(loss):
    return {"손실": loss}


def mech(c, raw, noconf, lc=39, lr=40, ln=40):
    return M.mechanism({M.CENTER: R(lc), "AB_RAW": R(lr), "AB_NOCONF": R(ln)},
                       {M.CENTER: T(c), "AB_RAW": T(raw), "AB_NOCONF": T(noconf)})["지지"]


def run():
    ok = []
    g = M.gt
    ok.append(("gt 0 > −0.1", g(0.0, -0.1) is True))
    ok.append(("gt −0.1 > 0 거짓", g(-0.1, 0.0) is False))
    ok.append(("gt 0 > 0 거짓", g(0.0, 0.0) is False))
    ok.append(("gt None 거짓", g(None, -5.0) is False and g(5.0, None) is False))
    ok.append(("gt nan 거짓", g(math.nan, -5.0) is False and g(5.0, math.nan) is False))
    ok.append(("GPT 반례: 중심 −0.10 · RAW 0.00 · NOCONF −0.20 → 미지지", mech(-0.10, 0.0, -0.20) is False))
    ok.append(("중심 0 · 대조 음수 → 지지", mech(0.0, -0.1, -0.2) is True))
    ok.append(("중심 양수 · 대조 결측 → 미지지", mech(0.3, None, -0.2) is False))
    ok.append(("중심 결측 → 미지지", mech(None, -0.1, -0.2) is False))
    ok.append(("손실 달 더 많으면 미지지", mech(0.3, 0.1, 0.1, lc=41) is False))
    ok.append(("손실 달 같고 스트레스 큼 → 지지", mech(0.3, 0.1, 0.1, lc=40) is True))
    # judge의 G2 관문: 앞 · 뒤 반 스트레스 0이면 탈락(> 0 이어야)
    base = {"최악날": -5.0, "최악달": -5.0, "앞손실": 10, "뒤손실": 10, "손실": 20, "MDD": -10.0, "연_거래일": 40.0}
    Rr = {"P0": dict(base, 손실=40, 앞손실=20, 뒤손실=20)}
    for c in M.ALL:
        Rr[c] = dict(base)
    Tt = {c: T(0.2) for c in M.ALL}
    yes = {"지지": True}
    _, rank, _ = M.judge(Rr, Tt, yes)
    ok.append(("judge: 모두 통과 칸 7", len(rank) == 7))
    Tt[M.CENTER] = T(0.2, front=0.0)
    _, rank2, why = M.judge(Rr, Tt, yes)
    ok.append(("judge: 앞 반 스트레스 0 → 그 칸 탈락", M.CENTER not in rank2 and why[M.CENTER]["G2 관문"] is False))
    Tt[M.CENTER] = T(0.2, year=None)
    _, rank3, _ = M.judge(Rr, Tt, yes)
    ok.append(("judge: 한 해 몰림 결측 → 탈락", M.CENTER not in rank3))
    _, rank4, _ = M.judge(Rr, {c: T(0.2) for c in M.ALL}, {"지지": False})
    ok.append(("judge: 기전 미지지 → G2 모두 탈락 · G1만", rank4 == ["G1_2N"]))
    for n, v in ok:
        print("PASS" if v else "FAIL", n)
    return all(v for _, v in ok)


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
