"""15분봉 45회차 — 1일봉 규칙 사기를 종가(동시호가) 대신 15시 값으로(40회차 1년: 15:15 값이 +0.16%p · 64%) — 긴 자료 확인.
야후 1시간봉 15시 봉 시가(= 15:00 값)와 그날 종가를 일봉 매매(2023-10 ~ 2026-09)마다 견줌. 해마다."""
import json
import statistics
import sys
sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import hlab as H
import ntools as T

got = T.once("일봉 새 82회차")
rows = [t for s in ("앞", "뒤") if got.get(s) for t in got[s]["매매목록"] if "20231001" <= t["산 날"] <= "20260925"]
codes = sorted({t["code"] for t in rows})
HD = H.load(codes)
P15 = {(c, t[:8]): b["o"][i] for c, b in HD.items() for i, t in enumerate(b["t"]) if t[8:10] == "15"}
CL = {(c, d): float(x) for c in codes for d, x in json.load(open(f"price-data/{c}.json", encoding="utf-8"))["closes"]}
by = {}
for what, key in (("사기", "산 날"), ("팔기", "판 날")):
    by = {}
    for t in rows:
        a, base = P15.get((t["code"], t[key])), CL.get((t["code"], t[key]))
        if not a or not base:
            continue
        diff = (base / a - 1) * 100 if what == "사기" else (a / base - 1) * 100
        by.setdefault(t[key][:4], []).append(diff)
        by.setdefault("모두", []).append(diff)
    print(f"  {what}: 종가 대신 15시 값 — " + " · ".join(f"{y} {statistics.mean(v):+.2f}(가운데 {statistics.median(v):+.2f} · {sum(x > 0 for x in v) / len(v) * 100:.0f}% · {len(v)})" for y, v in sorted(by.items())), flush=True)
print("끝", flush=True)
