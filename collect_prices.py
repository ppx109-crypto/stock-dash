"""관심종목의 일봉을 한국투자증권에서 받아 저장소에 모읍니다.

DART는 공시·재무만 주고 날짜별 주가는 주지 않습니다. 공공데이터포털 종가는
하루 늦게 들어오고 여러 해치를 한 번에 받기 번거롭습니다. 그래서 일봉은
증권사에서 받습니다. 조회 전용이며 주문과 무관합니다.

앱이 도는 서버에서는 이 호출이 막힐 수 있어 GitHub Actions에서 돌립니다.
바뀐 것이 있을 때만 저장하고, 실패한 종목은 이름을 남깁니다.
"""
import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import broker_kis

OUT = Path("price-data")
# 한계일 뿐입니다. 상장 이전에 닿으면 거기서 멈춥니다.
YEARS = int(os.getenv("PRICE_YEARS", "30"))


def codes_to_collect():
    picked = [c.strip() for c in os.getenv("PRICE_CODES", "").split(",") if c.strip()]
    if picked:
        return [c for c in picked if re.fullmatch(r"[0-9]{6}", c)]
    # 대상 목록이 있으면 그것을 씁니다. 없으면 이미 모아 둔 종목만 받습니다.
    try:
        chosen = json.loads(Path("universe.json").read_text(encoding="utf-8"))
        found = [c for c in chosen.get("codes", []) if re.fullmatch(r"[0-9]{6}", str(c))]
        if found:
            return found
    except (OSError, ValueError):
        pass
    found = []
    for path in sorted(Path("public-data").glob("*.json")):
        if path.name == "market-ranking.json":
            continue
        if re.fullmatch(r"[0-9]{6}", path.stem):
            found.append(path.stem)
    return found


