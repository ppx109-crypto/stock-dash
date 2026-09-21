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
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import broker_kis

OUT = Path("price-data")
YEARS = int(os.getenv("PRICE_YEARS", "5"))


def codes_to_collect():
    picked = [c.strip() for c in os.getenv("PRICE_CODES", "").split(",") if c.strip()]
    if picked:
        return [c for c in picked if re.fullmatch(r"[0-9]{6}", c)]
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


def main():
    codes = codes_to_collect()
    if not codes:
        print("모을 종목이 없습니다.")
        return 1
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
    saved, skipped, failed = 0, 0, []
    for index, code in enumerate(codes, 1):
        name = label.get(code, code)
        try:
            rows = client.history(code, days=YEARS * 365)
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
    print(f"\n저장 {saved} · 변화 없음 {skipped} · 실패 {len(failed)}")
    for name, why in failed:
        print("  실패:", name, "·", why)
    # 전부 실패했을 때만 실패로 끝냅니다. 한둘이 빠져도 나머지는 남겨야 합니다.
    return 1 if failed and not saved and not skipped else 0


if __name__ == "__main__":
    sys.exit(main())
