"""PATH-ENSEMBLE-0001 · PR #55 비용 2배 NAV 8개를 25%씩 합산(엔진 재실행 없음). python3 pe_sum.py <evidence 폴더>
입력: <evidence>/input/nav_{B,R}_x2_s{0..3}.csv · 출력: ens_{B4,R4}_EQUAL.csv · contrib_{B4,R4}_EQUAL.csv · pe_results.json"""
import csv
import json
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

EV = Path(sys.argv[1])
CASH = 10_000_000.0
GPT = {"B4": {"end": 18918651.9575, "mdd": -19.5064922531, "worst": -15.0600658655, "worst_at": "20260331", "breach": 1},
       "R4": {"end": 18924457.1650, "mdd": -19.4497002747, "worst": -12.6247609377, "worst_at": "20260304", "breach": 0},
       "R4_minus_B4": {"won": 5805.2075, "pct": 0.0306851012}}


def load(p):
    rows = list(csv.DictReader(open(p, encoding="utf-8")))
    return [r["date"] for r in rows], [Decimal(r["nav_won"]) for r in rows], [Decimal(r["invested_won"]) for r in rows]


def years(a, b):
    D = lambda x: date(int(x[:4]), int(x[4:6]), int(x[6:]))
    return (D(b) - D(a)).days / 365.25


def stats(days, nav, inv, sleeves_end):
    navf = [float(x) for x in nav]
    seg = [CASH] + navf
    rets = [seg[i] / seg[i - 1] - 1 for i in range(1, len(seg))]
    peak, mdd = CASH, 0.0
    for v in seg:
        peak = max(peak, v)
        mdd = min(mdd, v / peak - 1)
    wd = min(range(len(rets)), key=lambda i: rets[i])
    months = {}
    for d, r in zip(days, rets):
        months[d[:6]] = months.get(d[:6], 1.0) * (1 + r)
    wm = min(months, key=months.get)
    tot = sum(sleeves_end)
    return {"end_nav": nav[-1], "CAGR_pct": ((navf[-1] / CASH) ** (1 / years(days[0], days[-1])) - 1) * 100, "MDD_pct": mdd * 100,
            "worst_day_pct": rets[wd] * 100, "worst_day_at": days[wd], "day_breach_-15": sum(1 for r in rets if r < -0.15 - 1e-12),
            "worst_month_pct": (months[wm] - 1) * 100, "worst_month_at": wm, "month_breach_-15": sum(1 for v in months.values() if v - 1 < -0.15 - 1e-12),
            "avg_invest_ratio_pct": sum(float(i) / float(n) for i, n in zip(inv, nav)) / len(nav) * 100,
            "terminal_sleeve_share_pct": [float(x / tot) * 100 for x in sleeves_end], "first_day": days[0], "last_day": days[-1], "days": len(days)}


RES = {}
for name, tag in (("B4", "B"), ("R4", "R")):
    src = [load(EV / "input" / f"nav_{tag}_x2_s{s}.csv") for s in range(4)]
    if any(x[0] != src[0][0] for x in src):
        raise SystemExit(f"{name}: 날짜행이 다름 · 중단")
    days = src[0][0]
    q = Decimal("0.25")
    nav = [sum(q * x[1][i] for x in src) for i in range(len(days))]
    inv = [sum(q * x[2][i] for x in src) for i in range(len(days))]
    nav_rev = [sum(q * x[1][i] for x in src[::-1]) for i in range(len(days))]
    navf_rev = [sum(0.25 * float(x[1][i]) for x in src[::-1]) for i in range(len(days))]
    navf_fwd = [sum(0.25 * float(x[1][i]) for x in src) for i in range(len(days))]
    sleeves_end = [q * x[1][-1] for x in src]
    st = stats(days, nav, inv, sleeves_end)
    st["reverse_sum_max_diff_won_decimal"] = float(max(abs(a - b) for a, b in zip(nav, nav_rev)))
    st["reverse_sum_max_diff_won_float"] = max(abs(a - b) for a, b in zip(navf_fwd, navf_rev))
    g = GPT[name]
    st["vs_gpt"] = {"end": {"gpt": g["end"], "claude": float(st["end_nav"]), "same": abs(float(st["end_nav"]) - g["end"]) <= 0.01},
                    "mdd": {"gpt": g["mdd"], "claude": st["MDD_pct"], "same": abs(st["MDD_pct"] - g["mdd"]) <= 1e-8},
                    "worst": {"gpt": g["worst"], "claude": st["worst_day_pct"], "same": abs(st["worst_day_pct"] - g["worst"]) <= 1e-8},
                    "worst_at": {"gpt": g["worst_at"], "claude": st["worst_day_at"], "same": g["worst_at"] == st["worst_day_at"]},
                    "breach": {"gpt": g["breach"], "claude": st["day_breach_-15"], "same": g["breach"] == st["day_breach_-15"]}}
    RES[name] = st
    with open(EV / f"ens_{name}_EQUAL.csv", "w", encoding="utf-8") as f:
        f.write("date,nav_won,invested_won\n")
        f.writelines(f"{d},{n},{i}\n" for d, n, i in zip(days, nav, inv))
    with open(EV / f"contrib_{name}_EQUAL.csv", "w", encoding="utf-8") as f:
        f.write("date," + ",".join(f"s{s}_nav_x0.25,s{s}_daily_change_x0.25" for s in range(4)) + ",total_daily_change\n")
        for i, d in enumerate(days):
            parts, tot = [], Decimal(0)
            for x in src:
                prev = x[1][i - 1] if i else Decimal(CASH)
                ch = q * (x[1][i] - prev)
                tot += ch
                parts += [str(q * x[1][i]), str(ch)]
            f.write(d + "," + ",".join(parts) + f",{tot}\n")
    print(name, {k: v for k, v in st.items() if k != "vs_gpt"}, flush=True)
    print(name, "GPT 대조", {k: v["same"] for k, v in st["vs_gpt"].items()}, flush=True)
diff = RES["R4"]["end_nav"] - RES["B4"]["end_nav"]
RES["R4_minus_B4"] = {"won": float(diff), "pct": float(diff / RES["B4"]["end_nav"]) * 100,
                      "same_as_gpt": abs(float(diff) - GPT["R4_minus_B4"]["won"]) <= 0.01 and abs(float(diff / RES["B4"]["end_nav"]) * 100 - GPT["R4_minus_B4"]["pct"]) <= 1e-8}
r4 = RES["R4"]
crit = {"R4_end_ge_B4": RES["R4"]["end_nav"] >= RES["B4"]["end_nav"], "R4_no_day_breach": r4["day_breach_-15"] == 0,
        "R4_max_sleeve_share_lt_30": max(r4["terminal_sleeve_share_pct"]) < 30.0,
        "reverse_sum_ok": all(RES[n]["reverse_sum_max_diff_won_decimal"] <= 0.01 for n in ("B4", "R4")),
        "matches_gpt": all(v["same"] for n in ("B4", "R4") for v in RES[n]["vs_gpt"].values()) and RES["R4_minus_B4"]["same_as_gpt"]}
RES["criteria"] = crit
RES["verdict"] = "SHADOW_SPEC_READY" if crit["R4_end_ge_B4"] and crit["R4_no_day_breach"] and crit["R4_max_sleeve_share_lt_30"] else "NO_CANDIDATE"
print("판정", crit, RES["verdict"], flush=True)
(EV / "pe_results.json").write_text(json.dumps(RES, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
