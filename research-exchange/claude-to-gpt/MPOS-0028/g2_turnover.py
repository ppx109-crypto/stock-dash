"""G2_TURNOVER.md(셈 전 커밋 e759931b4) 2 ~ 6절: 공매도 정보의 RNA 후보 가용성 · 순위 겹침. 손익 · 가격 수익 안 읽음.
python3 g2_turnover.py <cands.json> <short-data 폴더> <출력 json> [test]"""
import json
import os
import random
import sys
from collections import Counter, defaultdict
from statistics import median

BAN = (("20200316", "20210502"), ("20231106", "20250330"))
PART = ("20210503", "20231105")


def load(folder):
    S = {}
    for f in sorted(os.listdir(folder)):
        if f.endswith(".json"):
            d = json.load(open(os.path.join(folder, f), encoding="utf-8"))
            S[d["code"]] = {r[0]: (r[1], r[2], r[3]) for r in d["rows"]}   # 날 → (공매도량, 비중, 거래량)
    return S


def calendar(S):
    c = Counter(d for v in S.values() for d in v)
    return sorted(d for d, n in c.items() if n > 100)


def window(cal, d, n, lag0=False):
    """판단일 d 앞 n 시장 거래일(lag0=True면 d 포함 · 돌연변이)."""
    import bisect
    i = bisect.bisect_right(cal, d) if lag0 else bisect.bisect_left(cal, d)
    return cal[max(0, i - n):i] if i >= n else None


def regime(w):
    lo, hi = w[0], w[-1]
    if any(not (hi < a or lo > b) for a, b in BAN):
        return "금지 닿음"
    if not (hi < PART[0] or lo > PART[1]):
        return "부분 재개"
    return "전면 허용"


def value(S, cal, code, d, kind, lag0=False):
    """(상태, 값). kind = F5 | D5."""
    if code not in S:
        return "파일 없음", None
    n = 20 if kind == "F5" else 5
    w = window(cal, d, n, lag0)
    if w is None:
        return "관측 부족", None
    rows = [S[code][x] for x in w if x in S[code] and S[code][x][2] and S[code][x][2] > 0]
    if len(rows) < (15 if kind == "F5" else 5):
        return "관측 부족", None
    rg = regime(w)
    if rg == "금지 닿음":
        return rg, None
    if sum(r[0] for r in rows) <= 0:
        return "공매도 합 0", None
    v = sum(r[1] for r in rows) / len(rows) if kind == "F5" else sum(r[0] for r in rows) / sum(r[2] for r in rows)
    return ("유효" if rg == "전면 허용" else "부분 재개 유효"), v


def spearman(a, b):
    n = len(a)
    ra = {x: i for i, x in enumerate(a)}
    rb = {x: i for i, x in enumerate(b)}
    return 1 - 6 * sum((ra[x] - rb[x]) ** 2 for x in a) / (n * (n * n - 1))


def compare(byday, kind, bought):
    """byday: 날 → [(종목, 순위 열쇠, 값)] (값 있는 것만)."""
    days = {d: v for d, v in byday.items() if len(v) >= 2}
    if not days:
        return {"고르기 관련 날": 0}
    agree, rho, ns, rnd = 0, [], [], []
    for d, v in days.items():
        now = [c for c, k, _ in sorted(v, key=lambda t: (t[1], t[0]))]
        alt = [c for c, _, x in sorted(v, key=lambda t: (t[2], t[0]))]
        agree += now[0] == alt[0]
        rho.append(spearman(now, alt))
        ns.append(len(v))
        rnd.append(1 / len(v))
    bd = [(d, c) for d, v in days.items() for c, _, _ in v if (c, d) in bought]
    b_top = sum(1 for d, c in bd if min(days[d], key=lambda t: (t[2], t[0]))[0] == c)
    return {"고르기 관련 날": len(days), "1등 일치율": agree / len(days), "무작위 기준(1/후보 수 평균)": sum(rnd) / len(rnd),
            "스피어만 가운데값": median(rho), "후보 수 가운데값 · 최대": [median(ns), max(ns)],
            f"산 종목(그날 {kind} 값 있는 후보 2개 이상)": len(bd), f"그중 {kind} 1등": b_top}


