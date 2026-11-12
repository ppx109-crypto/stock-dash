"""GPT H-RS 라벨 없는 진단(GPT #455 · 손익 · 승패 안 봄 · 사전등록 아님): 1일봉 정배열 갈래 후보에서 '시장 뺀 고유 강도'가
지금 순서 열쇠(rule.order = −추세 기울기 · 180일선 기울기) · 과거 수익 · G2 단기 기울기 · 종목 흔들림과 다른 정보인지.
원판 경로(장부 sha 0ec97a14… assert) · 후보 = BASE_HOLD 참 · 정배열 갈래 · 산 날 기간 안(diag24와 같은 3,329줄 기대).
정의(셈 전에 고정 · 하나만): 후보 (종목, 날 d, 칸 i)에서 i−1까지 값만.
- 시장 = 069500 종가(고정 나무 etf-data · 한투 수정주가) · 같은 '끝 날'을 가진 하루 수익끼리만 짝(시작 날도 같아야 함 · 결측 바 짝 안 지음).
- 추정 창: i−1에서 끝나는 250개 하루 수익(짝 지은 것 ≥ 200개) → 최소제곱 α · β · 잔차 σ.
- RS = 마지막 60개 짝 수익의 잔차 합 ÷ (잔차 σ × √60) — 60일 잔차 강도(표준화). 전체 기간 회귀 · 표준화 안 씀.
- 비교 변수: 추세 기울기(후보 줄 값 · 지금 순서) · 과거 20 · 60일 수익(i−1까지) · 종목 20일 σ(i−1까지) · β.
보고: 결측(이유별) · 순위 상관(전체 · 같은 날 안 평균) · 같은 날 정배열 후보 ≥ 2인 날에서 RS 1등 = 지금 순서 1등인 몫 · 층(진입 / 문 막힘 / 문까지 안 감)별 건수.
cwd = 고정 나무 · tree_run. 출력: EX_OUT json."""
import hashlib
import json
import math
import os
import sys

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "research"))
import lab  # noqa: E402
import nrl  # noqa: E402
import rule  # noqa: E402

RAW_SHA = "0ec97a14ba3d9b81168906eb332c6753d576ff57601e526c935345aafac75c99"
EST, WIN, MINPAIR = 250, 60, 200
CL = {c: [x for _, x in b["rows"]] for c, b in nrl.prices.items()}
DT = {c: [d for d, _ in b["rows"]] for c, b in nrl.prices.items()}
mk = json.load(open(os.path.join(os.getcwd(), "etf-data", "069500.json")))["closes"]
MK = [(str(d), float(x)) for d, x in mk if x]
MKR = {(MK[k - 1][0], MK[k][0]): MK[k][1] / MK[k - 1][1] - 1 for k in range(1, len(MK))}
CAND, KIN, ENTRY = {}, {}, set()
MISS = {"날짜 불일치": 0, "주가 바 모자람": 0, "짝 수익 < 200": 0, "잔차 σ 0": 0, "마지막 60 짝 모자람": 0}


def feat(code, d, i):
    xs, ds = CL[code], DT[code]
    if ds[i] != d:
        MISS["날짜 불일치"] += 1
        return None
    j = i - 1
    if j - EST < 0:
        MISS["주가 바 모자람"] += 1
        return None
    pairs = []                                   # (끝 날, 종목 수익, 시장 수익) — 시작 · 끝 날 모두 같은 것만
    for q in range(j - EST + 1, j + 1):
        m = MKR.get((ds[q - 1], ds[q]))
        if m is not None:
            pairs.append((ds[q], xs[q] / xs[q - 1] - 1, m))
    if len(pairs) < MINPAIR:
        MISS["짝 수익 < 200"] += 1
        return None
    n = len(pairs)
    mx = sum(p[2] for p in pairs) / n
    my = sum(p[1] for p in pairs) / n
    sxx = sum((p[2] - mx) ** 2 for p in pairs)
    beta = sum((p[2] - mx) * (p[1] - my) for p in pairs) / sxx if sxx > 0 else 0.0
    alpha = my - beta * mx
    res = [p[1] - alpha - beta * p[2] for p in pairs]
    sr = math.sqrt(sum(r * r for r in res) / (n - 2))
    if sr <= 1e-12:
        MISS["잔차 σ 0"] += 1
        return None
    last = [r for p, r in zip(pairs, res) if p[0] >= ds[j - WIN + 1]]
    if len(last) < WIN * 0.8:
        MISS["마지막 60 짝 모자람"] += 1
        return None
    rs = sum(last) / (sr * math.sqrt(len(last)))
    r20 = [xs[q] / xs[q - 1] - 1 for q in range(j - 19, j + 1)]
    m20 = sum(r20) / 20
    sd20 = math.sqrt(sum((r - m20) ** 2 for r in r20) / 19)
    return {"RS": rs, "β": beta, "과거20": xs[j] / xs[j - 20] - 1, "과거60": xs[j] / xs[j - 60] - 1, "σ20": sd20, "짝": n}


def hold_wrap(r):
    ok = nrl.BASE_HOLD(r)
    if ok and nrl.tier(r) == "정배열":
        CAND[(r["code"], r["date"])] = r
    return ok


