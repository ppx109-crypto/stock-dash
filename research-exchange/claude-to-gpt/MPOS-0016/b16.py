"""MPOS-0016 B안 탐색 진단(판정 없음 · 진단 전용 · GPT #440 B): 사건 없는 날의 시장 잔차 매도 충격 뒤 회복.
정의(셈 전에 고정):
- 대상: 1일봉 엔진 후보 풀(그날 시총 100위 줄 · nrl.inside) · 2017-07 ~ 2026-08(잔차 추정 창 120거래일 뒤).
- t0 잔차: r = 종목 그날 수익 · m = 코스피 그날 수익 · α · β = t0−120 ~ t0−1의 r ~ m 회귀(그때까지 자료) · e = r − α − β·m · z = e / (그 120일 잔차 표준편차).
- 충격: z ≤ −2.5. 단순 하락 대조: 시장 안 뺀 z_raw = r / (120일 r 표준편차) ≤ −2.5.
- 사건: event-data(날짜 단위 · 모은 종류만)에 t0−1 또는 t0 줄이 있으면 '사건 있음' · 없으면 '사건 없음(모은 종류 기준 · 뉴스는 모름)'.
- 진입: E1 = t0+1 종가(t0 종가로 판단 · 다음 날 종가 체결) · E2 = t0+1 종가 > t0 종가(회복 확인)면 t0+2 종가.
- 결과: 진입 종가 → H = 5 · 10 · 20거래일 뒤 종가 수익(왕복 0.25% 뺌) · 코스피 대비(같은 창 코스피 수익 뺌).
- 겹침(GPT #441 정정): 같은 (묶음, 종목)에서 앞 충격 줄 번호 i 뒤 20줄 안의 새 충격만 버림(진입 · 끝 기준 아님 · 묶음이 다르면 따로) · 다른 종목끼리 보유 창은 겹침.
- 평균 · t(GPT #441 정정): 충격일(t0)별 평균을 다시 날마다 같은 무게로 평균(사건별 평균 아님 · 사건별 평균도 따로 보고) · t는 그 날 평균들에 IID 표준오차(겹침 · 자기상관 보정 안 한 참고값).
- 표본 선택: 진입 뒤 22개 관측 종가가 있어야 셈(사후 평가 가능 표본 · 상장폐지 · 정지 영향 미확인) · '거래일'은 종목별 관측 종가 줄 수 · 시장 달력과 어긋난 수를 셈.
- 사건 자료 없음: event-data에 그 종목 파일이 없으면 '사건 모름(NA)'으로 따로 둠 · 날짜 단위라 t0 장 뒤 공시도 들어갈 수 있음(t0 종가 시각에 알려졌다고 단정 안 함 · 다음 날 실행 판단에만 씀).
- 보고만: P0(MIX-0054) 손실 달에 진입한 것의 평균(사후 라벨 · 진단 전용)."""
import bisect
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
L = lab.lanes(nrl.prices)
K = {r["date"]: r["종가"] for r in json.load(open(REPO / "market-data/index_KOSPI.json"))["rows"]}
kd = sorted(K)
EV = {}
for f in (REPO / "event-data").glob("*.json"):
    d = json.load(open(f))
    EV[d["code"]] = {r["date"] for r in d["rows"]}
P0LOSS = set(json.load(open(os.environ["P0LOSS"])))
COST = 0.25
W, ZC, HS = 120, -2.5, (5, 10, 20)


def kret(d0, d1):
    return K[d1] / K[d0] - 1 if d0 in K and d1 in K else None


def est(code, i):
    c, ds = L[code]["closes"], L[code]["날"]
    if i - W - 1 < 0:
        return None
    rs, ms = [], []
    for j in range(i - W, i):
        m = kret(ds[j - 1], ds[j])
        if m is None:
            return None
        rs.append(c[j] / c[j - 1] - 1)
        ms.append(m)
    mm, mr = S.mean(ms), S.mean(rs)
    vm = sum((x - mm) ** 2 for x in ms)
    if vm <= 0:
        return None
    beta = sum((x - mm) * (y - mr) for x, y in zip(ms, rs)) / vm
    res = [y - mr - beta * (x - mm) for x, y in zip(ms, rs)]
    a = mr - beta * mm
    return beta, a, S.stdev(res), S.stdev(rs)


