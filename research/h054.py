"""54회차 — +50% 넘게 오른 종목의 '오르기 전' 특징(사용자 요청 2026-09-30).
사건: 그날 종가에서 앞으로 60거래일 안에 종가가 +50% 이상 간 날(라벨만 앞날을 봄). '시작 날' = 사건 날인데 전날은 사건 날이 아닌 날.
특징: 모두 그날 종가까지 아는 값 — 일봉 표(study/features.json, daily guard.py로 검사된 값) · 시총 순위(caps.tag, 그날 아는 주식수)
· 수급(investor-data, 그날까지) · 공시(dart-events, 접수일이 그날까지) · 분기 실적(quarter-data, 접수일이 그날까지) · 시장 폭(그날 100위 안 '배열 3' 몫).
대상: 그날 시총 300위 안 · 2017-01 ~ 2026-07(라벨 60일이 2026-09-29 안에 끝나는 날까지 — 시험지 잠금).
보는 것: 특징 칸마다 '시작 날이 될 확률 ÷ 전체 확률'(들어올림) — 세 시기(2017~19 · 2020~22 · 2023~26)에서 한결같은지."""
import sys, json, bisect, gc
sys.path.insert(0, "/home/user/stock-dash")
from pathlib import Path
import numpy as np
import caps, lab
import final_group

H_DAYS, GOAL, END = 60, 50.0, "20260930"
rows = lab.load()
caps.tag(rows, 300)
rows = [r for r in rows if "20161001" <= r["date"] < END and r.get(caps.RANK) and r[caps.RANK] <= 300]
gc.collect()
print("줄", len(rows), flush=True)
# 시장 폭: 그날 100위 안에서 배열 3 몫
by_day = {}
for r in rows:
    if r[caps.RANK] <= 100:
        by_day.setdefault(r["date"], []).append(1 if r.get("배열") == 3 else 0)
breadth = {d: sum(v) / len(v) * 100 for d, v in by_day.items() if len(v) >= 30}
# 라벨: 종가 경로(price-data, 시험지 앞까지만)
closes = {}
def path(code):
    if code not in closes:
        try:
            got = [x for x in json.loads(Path(f"price-data/{code}.json").read_text(encoding="utf-8"))["closes"] if x[0] < END]
        except (OSError, ValueError):
            got = []
        closes[code] = ([x[0] for x in got], np.array([x[1] for x in got], float))
    return closes[code]
def label(code, day):
    d, c = path(code)
    k = bisect.bisect_left(d, day)
    if k >= len(d) or d[k] != day or k + H_DAYS >= len(d): return None
    return (c[k + 1:k + 1 + H_DAYS].max() / c[k] - 1) * 100
# 수급 · 공시 · 분기
FL, EV, QT = {}, {}, {}
def flows(code):
    if code not in FL:
        rs = final_group.flow_rows(code)
        FL[code] = ([r["date"] for r in rs], rs)
    return FL[code]
def events(code):
    if code not in EV:
        try:
            got = json.loads(Path(f"dart-events/{code}.json").read_text(encoding="utf-8")).get("rows") or {}
        except (OSError, ValueError):
            got = {}
        EV[code] = {k: sorted(str(x.get("rcept_no", ""))[:8] for x in v if x.get("rcept_no")) for k, v in got.items()}
    return EV[code]
def num(s):
    try: return float(str(s).replace(",", ""))
    except (TypeError, ValueError): return None
def quarters(code):
    if code not in QT:
        try:
            got = json.loads(Path(f"quarter-data/{code}.json").read_text(encoding="utf-8")).get("rows") or {}
        except (OSError, ValueError):
            got = {}
        qs = []
        for k, v in got.items():
            if not isinstance(v, dict): continue
            rc = str(v.get("접수번호", ""))[:8]
            op, op0, sa, sa0 = (num(v.get(x)) for x in ("영업이익", "영업이익_작년", "매출", "매출_작년"))
            if rc: qs.append((rc, op, op0, sa, sa0))
        QT[code] = sorted(qs, key=lambda x: x[0])
    return QT[code]
