"""일봉 새 92회차(G7b 막힌/바뀐 매매) — 운영(daily_live)은 닮음을 '두 종목 모두 오늘 창'(날짜 맞춤)으로 재고, 연구 엔진(lab.run)은
들고 있는 종목 창을 그 종목을 산 날에 둠(새 91회차 3: 날짜 맞춤 0.6이 앞 13.9 → 11.5 · 뒤 58.4 → 52.2).
날짜 맞춤이 어떤 매매를 막고 무엇을 대신 샀나 — 매매 목록끼리 (종목 · 산 날)로 견주고 계좌 몫(자리 × 손익 ÷ 10칸)을 더함."""
import bisect
import sys
sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import ntools as T
import nrl
import lab

steps = lab.moves(nrl.prices)
DAYS = {c: [str(d) for d, _ in b["rows"]] for c, b in nrl.prices.items()}


def aligned(edge, back=60):
    def ok(row, held):
        day = DAYS[row["code"]][row["i"]]
        for h in held:
            j = bisect.bisect_right(DAYS.get(h["code"], []), day) - 1
            if j >= 0 and lab.kinship(steps, row, {"code": h["code"], "i": j}, back) >= edge:
                return False
        return True
    return ok


def book(got):
    out = {}
    for side, g in got.items():
        for t in (g or {}).get("매매목록", []):
            key = (side, t["code"], str(t["산 날"]))
            out[key] = round(out.get(key, 0) + t["자리"] * t["손익"] / 10, 2)
    return out


print("== 일봉 새 92회차: 날짜 맞춘 닮음 0.6이 막은/바꾼 매매 ==", flush=True)
base = book(T.once("기준(연구 판 닮음)"))
nrl.kin = aligned(0.6)
got = book(T.once("날짜 맞춘 닮음 0.6(운영 판)"))
for side in ("앞", "뒤"):
    gone = {k: v for k, v in base.items() if k[0] == side and k not in got}
    new = {k: v for k, v in got.items() if k[0] == side and k not in base}
    same = [k for k in base if k[0] == side and k in got]
    print(f"  {side}: 같은 매매 {len(same)} · 몫 차이 {sum(got[k] - base[k] for k in same):+.1f} | 막힘 {len(gone)}건 몫 {sum(gone.values()):+.1f}"
          f" | 새로 삼 {len(new)}건 몫 {sum(new.values()):+.1f}", flush=True)
    for tag, d in (("막힘", gone), ("새로", new)):
        top = sorted(d.items(), key=lambda kv: -abs(kv[1]))[:6]
        print(f"    {tag} 큰 것: " + " · ".join(f"{k[1]} {k[2]} {v:+.1f}" for k, v in top), flush=True)
        yrs = {}
        for k, v in d.items():
            yrs[k[2][:4]] = round(yrs.get(k[2][:4], 0) + v, 1)
        print(f"    {tag} 해마다: " + " · ".join(f"{y} {v:+.1f}" for y, v in sorted(yrs.items())), flush=True)
print("끝", flush=True)
