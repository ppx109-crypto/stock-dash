"""front_pick 합성 시험: 앞 반 연으로 고르기 · 같으면 고정 순서 · 앞손실 먼저 · 뒤 반 값은 안 씀."""
import sys
sys.path.insert(0, "/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/mpos20")
import mpos20 as P
months = [f"{y}{m:02d}" for y in range(2017, 2027) for m in range(1, 13) if "201703" <= f"{y}{m:02d}" <= "202608"]
assert len(months) == 114
def cell(front_ret, fl, bl, back_ret=0.0):
    return {"달": {m: (front_ret if m <= "202112" else back_ret) for m in months}, "앞손실": fl, "뒤손실": bl}
R = {"IMM": cell(0.01, 20, 20)}
# 앞손실 같음(10) → 앞 반 연 큰 NP7 · CH40. 뒤 반 값은 일부러 반대로(NP3 뒤 반이 가장 좋음) → 안 써야 함
R.update(NP3=cell(0.01, 10, 0, 0.5), NP5=cell(0.02, 10, 30), NP7=cell(0.03, 10, 30), NP10=cell(0.025, 10, 30),
         CH10=cell(0.01, 10, 0, 0.5), CH20=cell(0.02, 10, 30), CH40=cell(0.04, 10, 30))
o = P.front_pick(R); assert o["NP"]["고른 칸"] == "NP7" and o["CH"]["고른 칸"] == "CH40", o
# 완전 같음 → 고정 순서 첫 칸
for c in P.CAND: R[c] = cell(0.02, 10, 10)
o = P.front_pick(R); assert o["NP"]["고른 칸"] == "NP3" and o["CH"]["고른 칸"] == "CH10", o
# 앞손실이 먼저: NP5 앞손실 9(연 낮음) > NP7 앞손실 10(연 높음)
R["NP5"] = cell(0.001, 9, 30); R["NP7"] = cell(0.05, 10, 0)
o = P.front_pick(R); assert o["NP"]["고른 칸"] == "NP5", o
# 앞 반 연 셈 값: 달 2% × 58달 → (1.02^58)^(12/58) − 1 = 1.02^12 − 1
assert abs(P.front_annual(cell(0.02, 0, 0)) - (1.02 ** 12 - 1) * 100) < 1e-9
print("front_pick 합성 시험 통과")
# mech_report: 원판 진입 A(판 05) · B(판 07) / 칸: A 판 03(앞당김) · 같은 날 A 재진입(03 산 · 06 판) · B 없음
base = [("A", "01", "05", 1.0, 0.5), ("A", "01", "04", 1.0, 0.5), ("B", "02", "07", 1.0, 1)]
led = {"IMM": base, **{c: base for c in P.CAND}}
led["NP3"] = [("A", "01", "03", -1.0, 1), ("A", "03", "06", 1.0, 1)]
m = P.mech_report(led)["NP3"]
assert m == {"진입": 2, "원판과 같은 진입": 1, "그중 판 날 앞당김": 1, "새 진입": 1, "원판에만 있는 진입": 1, "판 날 같은 날 같은 종목 재진입": 1}, m
assert P.mech_report(led)["NP5"]["그중 판 날 앞당김"] == 0
print("기전 진단 합성 시험 통과")
