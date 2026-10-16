"""MPOS-0018 H2 round 2(GPT #443 후속 · 수익률 안 봄): 신용 자료 감사 정밀화 + 비중첩 사건 정의(GPT 안) 사건 수 · 에피소드 · 연도 분포 · 제외 내역 · 새32·33회차 겹침.
공통 달력 = 코스피 지수 거래일(market-data/index_KOSPI.json). 기간 2017-07-03 ~ 2026-08-31(판단일 t).
감사: 정확 일치(잔고 차 = 신규 − 상환) · 1주 안 · 잔차 / 전일 잔고 · 잔차 / (신규 + 상환) 분포 · 중복 · 역순 · 공통 달력 대비 빠진 날 · 인접 비율 > 5 또는 < 0.2 플래그.
사건(t는 공통 달력 · 모든 값은 t−3까지):
  집중 = sum(상환 − 신규, t−16 … t−7) / 잔고[t−17] ≥ 0.10(잔고[t−17] > 0) · 진정 = sum(상환 − 신규, t−6 … t−3) ≤ 0 · 가격 = 종가[t−3] / 종가[t−23] − 1 < 0.
  t−23 … t−3 안에 공통 달력 날이 빠졌거나(신용 · 가격), 인접 비율 플래그 · 1주 넘는 항등식 어긋남이 있으면 제외(사유별로 셈).
  연속으로 참인 날은 한 에피소드(최초 판단일만 사건) · 하루라도 거짓이면 다음 참부터 새 에피소드.
겹침: 같은 모집단 · 같은 지연에서 새32 조건 A = 잔고[t−3] < 잔고[t−4] < 잔고[t−5] < 잔고[t−6](3일 연속 감소) — 날 단위 · 에피소드 단위 교집합 · 포함률 · Jaccard."""
import bisect
import collections
import hashlib
import json
import statistics as S
from pathlib import Path

R = Path("/home/user/stock-dash")
CAL = [r["date"] for r in json.load(open(R / "market-data/index_KOSPI.json"))["rows"]]
CI = {d: i for i, d in enumerate(CAL)}
T0, T1 = "20170703", "20260831"
audit = collections.Counter()
resid_bal, resid_flow = [], []
excl = collections.Counter()
ev_days, ev_eps, a_days, a_eps = set(), set(), set(), set()
yr_eps, yr_days = collections.Counter(), collections.Counter()
newrep = {"집중 창 신규 합": 0.0, "집중 창 상환 합": 0.0, "진정 창 신규 합": 0.0, "진정 창 상환 합": 0.0}
files = sorted((R / "credit-data").glob("*.json"))
for f in files:
    code = f.stem
    rows = json.load(open(f)).get("rows") or []
    dates = [r[0] for r in rows]
    audit["줄"] += len(rows)
    audit["중복 날짜"] += len(dates) - len(set(dates))
    audit["역순"] += sum(1 for a, b in zip(dates, dates[1:]) if b < a)
    cr = {}
    for r in rows:
        cr[r[0]] = r
    px = {d: c for d, c in json.load(open(R / "price-data" / f.name))["closes"]}
    bad = set()                                   # 인접(공통 달력 다음 날) 불일치 · 플래그 날
    for d in sorted(cr):
        i = CI.get(d)
        if i is None or i == 0:
            continue
        p = CAL[i - 1]
        if p not in cr:
            audit["앞 공통 거래일에 신용 줄 없음"] += 1
            continue
        a, b = cr[p], cr[d]
        if None in (a[2], b[2], b[4], b[5]):
            audit["값 빠짐"] += 1
            bad.add(d)
            continue
        audit["공통 달력 이어진 쌍"] += 1
        res = (b[2] - a[2]) - (b[4] - b[5])
        if res == 0:
            audit["정확 일치"] += 1
        if abs(res) <= 1:
            audit["1주 안"] += 1
        else:
            bad.add(d)
        if a[2] > 0:
            resid_bal.append(abs(res) / a[2])
            if b[2] / a[2] > 5 or b[2] / a[2] < 0.2:
                audit["인접 비율 > 5 또는 < 0.2"] += 1
                bad.add(d)
        g = b[4] + b[5]
        if g > 0:
            resid_flow.append(abs(res) / g)
    prev_ev, prev_a = False, False
    for t in CAL:
        if not (T0 <= t <= T1):
            continue
        i = CI[t]
        win = CAL[i - 23:i - 2]                    # t−23 … t−3
        if len(win) < 21:
            continue
        if any(d not in cr for d in win[-18:]):    # 신용 창 t−20 … t−3(분모 t−17 · 흐름 t−16 … t−3)
            excl["신용 줄 빠짐"] += 1
            prev_ev = prev_a = False
            continue
        if any(d not in px for d in (win[0], win[-1])):
            excl["가격 빠짐"] += 1
            prev_ev = prev_a = False
            continue
        if any(d in bad for d in win[-18:]):
            excl["창 안 어긋남 · 플래그"] += 1
            prev_ev = prev_a = False
            continue
        c = lambda d: cr[d]
        conc_days, calm_days = CAL[i - 16:i - 6], CAL[i - 6:i - 2]
        base = c(CAL[i - 17])[2]
        if not base or base <= 0:
            excl["분모 0"] += 1
            prev_ev = prev_a = False
            continue
        conc = sum(c(d)[5] - c(d)[4] for d in conc_days) / base
        calm = sum(c(d)[5] - c(d)[4] for d in calm_days)
        ret = px[win[-1]] / px[win[0]] - 1
        ev = conc >= 0.10 and calm <= 0 and ret < 0
        bals = [c(CAL[i - k])[2] for k in (6, 5, 4, 3)]
        aa = bals[0] > bals[1] > bals[2] > bals[3]
        if ev:
            ev_days.add((code, t))
            yr_days[t[:4]] += 1
            if not prev_ev:
                ev_eps.add((code, t))
                yr_eps[t[:4]] += 1
                for d in conc_days:
                    newrep["집중 창 신규 합"] += c(d)[4]
                    newrep["집중 창 상환 합"] += c(d)[5]
                for d in calm_days:
                    newrep["진정 창 신규 합"] += c(d)[4]
                    newrep["진정 창 상환 합"] += c(d)[5]
        if aa:
            a_days.add((code, t))
            if not prev_a:
                a_eps.add((code, t))
        prev_ev, prev_a = ev, aa


