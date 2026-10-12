"""KMF-0008 합성 시험(손익 셈 없음)."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "research"))
import kmf8 as K8  # noqa: E402
ok = 0


def chk(name, cond):
    global ok
    if not cond:
        print("실패:", name); sys.exit(1)
    ok += 1; print("통과:", name)


def day(d, prices, start=540, wide=0.1):
    return [(d, start + i, p, p + wide, p - wide, p, 1) for i, p in enumerate(prices)]


g = {c["tag"]: c for c in K8.grid()}
# 범위 첫 30분: 99 ~ 101(폭 2.2 · 고저 ±0.1 포함) → 5분봉 종가 101.5에서 삼 → 목표 k0.5 = 범위 위끝 101.1 + 1.1 = 102.2 넘으면 정리
p = [100.0 + (1 if i == 5 else -1 if i == 6 else 0) for i in range(30)] + [101.5] * 5 + [101.6] * 5 + [102.5] * 5 + [102.5] * 346
w = K8.signals(K8.prep(day("20260105", p)), g["N30_k0.5_H120"])
chk("1 5분봉 종가로 범위 위 돌파에 삼(6번째 봉)", w[6] == 1 and all(x is None for x in w[:6]))
chk("1b 목표(0.5 × 폭) 넘은 봉에 정리", w[8] == 0)
# 2 되돌림 멈춤: 범위 가운데(100) 아래로 마감하면 정리
p2 = [100.0 + (1 if i == 5 else -1 if i == 6 else 0) for i in range(30)] + [101.5] * 5 + [99.5] * 356
w = K8.signals(K8.prep(day("20260106", p2)), g["N30_k1.0_H120"])
chk("2 범위 가운데 넘어 되돌아오면 정리", w[6] == 1 and w[7] == 0)
# 3 시간 멈춤: 60분 지나면 정리
p3 = [100.0 + (1 if i == 5 else -1 if i == 6 else 0) for i in range(30)] + [101.5] * 361
w = K8.signals(K8.prep(day("20260107", p3)), g["N30_k1.0_H60"])
chk("3 든 뒤 60분 지난 봉에 정리", w[6] == 1 and w[18] == 0 and all(x is None for x in w[7:18]))
chk("4 격자 8칸 · 이름 겹침 없음", len(K8.grid()) == 8 and len({K8.name(c) for c in K8.grid()}) == 8)
chk("5 잠금 통과", bool(K8.verify_inputs()))
print(f"모두 통과 {ok}개")
