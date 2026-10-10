# 진단(공개용): 뒤 반 씨앗 0 · 2026-05 ~ 07 들고 있던 줄과 그 달 기여, 그리고 코스피 같은 달 등락
import sys; sys.path.insert(0, "/home/user/stock-dash"); sys.path.insert(0, "/home/user/stock-dash/research")
import nrl, rule, lab, z077
pool, since = nrl.inside, rule.MID
with z077.use(z077.make_holds(5, rule.SLOPE)):
    g = lab.run(pool, nrl.prices, nrl.BASE_HOLD, nrl.BASE_EXIT, rank=rule.order, slots=nrl.SLOTS, since=since, apart=nrl.kin,
                realistic=True, cap=130, detail=True, size=nrl.BASE_SIZE)
rows = [t for t in g["매매목록"] if t["판 날"] >= "20260501" and t["산 날"] <= "20260731"] + \
       [dict(t, **{"판 날": "(남음)", "손익": None}) for t in g["남은자리"] if t["산 날"] <= "20260731"]
for t in sorted(rows, key=lambda t: t["산 날"]):
    lane = nrl.lanes[t["code"]]; d, c = lane["날"], lane["closes"]
    def at(day):
        k = max(i for i, x in enumerate(d) if x <= day); return c[k]
    jun = (at("20260630") / at("20260529") - 1) * 100
    print(t["산 날"], t["판 날"], "자리", t["자리"], "손익", t["손익"], "· 6월 등락 %.1f%%" % jun, "· 갈래", "추세" if t.get("행") and z077.ORIG_HOLDS and rule.holds(t["행"]) else "정배열/남음")
idx = [k for k in nrl.lanes if k.startswith("KOSPI") or k in ("0001", "KS11")]
print("지수 줄 후보", idx[:5])