rows = {"충격 · 사건 없음": [], "충격 · 사건 있음": [], "충격 · 사건 모름(NA)": [], "단순 하락(대조)": []}
KSET = set(kd)
MIS = {"충격 줄의 전날이 시장 전 거래일과 다름": 0, "진입 + 20줄 날짜가 시장 달력 20거래일 뒤와 다름": 0, "검사한 충격": 0}
last = {}
for r in sorted(nrl.inside, key=lambda x: x["date"]):
    code, i, d = r["code"], r["i"], r["date"]
    if not ("20170701" <= d <= "20260831"):
        continue
    c, ds = L[code]["closes"], L[code]["날"]
    if i + 2 + max(HS) >= len(c):
        continue
    m = kret(ds[i - 1], d)
    if m is None:
        continue
    e = est(code, i)
    if e is None:
        continue
    beta, a, sres, sraw = e
    rr = c[i] / c[i - 1] - 1
    z = (rr - a - beta * m) / sres if sres > 0 else 0
    zraw = rr / sraw if sraw > 0 else 0
    kinds = []
    if z <= ZC:
        if code not in EV:
            kinds.append("충격 · 사건 모름(NA)")
        else:
            kinds.append("충격 · 사건 있음" if EV[code] & {ds[i - 1], d} else "충격 · 사건 없음")
        MIS["검사한 충격"] += 1
        ki = bisect.bisect_left(kd, d)
        if ki == 0 or kd[ki - 1] != ds[i - 1]:
            MIS["충격 줄의 전날이 시장 전 거래일과 다름"] += 1
        ke = bisect.bisect_left(kd, ds[i + 1])
        if ke + 20 >= len(kd) or kd[ke + 20] != ds[i + 21]:
            MIS["진입 + 20줄 날짜가 시장 달력 20거래일 뒤와 다름"] += 1
    if zraw <= ZC:
        kinds.append("단순 하락(대조)")
    for kd_ in kinds:
        key = (kd_, code)
        if key in last and i <= last[key] + max(HS):
            continue
        last[key] = i
        out = {"t0": d, "z": z, "code": code}
        for tag, ent in (("E1", i + 1), ("E2", i + 2 if c[i + 1] > c[i] else None)):
            if ent is None:
                continue
            for h in HS:
                g = (c[ent + h] / c[ent] - 1) * 100 - COST
                km = kret(ds[ent], ds[ent + h])
                out[f"{tag}_{h}"] = g
                out[f"{tag}_{h}_시장대비"] = g - km * 100 if km is not None else None
            out[f"{tag}_달"] = ds[ent][:6]
        rows[kd_].append(out)


def clustered(items, key):
    byd = {}
    for x in items:
        if x.get(key) is not None:
            byd.setdefault(x["t0"], []).append(x[key])
    v = [S.mean(a) for a in byd.values()]
    if len(v) < 3:
        return {"날": len(v)}
    m, sd = S.mean(v), S.stdev(v)
    return {"건": sum(len(a) for a in byd.values()), "날": len(v), "평균 %": round(m, 3), "t(날 단위)": round(m / (sd / math.sqrt(len(v))), 2) if sd > 0 else None}


def plain(items, key):
    v = [x[key] for x in items if x.get(key) is not None]
    return {"건": len(v), "사건별 평균 %": round(S.mean(v), 3)} if v else {"건": 0}


import hashlib  # noqa: E402
res = {"정의": __doc__, "달력 어긋남": MIS, "사건 자료 파일이 있는 종목 수": len(EV),
       "입력 지문": {"NRL_CACHE": hashlib.sha256(open(os.environ["NRL_CACHE"], "rb").read()).hexdigest(),
                  "index_KOSPI.json": hashlib.sha256(open(REPO / "market-data/index_KOSPI.json", "rb").read()).hexdigest(),
                  "event-data(파일 이름 · 지문 묶음)": hashlib.sha256("".join(f.name + hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted((REPO / "event-data").glob("*.json"))).encode()).hexdigest(),
                  "P0LOSS": hashlib.sha256(open(os.environ["P0LOSS"], "rb").read()).hexdigest(), "b16.py": hashlib.sha256(open(__file__, "rb").read()).hexdigest()}}
for g, items in rows.items():
    res[g] = {}
    for tag in ("E1", "E2"):
        for h in HS:
            for suf in ("", "_시장대비"):
                k = f"{tag}_{h}{suf}"
                res[g][k] = {"전체": clustered(items, k), "사건별": plain(items, k), "앞(~2021)": clustered([x for x in items if x["t0"] < "20220101"], k),
                             "뒤(2022~)": clustered([x for x in items if x["t0"] >= "20220101"], k),
                             "P0 손실 달 진입(보고만)": clustered([x for x in items if x.get(f"{tag}_달") in P0LOSS], k)}
json.dump(res, open(os.environ["OUT"], "w"), ensure_ascii=False, indent=1)
json.dump({g: [{k: v for k, v in x.items()} for x in items] for g, items in rows.items()}, open(os.environ["OUT"].replace(".json", "_events.json"), "w"), ensure_ascii=False)
print("달력 어긋남", MIS)
for g in rows:
    print(g, "충격 수", len(rows[g]))
    for k in ("E1_10", "E1_10_시장대비", "E2_10", "E2_10_시장대비", "E1_20_시장대비"):
        print("  ", k, res[g][k])
