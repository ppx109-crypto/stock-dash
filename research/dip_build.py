"""DIP-DEEP-0042 개발 자료 굽기 — 원자료를 읽자마자 CUT(2022-12-29)까지로 자르고, 그 잘린 것으로만 파생을 만듦(자르기 → 파생).
- 원자료: price-data/*.json(종가) · share-data/*.json(주식수 · 그날까지 접수된 것만 씀) · investor-data/*.json(수급) · etf-ohlc/069500.json
- 파생: lab.build(잘린 종가) → 표 줄 · caps.tag(시총 순위) · 시장 폭(잘린 lanes) · 수급 누적(잘린 줄) · 069500(잘린 줄)
- 1일봉 캐시(/tmp/nrl-cache.pkl) · 표(study/features.json) · nrl 모듈은 읽지도 import하지도 않음.
- 결과: SNAP(/tmp/dip-d.pkl) + 해시 표(research-exchange/claude-to-gpt/DIP-DEEP-0042/snapshot.json). 개발 도구(dip_dev)는 이 스냅샷만 읽음.
python3 research/dip_build.py            (DIP_SENTINEL=1이면 원자료를 읽은 직후 CUT 뒤 값을 바꿔 넣는 합성 시험용)"""
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
sys.path.insert(0, str(ROOT))
import caps  # noqa: E402
import final_study as FS  # noqa: E402
import lab  # noqa: E402

CUT = "20221229"
FROM = "20161001"           # 표 줄은 이날부터만 남김(지표의 앞 자료는 잘린 종가 전체에서 셈)
TOP = 100
COLS = ("개인", "외국인", "기관", "투신", "연기금", "사모")
SNAP = Path(os.getenv("DIP_SNAP", "/tmp/dip-d.pkl"))
SENT = os.getenv("DIP_SENTINEL") == "1"


def folder_hash(pattern):
    h = hashlib.sha256()
    for f in sorted(glob.glob(pattern)):
        h.update(f.encode())
        h.update(hashlib.sha256(Path(f).read_bytes()).digest())
    return h.hexdigest()


def read_prices():
    """price-data 원본 → 읽자마자 CUT까지만. (센티널: CUT 뒤 종가 × 3을 읽은 뒤 넣어 봄 — 자르기가 먼저라 사라져야 함)"""
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


def main():
    prices = read_prices()
    rows = []
    codes = sorted(prices)
    for k in range(0, len(codes), 25):
        part = {c: prices[c] for c in codes[k:k + 25]}
        for r in lab.build(part, horizons=(0,)):
            if FROM <= r["date"] <= CUT:
                r.pop("ahead", None)
                r.pop("met", None)
                rows.append(r)
    caps.tag(rows, TOP)
    rows = [r for r in rows if caps.inside(r, TOP)]
    lanes = lab.lanes(prices)
    shape = FS.shapes(lanes, {r["code"] for r in rows})
    br = FS.breadth_by_day(rows, shape)
    flow = {}
    for c in sorted({r["code"] for r in rows}):        # 순서 고정(집합 순서는 실행마다 다름)
        got = read_flow(c)
        if got and got[0]:
            flow[c] = got
    ix = json.loads(Path("etf-ohlc/069500.json").read_text())["raw"]
    if SENT:
        ix = ix + [["20230105", 1, 1, 1, 1, 1, 1]]
    ix = {x[0]: x[4] for x in ix if x[0] <= CUT}
    # 경계 확인
    assert max(d for b in prices.values() for d, _ in b["rows"]) <= CUT
    assert max(r["date"] for r in rows) <= CUT and max(br) <= CUT and max(ix) <= CUT
    assert all(not v[0] or v[0][-1] <= CUT for v in flow.values())
    snap = {"cut": CUT, "prices": prices, "rows": rows, "br": br, "flow": flow, "ix": ix}
    blob = pickle.dumps(snap, protocol=pickle.HIGHEST_PROTOCOL)
    SNAP.write_bytes(blob)
    meta = {"cut": CUT, "snapshot_sha256": hashlib.sha256(blob).hexdigest(), "snapshot_bytes": len(blob),
            "rows": len(rows), "codes": len(prices), "flow_codes": len(flow),
            "sources": {"price-data/*.json": folder_hash("price-data/*.json"),
                        "share-data/*.json": folder_hash("share-data/*.json"),
                        "investor-data/*.json": folder_hash("investor-data/*.json"),
                        "etf-ohlc/069500.json": hashlib.sha256(Path("etf-ohlc/069500.json").read_bytes()).hexdigest()},
            "code": {f: hashlib.sha256(Path(f).read_bytes()).hexdigest()
                     for f in ("research/dip_build.py", "lab.py", "caps.py", "final_study.py", "final_group.py")},
            "sentinel": SENT}
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
