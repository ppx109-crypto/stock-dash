"""MPOS-0024 준비 진단(G2 · 축 방향 일치 · 새 지표별 성과 안 봄 · GPT #454 G2 답): 원판 경로(장부 = 0ec97a14… · 안에서 assert)에서
1일봉 정배열 갈래 판단 집합을 세 층으로 셈 — ① 후보(BASE_HOLD 참 · 정배열 갈래 · 산 날 기간 안) ② 엔진이 닮은 종목 문까지 본 후보(통과/막힘)
③ 실제 진입(크기 함수 호출 = 산 것). 각 후보 줄(종목 · 날 d · 칸 i)에 전일(i−1)까지 값만으로:
- 축: 기존 RNA 선(final_group.LINES = 3 · 15 · 20 · 90 · 150 · 200 · 단순평균) 가운데 단기 축 = 20일선 · 중기 축 = 90일선(셈 전에 고정).
- 기울기 z = (선[i−1] / 선[i−6] − 1) ÷ (그 종목 i−1까지 20개 하루 수익 표준편차 × √5) — 5거래일 기울기를 흔들림으로 나눔.
- G2-A 방향 일치: 둘 다 > 0 '함께 오름' · 단기 ≤ 0 < 중기 '단기 꺾임' · 단기 > 0 ≥ 중기 '중기 꺾임' · 둘 다 ≤ 0 '함께 내림'.
- G2-B 둔화: z단기 − z중기(작을수록 단기가 중기보다 약함).
- 겹침 비교: 정배열일수(구간 나이 · nrl.shape) · BASE_SIZE 신선도(정배열 10일 안 · 거래량비 ≥ 2) · 20거래일 과거 수익(i−1까지).
결측: 선 · 흔들림 셈에 필요한 바가 모자라면 결측(이유 셈). 같은 종목 결측 바는 그 종목 자기 바 기준(거래일 시차 감사: 후보 날 d의 칸 i와 날짜 일치 확인).
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
import final_group  # noqa: E402

RAW_SHA = "0ec97a14ba3d9b81168906eb332c6753d576ff57601e526c935345aafac75c99"
assert tuple(final_group.LINES) == (3, 15, 20, 90, 150, 200)
SHORT, MID, K, VOLN = 20, 90, 5, 20
CL = {c: [x for _, x in b["rows"]] for c, b in nrl.prices.items()}
DT = {c: [d for d, _ in b["rows"]] for c, b in nrl.prices.items()}
CAND, KIN, ENTRY = {}, {}, set()
MISS = {"선 · 흔들림 바 모자람": 0, "흔들림 0": 0, "날짜 불일치": 0}


def sma_at(xs, j, n):
    return sum(xs[j - n + 1:j + 1]) / n if j - n + 1 >= 0 else None


def feat(code, d, i):
    xs, ds = CL[code], DT[code]
    if ds[i] != d:
        MISS["날짜 불일치"] += 1
        return None
    j = i - 1
    need = max(MID + K, VOLN + 1, 21)
    if j - need < 0:
        MISS["선 · 흔들림 바 모자람"] += 1
        return None
    rets = [xs[q] / xs[q - 1] - 1 for q in range(j - VOLN + 1, j + 1)]
    m = sum(rets) / len(rets)
    sd = math.sqrt(sum((r - m) ** 2 for r in rets) / (len(rets) - 1))
    if sd <= 1e-12:
        MISS["흔들림 0"] += 1
        return None
    z = {}
    for tag, n in (("단기", SHORT), ("중기", MID)):
        a, b = sma_at(xs, j, n), sma_at(xs, j - K, n)
        z[tag] = (a / b - 1) / (sd * math.sqrt(K))
    s, mz = z["단기"], z["중기"]
    cat = "함께 오름" if s > 0 and mz > 0 else "단기 꺾임" if s <= 0 < mz else "중기 꺾임" if s > 0 >= mz else "함께 내림"
    return {"z단기": s, "z중기": mz, "방향": cat, "둔화": s - mz, "과거20": xs[j] / xs[j - 20] - 1}


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
spans = []
for side, pool, since in (("앞", nrl.early, rule.SINCE), ("뒤", nrl.inside, rule.MID)):
    g = lab.run(pool, nrl.prices, hold_wrap, nrl.BASE_EXIT, slots=nrl.SLOTS, rank=rule.order, since=since, apart=apart, realistic=True, cap=130,
                detail=True, size=size)
    rows += [(t["code"], t["산 날"], t["판 날"], t["손익"], t["자리"] if t.get("자리") is not None else 1) for t in g["매매목록"]]
    spans.append((since, max(r["date"] for r in pool)))
assert hashlib.sha256(json.dumps(rows).encode()).hexdigest() == RAW_SHA, "장부가 원판과 다름"
# 후보는 holds가 모든 줄에 먼저 불리므로 각 반의 since 밖 줄도 들어옴 → since 안만
CAND = {k: v for k, v in CAND.items() if k[1] >= rule.SINCE}   # 앞 반(SINCE ~ MID) · 뒤 반(MID ~) 매매 기간 안 후보만
REC = []
for (c, d), r in sorted(CAND.items(), key=lambda t: t[0][1]):
    f = feat(c, d, r["i"])
    fresh = (r.get("거래량비") or 0) >= nrl.VOL_BIG and (r.get("정배열일수") or 999) <= nrl.FRESH_DAYS
    REC.append({"날": d, "종목": c, "층": "진입" if (c, d) in ENTRY else ("문 통과 · 안 삼" if KIN.get((c, d)) else ("닮은 종목 문 막힘" if (c, d) in KIN else "문까지 안 감")),
                "정배열일수": r.get("정배열일수"), "신선": fresh, **(f or {"방향": None})})


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
    a, b = ranks(x), ranks(y); n = len(a); ma, mb = sum(a) / n, sum(b) / n
    t = sum((p - ma) * (q - mb) for p, q in zip(a, b)); w = math.sqrt(sum((p - ma) ** 2 for p in a) * sum((q - mb) ** 2 for q in b))
    return t / w if w else None


ok = [x for x in REC if x["방향"] is not None]
CATS = ("함께 오름", "단기 꺾임", "중기 꺾임", "함께 내림")
summ = {"후보(정배열 갈래)": len(REC), "층": {k: sum(1 for x in REC if x["층"] == k) for k in ("진입", "문 통과 · 안 삼", "닮은 종목 문 막힘", "문까지 안 감")},
        "결측": MISS, "값 있음": len(ok),
        "방향 분포(전체 · 진입)": {k: [sum(1 for x in ok if x["방향"] == k), sum(1 for x in ok if x["방향"] == k and x["층"] == "진입")] for k in CATS},
        "방향 분포 앞(≤ 2021-12-31) · 뒤": {k: [sum(1 for x in ok if x["방향"] == k and x["날"] <= "20211231"), sum(1 for x in ok if x["방향"] == k and x["날"] > "20211231")] for k in CATS}}
age_bins = ((1, 1), (2, 5), (6, 10), (11, 20), (21, 9999))
summ["방향 × 구간 나이(진입만)"] = {f"{lo}~{hi}": {k: sum(1 for x in ok if x["층"] == "진입" and x["방향"] == k and lo <= (x["정배열일수"] or 0) <= hi) for k in CATS} for lo, hi in age_bins}
summ["방향 × 신선(진입만)"] = {str(fr): {k: sum(1 for x in ok if x["층"] == "진입" and x["방향"] == k and x["신선"] == fr) for k in CATS} for fr in (True, False)}
e = [x for x in ok if x["층"] == "진입" and x["정배열일수"] is not None]
summ["순위 상관(진입만)"] = {"z단기 대 과거20": round(spear([x["z단기"] for x in e], [x["과거20"] for x in e]), 4),
                        "z중기 대 과거20": round(spear([x["z중기"] for x in e], [x["과거20"] for x in e]), 4),
                        "둔화 대 과거20": round(spear([x["둔화"] for x in e], [x["과거20"] for x in e]), 4),
                        "z단기 대 정배열일수": round(spear([x["z단기"] for x in e], [x["정배열일수"] for x in e]), 4),
                        "둔화 대 정배열일수": round(spear([x["둔화"] for x in e], [x["정배열일수"] for x in e]), 4)}
dv = sorted(x["둔화"] for x in ok if x["층"] == "진입" and x["날"] <= "20211231")
summ["둔화 앞 기간 진입 분위 10 · 20 · 30%"] = [round(dv[int(p * (len(dv) - 1))], 4) for p in (.1, .2, .3)] if dv else None
json.dump({"장부 지문": RAW_SHA, "요약": summ, "후보 기록": REC}, open(os.environ["EX_OUT"], "w"), ensure_ascii=False)
print(json.dumps(summ, ensure_ascii=False, indent=1))
