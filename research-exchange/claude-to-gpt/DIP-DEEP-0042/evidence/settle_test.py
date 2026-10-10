"""lab.run settle_end 합성 시험 — 기간 끝 · 끝 날 하한가 · 보유 한도 초과 · 종목 줄 끝 진입 · 기본값(꺼짐)은 예전과 같음."""
import os, sys
root = sys.argv[1] if len(sys.argv) > 1 else "/home/user/stock-dash"
sys.path.insert(0, root)
import lab
fails = []
def ok(c, m):
    print(("통과 " if c else "실패 ") + m)
    if not c: fails.append(m)
days = [f"202001{d:02d}" for d in range(1, 31)][:12]
def mk(n_codes, closes_fn, buy_i, length=None):
    prices, rows = {}, []
    for k in range(n_codes):
        c = f"C{k:03d}"
        cl = closes_fn(k)
        L = length(k) if length else len(cl)
        prices[c] = {"name": c, "rows": [(days[i], cl[i]) for i in range(L)]}
        rows += [{"code": c, "date": days[i], "i": i, "buy": i == buy_i} for i in range(L)]   # 날마다 줄(엔진은 표 줄 마지막 날까지 돎)
    return prices, rows
never = lambda *a: False
flat = lambda k: [100.0 + i for i in range(12)]
kw = dict(slots=1000, rank=lambda r: 0, cost=0.25, detail=True, realistic=True, size=lambda r: 1)
# A 기간 끝: 줄 12칸 · 2칸에서 삼 · 청산 안 함 → 마지막 칸(11) 종가 정산
p, r = mk(70, flat, 2)
g = lab.run(r, p, lambda x: x["buy"], never, settle_end=True, **kw)
t = g["매매목록"]
ok(len(t) == 70 and all(x["정산"] == "끝 날 가상 정산" and x["판 날"] == days[11] for x in t), "기간 끝: 70건 모두 마지막 날 종가로 정산 기록")
ok(abs(t[0]["손익"] - round((111 / 102 - 1) * 100 - 0.25, 2)) < 1e-9, "정산 손익 = 마지막 종가 ÷ 산 값 − 비용")
ok(lab.run(r, p, lambda x: x["buy"], never, **kw) is None, "기본값(settle_end 꺼짐)은 예전처럼 열린 매매를 버림(60건 미만 → 결과 없음)")
# B 끝 날 하한가: 마지막 칸 −30%
lim = lambda k: [100.0 + i for i in range(11)] + [110.0 * 0.70]
p, r = mk(70, lim, 2)
t = lab.run(r, p, lambda x: x["buy"], never, settle_end=True, **kw)["매매목록"]
ok(len(t) == 70 and all(x["정산"] == "끝 날 하한가 가상 정산" for x in t), "끝 날 하한가여도 70건 모두 가상 정산으로 기록(실제 체결과 구분)")
ok(abs(t[0]["손익"] - round((77 / 102 - 1) * 100 - 0.25, 2)) < 1e-9, "하한가 날 종가로 평가")
# C 보유 한도: cap 5 → 6칸째(2 + 6 = 8칸) 종가로 정산
p, r = mk(70, flat, 2)
t = lab.run(r, p, lambda x: x["buy"], never, settle_end=True, cap=5, **kw)["매매목록"]
ok(len(t) == 70 and all(x["정산"] == "보유 한도 정산" and x["들고"] == 6 and x["판 날"] == days[8] for x in t), "보유 한도 넘음: 그날(8칸) 종가로 정산 기록")
# D 종목 줄 끝 진입: 줄 길이 6(마지막 칸 5)에서 5칸 신호 → 사지 않음 · 다른 70종목은 정상
p, r = mk(70, flat, 2)
p2, r2 = mk(5, flat, 5, length=lambda k: 6)
p2 = {k.replace("C", "E"): v for k, v in p2.items()}
r2 = [dict(x, code=x["code"].replace("C", "E")) for x in r2]
p.update(p2)
t = lab.run(r + r2, p, lambda x: x["buy"], never, settle_end=True, **kw)["매매목록"]
ok(not any(x["code"].startswith("E") for x in t) and len(t) == 70, "종목 자기 줄 마지막 칸에서는 새로 사지 않음")
# E 줄이 중간에 끝남: 줄 길이 8 · 2칸에서 삼 → 줄 마지막(7칸) 종가 정산
p, r = mk(70, flat, 2, length=lambda k: 8)
t = lab.run(r, p, lambda x: x["buy"], never, settle_end=True, **kw)["매매목록"]
ok(len(t) == 70 and all(x["판 날"] == days[7] for x in t), "줄이 먼저 끝난 종목: 그 마지막 종가로 정산")
print(f"합계: 실패 {len(fails)}"); sys.exit(1 if fails else 0)
