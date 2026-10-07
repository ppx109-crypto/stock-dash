"""MEAS-0001 C — RULES-0002 D1 씨앗0 장부(ASIS)를 a_mtm.account와 같은 흐름으로 따라가 현금 음수 · 노출 > 100% 날 세기(성과 재계산 아님).
python amtm_cash_audit.py <nrl-cache.pkl> <d1_ledger_ASIS.csv> <out.json>"""
import csv
import json
import pickle
import socket
import sys

socket.socket = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("네트워크 금지"))
CACHE, LED, OUT = sys.argv[1:4]
ALLOW = {("numpy._core.numeric", "_frombuffer"), ("numpy", "dtype")}


class Safe(pickle.Unpickler):
    def find_class(self, m, n):
        if (m, n) in ALLOW:
            return super().find_class(m, n)
        raise pickle.UnpicklingError(f"{m}.{n}")


prices = Safe(open(CACHE, "rb")).load()[0]
ledger = [(r["code"], r["entry"], r["exit"], float(r["pnl_pct_engine"]), int(r["slots"])) for r in csv.DictReader(open(LED, encoding="utf-8"))]
D = sorted({d for c in prices.values() for d, _ in c["rows"] if d >= "20170101"})
n, idx = len(D), {d: i for i, d in enumerate(D)}
px, buys, sells = {}, {}, {}
for t, (c, b, e, p, k) in enumerate(ledger):
    if b not in idx or e not in idx:
        continue
    px.setdefault(c, dict(prices.get(c, {}).get("rows") or []))
    buys.setdefault(idx[b], []).append(t)
    sells.setdefault(idx[e], []).append(t)
E, val, last, units = 1.0, {}, {}, {}
neg_days, over_days, min_cash, max_expo, dropped_same_day = 0, 0, 1.0, 0.0, 0
for t, (c, b, e, p, k) in enumerate(ledger):
    if b == e:
        dropped_same_day += 1
for i in range(1, n):
    cash = E - sum(val.values())
    for t in list(val):
        v = px[ledger[t][0]].get(D[i])
        if v:
            val[t] *= v / last[t]
            last[t] = v
    for t in sells.get(i, []):
        if t in val:
            cash += units[t] * (1 + ledger[t][3] / 100)
            val.pop(t)
    eq = cash + sum(val.values())
    for t in buys.get(i, []):
        c, b, e, p, k = ledger[t]
        v = px[c].get(D[i])
        if v and idx[e] > i:
            units[t] = eq * k / 10
            val[t] = units[t]
            last[t] = v
    E = eq
    c_after = E - sum(val.values())
    expo = sum(val.values()) / E if E > 0 else 0
    min_cash = min(min_cash, c_after / E if E > 0 else 0)
    max_expo = max(max_expo, expo)
    neg_days += c_after < -1e-12
    over_days += expo > 1 + 1e-12
out = {"ledger_rows": len(ledger), "days": n, "days_cash_negative": neg_days, "days_exposure_over_100pct": over_days,
       "min_cash_share_of_nav": min_cash, "max_exposure": max_expo, "same_day_rows_dropped_by_a_mtm": dropped_same_day,
       "meaning": "a_mtm은 산 날 '그날 계좌 × 칸/10'으로 사서 현금 제약이 없음 — 이 장부에서 실제로 현금 음수(빌린 돈)인 날 수"}
open(OUT, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
print(json.dumps(out, ensure_ascii=False))
