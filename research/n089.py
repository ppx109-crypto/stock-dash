"""일봉 새 89회차(G5 · 1일봉 — 추세 문 숫자는 일봉 표로 미리 구워 1시간봉 · 15분봉에선 바꾸기 무거움 → 1일봉 9년으로 봄).
기준 = 새 82회차(기울기 1.46 · 60일 20%). Q_PART=1: 기울기 1.16 · 1.76 / Q_PART=2: 60일 15 · 25%. 씨앗 8."""
import os
import sys
sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import ntools as T
import rule

part = os.environ.get("Q_PART", "1")
print(f"== 일봉 새 89회차({part}): 추세 문 숫자 ==", flush=True)
T.once("기준(기울기 1.46 · 60일 20%)")
keep = (rule.SLOPE, rule.SIXTY)
for name, val in ((("SLOPE", 1.16), ("SLOPE", 1.76)) if part == "1" else (("SIXTY", 15.0), ("SIXTY", 25.0))):
    setattr(rule, name, val)
    T.once(f"{'기울기' if name == 'SLOPE' else '60일'} {val:g}")
    rule.SLOPE, rule.SIXTY = keep
print("끝", flush=True)
