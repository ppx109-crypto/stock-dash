"""거래량을 모읍니다. 종가만으로는 '실제로 살 수 있었나'를 가릴 수 없습니다.

일봉 수집기는 종가만 남깁니다. 그것만으로 지나간 매매를 흉내 내면, 하루에
몇천 주밖에 거래되지 않는 종목을 자리 하나만큼 사는 것으로 세게 됩니다.
실제로는 그 주문이 들어가는 순간 값이 밀립니다.

그래서 거래량과 거래대금을 따로 모읍니다. 일봉 파일은 건드리지 않습니다.
서른 해치를 다시 받는 일이라, 끊기면 그 자리에서 이어받습니다.
"""
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import broker_kis

OUT = Path("volume-data")
YEARS = int(os.getenv("VOLUME_YEARS", "30"))
KEEP = ("거래량", "거래대금", "고가", "저가")


def codes_to_collect():
    picked = [c.strip() for c in os.getenv("VOLUME_CODES", "").split(",") if c.strip()]
    if picked:
        return [c for c in picked if re.fullmatch(r"[0-9]{6}", c)]
    return sorted(p.stem for p in Path("price-data").glob("*.json")
                  if re.fullmatch(r"[0-9]{6}", p.stem))


def save(code, rows):
    """내용이 같으면 파일을 건드리지 않습니다."""
    OUT.mkdir(exist_ok=True)
    path = OUT / f"{code}.json"
    days = [[day, *[got.get(name) for name in KEEP]] for day, got in rows]
    body = {"code": code, "칸": ["날짜", *KEEP], "날": days,
            "fetched": datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d")}
    if path.exists():
        try:
            old = json.loads(path.read_text(encoding="utf-8"))
            if old.get("날") == body["날"]:
                return False
        except (OSError, ValueError):
            pass
    path.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
    return True


def done_today(code, on_day):
    try:
        kept = json.loads((OUT / f"{code}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return kept.get("fetched") == on_day and len(kept.get("날") or []) >= 120


def main():
    codes = codes_to_collect()
    if not codes:
        print("모을 종목이 없습니다. price-data가 비어 있습니까?")
        return 1
    today = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d")
    if os.getenv("VOLUME_SKIP_DONE", "1").strip() not in ("0", "false", "False"):
        before = len(codes)
        codes = [c for c in codes if not done_today(c, today)]
        if before != len(codes):
            print(f"오늘 이미 받아 둔 {before - len(codes)}종목은 건너뜁니다.")
        if not codes:
            print("모두 받아 두었습니다.")
            return 0
    try:
        client = broker_kis.market()
    except broker_kis.BrokerError as error:
        print("증권사 연결을 만들지 못했습니다 ·", error)
        print("저장소 시크릿 KIS_APP_KEY / KIS_APP_SECRET 를 확인하세요.")
        return 1
    saved, skipped, failed = 0, 0, []
    for index, code in enumerate(codes, 1):
        try:
            rows = client.history(code, days=YEARS * 365, detail=True)
        except broker_kis.BrokerError as error:
            failed.append((code, str(error)[:60]))
            print(f"[{index}/{len(codes)}] {code} 실패 · {error}")
            continue
        if len(rows) < 120:
            failed.append((code, f"거래일 {len(rows)}일"))
            print(f"[{index}/{len(codes)}] {code} 자료 부족 · {len(rows)}일")
            continue
        if save(code, rows):
            saved += 1
            print(f"[{index}/{len(codes)}] {code} {len(rows)}일 저장")
        else:
            skipped += 1
            print(f"[{index}/{len(codes)}] {code} 그대로")
    print(f"\n저장 {saved} · 그대로 {skipped} · 실패 {len(failed)}")
    for code, why in failed[:20]:
        print(f"  {code} · {why}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
