"""KMF-0011 합성 시험(손익 셈 없음)."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "research"))
import kmf11 as M  # noqa: E402
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


base = [100.0 + (5 if i == 5 else -5 if i == 6 else 0) for i in range(30)]   # 범위 94.9 ~ 105.1 · 폭 10.2 · R 자리 102.55 / 97.45
p1 = base + [108.0] * 5 + [102.0] * 5 + [99.0] * 5 + [94.0] * 5 + [100.0] * 341          # 돌파(거래 멈춤까지 5.45) → 102 종가(멈춤) → 극값 108.1까지 6.1
w = sig(p1, "N30_b0.25_S10")
chk("1 S10: 돌파에 삼 → 거래 멈춤에 덫으로 팖(6.1 ≤ 10) → 범위 안(99)에서는 들고 있음 → 아래끝 닿으면 정리", w[6] == 1 and w[7] == -1 and w[8] is None and w[9] == 0 and all(x is None for x in w[10:]))
w = sig(p1, "N30_b0.25_S6")
chk("2 S6: 돌파에 삼(5.45 ≤ 6) → 거래 멈춤에 정리만(6.1 > 6이라 덫 안 듦)", w[6] == 1 and w[7] == 0 and all(x is None for x in w[8:]))
p3 = base + [111.0] * 5 + [100.0] * 356                                        # b 0.5 돌파(110.2 넘음) · 거래 멈춤까지 8.45
chk("3 b0.5 · S6: 거리 8.45 > 6이면 안 들고 그날 쉼", all(x is None for x in sig(p3, "N30_b0.5_S6")))
chk("4 b0.5 · S10: 거리 8.45 ≤ 10이면 듦", sig(p3, "N30_b0.5_S10")[6] == 1)
p5 = base + [108.0] * 5 + [102.0] * 5 + [109.0] * 5 + [100.0] * 346          # 덫 뒤 극값(108.1) 넘는 종가 → 덫 거래 멈춤
w = sig(p5, "N30_b0.25_S10")
chk("5 덫 거래 멈춤: 극값 넘는 종가에 정리", w[6] == 1 and w[7] == -1 and w[8] == 0 and all(x is None for x in w[9:]))
p6 = base + [92.0] * 5 + [98.0] * 5 + [106.0] * 5 + [100.0] * 346           # 아래 돌파 → 97.45 위 종가 → 덫 삼 → 위끝 닿으면 정리
w = sig(p6, "N30_b0.25_S10")
chk("6 아래쪽 대칭", w[6] == -1 and w[7] == 1 and w[8] == 0)
late = base + [100.0] * 335 + [108.0] * 26
chk("7 15:00 판단 뒤에는 새로 안 듦", all(x is None for x in sig(late, "N30_b0.25_S10")))
chk("8 격자 8칸 · 이름 겹침 없음", len(M.grid()) == 8 and len({M.name(c) for c in M.grid()}) == 8)
chk("9 잠금 통과", bool(M.verify_inputs()))
print(f"모두 통과 {ok}개")