def names():
    found = {}
    for path in sorted(Path("public-data").glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if data.get("code"):
            found[str(data["code"])] = data.get("name") or data["code"]
    return found


def save(code, name, rows):
    """내용이 같으면 파일을 건드리지 않습니다. 커밋이 없으면 앱도 안 멈춥니다."""
    OUT.mkdir(exist_ok=True)
    path = OUT / f"{code}.json"
    body = {"code": code, "name": name, "closes": [[d, c] for d, c in rows],
            "fetched": datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d")}
    if path.exists():
        try:
            old = json.loads(path.read_text(encoding="utf-8"))
            if old.get("closes") == body["closes"]:
                return False
        except (OSError, ValueError):
            pass
    path.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
    return True


def kept_rows(code):
    """이미 받아 둔 일봉. 없으면 빈 목록입니다."""
    try:
        kept = json.loads((OUT / f"{code}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    rows = kept.get("closes") or []
    return [(str(d), c) for d, c in rows
            if re.fullmatch(r"[0-9]{8}", str(d)) and c is not None]


def catch_up(client, code, have, back=25):
    """이미 받아 둔 종목은 빠진 날만 받습니다.

    서른 해를 140일씩 거슬러 오르면 종목 하나에 일흔여덟 번을 묻습니다.
    이미 받아 둔 종목까지 날마다 그렇게 하면 새 종목을 받을 시간이 남지
    않습니다. 그래서 겹치는 구간을 먼저 받아 예전 값과 맞춰 봅니다.
    같으면 이어 붙이고, 다르면 처음부터 다시 받습니다 — 액면분할이나
    무상증자가 있으면 지난 수정주가가 통째로 바뀌기 때문입니다.

    (일봉, 어떻게 받았는지)를 돌려줍니다. 이어받을 수 없으면 (None, 까닭)
    입니다. 그때는 부르는 쪽이 처음부터 받습니다.
    """
    if len(have) < 120:
        return None, "받아 둔 것이 모자람"
    last = have[-1][0]
    today = datetime.now(ZoneInfo("Asia/Seoul")).date()
    edge = datetime.strptime(last, "%Y%m%d").date() - timedelta(days=back)
    # 한 번에 100거래일까지 옵니다. 그보다 오래 비었으면 이어받기로는
    # 메울 수 없습니다.
    if (today - edge).days > 130:
        return None, "너무 오래 비었음"
    fresh = client.daily(code, edge.strftime("%Y%m%d"), today.strftime("%Y%m%d"))
    if not fresh:
        return have, "새로 나온 날 없음"
    was = dict(have)
    shared = [(day, close) for day, close in fresh if day in was]
    if not shared:
        return None, "겹치는 날이 없음"
    for day, close in shared:
        before = was[day]
        if not before or abs(close - before) > max(abs(before), abs(close)) * 0.001:
            # 지난 값이 바뀌었습니다. 수정주가가 다시 매겨진 것이라
            # 이어 붙이면 어긋납니다.
            return None, "지난 값이 바뀜"
    merged = dict(have)
    merged.update(dict(fresh))
    return sorted(merged.items()), f"이어받음 · 새 {len(fresh) - len(shared)}일"


def done_today(code, on_day):
    """오늘 이미 받아 둔 종목인지 봅니다. 이어받을 때 시간을 아낍니다."""
    try:
        kept = json.loads((OUT / f"{code}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return kept.get("fetched") == on_day and len(kept.get("closes") or []) >= 120


def main():
    codes = codes_to_collect()
    if not codes:
        print("모을 종목이 없습니다.")
        return 1
    if os.getenv("PRICE_SKIP_DONE", "1").strip() not in ("0", "false", "False"):
        today = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d")
        before = len(codes)
        codes = [c for c in codes if not done_today(c, today)]
        if before != len(codes):
            print(f"오늘 이미 받아 둔 {before - len(codes)}종목은 건너뜁니다.")
        if not codes:
            print("모두 받아 두었습니다.")
            return 0
    label = names()
    try:
        client = broker_kis.market()
    except broker_kis.BrokerError as error:
        # 무엇이 없어서 못 도는지 바로 보이게 적습니다.
        print("증권사 연결을 만들지 못했습니다 ·", error)
        print("저장소 시크릿 KIS_APP_KEY / KIS_APP_SECRET 가 비어 있는지 확인하세요.")
        print("  KIS_APP_KEY 길이:", len(os.getenv("KIS_APP_KEY", "")))
        print("  KIS_APP_SECRET 길이:", len(os.getenv("KIS_APP_SECRET", "")))
        return 1
    saved, skipped, failed, caught = 0, 0, [], 0
    for index, code in enumerate(codes, 1):
        name = label.get(code, code)
        try:
            # 이미 받아 둔 종목은 빠진 날만 받습니다. 안 되면 처음부터.
            rows, how = catch_up(client, code, kept_rows(code))
            if rows is None:
                rows = client.history(code, days=YEARS * 365)
            else:
                caught += 1
        except broker_kis.BrokerError as error:
            failed.append((name, str(error)[:60]))
            print(f"[{index}/{len(codes)}] {name} 실패 · {error}")
            continue
        if len(rows) < 120:
            failed.append((name, f"거래일 {len(rows)}일"))
            print(f"[{index}/{len(codes)}] {name} 자료 부족 · {len(rows)}일")
            continue
        if save(code, name, rows):
            saved += 1
            print(f"[{index}/{len(codes)}] {name} · {len(rows)}일 · {rows[0][0]}~{rows[-1][0]}")
        else:
            skipped += 1
            print(f"[{index}/{len(codes)}] {name} · 변화 없음")
    print(f"\n저장 {saved} · 변화 없음 {skipped} · 실패 {len(failed)}"
          f" · 이어받은 종목 {caught}")
    for name, why in failed:
        print("  실패:", name, "·", why)
    # 전부 실패했을 때만 실패로 끝냅니다. 한둘이 빠져도 나머지는 남겨야 합니다.
    return 1 if failed and not saved and not skipped else 0


if __name__ == "__main__":
    sys.exit(main())
