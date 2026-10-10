"""OVN-0032 분배금 표 만들기(가격 수익 셈 아님) — etf-ohlc/069500.json에서.
- 2011 ~: 예탁원 배당일정(한투 HHKDB669102C0) 1주당 현금 · 기준일. 분배락 날 = 기준일 바로 앞 거래일.
- 2002 ~ 2010: 예탁원 목록이 비어 있어(해마다 0건) 한투 수정 계수(원주가 ÷ 수정 종가)가 바뀐 날에서 거꾸로 셈:
  D = 앞날 원주가 종가 × (1 − 뒤 3일 평균 계수 ÷ 앞 3일 평균 계수). 바뀜 크기 > 0.1%이고 하루 바뀜 > 0.1%인 날만(반올림 흔들림 거르기).
- 검산: 2011 ~ 예탁원 48건이 같은 식의 계수 바뀜과 모두 3e-4 안으로 맞는지 봄(맞지 않으면 멈춤).
python3 research/t004_dist.py > research-exchange/claude-to-gpt/OVN-0032/dist.json"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
d = json.loads((ROOT / "etf-ohlc/069500.json").read_text())
a = {x[0]: x for x in d["adjusted"]}; r = {x[0]: x for x in d["raw"]}
days = sorted(a)
k = {t: r[t][4] / a[t][4] for t in days}
def fac(i):
    pre = sum(k[days[j]] for j in range(i - 3, i)) / 3
    post = sum(k[days[j]] for j in range(i, i + 3)) / 3
    return post / pre
out, checks = [], []
for x in d["dividends"]:
    rd = x["record_date"]
    i = max(j for j, t in enumerate(days) if t < rd)
    exp = 1 - x["per_share_cash"] / r[days[i - 1]][4]
    checks.append([rd, days[i], round(fac(i) - exp, 6)])
    if abs(fac(i) - exp) >= 3e-4:
        sys.exit(f"예탁원 분배금과 수정 계수가 다름 {rd}")
    out.append({"ex_date": days[i], "record_date": rd, "cash": x["per_share_cash"], "source": "예탁원(한투 HHKDB669102C0)"})
first_ksd = min(x["ex_date"] for x in out)
for i in range(4, len(days) - 3):
    t = days[i]
    if t >= first_ksd[:4] + "0101":
        break
    if abs(fac(i) - 1) > 1e-3 and abs(k[t] / k[days[i - 1]] - 1) > 1e-3:
        if out and any(abs(days.index(o["ex_date"]) - i) <= 2 for o in out if o["ex_date"] < first_ksd):
            continue
        out.append({"ex_date": t, "record_date": None, "cash": round(r[days[i - 1]][4] * (1 - fac(i)), 1),
                    "source": "한투 수정 계수에서 거꾸로 셈(예탁원 목록 없음)"})
out.sort(key=lambda o: o["ex_date"])
print(json.dumps({"code": "069500", "rows": out, "ksd_check_max_abs": max(abs(c[2]) for c in checks), "ksd_n": len(checks)}, ensure_ascii=False, indent=0))
