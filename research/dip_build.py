"""DIP-DEEP-0042 개발 자료 굽기 — 원자료를 읽자마자 CUT(2022-12-29)까지로 자르고, 그 잘린 것으로만 파생을 만듦(자르기 → 파생).
- round 4 안(GPT #193 6095950168 지적 반영 · 사용자 예외 승인 전 준비):
  · lab.build · caps.tag를 쓰지 않음(그 안에서 volume-data · public-data · opinion-data · event-data · loan-data를 읽기 때문).
  · 읽는 원자료는 넷뿐: price-data(종가) · share-data(주식수) · investor-data(수급) · etf-ohlc/069500.json. 모두 읽은 즉시 CUT까지로 자름.
  · 표 줄은 {code, date, i, price, 시가총액, 시총순위}만 만듦(시가총액 = 그날까지 접수된 주식수 × 그날 종가 · CAPS_ADJ 경로 없음).
  · 시장 폭 = 그날 시총 100위 안 종목 가운데 50일 단순평균 > 200일 단순평균인 몫(잘린 종가로 · 30종목 이상인 날만).
- 1일봉 캐시 · 표(study/features.json) · nrl · lab · caps 모듈을 읽지도 import하지도 않음(표준 모듈만).
- 결과: SNAP(/tmp/dip-d.pkl) + 해시 표(snapshot.json). 개발 도구(dip_dev)는 이 스냅샷만 읽음.
python3 research/dip_build.py            (DIP_SENTINEL=1이면 원자료를 읽은 직후 CUT 뒤 값 · 줄을 바꿔 넣는 경계 시험)"""
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
CUT = "20221229"
FROM = "20161001"
WARM = 120
TOP = 100
COLS = ("개인", "외국인", "기관", "투신", "연기금", "사모")
SNAP = Path(os.getenv("DIP_SNAP", "/tmp/dip-d.pkl"))
SENT = os.getenv("DIP_SENTINEL") == "1"
if os.getenv("CAPS_ADJ", "0") != "0":
    sys.exit("CAPS_ADJ가 켜져 있음 — 이 굽기는 원 주식수만 씀(멈춤)")


def folder_hash(pattern):
    h = hashlib.sha256()
    for f in sorted(glob.glob(pattern)):
        h.update(Path(f).name.encode())
        h.update(hashlib.sha256(Path(f).read_bytes()).digest())
    return h.hexdigest()


def read_prices():
    out = {}
    for path in sorted(Path("price-data").glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        rows = [(str(d), float(c)) for d, c in (data.get("closes") or []) if c and float(c) > 0]
        if SENT:
            rows = [(d, c * 3 if d > CUT else c) for d, c in rows] + [("20230105", 1.0)]
        rows = [(d, c) for d, c in rows if d <= CUT]
        if len(rows) >= 120:
            out[path.stem] = {"name": data.get("name", ""), "rows": rows}
    return out


def read_shares(code):
    path = Path("share-data") / f"{code}.json"
    if not path.exists():
        return []
    body = json.loads(path.read_text(encoding="utf-8"))
    got = [(str(d), int(c)) for d, c in body.get("날") or [] if d and c]
    if SENT:
        got = got + [("20230105", 10 ** 12)]
    return sorted(x for x in got if x[0] <= CUT)


def read_flow(code):
    try:
        body = json.loads((Path("investor-data") / f"{code}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    cols = body.get("cols") or []
    fr = [dict(zip(cols, one)) for one in body.get("rows") or []]
    if SENT:
        fr = fr + [{"date": "20230105", **{c: 1e12 for c in COLS}}]
    fr = [x for x in fr if str(x.get("date", "")) <= CUT]
    days = [x["date"] for x in fr]
    acc = {c: [0.0] for c in COLS}
    ok = [0]
    for x in fr:
        good = all(x.get(c) is not None for c in COLS)
        ok.append(ok[-1] + (1 if good else 0))
        for c in COLS:
            acc[c].append(acc[c][-1] + (x.get(c) or 0.0))
    return days, acc, ok


def sma_cmp(closes, i, a=50, b=200):
    if i < b - 1:
        return None
    return sum(closes[i - a + 1:i + 1]) / a > sum(closes[i - b + 1:i + 1]) / b


def main():
    prices = read_prices()
    by_day = {}
    for code in sorted(prices):
        sh = read_shares(code)
        if not sh:
            continue
        sd = [d for d, _ in sh]
        for i, (d, c) in enumerate(prices[code]["rows"]):
            if i < WARM or d < FROM:
                continue
            k = bisect.bisect_right(sd, d) - 1
            if k < 0:
                continue
            by_day.setdefault(d, []).append({"code": code, "date": d, "i": i, "price": c, "시가총액": sh[k][1] * c})
    rows = []
    br = {}
    for d in sorted(by_day):
        here = sorted(by_day[d], key=lambda r: (-r["시가총액"], r["code"]))
        top = here[:TOP]
        for place, r in enumerate(top, 1):
            r["시총순위"] = place
        rows += top
        marks = [sma_cmp([x for _, x in prices[r["code"]]["rows"]], r["i"]) for r in top]
        marks = [m for m in marks if m is not None]
        if len(marks) >= 30:
            br[d] = sum(marks) / len(marks) * 100
    flow = {}
    for c in sorted({r["code"] for r in rows}):
        got = read_flow(c)
        if got and got[0]:
            flow[c] = got
    ix = json.loads(Path("etf-ohlc/069500.json").read_text())["raw"]
    if SENT:
        ix = ix + [["20230105", 1, 1, 1, 1, 1, 1]]
    ix = {x[0]: x[4] for x in ix if x[0] <= CUT}
    assert max(d for b in prices.values() for d, _ in b["rows"]) <= CUT
    assert max(r["date"] for r in rows) <= CUT and max(br) <= CUT and max(ix) <= CUT
    assert all(not v[0] or v[0][-1] <= CUT for v in flow.values())
    snap = {"cut": CUT, "prices": prices, "rows": rows, "br": br, "flow": flow, "ix": ix}
    blob = pickle.dumps(snap, protocol=pickle.HIGHEST_PROTOCOL)
    SNAP.write_bytes(blob)
    meta = {"cut": CUT, "snapshot_sha256": hashlib.sha256(blob).hexdigest(), "snapshot_bytes": len(blob),
            "rows": len(rows), "codes": len(prices), "flow_codes": len(flow), "days": len(by_day),
            "sources": {"price-data/*.json": folder_hash("price-data/*.json"),
                        "share-data/*.json": folder_hash("share-data/*.json"),
                        "investor-data/*.json": folder_hash("investor-data/*.json"),
                        "etf-ohlc/069500.json": hashlib.sha256(Path("etf-ohlc/069500.json").read_bytes()).hexdigest()},
            "code": {"research/dip_build.py": hashlib.sha256(Path("research/dip_build.py").read_bytes()).hexdigest()},
            "CAPS_ADJ": os.getenv("CAPS_ADJ", "0"), "sentinel": SENT}
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
