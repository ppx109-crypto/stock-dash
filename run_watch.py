"""봇 지킴이 — 평일 16:05(한국 시각)에 오늘 세 모의투자 봇이 제대로 돌았는지 보고, 아니면 디스코드로 알림.

사용자 2026-10-04 "5번 진행"(점검 A4 · A23: 봇이 하루만 빠져도 큰 매매를 놓치면 1년 성적이 크게 달라짐).
보는 것(저장소에 봇들이 남긴 장부 · 키 · 계좌 · 증권사 응답은 읽지도 찍지도 않음):
  1일봉   : daily-live/today.json 날짜가 오늘인지 · late(15:28 넘어 주문 건너뜀)가 아닌지
  빈칸 엔진: idle-live/today.json 날짜가 오늘인지 · late(15:18 넘어 주문 건너뜀)가 아닌지(IDLE_START 전은 안 봄)
  15분봉  : m15-live/state.json last_bar가 오늘 15:00 뒤 봉인지
알림이 오면 GitHub Actions에서 그 작업을 '수동 실행(Run workflow)'할 수 있음(이미 늦었으면 다음 날 판단부터 정상).
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")
IDLE_START = os.environ.get("IDLE_START", "20261005")


def _load(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def trading_day(day: str) -> bool:
    from idle_live import HOLIDAYS
    d = datetime.strptime(day, "%Y%m%d")
    return d.weekday() < 5 and day not in HOLIDAYS


def check(day: str, daily: dict, idle: dict, m15: dict) -> list[str]:
    """빠진 · 늦은 봇마다 한 줄. 모두 괜찮으면 빈 목록."""
    bad = []
    if daily.get("date") != day:
        bad.append(f"1일봉 봇이 오늘 돌지 않았어요(마지막 {daily.get('date') or '없음'}) → Actions 'Daily rule live'")
    elif daily.get("late"):
        bad.append("1일봉 봇이 늦게 돌아 오늘 주문을 건너뛰었어요(15:28 넘음)")
    if day >= IDLE_START:
        if idle.get("date") != day:
            bad.append(f"빈칸 엔진 · 코스닥 인버스가 오늘 돌지 않았어요(마지막 {idle.get('date') or '없음'}) → Actions 'Daily rule live'")
        elif idle.get("late"):
            bad.append("빈칸 엔진 · 코스닥 인버스가 늦게 돌아 오늘 주문을 건너뛰었어요(15:18 넘음)")
    last = str(m15.get("last_bar") or "")
    if not last.startswith(day) or last[8:] < "1500":
        bad.append(f"15분봉 봇이 오늘 끝까지 돌지 않았어요(마지막 봉 {last or '없음'}) → Actions 'M15 live'")
    return bad


def main() -> int:
    day = os.environ.get("WATCH_DAY") or datetime.now(KST).strftime("%Y%m%d")
    if not trading_day(day):
        print(f"{day} 휴장 · 안 봄")
        return 0
    bad = check(day, _load("daily-live/today.json"), _load("idle-live/today.json"), _load("m15-live/state.json"))
    if not bad:
        print(f"{day} 세 봇 모두 정상")
        return 0
    lines = [f"⚠️ **봇 지킴이 · {day[4:6]}-{day[6:]}** 모의투자 봇 확인 필요"] + ["· " + b for b in bad]
    lines.append("※ 연구용 자동 알림 · 실전 계좌 주문은 없음")
    print("\n".join(lines))
    url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if url:
        import requests
        try:
            requests.post(url, json={"content": "\n".join(lines)}, timeout=(10, 20))
        except requests.RequestException:
            print("디스코드 보내기 실패")
    return 0


if __name__ == "__main__":
    sys.exit(main())
