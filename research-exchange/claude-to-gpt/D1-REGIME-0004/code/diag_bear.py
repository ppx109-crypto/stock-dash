# 진단(공개 · 고르기에 안 씀): 씨앗 0 매매 줄을 '산 달의 코스피 장'과 갈래(추세 ① / 정배열 ②)로 나눠 줄 수 · 평균 손익 · 칸 가중 합
import sys; sys.path.insert(0, "/home/user/stock-dash"); sys.path.insert(0, "/home/user/stock-dash/research")
import rule, z081
for which in ("앞", "뒤"):
    g = z081.ledgers(which, z081.holds_b0)[0]
    tab = {}
    for t in g["led"]:
        br = "①추세" if z081.holds_b0(t["행"]) else "②정배열"
        reg = z081.regime_of(t["산 날"][:6])
        k = (reg, br); x = tab.setdefault(k, [0, 0.0, 0.0])
        x[0] += 1; x[1] += t["손익"]; x[2] += t["손익"] * t["자리"] / 10
    for k in sorted(tab):
        n, s, w = tab[k]
        print(f"[{which}] 산 달 {k[0]}장 · {k[1]}: {n}줄 · 평균 {s/n:+.2f}% · 칸 가중 합 {w:+.1f}%p", flush=True)
