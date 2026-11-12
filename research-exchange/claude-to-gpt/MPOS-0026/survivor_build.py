"""생존 편향 판 NRL 캐시 만들기(SURVIVOR.md). EX_SV=A | B.
- 2020-01-02(공공 자료 첫날) 앞: 정직 캐시 next 판과 같은 순위(주식수 접수일 다음 거래일 × 종가 · 우리 507종목).
- 그 뒤: 공공 자료 실제 시가총액 순위 · 우선주(코드 끝자리 ≠ 0) 뺌. A = 우리 종목끼리 · B = 그날 상장 전 보통주(빠진 종목 포함).
- B: 실제 100위에 든 적 있는 보통주 가운데 우리 목록에 없는 종목을 공공 자료 가격(대비로 이어 붙인 수정 종가)으로 행을 만듦 ·
  거래량비는 공공 거래량으로(lab.volume_line을 그 종목만 바꿔 끼움).
- 달 문턱 · shape · BR은 이 판의 행 · inside로 다시 셈(honest_cache와 같은 함수).
출력: EX_OUT(nrl.py 캐시 모양) · EX_OUT_T(T · 빠진 종목 · 실측). cwd = 고정 나무 · tree_run. 손익 없음."""
import csv
import json
import os
import pickle
import sys
import time

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "research"))
HC = os.environ["EX_HC"]
ns = {"__name__": "honest_cache", "__file__": HC}
exec(compile(open(HC, encoding="utf-8").read(), HC, "exec"), ns)
import caps  # noqa: E402
import lab  # noqa: E402
import rule  # noqa: E402
import study  # noqa: E402
import final_study as F  # noqa: E402

assert not caps.ADJ
SV, OUT, OUT_T, TMP = os.environ["EX_SV"], os.environ["EX_OUT"], os.environ["EX_OUT_T"], os.environ["EX_TMP"]
t0 = time.time()
P = study.load_prices()
OURS = set(P)
pub = {}
for y in range(2020, 2027):
    for r in csv.DictReader(open(f"public-daily-v2/{y}.csv", encoding="utf-8")):
        pub.setdefault(r["날"], []).append(r)
PDAYS = sorted(pub)
FIRST = PDAYS[0]
common = lambda c: c[-1] == "0"   # noqa: E731  우선주 뺌(pick_universe.py와 같은 끝자리 규칙)
rank_pub = {}
for d in PDAYS:
    rs = [r for r in pub[d] if common(r["코드"]) and r["시가총액(억)"] and (SV == "B" or r["코드"] in OURS)]
    rs.sort(key=lambda r: (-float(r["시가총액(억)"]), r["코드"]))
    rank_pub[d] = {r["코드"]: (k, float(r["시가총액(억)"]) * 1e8) for k, r in enumerate(rs, 1)}
missing = []
pubvol = {}
if SV == "B":
    missing = sorted({c for d in PDAYS for c, (k, _) in rank_pub[d].items() if k <= rule.TOP} - OURS)
    pos = {d: i for i, d in enumerate(PDAYS)}
    for c in missing:
        seq = sorted((r["날"], float(r["종가"]), float(r["대비"] or 0), float(r["거래량"] or 0)) for d in PDAYS for r in pub[d] if r["코드"] == c)
        rows, prev_d, adj = [], None, None
        for d, close, diff, vol in seq:
            if adj is None:
                adj = close
            elif pos[d] == pos[prev_d] + 1 and close - diff > 0:
                adj *= close / (close - diff)          # 기준가(분할 · 권리락 맞춤)로 그날 수정 수익
            else:
                adj *= close / prev_close              # 400위 밖이던 날을 건너뜀(수정 못 함 · 드묾)
            rows.append((d, round(adj, 6)))
            prev_d, prev_close = d, close
            pubvol.setdefault(c, {})[d] = vol
        if len(rows) >= 120:
            P[c] = {"name": seq and next(r["이름"] for r in pub[seq[0][0]] if r["코드"] == c), "rows": rows}
_vl = lab.volume_line


