"""KMF-0012 합성 시험(손익 셈 없음 · 시험 10만 합성 하루 손익 셈)."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "research"))
import kmf12 as M  # noqa: E402
import kmf as K  # noqa: E402
ok = 0


def chk(name, cond):
    global ok
    if not cond:
        print("실패:", name); sys.exit(1)
    ok += 1; print("통과:", name)


def day(d, prices, start=540):
    return [(d, start + i, p, p + 0.1, p - 0.1, p, 1) for i, p in enumerate(prices)]


def sig(prices, tag, d="20260105"):
    return M.signals(M.prep(day(d, prices)), {c["tag"]: c for c in M.grid()}[tag])


base = [100.0 + (10 if i == 5 else -10 if i == 6 else 0) for i in range(30)]   # 범위 89.9 ~ 110.1 · 폭 20.2 · R 자리 105.05 / 94.95
p1 = base + [116.0] * 5 + [104.0] * 5 + [98.0] * 5 + [88.0] * 5 + [100.0] * 341   # 돌파(거래 멈춤까지 10.95) → 104 종가 → 극값 116.1까지 12.1
w = sig(p1, "N30_b0.25_S20")
chk("1 S20: 돌파에 삼 → 거래 멈춤에 덫으로 팖(12.1 ≤ 20) → 범위 안에서는 들고 있음 → 아래끝 닿으면 정리",
    w[6] == 1 and w[7] == -1 and w[8] is None and w[9] == 0 and all(x is None for x in w[10:]))
w = sig(p1, "N30_b0.25_S12")
chk("2 S12: 돌파에 삼(10.95 ≤ 12) → 거래 멈춤에 정리만(12.1 > 12)", w[6] == 1 and w[7] == 0 and all(x is None for x in w[8:]))
p3 = base + [122.0] * 5 + [100.0] * 356                                         # b 0.5 돌파(120.2 넘음) · 거리 16.95
chk("3 b0.5 · S12: 거리 16.95 > 12면 안 들고 그날 쉼", all(x is None for x in sig(p3, "N30_b0.5_S12")))
chk("4 b0.5 · S20: 거리 16.95 ≤ 20이면 듦", sig(p3, "N30_b0.5_S20")[6] == 1)
p5 = base + [116.0] * 5 + [104.0] * 5 + [118.0] * 5 + [100.0] * 346
w = sig(p5, "N30_b0.25_S20")
chk("5 덫 거래 멈춤: 극값 넘는 종가에 정리", w[6] == 1 and w[7] == -1 and w[8] == 0 and all(x is None for x in w[9:]))
p6 = base + [84.0] * 5 + [96.0] * 5 + [112.0] * 5 + [100.0] * 346
w = sig(p6, "N30_b0.25_S20")
chk("6 아래쪽 대칭", w[6] == -1 and w[7] == 1 and w[8] == 0)
late = base + [100.0] * 335 + [116.0] * 26
chk("7 15:00 판단 뒤에는 새로 안 듦", all(x is None for x in sig(late, "N30_b0.25_S20")))
chk("8 격자 8칸 · S 12 · 20", len(M.grid()) == 8 and len({M.name(c) for c in M.grid()}) == 8 and {c["S"] for c in M.grid()} == {12, 20})
chk("9 잠금 통과", bool(M.verify_inputs()))
rows = day("20260105", [100.0] * 10 + [100.0 - i for i in range(1, 40)] + [60.0] * 346)    # 09:05 판단에 삼 → 계속 떨어짐
want = [None] * len(rows); want[5] = 1
days, tr = K.simulate(rows, want)
chk("10 하루 멈춤이 −25p(−12p 아님 · 봉 사이 틈 미끄러짐 0.5p 안)", K.DAY_STOP == -25.0 and -25.5 <= days["20260105"] <= -25.0 and len(tr) == 1)
print(f"모두 통과 {ok}개")