def ov(x, y):
    i = len(x & y)
    return {"H2": len(x), "새32": len(y), "교집합": i, "H2 가운데 새32 몫 %": round(i / len(x) * 100, 2) if x else None,
            "새32 가운데 H2 몫 %": round(i / len(y) * 100, 2) if y else None, "Jaccard": round(i / len(x | y), 4) if x | y else None}


q = lambda v: {k: round(S.quantiles(v, n=100)[k - 1], 6) for k in (50, 90, 99)} if len(v) > 100 else None
out = {"정의": __doc__, "입력 지문": hashlib.sha256("".join(f.name + hashlib.sha256(f.read_bytes()).hexdigest() for f in files).encode()).hexdigest(),
       "감사": dict(audit), "정확 일치 %": round(audit["정확 일치"] / audit["공통 달력 이어진 쌍"] * 100, 2),
       "1주 안 %": round(audit["1주 안"] / audit["공통 달력 이어진 쌍"] * 100, 2),
       "|잔차| / 전일 잔고 백분위(50 · 90 · 99)": q(resid_bal), "|잔차| / (신규 + 상환) 백분위": q(resid_flow),
       "사건 제외(판단일 수)": dict(excl), "사건 날 수": len(ev_days), "사건 에피소드 수": len(ev_eps),
       "연도별 에피소드": dict(sorted(yr_eps.items())), "연도별 사건 날": dict(sorted(yr_days.items())), "사건 종목 수": len({c for c, _ in ev_eps}),
       "에피소드 창 신규 · 상환 합(주)": newrep, "겹침 날 단위": ov(ev_days, a_days), "겹침 에피소드 단위(최초 날)": ov(ev_eps, a_eps),
       "주의": "3거래일 지연은 회고 감사의 가정(PIT 입증 아님) · 가격은 price-data(KIS 수정주가) · 수익률 안 봄"}
json.dump(out, open(Path(__file__).with_suffix(".json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in out.items() if k != "정의"}, ensure_ascii=False))
