"""누가 사고 누가 팔았는지를 날짜별로 쌓습니다.

외국인이 사들이고 개인이 파는 날이 있습니다. 그 반대인 날도 있습니다.
급락 뒤 반등을 가르는 것이 여기 있을 수 있습니다.

다만 이 API는 기간을 받지 않고 최근 며칠만 돌려줍니다. 과거를 한꺼번에
받을 수 없으므로, 매일 받아 합쳐 두어야 기간이 길어집니다. 오늘 시작하면
한 달 뒤에 한 달치가 쌓입니다. 그때까지는 이 자료로 결론을 내지 않습니다.
"""
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import broker_kis

OUT = Path("flow-data")
PAUSE = float(os.getenv("FLOW_PAUSE", "0.15"))


def codes_to_collect():
    picked = [c.strip() for c in os.getenv("FLOW_CODES", "").split(",") if c.strip()]
    if picked:
        return [c for c in picked if re.fullmatch(r"[0-9]{6}", c)]
    try:
        chosen = json.loads(Path("universe.json").read_text(encoding="utf-8"))
        found = [c for c in chosen.get("codes", []) if re.fullmatch(r"[0-9]{6}", str(c))]
        if found:
            return found
    except (OSError, ValueError):
        pass
    return sorted(p.stem for p in Path("price-data").glob("*.json")
                  if re.fullmatch(r"[0-9]{6}", p.stem))


def merge(old, fresh):
    """이미 쌓아 둔 것과 새로 받은 것을 합칩니다. 같은 날은 새것으로 덮습니다."""
    kept = {r["date"]: r for r in (old or []) if re.fullmatch(r"[0-9]{8}", str(r.get("date", "")))}
    for row in fresh or []:
        if re.fullmatch(r"[0-9]{8}", str(row.get("date", ""))):
            kept[row["date"]] = row
    return [kept[day] for day in sorted(kept)]


def main():
    codes = codes_to_collect()
    if not codes:
        print("모을 종목이 없습니다.")
        return 1
    try:
        client = broker_kis.market()
    except broker_kis.BrokerError as error:
        print("증권사 연결을 만들지 못했습니다 ·", error)
        return 1
    OUT.mkdir(exist_ok=True)
    saved, failed, spans = 0, [], []
    for index, code in enumerate(codes, 1):
        path = OUT / f"{code}.json"
        try:
            old = json.loads(path.read_text(encoding="utf-8")).get("rows", [])
        except (OSError, ValueError):
            old = []
        try:
            fresh = client.flows(code)
        except broker_kis.BrokerError as error:
            failed.append((code, str(error)[:50]))
            time.sleep(PAUSE)
            continue
        rows = merge(old, fresh)
        if not rows:
            time.sleep(PAUSE)
            continue
        body = {"code": code, "rows": rows,
                "fetched": datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d")}
        before = json.dumps(old, ensure_ascii=False, sort_keys=True)
        if before != json.dumps(rows, ensure_ascii=False, sort_keys=True):
            path.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
            saved += 1
        spans.append(len(rows))
        if index % 50 == 0:
            print(f"  {index}/{len(codes)} · 저장 {saved} · 실패 {len(failed)}")
        time.sleep(PAUSE)
    if spans:
        spans.sort()
        print(f"\n저장 {saved} · 실패 {len(failed)} · 쌓인 날 중앙 {spans[len(spans) // 2]}일 "
              f"(가장 긴 종목 {spans[-1]}일)")
    for code, why in failed[:10]:
        print("  실패:", code, "·", why)
    return 1 if failed and not saved else 0


if __name__ == "__main__":
    sys.exit(main())
