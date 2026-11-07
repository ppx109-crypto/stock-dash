"""MPOS-0021 합성 시험: A 갈래 국면 함수(두 국면 · 네 국면 · 늘 상승) · 목표 몫 · 경계 · 버팀 전환 · 앞 기간 고르기 가까운 동률. 성과 출력 없음. 출력: self_out.json."""
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.argv = [sys.argv[0]]
sys.path.insert(0, str(HERE))
import mpos21 as P  # noqa: E402

out = {"행": []}


def check(name, ok, **info):
    out["행"].append({"시험": name, "판정": "PASS" if ok else "FAIL", **info})


two = {"kind": "two", "n": 60}
check("두 국면 · 종가 < 60일선 = 하락", P.raw_state({"close": 99.0, "ma60": 100.0}, two) == "하락")
check("두 국면 · 종가 = 60일선 = 상승(밑으로 마감만 하락)", P.raw_state({"close": 100.0, "ma60": 100.0}, two) == "상승")
check("두 국면 · 종가 > 60일선 = 상승", P.raw_state({"close": 101.0, "ma60": 100.0}, two) == "상승")
check("두 국면 · 평균 모자람 = 하락(없음)", P.raw_state({"close": 101.0, "_k": 3}, two) == "하락")
check("늘 상승", P.raw_state({"close": 1.0}, {"kind": "always"}) == "상승")
s = 0.2 * math.sqrt(20 / 250)          # 20일 흔들림 연 20%
five = {"kind": "five", "zb": 1.0}
for z, want in ((1.001, "강상승"), (0.999, "약상승"), (0.0, "약상승"), (-0.001, "약하락"), (-0.999, "약하락"), (-1.001, "강하락")):
    got = P.raw_state({"close": 100 * (1 + z * s), "ma60": 100.0, "v20a": 0.2}, five)
    check(f"네 국면 · z {z:+.3f} → {want}", got == want, 얻음=got)
check("네 국면 · 흔들림 없음 = 강하락(없음)", P.raw_state({"close": 100.0, "ma60": 99.0}, five) == "강하락")
want = {"강상승": (1.0, "122630", 0.4), "약상승": (1.0, "122630", 0.2), "약하락": (1.0, "114800", 0.2), "강하락": (1.0, "114800", 0.0)}
check("네 국면 목표 몫", all(P.targets(k, {}) == v for k, v in want.items()))
cfg = dict(P.M.CFG, **P.ACELLS["A2_60"])
check("두 국면 목표: 상승 → 레버리지 0.4 · 하락 → 없음", P.targets("상승", cfg) == (1.0, "122630", 0.4) and P.targets("하락", cfg)[2] == 0.0)
check("A_OFF 목표 몫 0", all(P.targets(k, dict(P.M.CFG, **P.ACELLS["A_OFF"]))[2] == 0.0 for k in ("상승", "횡보", "하락")))
check("기본 국면(MIX-0054)은 원 함수 그대로", P.raw_state({"close": 99.0, "ma24": None, "_k": 0}, P.M.CFG) == P._RAW({"close": 99.0, "_k": 0}, P.M.CFG))
# 경계 정확값(band 직접 · GPT #450 3)
for z, want in ((1.0, "강상승"), (0.0, "약상승"), (-1.0, "약하락"), (-1.0000001, "강하락"), (0.9999999, "약상승")):
    check(f"네 국면 경계 z = {z} → {want}", P.band(z, 1.0) == want)
# 버팀 3 · 처음 상태(횡보) · 전환(Dv.states)
cfg5 = dict(P.M.CFG, **P.ACELLS["A5_100"])
seq = {f"2020010{i}": {"close": c, "ma60": 100.0, "v20a": 0.2} for i, c in enumerate([120, 120, 120, 101, 101, 120, 101, 101, 101], 1)}
st = P.Dv.states(seq, cfg5)
got = [st[d] for d in sorted(st)]
want = ["횡보", "횡보", "강상승", "강상승", "강상승", "강상승", "강상승", "강상승", "약상승"]
check("버팀 3: 처음 횡보 → 3일째 강상승 → 끊기면 유지 → 3일 이어져야 약상승", got == want, 얻음=got)
# 앞 기간 고르기 가까운 동률(GPT #450 1 반례): 앞손실 같음 · A2_60 앞 첫 달만 +1e-12 → A2_60
months = [f"{y}{m:02d}" for y in range(2017, 2027) for m in range(1, 13) if "201703" <= f"{y}{m:02d}" <= "202608"]
R = {c: {"달": {m: 0.0 for m in months}, "앞손실": 5, "뒤손실": 5} for c in P.CAND + ["BASE"]}
R["A2_60"]["달"]["201703"] += 1e-12
pick = P.front_pick(R)
check("앞 기간 고르기 · 가까운 동률이면 앞 반 연이 큰 칸(반올림 없음)", pick["A2"]["고른 칸"] == "A2_60" and P.front_annual(R["A2_60"]) > P.front_annual(R["A2_50"]),
      얻음=pick["A2"]["고른 칸"])
check("앞 기간 고르기 · 완전 동률이면 고정 순서 첫 칸", pick["A5"]["고른 칸"] == "A5_075" and pick["C"]["고른 칸"] == "C0")
json.dump(out, open(HERE / "self_out.json", "w"), ensure_ascii=False, indent=1)
print(sum(r["판정"] == "PASS" for r in out["행"]), "/", len(out["행"]))
sys.exit(0 if all(r["판정"] == "PASS" for r in out["행"]) else 3)