def volume_line(code, days):
    if code not in pubvol:
        return _vl(code, days)
    import statistics                          # lab.volume_line 본문과 같은 셈(거래량 출처만 공공 자료)
    seen = pubvol[code]
    line = [seen.get(day) for day in days]
    out = [None] * len(days)
    for k in range(len(days)):
        if not line[k]:
            continue
        back = [v for v in line[max(0, k - lab.VOLUME_BACK):k] if v]
        if len(back) >= lab.VOLUME_BACK // 2:
            middle = statistics.median(back)
            if middle:
                out[k] = line[k] / middle
    return out


lab.volume_line = volume_line
known = ns["make_known"]("next")
os.makedirs(TMP, exist_ok=True)
vols = []
for c in sorted(P):
    keep = []
    for r in lab.build({c: P[c]}, horizons=(0,)):
        r.pop("ahead", None)
        vols.append((r["date"], r.get("변동성")))
        if r["date"] >= ns["KEEP_FROM"]:
            keep.append(r)
    with open(os.path.join(TMP, f"{c}.pkl"), "wb") as fh:
        pickle.dump(keep, fh, protocol=pickle.HIGHEST_PROTOCOL)
# 2020 앞: 정직 next 판 순위(우리 종목 · 그날 행끼리) · 뒤: 공공 순위
pre = {}
for c in sorted(P):
    if c not in OURS:
        continue
    for r in pickle.load(open(os.path.join(TMP, f"{c}.pkl"), "rb")):
        if r["date"] < FIRST:
            cnt = known(c, r["date"])
            if cnt is not None and r.get("price"):
                pre.setdefault(r["date"], []).append((c, cnt * r["price"]))
rank_pre = {}
for d, here in pre.items():
    here.sort(key=lambda one: -one[1])
    for place, (c, s) in enumerate(here, 1):
        rank_pre[(c, d)] = (place, s)
inside, norank = {}, 0
for c in sorted(P):
    for r in pickle.load(open(os.path.join(TMP, f"{c}.pkl"), "rb")):
        d = r["date"]
        got = rank_pre.get((c, d)) if d < FIRST else (rank_pub.get(d) or {}).get(c)
        if d >= FIRST and d not in rank_pub:
            norank += 1
        if got is not None:
            r[caps.RANK], r[caps.SIZE] = got
        if caps.inside(r, rule.TOP):
            inside[(c, d)] = r
first_day = {}
for d, _ in vols:
    if d < first_day.get(d[:6], "99999999"):
        first_day[d[:6]] = d
T = ns["month_edges_asof"](vols, sorted(m for m in first_day if m >= ns["MONTH_FROM"]), first_day)
lanes = lab.lanes(P)
shape = F.shapes(lanes, {k[0] for k in inside})
BR = F.breadth_by_day(list(inside.values()), shape)
ins = [inside[k] for k in sorted(inside, key=lambda k: (k[1], k[0])) if k[1] >= rule.SINCE]
pickle.dump((P, lanes, shape, BR, ins, None, None), open(OUT, "wb"), protocol=pickle.HIGHEST_PROTOCOL)
since20 = [k for k in inside if k[1] >= FIRST]
meas = {"판": SV, "공공 첫날": FIRST, "빠진 종목(행 만든 것)": [c for c in missing if c in P], "빠진 종목(120일 못 채움)": [c for c in missing if c not in P],
        "inside 행(SINCE ~)": len(ins), "2020 ~ inside 행": len(since20), "2020 ~ inside 중 빠진 종목 행": sum(1 for k in since20 if k[0] in missing),
        "2020 ~ 날 inside 수 최소 · 최대": [min(v) if (v := list(__import__('collections').Counter(k[1] for k in since20).values())) else None, max(v) if v else None],
        "공공 자료에 없는 날의 행(순위 없음)": norank, "초": round(time.time() - t0, 1)}
pickle.dump({"T": T, "missing": missing, "실측": meas}, open(OUT_T, "wb"))
print(json.dumps(meas, ensure_ascii=False))
