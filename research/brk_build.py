"""BRK-FLOW-0044 자료 굽기 — 원자료를 읽자마자 [FROM, CUT] 바깥을 버리고, 그 잘린 것으로만 파생(자르기 → 파생 · 표준 모듈만).
- 원자료 넷: price-data(종가) · volume-data(거래대금 = '날' 줄의 셋째 칸) · investor-full(수급) · etf-ohlc/069500.json
- 대상: investor-full 268종목 가운데 그날 **전날까지 20거래일 평균 거래대금** 상위 100(F7b · F7c 정의)
- 표 줄 {code, date, i, price, 거래대금20, 순위} · 시장 폭(그날 대상 100종목 중 50일선 > 200일선 몫 · 30종목 이상)
- 개발: BRK_FROM=20160104 BRK_CUT=20221229(기본) · 시험(H): BRK_FROM=20050103 BRK_CUT=20161229
python3 research/brk_build.py            (BRK_SENTINEL=1이면 원자료를 읽은 직후 [FROM, CUT] 밖 값 · 줄을 바꿔 넣는 경계 시험)"""
import bisect
import glob
import hashlib
import json
import os
import pickle
import sys
from pathlib import Path

ROOT = Path("/home/user/stock-dash")
os.chdir(ROOT)
FROM = os.getenv("BRK_FROM", "20160104")
CUT = os.getenv("BRK_CUT", "20221229")
WARM, TOP, TVN = 120, 100, 20
COLS = ("개인", "외국인", "기관", "투신", "연기금", "사모")
SNAP = Path(os.getenv("BRK_SNAP", "/tmp/brk-d.pkl"))
SENT = os.getenv("BRK_SENTINEL") == "1"
EARLY, LATE = "19990104", "20260105"      # 센티널이 넣는 바깥 날


def inside(d):
    return FROM <= d <= CUT


def folder_hash(pattern):
    h = hashlib.sha256()
    for f in sorted(glob.glob(pattern)):
        h.update(Path(f).name.encode())
        h.update(hashlib.sha256(Path(f).read_bytes()).digest())
    return h.hexdigest()


def codes():
    return sorted(Path(p).stem for p in glob.glob("investor-full/*.json"))


def read_prices(cs):
    out = {}
    for c in cs:
        path = Path("price-data") / f"{c}.json"
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        rows = [(str(d), float(x)) for d, x in (data.get("closes") or []) if x and float(x) > 0]
        if SENT:
            rows = [(d, x * 3 if not inside(d) else x) for d, x in rows] + [(EARLY, 1.0), (LATE, 1.0)]
        rows = sorted((d, x) for d, x in rows if inside(d))
        if len(rows) >= 120:
            out[c] = {"name": data.get("name", ""), "rows": rows}
    return out


def read_tv(c):
    path = Path("volume-data") / f"{c}.json"
    if not path.exists():
        return [], []
    v = json.loads(path.read_text(encoding="utf-8")).get("날") or []
    got = [(str(x[0]), float(x[2]) if len(x) > 2 and x[2] else 0.0) for x in v]
    if SENT:
        got = got + [(EARLY, 1e15), (LATE, 1e15)]
    got = sorted(x for x in got if inside(x[0]))
    return [d for d, _ in got], [t for _, t in got]


def read_flow(c):
    body = json.loads((Path("investor-full") / f"{c}.json").read_text(encoding="utf-8"))
    cols = body["cols"]
    fr = [dict(zip(cols, r)) for r in body["rows"]]
    if SENT:
        fr = fr + [{"date": EARLY, **{k: 1e12 for k in COLS}}, {"date": LATE, **{k: 1e12 for k in COLS}}]
    fr = sorted((x for x in fr if inside(str(x.get("date", "")))), key=lambda x: x["date"])
    days = [x["date"] for x in fr]
    acc = {k: [0.0] for k in COLS}
    ok = [0]
    for x in fr:
        good = all(x.get(k) is not None for k in COLS)
        ok.append(ok[-1] + (1 if good else 0))
        for k in COLS:
            acc[k].append(acc[k][-1] + (x.get(k) or 0.0))
    return days, acc, ok


def sma_cmp(closes, i, a=50, b=200):
    if i < b - 1:
        return None
    return sum(closes[i - a + 1:i + 1]) / a > sum(closes[i - b + 1:i + 1]) / b


def main():
    cs = codes()
    prices = read_prices(cs)
    by_day = {}
    for c in sorted(prices):
        td, tv = read_tv(c)
        if not td:
            continue
        acc = [0.0]
        for t in tv:
            acc.append(acc[-1] + t)
        for i, (d, x) in enumerate(prices[c]["rows"]):
            if i < WARM:
                continue
            k = bisect.bisect_left(td, d)          # 전날까지
            if k < TVN:
                continue
            avg = (acc[k] - acc[k - TVN]) / TVN
            if avg <= 0:
                continue
            by_day.setdefault(d, []).append({"code": c, "date": d, "i": i, "price": x, "거래대금20": avg})
    rows, br = [], {}
    for d in sorted(by_day):
        here = sorted(by_day[d], key=lambda r: (-r["거래대금20"], r["code"]))[:TOP]
        for place, r in enumerate(here, 1):
            r["순위"] = place
        rows += here
        marks = [sma_cmp([x for _, x in prices[r["code"]]["rows"]], r["i"]) for r in here]
        marks = [m for m in marks if m is not None]
        if len(marks) >= 30:
            br[d] = sum(marks) / len(marks) * 100
    flow = {}
    for c in sorted({r["code"] for r in rows}):
        got = read_flow(c)
        if got[0]:
            flow[c] = got
    ix = json.loads(Path("etf-ohlc/069500.json").read_text())["raw"]
    if SENT:
        ix = ix + [[EARLY, 1, 1, 1, 1, 1, 1], [LATE, 1, 1, 1, 1, 1, 1]]
    ix = {x[0]: x[4] for x in ix if inside(x[0])}
    allp = [d for b in prices.values() for d, _ in b["rows"]]
    assert min(allp) >= FROM and max(allp) <= CUT
    assert min(r["date"] for r in rows) >= FROM and max(r["date"] for r in rows) <= CUT
    assert min(br) >= FROM and max(br) <= CUT and min(ix) >= FROM and max(ix) <= CUT
    assert all(not v[0] or (v[0][0] >= FROM and v[0][-1] <= CUT) for v in flow.values())
    snap = {"from": FROM, "cut": CUT, "prices": prices, "rows": rows, "br": br, "flow": flow, "ix": ix}
    blob = pickle.dumps(snap, protocol=pickle.HIGHEST_PROTOCOL)
    SNAP.write_bytes(blob)
    meta = {"from": FROM, "cut": CUT, "snapshot_sha256": hashlib.sha256(blob).hexdigest(), "snapshot_bytes": len(blob),
            "rows": len(rows), "codes": len(prices), "flow_codes": len(flow), "days": len(by_day),
            "sources": {"price-data/*.json": folder_hash("price-data/*.json"), "volume-data/*.json": folder_hash("volume-data/*.json"),
                        "investor-full/*.json": folder_hash("investor-full/*.json"),
                        "etf-ohlc/069500.json": hashlib.sha256(Path("etf-ohlc/069500.json").read_bytes()).hexdigest()},
            "code": {"research/brk_build.py": hashlib.sha256(Path("research/brk_build.py").read_bytes()).hexdigest()},
            "sentinel": SENT}
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
