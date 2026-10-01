"""15분봉 44회차(40회차 확인 줄) — 1일봉 규칙(새 82회차) 주문 시각을 긴 자료로: 1시간봉 연구용 야후 1시간봉(2023-10 ~ 2026-09)의 09시 봉 시가 = 그날 시가.
일봉 매매(씨앗 0)마다 사기: 그날 종가(지금) vs 다음 날 09시 시가 vs 다음 날 10시 시가 / 팔기: 그날 종가 vs 다음 날 09 · 10시 시가.
매매 하나당 손익 차이(%p) · 해마다. 40회차(15분봉 1년 · 81건)에선 다음 날 09:00이 사기 +0.46 · 팔기 +0.38%p 나았음."""
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
OPEN = {}
for c, b in HD.items():
    for i, t in enumerate(b["t"]):
        if t[8:10] in ("09", "10"):
            OPEN[(c, t[:8], t[8:10])] = b["o"][i]
CL = {}
for c in codes:
    for d, x in json.load(open(f"price-data/{c}.json", encoding="utf-8"))["closes"]:
        CL[(c, d)] = float(x)
DAYS = sorted({k[1] for k in OPEN})


def nxt(d):
    import bisect
    k = bisect.bisect_right(DAYS, d)
    return DAYS[k] if k < len(DAYS) else None


print(f"== 15분봉 44회차: 1일봉 규칙 주문 시각 · 긴 자료(야후 1시간봉 · 매매 {len(rows)}건) ==", flush=True)
for what, key in (("사기", "산 날"), ("팔기", "판 날")):
    for hh in ("09", "10"):
        by = {}
        for t in rows:
            d = t[key]
            base = CL.get((t["code"], d))
            n = nxt(d)
            a = OPEN.get((t["code"], n, hh)) if n else None
            if not base or not a:
                continue
            diff = (base / a - 1) * 100 if what == "사기" else (a / base - 1) * 100
            by.setdefault(d[:4], []).append(diff)
            by.setdefault("모두", []).append(diff)
        parts = [f"{y} {statistics.mean(v):+.2f}({sum(x > 0 for x in v) / len(v) * 100:.0f}% · {len(v)})" for y, v in sorted(by.items())]
        print(f"  {what}: 그날 종가 대신 다음 날 {hh}시 시가 — " + " · ".join(parts), flush=True)
print("끝", flush=True)
