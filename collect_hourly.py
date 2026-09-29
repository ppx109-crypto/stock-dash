"""1시간봉 모으기(1시간봉 RL 재료, 조회 전용).

야후 파이낸스 60분봉(.KS · .KQ)은 약 730거래일(2023-09~)까지 거슬러 줍니다. 처음에 한 번 다 받고, 그 뒤로는
날마다 새 봉을 이어 붙여 과거가 계속 쌓이게 합니다(야후 창이 밀려도 저장소에는 남음).

저장: hourly-data/{종목코드}/{해}.csv — 한 줄에 "YYYYMMDDHH,시가,고가,저가,종가,거래량" (시각은 한국 시각, 봉이 시작한 시).
미래 참조 막기: **장이 끝난 날의 봉만** 저장합니다(한국 시각 16시 전에 돌면 오늘 봉은 버림). 값이 비어 있는 봉도 버립니다.
종목: hourly-data/universe.json(2023-09 뒤로 하루라도 시총 150위 안에 든 종목) + 코스피 · 코스닥 지수.
python collect_hourly.py [종목코드,...]
"""
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

HOME = Path("hourly-data")
KST = timezone(timedelta(hours=9))
INDEXES = {"KOSPI": "^KS11", "KOSDAQ": "^KQ11"}
URL = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}"


def parse(payload):
    """야후 응답에서 [(YYYYMMDDHH, o, h, l, c, v)]. 값이 빈 봉과 장 시간(9~15시) 밖 봉은 버림."""
    res = ((payload or {}).get("chart") or {}).get("result") or []
    if not res:
        return []
    one = res[0]
    ts = one.get("timestamp") or []
    q = (((one.get("indicators") or {}).get("quote")) or [{}])[0]
    found = []
    for k, t in enumerate(ts):
        try:
            o, h, l, c = (q.get(n)[k] for n in ("open", "high", "low", "close"))
            v = (q.get("volume") or [None] * len(ts))[k] or 0
        except (TypeError, IndexError):
            continue
        if None in (o, h, l, c) or min(o, h, l, c) <= 0:
            continue
        at = datetime.fromtimestamp(int(t), KST)
        if not 9 <= at.hour <= 15:
            continue
        found.append((at.strftime("%Y%m%d%H"), round(o, 2), round(h, 2), round(l, 2), round(c, 2), int(v)))
    return found


def closed_only(bars, now=None):
    """장이 끝난 날의 봉만. 16시(한국) 전이면 오늘 봉을 버림 — 아직 움직이는 봉을 저장하지 않음."""
    now = now or datetime.now(KST)
    today = now.strftime("%Y%m%d")
    if now.hour >= 16:
        return [b for b in bars if b[0][:8] <= today]
    return [b for b in bars if b[0][:8] < today]


def merge(folder, bars):
    """해마다 파일에 합침. 새로 받은 날은 **그날 봉을 통째로** 새 것으로 바꿈(야후는 가장 최근 날만 15시 봉을 따로 주다가
    나중에 14시 봉에 합치므로, 시각 단위로 덮으면 낡은 15시 봉이 남음). 바뀐 파일 수를 돌려줌."""
    by_year = {}
    for b in bars:
        by_year.setdefault(b[0][:4], []).append(b)
    changed = 0
    for year, new in by_year.items():
        path = folder / f"{year}.csv"
        old = {}
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                parts = line.split(",")
                if len(parts) == 6:
                    old[parts[0]] = line
        before = dict(old)
        fresh_days = {b[0][:8] for b in new}
        old = {k: v for k, v in old.items() if k[:8] not in fresh_days}
        for b in new:
            old[b[0]] = ",".join(str(x) for x in b)
        if old != before:
            folder.mkdir(parents=True, exist_ok=True)
            path.write_text("\n".join(old[k] for k in sorted(old)) + "\n", encoding="utf-8")
            changed += 1
    return changed


def fetch(sym, rng="730d"):
    r = requests.get(URL.format(sym=sym), params={"interval": "60m", "range": rng},
                     headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    if r.status_code != 200:
        return []
    return parse(r.json())


def symbol_for(code, suffixes):
    if code in INDEXES:
        return [INDEXES[code]]
    known = suffixes.get(code)
    return [f"{code}.{known}"] if known else [f"{code}.KS", f"{code}.KQ"]


def main(codes=None):
    uni = json.loads((HOME / "universe.json").read_text(encoding="utf-8"))
    codes = codes or (uni["codes"] + list(INDEXES))
    sfile = HOME / "suffix.json"
    suffixes = json.loads(sfile.read_text(encoding="utf-8")) if sfile.exists() else {}
    got = miss = 0
    for code in codes:
        folder = HOME / code
        rng = "730d" if not folder.exists() else "60d"
        bars = []
        for sym in symbol_for(code, suffixes):
            try:
                bars = fetch(sym, rng)
            except (requests.RequestException, ValueError):
                bars = []
            if bars:
                if code not in INDEXES:
                    suffixes[code] = sym.split(".")[-1]
                break
            time.sleep(0.5)
        bars = closed_only(bars)
        if not bars:
            miss += 1
            print(f"  {code} · 봉 없음", flush=True)
            continue
        merge(folder, bars)
        got += 1
        time.sleep(0.3)
    sfile.write_text(json.dumps(suffixes, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")
    print(f"받음 {got} · 없음 {miss}", flush=True)
    return 0 if got else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1].split(",") if len(sys.argv) > 1 else None))
