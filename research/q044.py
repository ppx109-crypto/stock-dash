"""15분봉 43회차(줄 5 · 6) — 운영 중인 1일봉 규칙(새 82회차)의 손절 · 익절을 장중 15분봉 종가로 보면(지금은 종가만).
일봉 매매(씨앗 0 · 2025-09-17 ~ 2026-08-31에 산 것 · 15분봉 있는 종목)마다 산 다음 날 09:00 칸부터 원래 판 날 15:00 칸까지 15분봉 종가에서
추세 문(rule.holds): −5% 이하(손절) · +13% 이상(익절) / 정배열 문: −10% 이하 · (+8% 닿은 뒤) +1% 이하 가 먼저 나오면 다음 15분봉 시가에 판 것으로.
원래 = 판 날 종가(15:15 칸 종가). 매매 하나당 손익 차이 · 바뀐 몫 · 두 반. Q_PART=stop · take · both."""
import os
import statistics
import sys
sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import m15lab as M2
import ntools as T
import rule

M15 = M2.load(None, os.environ.get("M15_HOME"))
IDX = {c: {t: i for i, t in enumerate(b["t"])} for c, b in M15.items()}
part = os.environ.get("Q_PART", "both")
got = T.once("일봉 새 82회차")
print(f"== 15분봉 43회차({part}): 1일봉 규칙 손절 · 익절을 장중 15분봉으로 ==", flush=True)
for side in ("앞", "뒤"):
    rows = [t for t in (got.get(side) or {}).get("매매목록", []) if "20250917" <= t["산 날"] <= "20260831" and t["code"] in M15]
    d = []
    for t in rows:
        c, b15, ix = t["code"], M15[t["code"]], IDX[t["code"]]
        i0, i1 = ix.get(t["산 날"] + "1515"), ix.get(t["판 날"] + "1515")
        if i0 is None or i1 is None or i1 <= i0:
            continue
        price = b15["c"][i0]
        trend = t.get("행") is not None and rule.holds(t["행"])
        base = (b15["c"][i1] / price - 1) * 100
        new, peak = base, price
        for j in range(i0 + 1, i1):
            cl = b15["c"][j]
            peak = max(peak, cl)
            g, pg = (cl / price - 1) * 100, (peak / price - 1) * 100
            if trend:
                hit = (part in ("stop", "both") and g <= -5) or (part in ("take", "both") and g >= 13)
            else:
                hit = (part in ("stop", "both") and g <= -10) or (part in ("take", "both") and pg >= 8 and g <= 1)
            if hit:
                new = (b15["o"][j + 1] / price - 1) * 100
                break
        d.append((new - base) * (t.get("자리") or 1) / 10)
    ch = [x for x in d if x != 0]
    if d:
        print(f"  {side}: 매매 {len(d)} · 바뀐 {len(ch)} · 계좌 몫 합 {sum(d):+.1f}%p · 바뀐 매매 평균 {statistics.mean(ch) if ch else 0:+.2f} · 나아진 몫 {sum(x > 0 for x in ch) / max(1, len(ch)) * 100:.0f}%", flush=True)
print("끝", flush=True)
