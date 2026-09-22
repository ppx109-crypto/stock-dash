"""증권사 목표주가를 날짜와 함께 모읍니다.

지금까지 목표주가는 오늘 시점 값만 보고 버렸습니다. 그래서 '목표가가 높았던
종목이 실제로 올랐는가'를 물어볼 수가 없었습니다. 증권사 투자의견 API가 한
해치를 날짜와 함께 주므로, 그것을 쌓아 두면 그 물음에 답할 수 있습니다.

조회 전용이며 주문과 무관합니다. 앱이 도는 서버에서는 막힐 수 있어
GitHub Actions에서 돌립니다.
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

OUT = Path("opinion-data")
DAYS = int(os.getenv("OPINION_DAYS", "365"))
PAUSE = float(os.getenv("OPINION_PAUSE", "0.15"))


def codes_to_collect():
    picked = [c.strip() for c in os.getenv("OPINION_CODES", "").split(",") if c.strip()]
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
    """이미 모아 둔 것과 새로 받은 것을 합칩니다.

    API는 한 해치만 줍니다. 해가 바뀌면 옛것이 사라지므로, 받을 때마다 합쳐
    두어야 시간이 갈수록 기간이 길어집니다. 같은 증권사가 같은 날 낸 것은
    한 건으로 봅니다.
    """
    kept = {}
    for row in (old or []) + (fresh or []):
        day = str(row.get("date", ""))
        member = str(row.get("member", ""))
        if not re.fullmatch(r"[0-9]{8}", day) or not row.get("target"):
            continue
        kept[(day, member)] = {"date": day, "member": member,
                               "target": float(row["target"]),
                               "opinion": str(row.get("opinion", "")),
                               "prior_opinion": str(row.get("prior_opinion", ""))}
    return [kept[key] for key in sorted(kept)]


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
    saved, empty, failed = 0, 0, []
    for index, code in enumerate(codes, 1):
        path = OUT / f"{code}.json"
        try:
            old = json.loads(path.read_text(encoding="utf-8")).get("rows", [])
        except (OSError, ValueError):
            old = []
        try:
            fresh = client.opinions(code, days=DAYS)
        except broker_kis.BrokerError as error:
            failed.append((code, str(error)[:50]))
            time.sleep(PAUSE)
            continue
        rows = merge(old, fresh)
        if not rows:
            empty += 1
            time.sleep(PAUSE)
            continue
        body = {"code": code, "rows": rows,
                "fetched": datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d")}
        before = json.dumps(old, ensure_ascii=False, sort_keys=True)
        if before != json.dumps(rows, ensure_ascii=False, sort_keys=True):
            path.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
            saved += 1
        if index % 50 == 0:
            print(f"  {index}/{len(codes)} · 저장 {saved} · 의견 없음 {empty} · 실패 {len(failed)}")
        time.sleep(PAUSE)
    print(f"\n저장 {saved} · 의견 없음 {empty} · 실패 {len(failed)}")
    for code, why in failed[:10]:
        print("  실패:", code, "·", why)
    return 1 if failed and not saved else 0


if __name__ == "__main__":
    sys.exit(main())
