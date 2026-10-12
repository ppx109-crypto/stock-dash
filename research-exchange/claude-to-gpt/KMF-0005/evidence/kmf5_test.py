"""KMF-0005 합성 · 성질 시험(손익 셈 없음)."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "research"))
import kmf as K  # noqa: E402
import kmf5 as K5  # noqa: E402
import numpy as np  # noqa: E402
ok = 0


def chk(name, cond):
    global ok
    if not cond:
        print("실패:", name); sys.exit(1)
    ok += 1; print("통과:", name)


def day(d, prices, start=540):
    return [(d, start + i, p, p + 0.1, p - 0.1, p, 1) for i, p in enumerate(prices)]


g = {c["tag"]: c for c in K5.grid()}
# 1 범위(첫 60분 = 15분봉 4개) 뒤 15분봉 종가가 위면 삼 · 한 번 · 1분 안의 돌파는 15분봉 종가가 아니면 안 셈
p = [100.0] * 60 + [100.5] * 5 + [100.0] * 10 + [101.0] * 316       # 10:00 ~ 10:04 위(15분봉 종가 아님) → 10:15 봉 종가 위
b = K5.prep(day("20260105", p))
w = K5.signals(b, g["N60_day_e1"])
chk("1 15분봉 종가로만 판단(10:14 봉 종가는 범위 안 → 10:29 봉에서 삼)", w[4] is None and w[5] == 1 and sum(1 for x in w if x is not None) == 1)
# 2 range 멈춤 · 하루 2번
p2 = [100.0] * 60 + [101.0] * 15 + [99.0] * 15 + [98.0] * 301
w = K5.signals(K5.prep(day("20260106", p2)), g["N60_range_e2"])
chk("2 range 멈춤 뒤 아래 돌파 두 번째 들기", w[4] == 1 and w[5] == 0 and w[6] == -1)
# 3 일봉 RNA: 앞 날 종가가 꾸준히 오르면 '오름' → 아래 돌파는 안 듦 · 위 돌파는 듦
rows = []
for k in range(25):
    rows += day(f"2026{1 + k // 20:02d}{5 + k % 20:02d}", [100.0 + k] * 391)
st = K5.daily_state(K5.prep(rows))
chk("3 꾸준히 오른 앞 날들 → 오름", list(st.values())[-1] == "오름")
dn = rows + day("20260226", [130.0] * 60 + [120.0] * 331)
up = rows + day("20260226", [130.0] * 60 + [140.0] * 331)
wd = K5.signals(K5.prep(dn), g["N60_day_e1_RNA"]); wu = K5.signals(K5.prep(up), g["N60_day_e1_RNA"])
chk("3b 역추세금지: 오름 날 아래 돌파 안 듦 · 위 돌파 듦", all(x is None for x in wd[-26:]) and 1 in wu[-26:])
# 4 일봉 상태는 앞 날 값만: 그날 종가를 바꿔도 그날 상태가 같음
s1 = K5.daily_state(K5.prep(dn)); s2 = K5.daily_state(K5.prep(up))
chk("4 그날 상태는 앞 날까지 값(그날 값 바뀌어도 같음)", s1["20260226"] == s2["20260226"])
chk("5 격자 12칸 · 이름 겹침 없음", len(K5.grid()) == 12 and len({K5.name(c) for c in K5.grid()}) == 12)
chk("6 잠금 통과", bool(K5.verify_inputs()))
print(f"모두 통과 {ok}개")
