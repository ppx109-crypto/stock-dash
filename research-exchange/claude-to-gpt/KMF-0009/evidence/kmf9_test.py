"""KMF-0009 합성 시험(손익 셈 없음)."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "research"))
import kmf9 as K9  # noqa: E402
ok = 0


def chk(name, cond):
    global ok
    if not cond:
        print("실패:", name); sys.exit(1)
    ok += 1; print("통과:", name)


def day(d, prices, start=540):
    return [(d, start + i, p, p + 0.1, p - 0.1, p, 1) for i, p in enumerate(prices)]


g = {c["tag"]: c for c in K9.grid()}
base = [100.0 + (5 if i == 5 else -5 if i == 6 else 0) for i in range(30)]          # 범위 94.9 ~ 105.1 · 폭 10.2 · 가운데 100
# 1 횡보: 위끝 쪽(z 0.15 → 103.57 ~ 105.1)에서 팖 → 가운데(100) 닿으면 정리
p = base + [104.0] * 5 + [102.0] * 5 + [99.0] * 351
w = K9.signals(K9.prep(day("20260105", p)), g["N30_z0.15_b0.25"])
chk("1 위끝 쪽에서 팖 · 가운데에서 정리", w[6] == -1 and w[8] == 0)
# 2 뒤집기: 되돌림으로 판 뒤 범위 위로 b 0.25 × 폭(2.55) 넘게(107.65 넘음) 나가면 삼으로 뒤집고 장 끝까지
p2 = base + [104.0] * 5 + [108.0] * 356
w = K9.signals(K9.prep(day("20260106", p2)), g["N30_z0.15_b0.25"])
chk("2 판 뒤 범위 위로 크게 뚫리면 삼으로 뒤집음 · 그 뒤 신호 없음(장 끝까지)", w[6] == -1 and w[7] == 1 and all(x is None for x in w[8:]))
# 3 추세 든 뒤 되돌림 다시 안 켬
p3 = base + [108.0] * 10 + [104.0] * 351
w = K9.signals(K9.prep(day("20260107", p3)), g["N30_z0.15_b0.25"])
chk("3 추세 든 뒤 되돌림 끔", w[6] == 1 and all(x is None for x in w[7:]))
# 4 b 0.5는 107.65로는 안 뒤집음(110.2 넘어야)
w = K9.signals(K9.prep(day("20260108", p2)), g["N30_z0.15_b0.5"])
chk("4 b 0.5는 더 크게 뚫려야 뒤집음", w[6] == -1 and 1 not in w)
chk("5 격자 8칸 · 이름 겹침 없음", len(K9.grid()) == 8 and len({K9.name(c) for c in K9.grid()}) == 8)
chk("6 잠금 통과", bool(K9.verify_inputs()))
print(f"모두 통과 {ok}개")
