"""NEW-RULES-0001 합성 검사(자료 · 네트워크 없음): 달력월 정지 · 노출 줄이기 · 종목별 손익 합 · 다음 날 체결.
python3 -I test_nr.py → JSON. 장부 자체 검사는 test_kernel.py(PR #41 그대로)."""
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nr_engine as E  # noqa: E402


def days(n, start=date(2012, 1, 2)):
    out, d = [], start
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.strftime("%Y%m%d"))
        d += timedelta(days=1)
    return out


R = {}


def check(name, ok, detail=None):
    R[name] = {"pass": bool(ok), "detail": detail}


def month_end_index(cal, after):
    """after 뒤 첫 달 끝(다음 날의 달이 다른 날) 위치."""
    for i in range(after, len(cal) - 1):
        if cal[i + 1][4:6] != cal[i][4:6]:
            return i
    return None


def wiggle(i):
    return 1 + 0.004 * (1 if i % 2 else -1)         # 변동성이 0이 되지 않게 작은 흔들림


# 1) 달력월 정지: A(한 종목 35% 상한)로 들고 있다가 새 달 초에 급락 → mtd ≤ −6%인 날 다음 날 모두 팖 · 그달 새 매수 없음
cal = days(360)
me = month_end_index(cal, 300)
px = [10000.0]
for i in range(1, 360):
    f = 1.003 * wiggle(i)
    if me + 3 <= i < me + 7:
        f = 0.92
    px.append(px[-1] * f)
r = E.Runner(cal, {"069500": (cal, np.array(px))}, "A", {"K": 3, "V": 5.0}, cash=1e7, start=cal[0]).run()
stop = [e for e in r["events"] if e[1] == "달력월 정지"]
ok = bool(stop)
if ok:
    sd = stop[0][0]
    after = [f for f in r["fills"] if f["fill_at"] > sd and f["fill_at"][:6] == sd[:6]]
    first = after[0] if after else None
    nav_on = dict((d, inv) for d, _, inv in r["nav"])
    ok = (first is not None and first["side"] == "sell" and first["decision_at"] == sd
          and not any(f["side"] == "buy" for f in after) and nav_on[first["fill_at"]] == 0.0)
check("month_stop_liquidate_next_day_and_block", ok, {"stop": stop[:1]})

# 2) 노출 줄이기: 달 끝을 사이에 두고 나눠 빠짐(고점 대비 −5% ~ −10% · 달 손실은 −6%보다 덜함) → 다음 날 보유를 절반으로
cal2 = days(460)
me2 = month_end_index(cal2, 420)
p2 = [10000.0]
for i in range(1, 460):
    f = 1.002 * wiggle(i)
    if me2 - 4 <= i <= me2 + 5:
        f = 0.975
    p2.append(p2[-1] * f)
r2 = E.Runner(cal2, {"069500": (cal2, np.array(p2))}, "A", {"K": 3, "V": 5.0}, cash=1e7, start=cal2[0]).run()
sc = [e for e in r2["events"] if e[1] == "노출 줄이기"]
ok2 = bool(sc) and sc[0][2] == 1.0 and sc[0][3] == 0.5
if ok2:
    dsc = sc[0][0]
    nxt = [f for f in r2["fills"] if f["decision_at"] == dsc and f["side"] == "sell"]
    inv = {d: v for d, _, v in r2["nav"]}
    i_dec = [d for d, _, _ in r2["nav"]].index(dsc)
    d_fill = r2["nav"][i_dec + 1][0]
    ratio = inv[d_fill] / inv[dsc] / (p2[cal2.index(d_fill)] / p2[cal2.index(dsc)])     # 값 변화를 뺀 수량 비율
    ok2 = bool(nxt) and abs(ratio - 0.5) < 0.02
check("drawdown_scale_down_half_next_day", ok2, {"event": sc[:1], "qty_ratio_after": round(ratio, 4) if sc else None,
                                                  "month_stops": r2["notes"].get("month_stop", 0)})

# 3) 종목별 손익 합 = NAV 변화(비용 포함)
for name, rr in (("B_synthetic", r), ("A_synthetic", r2)):
    tot = sum(rr["attr"].values())
    gap = abs(tot - (rr["nav"][-1][1] - rr["cash0"]))
    check(f"attribution_sums_to_nav_change_{name}", gap < 1.0, {"gap_won": round(gap, 6)})

# 4) 다음 날 체결: 모든 체결은 판단일 다음 거래일 이후
bad = sum(1 for rr in (r, r2) for f in rr["fills"] if f["status"] in ("FILLED", "REDUCED") and f["fill_at"] <= f["decision_at"])
check("fills_strictly_after_decision", bad == 0, {"violations": bad})

ok = all(x["pass"] for x in R.values())
print(json.dumps({"all_pass": ok, "n": len(R), "results": R}, ensure_ascii=False, indent=1, default=str))
sys.exit(0 if ok else 1)