def analyse(S, cands, bought):
    cal = calendar(S)
    out = {"시장 달력": [cal[0], cal[-1], len(cal)]}
    for kind in ("F5", "D5"):
        st, per, byday = Counter(), defaultdict(Counter), {"유효": defaultdict(list), "부분 재개 유효": defaultdict(list)}
        for code, d, key in cands:
            s, v = value(S, cal, code, d, kind)
            st[s] += 1
            per[d[:4]][s] += 1
            if v is not None:
                byday[s][d].append((code, key, v))
        out[kind] = {"상태": dict(st), "해별 상태": {y: dict(c) for y, c in sorted(per.items())},
                     "주 표본(전면 허용)": compare(byday["유효"], kind, bought),
                     "부분 재개(잠정)": compare(byday["부분 재개 유효"], kind, bought)}
    # 관측 감소 시작(270종목 합 공매도량 ÷ 거래량 < 0.5%가 처음 나온 날 · 공식 금지 시작 근처)
    obs = {}
    for start in ("20200316", "20231106"):
        for x in cal[cal.index(next(c for c in cal if c >= start)) - 3:][:8]:
            sv = sum(S[c][x][0] for c in S if x in S[c])
            vv = sum(S[c][x][2] for c in S if x in S[c] and S[c][x][2])
            obs.setdefault(start, []).append([x, round(100 * sv / vv, 3)])
    out["공식 금지 시작 앞뒤 270종목 합 공매도량 ÷ 거래량 %"] = obs
    return out


def test(S, cands):
    cal = calendar(S)
    rnd = random.Random(20261019)
    smp = rnd.sample(cands, 300)
    bad_cut = caught = 0
    for code, d, _ in smp:
        if code not in S:
            continue
        for kind in ("F5", "D5"):
            for lag0 in (False, True):
                a = value(S, cal, code, d, kind, lag0)
                keep = S[code]
                S[code] = {x: ((r[0] * rnd.uniform(0, 9), rnd.uniform(0, 50), r[2] * rnd.uniform(0.1, 9)) if x >= d else r)
                           for x, r in keep.items()}
                b = value(S, cal, code, d, kind, lag0)
                S[code] = keep
                if not lag0 and a != b:
                    bad_cut += 1
                if lag0 and a != b:
                    caught += 1
    assert bad_cut == 0, bad_cut
    assert caught > 0, "돌연변이(당일 포함)가 안 잡힘"
    # 합성 분류 시험
    cal2 = [f"2020{m:02d}{d:02d}" for m in (1, 2, 3, 4) for d in range(1, 29)]
    T = {"A": {x: (10, 5.0, 100) for x in cal2}, "Z": {x: (0, 0.0, 100) for x in cal2},
         "F": {x: (10, 5.0, 100) for x in cal2[:30]}}
    assert value(T, cal2, "A", "20200210", "F5") == ("유효", 5.0)
    assert value(T, cal2, "A", "20200320", "F5")[0] == "금지 닿음"
    assert value(T, cal2, "Z", "20200210", "F5")[0] == "공매도 합 0"
    assert value(T, cal2, "F", "20200228", "F5")[0] == "관측 부족"
    assert value(T, cal2, "Q", "20200210", "F5")[0] == "파일 없음"
    assert value(T, cal2, "A", "20200210", "D5") == ("유효", 0.1)
    return {"자르기 시험 다름": bad_cut, "돌연변이 잡힘(당일 포함 · 값 바뀐 경우)": caught, "합성 분류 시험": "통과"}


if __name__ == "__main__":
    C = json.load(open(sys.argv[1], encoding="utf-8"))
    S = load(sys.argv[2])
    if len(sys.argv) > 4 and sys.argv[4] == "test":
        r = test(S, C["후보"])
    else:
        r = analyse(S, C["후보"], {tuple(x) for x in C["산 것"]})
        r["후보 수"] = len(C["후보"])
        r["산 (종목, 날)"] = len(C["산 것"])
    json.dump(r, open(sys.argv[3], "w"), ensure_ascii=False, indent=1)
    print(json.dumps(r, ensure_ascii=False)[:3000])
