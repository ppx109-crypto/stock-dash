"""일봉 새 95회차(A2 · 연구 ↔ 운영 작은 다름) — 기준 = 새 82회차 · 씨앗 8.
④ 130일 넘게 든 매매: 연구(lab.run cap=130)는 손익을 적지 않고 지움 · 운영은 끝까지 들고 감 → cap 400.
⑤ 상한가 문턱: 연구는 제한폭 × 0.95(28.5%) · 운영(daily_live)은 29.5%."""
import sys
sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import ntools as T
import nrl
import lab
import rule


def once_cap(tag, cap):
    out = [f"  {tag:40s}"]
    for side, pool, since in (("앞", nrl.early, rule.SINCE), ("뒤", nrl.inside, rule.MID)):
        g = lab.wobble(pool, nrl.prices, nrl.BASE_HOLD, nrl.BASE_EXIT, tries=8, slots=nrl.SLOTS, since=since,
                       apart=nrl.kin, realistic=True, cap=cap, detail=True, size=nrl.BASE_SIZE, rank=rule.order)
        long = sum(1 for t in (g or {}).get("매매목록", []) if t["들고"] > 130)
        out.append(side + " " + nrl.line(g, nrl.SLOTS, since) + f" · 130일 넘게 든 매매 {long}")
    print(" | ".join(out), flush=True)


print("== 일봉 새 95회차: 연구 ↔ 운영 작은 다름 ==", flush=True)
once_cap("기준(cap 130)", 130)
once_cap("④ cap 400(운영처럼 끝까지)", 400)
old = lab.limit_of
lab.limit_of = lambda day: old(day) * (0.295 / 0.30) / 0.95
T.once("⑤ 상한가 문턱 29.5%(운영)")
lab.limit_of = old
print("끝", flush=True)
