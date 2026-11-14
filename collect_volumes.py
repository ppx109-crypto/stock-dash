"""거래량을 모읍니다. 종가만으로는 '실제로 살 수 있었나'를 가릴 수 없습니다.

일봉 수집기는 종가만 남깁니다. 그것만으로 지나간 매매를 흉내 내면, 하루에
몇천 주밖에 거래되지 않는 종목을 자리 하나만큼 사는 것으로 세게 됩니다.
실제로는 그 주문이 들어가는 순간 값이 밀립니다.

그래서 거래량과 거래대금을 따로 모읍니다. 일봉 파일은 건드리지 않습니다.
서른 해치를 다시 받는 일이라, 끊기면 그 자리에서 이어받습니다.

BOOST-0001-D D7: '오늘 받음'으로 건너뛰는 것은 받은 날 = 오늘 · 120줄에 더해 마지막 줄 = 기대 날(판 고정 달력의 앞 거래일)이고
그 줄의 칸이 다 있을 때만입니다. 달력을 못 읽으면 예전처럼 받은 날과 줄 수만 봅니다(수집을 멈추지 않음).
"""
import json
import os
import re
import sys
from datetime import datetime, timedelta
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


def kept_rows(code):
    """이미 받아 둔 거래량. (날짜, 묶음) 꼴로 돌려줍니다."""
    try:
        kept = json.loads((OUT / f"{code}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    names = kept.get("칸") or ["날짜", *KEEP]
    found = []
    for row in kept.get("날") or []:
        if not row or not re.fullmatch(r"[0-9]{8}", str(row[0])):
            continue
        found.append((str(row[0]), dict(zip(names[1:], row[1:]))))
    return found


def catch_up(client, code, have, back=25):
    """빠진 날만 받습니다. 일봉 수집기와 같은 셈입니다.

    서른 해를 140일씩 거슬러 오르면 종목 하나에 일흔여덟 번을 묻습니다.
    이미 받아 둔 종목까지 날마다 그렇게 하면 두 수집기가 하루를 다 씁니다.
    겹치는 구간의 거래량이 예전과 같으면 이어 붙이고, 다르면 처음부터
    받습니다.
    """
    if len(have) < 120:
        return None, "받아 둔 것이 모자람"
    last = have[-1][0]
    today = datetime.now(ZoneInfo("Asia/Seoul")).date()
    edge = datetime.strptime(last, "%Y%m%d").date() - timedelta(days=back)
    if (today - edge).days > 130:
        return None, "너무 오래 비었음"
    fresh = client.daily(code, edge.strftime("%Y%m%d"), today.strftime("%Y%m%d"),
                         detail=True)
    if not fresh:
        return have, "새로 나온 날 없음"
    was = dict(have)
    shared = [(day, got) for day, got in fresh if day in was]
    if not shared:
        return None, "겹치는 날이 없음"
    for day, got in shared:
        before = was[day].get("거래량")
        now = got.get("거래량")
        if before != now:
            return None, "지난 거래량이 바뀜"
    merged = dict(have)
    merged.update(dict(fresh))
    return sorted(merged.items()), f"이어받음 · 새 {len(fresh) - len(shared)}일"


def expected_day(now=None, folder=None):
    """D7 기대 날 = 판 고정 달력의 앞 거래일(오늘 한국 날짜 앞 마지막 거래일 · 장이 끝나 자료가 다 나왔을 가장 늦은 날).
    못 읽으면 None(예전처럼 마지막 줄을 안 봄)."""
    today = (now or datetime.now(ZoneInfo("Asia/Seoul"))).strftime("%Y%m%d")
    try:
        import trade_calendar
        return trade_calendar.latest_done(today, folder=folder)
    except Exception:
        return None


def done_today(code, on_day, expect=None):
    """오늘 이미 받아 둔 종목이면 참(건너뜀): 받은 날 = 오늘 · 120줄 이상. expect(D7 기대 날)를 주면 마지막 줄 = expect이고
    그 줄의 거래량 · 거래대금 · 고가 · 저가가 모두 있어야 참(빈 칸 · 낡은 마지막 줄이면 다시 받음). expect가 없으면 예전 그대로."""
    try:
        kept = json.loads((OUT / f"{code}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    if not isinstance(kept, dict):
        return False
    rows = kept.get("날") or []
    if not (kept.get("fetched") == on_day and len(rows) >= 120):
        return False
    if expect is None:
        return True
    last = rows[-1]
    if not isinstance(last, list) or not last or str(last[0]) != str(expect):
        return False
    got = dict(zip((kept.get("칸") or ["날짜", *KEEP])[1:], last[1:]))
    return all(got.get(name) is not None for name in KEEP)


def main():
    codes = codes_to_collect()
    if not codes:
        print("모을 종목이 없습니다. price-data가 비어 있습니까?")
        return 1
    today = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d")
    if os.getenv("VOLUME_SKIP_DONE", "1").strip() not in ("0", "false", "False"):
        expect = expected_day()          # BOOST-0001-D D7: 마지막 줄로 기대하는 날(달력을 못 읽으면 None = 예전처럼)
        print("건너뛰기 기준 · 받은 날 오늘 · 120줄 · " + (f"마지막 줄 {expect}(판 고정 달력) · 칸 다 있음" if expect
                                                        else "달력을 못 읽어 마지막 줄은 안 봄(예전 방식)"))
        before = len(codes)
        codes = [c for c in codes if not done_today(c, today, expect)]
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
    saved, skipped, failed, caught = 0, 0, [], 0
    for index, code in enumerate(codes, 1):
        try:
            rows, _how = catch_up(client, code, kept_rows(code))
            if rows is None:
                rows = client.history(code, days=YEARS * 365, detail=True)
            else:
                caught += 1
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
    print(f"\n저장 {saved} · 그대로 {skipped} · 실패 {len(failed)}"
          f" · 이어받은 종목 {caught}")
    for code, why in failed[:20]:
        print(f"  {code} · {why}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
