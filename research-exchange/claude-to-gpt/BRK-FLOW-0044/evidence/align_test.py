"""lab.run align_days · 다음 날 팔기(next_exit) 합성 시험 — 정지 · 결측일에 미래 종가를 앞당기지 않음 · t 판단 t + 1 체결."""
import sys
root = sys.argv[1] if len(sys.argv) > 1 else "/home/user/stock-dash"
sys.path.insert(0, root)
import lab
fails = []
def ok(c, m):
    print(("통과 " if c else "실패 ") + m)
    if not c: fails.append(m)
days = [f"202003{d:02d}" for d in range(2, 22)]        # 20일
miss = days[5]                                          # A 종목은 이날 바 없음(정지)
def mk(n):
    prices, rows = {}, []
    for k in range(n):
        a = f"A{k:03d}"
        ad = [d for d in days if d != miss]
        prices[a] = {"name": a, "rows": [(d, 100.0 + i) for i, d in enumerate(ad)]}
        rows += [{"code": a, "date": d, "i": i, "buy": i == 2} for i, d in enumerate(ad)]
    prices["CAL"] = {"name": "CAL", "rows": [(d, 100.0) for d in days]}     # 달력을 채우는 종목(안 삼)
    rows += [{"code": "CAL", "date": d, "i": i, "buy": False} for i, d in enumerate(days)]
    return prices, rows
p, r = mk(70)
kw = dict(slots=1000, rank=lambda x: 0, cost=0.25, detail=True, realistic=True, size=lambda x: 1, settle_end=True)
hold4 = lambda lane, start, price, step, peak, row=None: step >= 4      # 4번째 바에서 팖
g = lab.run(r, p, lambda x: x["buy"], hold4, align_days=True, **kw)
t = g["매매목록"][0]
ad = [d for d in days if d != miss]
ok(t["판 날"] == ad[6] and t["들고"] == 4, f"정지일을 건너뛰고 종목 자기 4번째 바({ad[6]})에 팖 · 장부 날짜 = 실제 바 날짜")
ok(abs(t["손익"] - round((106 / 102 - 1) * 100 - 0.25, 2)) < 1e-9, "그 바의 종가로 셈")
g0 = lab.run(r, p, lambda x: x["buy"], hold4, **kw)
t0 = g0["매매목록"][0]
ok(t0["판 날"] == days[6] and t0["판 날"] != ad[6], f"(대조) 끄면 예전처럼 달력 {days[6]}에 종목 칸 {ad[6]} 값으로 적힘 → 켜서 고침")
sys.path.insert(0, root + "/research")
import importlib.util
spec = importlib.util.spec_from_file_location("bd", root + "/research/brk_dev.py")
src = open(root + "/research/brk_dev.py").read()
ns = {}
exec(src[src.index("def next_exit"):src.index("def fixed_exit")], ns)
nx = ns["next_exit"](5, 7, 10)
lane = {"closes": [100, 101, 106, 99, 98]}
ok(nx(lane, 0, 100, 1, 101) is False, "산 다음 칸(step 1)은 안 팖")
ok(nx(lane, 0, 100, 2, 106) is False, "step 2: 앞 칸(101 · +1%) 기준 → 안 팖(그날 106을 보고 같은 종가에 팔지 않음)")
ok(nx(lane, 0, 100, 3, 106) is True, "step 3: 앞 칸(106 · +6%)이 익절 문턱 → 이 칸(99) 종가에 팖(다음 날 체결)")
lane2 = {"closes": [100] * 15}
ok(nx(lane2, 0, 100, 10, 100) is False and nx(lane2, 0, 100, 11, 100) is True, "기간 10: 앞 칸까지 10거래일 들고 나서 다음 칸에 팖")
print(f"합계: 실패 {len(fails)}"); sys.exit(1 if fails else 0)
