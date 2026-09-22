"""주식 총수를 해마다 모읍니다. 과거 시가총액을 만들기 위해서입니다.

'살 때 코스피 100등 안'을 지나간 자료로 가리려면 그날의 시가총액이 있어야
합니다. 오늘의 100등으로 과거를 고르면 그 자체가 미래참조입니다 — 지금 큰
회사는 그동안 잘된 회사이고, 그 사실을 그때는 알 수 없었습니다.

DART의 주식총수 현황(stockTotqySttus)은 보고서마다 그때의 발행주식수를
줍니다. 접수일과 함께 두면, 그날까지 알려진 주식수를 쓸 수 있습니다.
종가를 곱하면 그날의 시가총액이 나옵니다.
"""
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from providers import DataError, Official

OUT = Path("share-data")
FIRST = int(os.getenv("SHARE_FIRST", "2015"))
PAUSE = float(os.getenv("SHARE_PAUSE", "0.12"))
# 사업보고서·반기·분기 순으로 물어봅니다. 하나라도 답하면 그 해는 됩니다.
KINDS = ("11011", "11012", "11013", "11014")


def codes_to_collect():
    picked = [c.strip() for c in os.getenv("SHARE_CODES", "").split(",") if c.strip()]
    if picked:
        return [c for c in picked if re.fullmatch(r"[0-9]{6}", c)]
    return sorted(p.stem for p in Path("price-data").glob("*.json")
                  if re.fullmatch(r"[0-9]{6}", p.stem))


def count_of(payload):
    """보통주 발행총수에서 자기주식을 뺀 수. 없으면 발행총수 그대로."""
    issued = traded = None
    for row in payload.get("list") or []:
        if "보통주" not in str(row.get("se", "")):
            continue
        for key, keep in (("istc_totqy", "issued"), ("distb_stock_co", "traded")):
            raw = str(row.get(key, "")).replace(",", "").strip()
            if not raw or raw in ("-", "0"):
                continue
            try:
                got = int(raw)
            except ValueError:
                continue
            if keep == "issued":
                issued = max(issued or 0, got)
            else:
                traded = max(traded or 0, got)
    return traded or issued


def gather(client, code):
    """해마다 (접수일, 주식수)를 모읍니다. 접수일은 그날 공개된 날입니다."""
    corp = client.corp(code)
    this_year = datetime.now(ZoneInfo("Asia/Seoul")).year
    found = {}
    for year in range(FIRST, this_year + 1):
        for kind in KINDS:
            try:
                payload = client.dart("stockTotqySttus.json", corp_code=corp,
                                      bsns_year=str(year), reprt_code=kind)
            except DataError:
                continue
            finally:
                time.sleep(PAUSE)
            if not payload:
                continue
            count = count_of(payload)
            if not count:
                continue
            stamp = None
            for row in payload.get("list") or []:
                got = str(row.get("rcept_no", ""))[:8]
                if re.fullmatch(r"[0-9]{8}", got):
                    stamp = got if stamp is None else min(stamp, got)
            if stamp:
                found[stamp] = count
            break
    return sorted(found.items())


def save(code, rows):
    OUT.mkdir(exist_ok=True)
    path = OUT / f"{code}.json"
    body = {"code": code, "칸": ["접수일", "주식수"],
            "날": [[day, count] for day, count in rows],
            "fetched": datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d")}
    if path.exists():
        try:
            if json.loads(path.read_text(encoding="utf-8")).get("날") == body["날"]:
                return False
        except (OSError, ValueError):
            pass
    path.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
    return True


def main():
    codes = codes_to_collect()
    if not codes:
        print("모을 종목이 없습니다.")
        return 1
    client = Official()
    if not client.dart_key:
        print("DART_CRTFC_KEY가 비어 있습니다.")
        return 1
    saved, empty = 0, []
    for index, code in enumerate(codes, 1):
        try:
            rows = gather(client, code)
        except DataError as error:
            empty.append((code, str(error)[:50]))
            print(f"[{index}/{len(codes)}] {code} 실패 · {error}")
            continue
        if not rows:
            empty.append((code, "주식수 없음"))
            print(f"[{index}/{len(codes)}] {code} 주식수를 받지 못했습니다")
            continue
        if save(code, rows):
            saved += 1
        print(f"[{index}/{len(codes)}] {code} {len(rows)}개 시점")
    print(f"\n저장 {saved} · 못 받은 종목 {len(empty)}")
    for code, why in empty[:20]:
        print(f"  {code} · {why}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