def feat(r):
    code, day = r["code"], r["date"]
    f = {k: r.get(k) for k in ("배열", "정배열일수", "장기상승일수", "20일 전 대비", "60일 전 대비", "거래량비", "60일 전고점 대비",
                               "120일 전고점 대비", "250일 전고점 대비", "변동성", "밴드 자리", "밴드 폭", "모임폭", "추세 기울기", "단기 기울기", "EMA20 이격", "정배열폭")}
    f["순위"] = r[caps.RANK]
    f["시장폭"] = breadth.get(day)
    ds, rs = flows(code)
    k = bisect.bisect_right(ds, day)
    for n in (5, 20):
        last = rs[max(0, k - n):k]
        if len(last) == n:
            for col in ("외국인", "투신", "개인", "기관", "연기금", "사모"):
                f[f"{col}{n}일 순매수 날 몫"] = sum(1 for x in last if (x.get(col) or 0) > 0) / n
    ev = events(code)
    lo20 = str(int(day) - 100)  # 대략 한 달 반(날짜 수 차이 아님) — 아래에서 정확히 거래일로 씀
    d, _ = path(code); kk = bisect.bisect_left(d, day); lo = d[max(0, kk - 60)] if d else day
    for name, kinds in (("자사주 공시 60일", ("자기주식취득", "자기주식신탁체결")), ("희석 공시 60일", ("유상증자", "전환사채", "신주인수권부사채", "교환사채")),
                        ("무상증자 60일", ("무상증자", "유무상증자"))):
        f[name] = int(any(lo < x <= day for kd in kinds for x in ev.get(kd, ())))
    q = [x for x in quarters(code) if x[0] <= day]
    if q:
        rc, op, op0, sa, sa0 = q[-1]
        f["영업이익 작년 대비"] = ((op - op0) / abs(op0) * 100) if (op is not None and op0) else None
        f["매출 작년 대비"] = ((sa - sa0) / abs(sa0) * 100) if (sa is not None and sa0) else None
        f["흑자 전환"] = int(op is not None and op0 is not None and op > 0 >= op0)
        f["실적 공시 뒤 날수"] = (int(day[:4]) * 372 + int(day[4:6]) * 31 + int(day[6:])) - (int(rc[:4]) * 372 + int(rc[4:6]) * 31 + int(rc[6:]))
    return f
data = []
for r in rows:
    y = label(r["code"], r["date"])
    if y is None: continue
    data.append((r["code"], r["date"], y, feat(r)))
del rows; gc.collect()
data.sort(key=lambda x: (x[0], x[1]))
# 시작 날
start = set()
prev = {}
for code, day, y, f in data:
    hit = y >= GOAL
    if hit and not prev.get(code, False): start.add((code, day))
    prev[code] = hit
import pickle
pickle.dump((data, sorted(start)), open("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/h054.pkl", "wb"))
PER = (("2017~19", "20170101", "20200101"), ("2020~22", "20200101", "20230101"), ("2023~26", "20230101", END))
def per(day):
    for n, a, b in PER:
        if a <= day < b: return n
print("날 수", len(data), "· 시작 날", len(start), "· 사건 날(60일 안 +50%)", sum(1 for x in data if x[2] >= GOAL), flush=True)
for n, a, b in PER:
    tot = [x for x in data if a <= x[1] < b]
    print(f"  {n}: 날 {len(tot)} · 시작 날 {sum(1 for x in tot if (x[0], x[1]) in start)} · 기본 확률 {sum(1 for x in tot if (x[0], x[1]) in start) / max(len(tot), 1) * 100:.3f}%", flush=True)
keys = sorted({k for x in data for k in x[3]})
out = {}
for key in keys:
    vals = np.array([x[3].get(key) if x[3].get(key) is not None else np.nan for x in data], float)
    ok = ~np.isnan(vals)
    if ok.sum() < 1000: continue
    uniq = np.unique(vals[ok])
    if len(uniq) <= 6:
        edges = None; buck = lambda v: f"={v:g}"
    else:
        edges = np.nanquantile(vals, [0.1, 0.3, 0.5, 0.7, 0.9])
        buck = lambda v: ("~10%" if v <= edges[0] else "10~30%" if v <= edges[1] else "30~50%" if v <= edges[2] else "50~70%" if v <= edges[3] else "70~90%" if v <= edges[4] else "90%~")
    table = {}
    for (code, day, y, f), v in zip(data, vals):
        if np.isnan(v): continue
        p = per(day)
        if p is None: continue
        b = buck(v)
        t = table.setdefault(b, {n: [0, 0] for n, _, _ in PER})
        t[p][0] += 1; t[p][1] += (code, day) in start
    base = {n: (sum(1 for x in data if a <= x[1] < b and (x[0], x[1]) in start) / max(sum(1 for x in data if a <= x[1] < b), 1)) for n, a, b in PER}
    lines = []
    for b in sorted(table):
        lifts = [(table[b][n][1] / table[b][n][0]) / base[n] if table[b][n][0] and base[n] else float("nan") for n, _, _ in PER]
        lines.append((b, lifts, [table[b][n] for n, _, _ in PER]))
    out[key] = (edges.tolist() if edges is not None else None, lines)
    print(f"  [{key}] 칸 경계 {np.round(edges, 2).tolist() if edges is not None else '값 그대로'}", flush=True)
    for b, lifts, cnt in lines:
        print(f"      {b:8s} 들어올림 " + " · ".join(f"{l:4.2f}" for l in lifts) + "   (날/시작: " + " · ".join(f"{c[0]}/{c[1]}" for c in cnt) + ")", flush=True)
json.dump({"keys": {k: v for k, v in out.items()}}, open("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/h054.json", "w"), ensure_ascii=False, default=float)
print("끝", flush=True)
