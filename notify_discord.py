"""오늘의 A그룹(study/a_group.json)을 디스코드로 보냅니다.

웹훅 주소는 환경변수 DISCORD_WEBHOOK_URL(GitHub Secrets)로만 받고, 어디에도 찍지 않습니다.
주소가 없으면 아무것도 보내지 않고 조용히 끝납니다. A그룹이 없는 날에도 'A그룹 없음'을 보냅니다(B그룹은 싣지 않음 — 사용자 요청).
"""
import json
import os
import sys
from pathlib import Path

import requests

LIMIT = 1900          # 디스코드 한 메시지 2000자 제한 아래로


def _won(v):
    try:
        return f"{float(v):,.0f}원"
    except (TypeError, ValueError):
        return "-"


def lines(found):
    day = str(found.get("date") or "")
    day = f"{day[:4]}-{day[4:6]}-{day[6:8]}" if len(day) == 8 else day or "날짜 모름"
    picks = found.get("picks") or []
    out = [f"📊 **{day} 장 마감 기준 A그룹**",
           f"시장 폭 {found.get('breadth', '-')}% (시총 100위 안에서 오르는 추세인 종목 비율) · "
           f"정배열 갈래 {'열림' if found.get('align_open') else '닫힘(시장 폭 50% 미만)'} · 살펴본 종목 {len(found.get('counted') or [])}개"]
    if picks:
        out.append(f"🟢 **A그룹 {len(picks)}종목** (자리 {found.get('slots', 5)}칸)")
        for one in picks:
            doors = "·".join(one.get("갈래") or [])
            out.append(f"• **{one.get('name')}**({one.get('code')}) · {doors} · 종가 {_won(one.get('종가'))} · 시총 {one.get('시총순위', '-')}위")
            out.append(f"  팔기: {one.get('팔기', '-')}")
    else:
        out.append("⚪ 오늘은 A그룹 종목이 없어요.")
    out.append("※ 연구용 자동 알림이에요. 매매 판단은 직접 확인한 뒤에 하세요.")
    return out


def chunks(rows):
    msg, found = "", []
    for row in rows:
        if len(msg) + len(row) + 1 > LIMIT:
            found.append(msg)
            msg = ""
        msg += row + "\n"
    if msg:
        found.append(msg)
    return found


def main():
    url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if not url:
        print("디스코드 웹훅이 설정되지 않아 보내지 않습니다.")
        return 0
    try:
        found = json.loads(Path("study/a_group.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        print("A그룹 파일을 읽지 못했습니다.")
        return 1
    for msg in chunks(lines(found)):
        try:
            r = requests.post(url, json={"content": msg}, timeout=(10, 20))
        except requests.RequestException:
            print("디스코드에 보내지 못했습니다(연결 오류).")
            return 1
        if r.status_code >= 300:
            print(f"디스코드가 받지 않았습니다 · HTTP {r.status_code}")
            return 1
    print("디스코드로 보냈습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
