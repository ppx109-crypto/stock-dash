"""일봉 새 78회차 — 거래량 폭발 + 급등이 겹친 날(과열 꼭대기)에 들고 있는 매매를 파는가(파는 쪽에 거래량을 쓴 첫 시험).

그날 거래량비(그날 거래량 ÷ 앞 20일 가운데값, lab.volume_line · dguard 검사 통과)와 그날 종가 오름폭 · 산 값 대비 손익으로 그날 종가에 팜.
바뀐 매매 손익을 직접 봄.
실행: NRL_CACHE=... python3 research/n078.py
"""
import sys

sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import lab
import ntools as T
import nrl

VR = {}


def vr(lane, spot):
    code = lane["code"]
    if code not in VR:
        VR[code] = lab.volume_line(code, lane["날"])
    return VR[code][spot] if spot < len(VR[code]) else None


def climax(vmin, day_up, gain_min, part):
    """과열 날: 거래량비 ≥ vmin · 그날 오름 ≥ day_up% · 산 값 대비 ≥ gain_min% → part('all' 또는 절반)."""
    def check(lane, start, price, step, peak, row=None):
        spot = start + step
        c = lane["closes"]
        v = vr(lane, spot)
        up = (c[spot] / c[spot - 1] - 1) * 100 if spot > 0 else 0
        gain = (c[spot] / price - 1) * 100
        return v is not None and v >= vmin and up >= day_up and gain >= gain_min
    return check


def with_climax(which, check, half):
    def wrap(base):
        def go(lane, start, price, step, peak, row=None):
            got = base(lane, start, price, step, peak, row)
            if got:
                return got
            if check(lane, start, price, step, peak, row):
                return max(1, nrl.BASE_SIZE(row) // 2) if half else True
            return False
        return go
    rule_exit = wrap(nrl.RULE_EXIT) if which in ("둘", "추세") else nrl.RULE_EXIT
    line_exit = wrap(nrl.broken) if which in ("둘", "정배열") else nrl.broken
    return lab.exit_per_tier(nrl.tier, {"규칙": rule_exit, "정배열": line_exit})


print("== 일봉 새 78회차: 과열 꼭대기(거래량 폭발 + 급등)에 팔기 ==", flush=True)
base = T.once("지금 규칙(기준)")
for which in ("정배열", "둘"):
    for vmin, up, gmin in ((3.0, 5, 10), (3.0, 8, 15), (4.0, 5, 10), (5.0, 8, 20)):
        for half in (True, False):
            got = T.once(f"{which}: 거래량 {vmin}배 · 그날 +{up}% · 손익 +{gmin}%↑ → {'절반' if half else '전부'}",
                         exit_at=with_climax(which, climax(vmin, up, gmin, None), half))
            if which == "정배열" and vmin == 3.0 and up == 5 and half:
                T.diff_check(base, got)
print("끝", flush=True)
