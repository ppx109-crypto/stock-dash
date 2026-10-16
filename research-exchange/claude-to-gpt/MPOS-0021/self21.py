"""MPOS-0021 합성 시험: A 갈래 국면 함수(두 국면 · 다섯 국면 · 늘 상승)와 목표 몫 경계. 성과 출력 없음. 출력: self_out.json."""
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
    check(f"다섯 국면 · z {z:+.3f} → {want}", got == want, 얻음=got)
check("다섯 국면 · 흔들림 없음 = 강하락(없음)", P.raw_state({"close": 100.0, "ma60": 99.0}, five) == "강하락")
want = {"강상승": (1.0, "122630", 0.4), "약상승": (1.0, "122630", 0.2), "약하락": (1.0, "114800", 0.2), "강하락": (1.0, "114800", 0.0)}
check("다섯 국면 목표 몫", all(P.targets(k, {}) == v for k, v in want.items()))
cfg = dict(P.M.CFG, **P.ACELLS["A2_60"])
check("두 국면 목표: 상승 → 레버리지 0.4 · 하락 → 없음", P.targets("상승", cfg) == (1.0, "122630", 0.4) and P.targets("하락", cfg)[2] == 0.0)
check("A_OFF 목표 몫 0", all(P.targets(k, dict(P.M.CFG, **P.ACELLS["A_OFF"]))[2] == 0.0 for k in ("상승", "횡보", "하락")))
check("기본 국면(MIX-0054)은 원 함수 그대로", P.raw_state({"close": 99.0, "ma24": None, "_k": 0}, P.M.CFG) == P._RAW({"close": 99.0, "_k": 0}, P.M.CFG))
json.dump(out, open(HERE / "self_out.json", "w"), ensure_ascii=False, indent=1)
print(sum(r["판정"] == "PASS" for r in out["행"]), "/", len(out["행"]))
sys.exit(0 if all(r["판정"] == "PASS" for r in out["행"]) else 3)