def apart(row, held):
    ok = nrl.kin(row, held)
    if nrl.tier(row) == "정배열":
        KIN[(row["code"], row["date"])] = ok
    return ok


def size(r):
    if nrl.tier(r) == "정배열":
        ENTRY.add((r["code"], r["date"]))
    return nrl.BASE_SIZE(r)


rows = []
for side, pool, since in (("앞", nrl.early, rule.SINCE), ("뒤", nrl.inside, rule.MID)):
    g = lab.run(pool, nrl.prices, hold_wrap, nrl.BASE_EXIT, slots=nrl.SLOTS, rank=rule.order, since=since, apart=apart, realistic=True, cap=130,
                detail=True, size=size)
    rows += [(t["code"], t["산 날"], t["판 날"], t["손익"], t["자리"] if t.get("자리") is not None else 1) for t in g["매매목록"]]
assert hashlib.sha256(json.dumps(rows).encode()).hexdigest() == RAW_SHA, "장부가 원판과 다름"
CAND = {k: v for k, v in CAND.items() if k[1] >= rule.SINCE}
REC = []
for (c, d), r in sorted(CAND.items(), key=lambda t: t[0][1]):
    f = feat(c, d, r["i"])
    layer = "진입" if (c, d) in ENTRY else ("문 통과 · 안 삼" if KIN.get((c, d)) else ("닮은 종목 문 막힘" if (c, d) in KIN else "문까지 안 감"))
    REC.append({"날": d, "종목": c, "층": layer, "추세 기울기": r.get("추세 기울기"), **(f or {})})


def ranks(xs):
    o = sorted(range(len(xs)), key=lambda i: xs[i]); r = [0.0] * len(xs); i = 0
    while i < len(o):
        j = i
        while j + 1 < len(o) and xs[o[j + 1]] == xs[o[i]]:
            j += 1
        for k in range(i, j + 1):
            r[o[k]] = (i + j) / 2
        i = j + 1
    return r


def spear(x, y):
    if len(x) < 3:
        return None
    a, b = ranks(x), ranks(y); n = len(a); ma, mb = sum(a) / n, sum(b) / n
    t = sum((p - ma) * (q - mb) for p, q in zip(a, b)); w = math.sqrt(sum((p - ma) ** 2 for p in a) * sum((q - mb) ** 2 for q in b))
    return t / w if w else None


ok = [x for x in REC if "RS" in x and x["추세 기울기"] is not None]
VARS = ("추세 기울기", "과거20", "과거60", "σ20", "β")
summ = {"후보(정배열 갈래)": len(REC), "층": {k: sum(1 for x in REC if x["층"] == k) for k in ("진입", "문 통과 · 안 삼", "닮은 종목 문 막힘", "문까지 안 감")},
        "결측": MISS, "값 있음": len(ok), "값 있음 · 진입": sum(1 for x in ok if x["층"] == "진입"),
        "RS 분위 10 · 50 · 90": [round(sorted(x["RS"] for x in ok)[int(p * (len(ok) - 1))], 3) for p in (.1, .5, .9)],
        "β 분위 10 · 50 · 90": [round(sorted(x["β"] for x in ok)[int(p * (len(ok) - 1))], 3) for p in (.1, .5, .9)],
        "순위 상관 RS 대(전체)": {v: round(spear([x["RS"] for x in ok], [x[v] for x in ok]), 4) for v in VARS}}
byday = {}
for x in ok:
    byday.setdefault(x["날"], []).append(x)
multi = {d: v for d, v in byday.items() if len(v) >= 2}
same_day = {v: [] for v in VARS}
agree = 0
for d, v in multi.items():
    for k in VARS:
        s = spear([x["RS"] for x in v], [x[k] for x in v])
        if s is not None:
            same_day[k].append(s)
    agree += max(v, key=lambda x: x["RS"])["종목"] == max(v, key=lambda x: x["추세 기울기"])["종목"]
summ["같은 날 정배열 후보 ≥ 2인 날"] = len(multi)
summ["그날 후보 수 분포(2 · 3 ~ 5 · 6+)"] = [sum(1 for v in multi.values() if len(v) == 2), sum(1 for v in multi.values() if 3 <= len(v) <= 5),
                                     sum(1 for v in multi.values() if len(v) >= 6)]
summ["같은 날 안 순위 상관 평균(후보 ≥ 3인 날)"] = {k: (round(sum(s) / len(s), 4) if s else None) for k, s in same_day.items()}
summ["같은 날 RS 1등 = 지금 순서(추세 기울기) 1등 몫"] = round(agree / len(multi), 4) if multi else None
summ["앞(≤ 2021-12-31) · 뒤 값 있음"] = [sum(1 for x in ok if x["날"] <= "20211231"), sum(1 for x in ok if x["날"] > "20211231")]
json.dump({"장부 지문": RAW_SHA, "069500 지문": hashlib.sha256(open(os.path.join(os.getcwd(), "etf-data", "069500.json"), "rb").read()).hexdigest(),
           "요약": summ, "후보 기록": REC}, open(os.environ["EX_OUT"], "w"), ensure_ascii=False)
print(json.dumps(summ, ensure_ascii=False, indent=1))
