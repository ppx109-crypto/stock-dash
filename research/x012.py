"""겹침 비중 2회(F11) — x011에 이어: 칸 늘리기 고원(×1.25 · ×2 · 최대 5 · 8) · 반대(겹치면 줄이기) · 안 겹친 것만 늘리기. 씨앗 16.
Q_SRC=yahoo · kis."""
import os
import sys
src_text = open("/home/user/stock-dash/research/x011.py", encoding="utf-8").read()
exec(src_text.split('print(f"== 겹침 추가 배팅')[0])


def scaled(kind, mult, cap=6, invert=False):
    test = KINDS[kind]

    def f(c, b, k):
        n = BASE_SIZE(c, b, k)
        hit = test(c, b["t"][k][:8])
        if hit != invert:
            return int(max(1, min(cap, round(n * mult))))
        return n
    return f


print(f"== 겹침 비중 2회 ({'한투 1년' if src == 'kis' else '야후 3년'}) ==", flush=True)
go("기준", BASE_SIZE)
for kind in ("보유 또는 신호", "신호"):
    for mult, cap in ((1.25, 6), (1.5, 5), (1.5, 8), (2.0, 8)):
        go(f"{kind} → ×{mult}(최대 {cap})", scaled(kind, mult, cap))
    go(f"{kind} → ×0.5(줄이기)", scaled(kind, 0.5))
    go(f"{kind} 아닌 것 → ×1.5(최대 6)", scaled(kind, 1.5, 6, invert=True))
print("끝", flush=True)
