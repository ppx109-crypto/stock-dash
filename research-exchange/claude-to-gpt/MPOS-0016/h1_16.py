"""MPOS-0016 GPT H1 작은 적용 범위 진단(판정 없음): 1일봉 원판(IMM) 보유 중 '사건 없는 시장 잔차 충격'(b16과 같은 정의 · z ≤ −2.5 · α · β · σ는 그 날 앞 120줄)이
몇 번 났고, 원래 규칙이 그날 팔지 않았을 때 다음 날 종가 → 원래 판 날 종가의 잔여 보유 수익(비용 없음 · 원 장부 판 날 기준 · 부분 청산은 마지막 판 날)이 어땠는지.
묶음: 원래 그날 팖(판 날 = 충격 날) / 계속 보유. 진입 단위(종목 + 산 날) · 충격이 여러 번이면 첫 충격만."""
import json
import math
import os
import statistics as S
import sys
from pathlib import Path

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "research"))
import lab  # noqa: E402
import nrl  # noqa: E402

REPO = Path("/home/user/stock-dash")
SP = Path("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad")
L = lab.lanes(nrl.prices)
K = {r["date"]: r["종가"] for r in json.load(open(REPO / "market-data/index_KOSPI.json"))["rows"]}
EV = {json.load(open(f))["code"]: {r["date"] for r in json.load(open(f))["rows"]} for f in (REPO / "event-data").glob("*.json")}
raw = json.load(open(SP / "z055_d1_raw.json"))
ent = {}
for c, b, e, p, s in raw:
    x = ent.setdefault((c, b), {"끝": "", "자리": 0})
    x["끝"] = max(x["끝"], e)
    x["자리"] += s


def z_at(code, i):
    c, ds = L[code]["closes"], L[code]["날"]
    if i - 121 < 0 or ds[i - 1] not in K or ds[i] not in K:
        return None
    rs, ms = [], []
    for j in range(i - 120, i):
        if ds[j - 1] not in K or ds[j] not in K:
            return None
        rs.append(c[j] / c[j - 1] - 1)
        ms.append(K[ds[j]] / K[ds[j - 1]] - 1)
    mm, mr = S.mean(ms), S.mean(rs)
    vm = sum((x - mm) ** 2 for x in ms)
    if vm <= 0:
        return None
    beta = sum((x - mm) * (y - mr) for x, y in zip(ms, rs)) / vm
    a = mr - beta * mm
    sres = S.stdev([y - a - beta * x for x, y in zip(ms, rs)])
    r = c[i] / c[i - 1] - 1
    m = K[ds[i]] / K[ds[i - 1]] - 1
    return (r - a - beta * m) / sres if sres > 0 else None


out = {"원래 그날 팖": [], "계속 보유": []}
held_days = 0
for (code, b), v in ent.items():
    ds, c = L[code]["날"], L[code]["closes"]
    if b not in ds or v["끝"] not in ds:
        continue
    ib, ie = ds.index(b), ds.index(v["끝"])
    for i in range(ib + 1, ie + 1):
        held_days += 1
        z = z_at(code, i)
        if z is None or z > -2.5 or (EV.get(code, set()) & {ds[i - 1], ds[i]}):
            continue
        if i == ie:
            out["원래 그날 팖"].append({"code": code, "b": b, "d": ds[i]})
        else:
            rest = (c[ie] / c[i + 1] - 1) * 100 if i + 1 <= ie else 0.0
            out["계속 보유"].append({"code": code, "b": b, "d": ds[i], "잔여 %(다음 날 종가 → 원래 판 날 종가)": rest, "남은 줄": ie - i - 1})
        break


def st(v):
    if len(v) < 2:
        return {"건": len(v)}
    m, sd = S.mean(v), S.stdev(v)
    return {"건": len(v), "평균 %": round(m, 3), "t": round(m / (sd / math.sqrt(len(v))), 2) if sd > 0 else None, "이긴 몫 %": round(sum(x > 0 for x in v) / len(v) * 100, 1)}


keep = out["계속 보유"]
res = {"정의": __doc__, "보유 줄-날 수": held_days, "진입 수": len(ent),
       "충격이 난 진입 · 원래 그날 팖": len(out["원래 그날 팖"]), "충격이 난 진입 · 계속 보유": len(keep),
       "계속 보유 잔여 수익": st([x["잔여 %(다음 날 종가 → 원래 판 날 종가)"] for x in keep]),
       "앞(~2021)": st([x["잔여 %(다음 날 종가 → 원래 판 날 종가)"] for x in keep if x["d"] < "20220101"]),
       "뒤(2022~)": st([x["잔여 %(다음 날 종가 → 원래 판 날 종가)"] for x in keep if x["d"] >= "20220101"]),
       "사례": keep}
json.dump(res, open(os.environ["OUT"], "w"), ensure_ascii=False, indent=1)
print({k: v for k, v in res.items() if k not in ("사례", "정의")})
