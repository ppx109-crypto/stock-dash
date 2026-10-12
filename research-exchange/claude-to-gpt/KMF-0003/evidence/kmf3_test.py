"""KMF-0003 합성 시험(성과 셈 없음 · 가짜 분봉)."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "research"))
import kmf as K  # noqa: E402
import kmf3 as K3  # noqa: E402
ok = 0


def chk(name, cond):
    global ok
    if not cond:
        print("실패:", name); sys.exit(1)
    ok += 1; print("통과:", name)


def day(d, prices, start=540, wide=0.1):
    return [(d, start + i, p, p + wide, p - wide, p, 10) for i, p in enumerate(prices)]


base = K3.grid()[0]
g = {c["tag"]: c for c in K3.grid()}
up = [100.0] * 60 + [101.0] + [102.0] * 330           # 범위 99.9 ~ 100.1 · 600분 위로 돌파
# 1 W15: 범위 폭 0.2 → 듦 · 폭을 넓히면(20p) 안 듦
chk("1 W15 좁은 날 듦", K3.signals(day("20260105", up), g["W15"])[60] == 1)
wide = [100.0 + (10 if i == 5 else -10 if i == 6 else 0) for i in range(60)] + [111.0] + [112.0] * 330
chk("1b W15 범위 20p 넘는 날 안 듦", all(x is None for x in K3.signals(day("20260105", wide), g["W15"])))
# 2 WR: 앞 날 20일이 모자라면 안 듦 · 앞 날 폭 평균의 r배 넘으면 안 듦
chk("2 WR 앞 날 모자라면 안 듦", all(x is None for x in K3.signals(day("20260105", up), g["WR1.5"])))
rows = []
for k in range(20):
    rows += day(f"202601{5 + k:02d}", [100.0] * 391, wide=1.0)  # 앞 날 폭 2.0
rows += day("20260126", [100.0] * 60 + [103.0] + [104.0] * 330, wide=1.4)   # 폭 2.8 ≤ 2.0 × 1.5
w = K3.signals(rows, g["WR1.5"])
chk("2b WR 앞 날 평균 × 1.5 안이면 듦", w[20 * 391 + 60] == 1)
rows2 = rows[:20 * 391] + day("20260126", [100.0] * 60 + [103.0] + [104.0] * 330, wide=1.6)  # 폭 3.2 > 3.0
chk("2c WR 넘으면 안 듦", all(x is None for x in K3.signals(rows2, g["WR1.5"])[20 * 391:]))
# 3 S6: 들기 값(다음 분 시가 101.5) 대비 종가가 6p 넘게 불리하면 정리
rows3 = day("20260107", [100.0] * 60, wide=3.0) + [("20260107", 600 + i, p, p + 0.1, p - 0.1, p, 10) for i, p in enumerate([104.0, 104.0, 99.0, 97.5] + [97.5] * 327)]
w = K3.signals(rows3, g["S6"])                      # 범위 97 ~ 103 · 104에 듦 · 들기 값 104(다음 분 시가) · 97.5는 6.5p 불리 → 정리
chk("3 S6 거래 멈춤(104 − 6 = 98 아래 종가 · 반대 범위 97 위)", w[60] == 1 and w[62] is None and w[63] == 0)
chk("3b B0는 같은 날 정리 안 함", K3.signals(rows3, base)[63] is None)
# 4 T660: 11:00 뒤 첫 돌파는 안 듦
p4 = [100.0] * 150 + [101.0] * 241
chk("4 T660 11:00 뒤 돌파 안 듦", all(x is None for x in K3.signals(day("20260108", p4), g["T660"])))
chk("4b B0는 듦", K3.signals(day("20260108", p4), base)[150] == 1)
# 5 G20: 앞 날 종가와 갭 25p면 안 듦 · 앞 날 없으면 안 듦
two = day("20260109", [100.0] * 391) + day("20260112", [125.0] * 60 + [126.0] * 331)
chk("5 G20 갭 25p 안 듦", all(x is None for x in K3.signals(two, g["G20"])[391:]))
chk("5b G30 갭 25p 듦", K3.signals(two, g["G30"])[391 + 60] == 1)
# 6 C5: 1분봉으로는 600분에 돌파지만, 5분봉 끝(604분 · 609분 …)에서만 판단 · 604분 종가가 범위 안이면 안 듦
p6 = [100.0] * 60 + [101.0, 101.0, 100.0, 100.0, 100.0] + [101.0] * 326      # 600 · 601 돌파 → 604 범위 안 → 609 돌파
w = K3.signals(day("20260113", p6), g["C5"])
chk("6 C5 들기는 5분봉 끝에서만(604 안 · 609 듦)", w[60] is None and w[64] is None and w[69] == 1)
chk("6b B0는 600분에 듦", K3.signals(day("20260113", p6), base)[60] == 1)
chk("6c C15 첫 판단은 614분", K3.signals(day("20260113", p6), g["C15"]).index(1) == 74)
chk("7 격자 14칸 · 이름 겹침 없음", len(K3.grid()) == 14 and len({K3.name(c) for c in K3.grid()}) == 14)
chk("8 잠금 통과", bool(K3.verify_inputs()))
print(f"모두 통과 {ok}개")
