"""KMF-0010 합성 시험(손익 셈 없음)."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "research"))
import kmf10 as M  # noqa: E402
ok = 0


def chk(name, cond):
    global ok
    if not cond:
        print("실패:", name); sys.exit(1)
    ok += 1; print("통과:", name)


def day(d, prices, start=540):
    return [(d, start + i, p, p + 0.1, p - 0.1, p, 1) for i, p in enumerate(prices)]


g = {c["tag"]: c for c in M.grid()}
base = [100.0 + (5 if i == 5 else -5 if i == 6 else 0) for i in range(30)]          # 범위 94.9 ~ 105.1 · 폭 10.2
up_fail = base + [108.0] * 5 + [102.0] * 5 + [94.0] * 5 + [100.0] * 346           # 위로 뚫림(107.65 넘음) → 102.55 아래로 되돌림 → 아래끝 닿음
w = M.signals(M.prep(day("20260105", up_fail)), g["N30_b0.25_t1"])
chk("1 위 돌파에 삼 → 범위 안으로 되돌면 팖(뒤집기) → 아래끝 닿으면 정리 → 그날 끝", w[6] == 1 and w[7] == -1 and w[8] == 0 and all(x is None for x in w[9:]))
w = M.signals(M.prep(day("20260105", up_fail)), g["N30_b0.25_t0"])
chk("2 trap 0은 돌파에 들고 장 끝까지(되돌아와도 그대로)", w[6] == 1 and all(x is None for x in w[7:]))
w = M.signals(M.prep(day("20260105", up_fail)), g["N30_b0.5_t1"])
chk("3 b 0.5는 108로는 안 듦(110.2 넘어야)", all(x is None for x in w))
dn_fail = base + [92.0] * 5 + [98.0] * 5 + [106.0] * 5 + [100.0] * 346            # 아래로 뚫림(92.35 밑) → 97.45 위로 되돌림 → 위끝 닿음
w = M.signals(M.prep(day("20260106", dn_fail)), g["N30_b0.25_t1"])
chk("4 아래 돌파에 팖 → 되돌면 삼 → 위끝 닿으면 정리", w[6] == -1 and w[7] == 1 and w[8] == 0 and all(x is None for x in w[9:]))
late = base + [100.0] * 335 + [108.0] * 26                                        # 15:05 뒤 돌파
w = M.signals(M.prep(day("20260107", late)), g["N30_b0.25_t1"])
chk("5 15:00 판단 뒤에는 새로 안 듦", all(x is None for x in w))
hold = base + [108.0] * 5 + [104.0] * 356                                          # 범위 안으로 들어왔지만 R × W(102.55)까지는 아님
w = M.signals(M.prep(day("20260108", hold)), g["N30_b0.25_t1"])
chk("6 R × W 만큼 안 되돌면 뒤집지 않음", w[6] == 1 and all(x is None for x in w[7:]))
chk("7 격자 8칸 · 이름 겹침 없음", len(M.grid()) == 8 and len({M.name(c) for c in M.grid()}) == 8)
chk("8 잠금 통과", bool(M.verify_inputs()))
print(f"모두 통과 {ok}개")
