"""15분봉 40회차 — 운영 중인 1일봉 규칙(새 82회차)의 '주문 넣는 때'. 일봉 매매(씨앗 0 · 2025-09-17 ~ 2026-08-31에 산 것)마다:
- 사기: 그날 종가(동시호가 = 지금) vs 15:15 값(15:00 칸 종가) vs 다음 날 09:00 · 09:15 · 09:30 시가
- 팔기: 그날 종가(지금) vs 15:15 값 vs 다음 날 09:00 · 09:15 시가
매매 하나당 손익 차이(%p)의 평균 · 가운데 · 나은 몫. 161종목 15분봉에 있는 종목만."""
import os
import statistics
import sys
sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import m15lab as M2
import ntools as T

M15 = M2.load(None, os.environ.get("M15_HOME"))
BAR = {}
for c, b in M15.items():
    for i, t in enumerate(b["t"]):
        BAR[(c, t)] = (b["o"][i], b["c"][i])
DAYS = sorted({t[:8] for b in M15.values() for t in b["t"]})


def nxt(d):
    k = DAYS.index(d) if d in DAYS else None
    return DAYS[k + 1] if k is not None and k + 1 < len(DAYS) else None


def at(c, d, hhmm, which):
    got = BAR.get((c, d + hhmm))
    return None if got is None else (got[0] if which == "o" else got[1])


got = T.once("일봉 새 82회차")
rows = [t for s in ("앞", "뒤") if got.get(s) for t in got[s]["매매목록"]
        if "20250917" <= t["산 날"] <= "20260831" and t["code"] in M15]
print(f"== 15분봉 40회차: 1일봉 규칙 주문 시각 (매매 {len(rows)}건) ==", flush=True)
for what, key in (("사기", "산 날"), ("팔기", "판 날")):
    base_name = "그날 종가"
    for alt, fn in (("15:15 값", lambda c, d: at(c, d, "1500", "c")),
                    ("다음 날 09:00 시가", lambda c, d: nxt(d) and at(c, nxt(d), "0900", "o")),
                    ("다음 날 09:15 시가", lambda c, d: nxt(d) and at(c, nxt(d), "0915", "o")),
                    ("다음 날 09:30 시가", lambda c, d: nxt(d) and at(c, nxt(d), "0930", "o"))):
        d = []
        for t in rows:
            day = t[key]
            base = at(t["code"], day, "1515", "c")
            a = fn(t["code"], day)
            if not base or not a:
                continue
            d.append((base / a - 1) * 100 if what == "사기" else (a / base - 1) * 100)   # +면 바꾼 쪽이 이득
        if d:
            print(f"  {what}: {base_name} 대신 {alt}: 평균 {statistics.mean(d):+.3f}%p · 가운데 {statistics.median(d):+.3f} · 나은 몫 {sum(x > 0 for x in d) / len(d) * 100:.0f}% ({len(d)})", flush=True)
print("끝", flush=True)
