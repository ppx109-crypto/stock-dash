"""BULL-OOS-0040 합성 시험 — 실제 수익 셈 없음."""
import importlib.util, random, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location("t010", Path(__file__).resolve().parents[4] / "research/t010.py")
t = importlib.util.module_from_spec(spec); spec.loader.exec_module(t)
fails = []
def ok(c, m):
    print(("통과 " if c else "실패 ") + m)
    if not c: fails.append(m)
ok(abs(t.side(10000, t.MAIN) - (0.00015 + 0.0005)) < 1e-12, "편도 비용 1만 원 = 0.065%")
days = [f"D{i:05d}" for i in range(600)]
rng = random.Random(3); px, v = {}, 10000.0
for d in days:
    v *= 1 + rng.gauss(0.0003, 0.012); px[d] = round(v / 5) * 5
on = t.signal(days, px)
ok(min(on) == days[199], "신호는 200번째 날부터")
part = t.signal(days[:400], {d: px[d] for d in days[:400]})
ok(all(on[d] == part[d] for d in part), "신호 자르기: 앞 400일 같음")
flat = {d: 10000.0 for d in days}
on2 = {d: (300 <= i < 310) for i, d in enumerate(days)}
nav, wins = t.account(days, flat, flat, on2, t.MAIN, "zero")
nv = dict(nav)
ok(nv[days[300]] == 1.0, "켜진 그날 종가에는 안 삼")
ok(abs(nv[days[301]] - (1 - 0.5 * 0.00065)) < 1e-12, "다음 날 종가에 계좌 50% 사며 비용만큼 줄어듦")
ok(abs(nv[days[311]] - (0.5 + 0.5 * (1 - 0.00065) ** 2)) < 1e-12, "꺼진 다음 날 종가에 다 팖(손셈 같음)")
ok(wins == [(days[301], days[311])], "창 산 날 · 판 날")
up = dict(flat)
for d in days[305:]: up[d] = 11000.0
nav, _ = t.account(days, up, up, on2, t.MAIN, "adj")
n = dict(nav)
ok(abs(n[days[305]] / n[days[304]] - 1 - (0.5 * (1 - 0.00065) * 0.1) / n[days[304]]) < 1e-12, "10% 오른 날 = 든 몫 × 10%")
nav, _ = t.account(days, up, up, on2, t.MAIN, "adj", gate=False)
ok(abs(dict(nav)[days[0]] - (1 - 0.5 * 0.00065)) < 1e-12, "대조(늘 50%)는 첫날 삼")
# round 2: H2는 이어받음 — H2 첫날 수익의 기준은 H1 마지막 날 계좌
navx = [("20091229", 1.0), ("20091230", 1.2), ("20100104", 1.32)]
rep, raw, rets = t.risk(navx, "20100104", "20161230")
ok(abs(rets[0][1] - 0.1) < 1e-12, "H2 첫날 수익 = 2009-12-30 계좌 대비(재시작 아님)")
# round 2: 자르기 신호 완전 비교 — 누락 · 추가 · 값 변경 각각 실패
base_sig = [["20091228", True], ["20091229", False], ["20091230", True], ["20100104", True]]
full = {"H1": {"a": 1}, "signals": base_sig}
cut = {"H1": {"a": 1}, "signals": base_sig[:3]}
bad, sig = t.cut_same(full, cut); ok(not bad and sig, "같으면 통과(컷 뒤 신호는 비교 밖)")
bad, sig = t.cut_same(full, {"H1": {"a": 1}, "signals": base_sig[1:3]}); ok(not sig, "컷 쪽 신호 한 칸 누락 → 실패")
bad, sig = t.cut_same(full, {"H1": {"a": 1}, "signals": [["20091227", True]] + base_sig[:3]}); ok(not sig, "컷 쪽 신호 한 칸 추가 → 실패")
bad, sig = t.cut_same(full, {"H1": {"a": 1}, "signals": [["20091228", False]] + base_sig[1:3]}); ok(not sig, "컷 쪽 신호 값 하나 바뀜 → 실패")
bad, sig = t.cut_same(full, {"H1": {"a": 2}, "signals": base_sig[:3]}); ok(bad == ["H1"], "H1 결과 다르면 실패")
print(f"합계: 실패 {len(fails)}"); sys.exit(1 if fails else 0)
