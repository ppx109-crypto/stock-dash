"""장중 상주 실행기(사용자 2026-10-06 "1번으로 진행" — GitHub 예약이 10~20분 늦고 15분봉 예약의 1/3이 빠지던 것을 막음).

GitHub 예약(schedule)은 정각 무렵 붐비면 늦게 시작하거나 회차를 건너뜁니다(10-02 · 10-05: 15분봉 28번 중 17~19번만 · 1시간봉 늘 9~13분 늦음).
그래서 작업 하나를 장 시작 전에 일찍 띄워 두고, 그 안에서 시각을 직접 재며 정해진 때에 봇을 돌립니다.
- 1시간봉(hourly_a.py live): 09:01 · 10:01 · 11:01 · 12:01 · 13:01 · 14:01 · 15:31
- 15분봉(m15_live.py): 09:03부터 15:48까지 :03 · :18 · :33 · :48
돌리기 전마다 저장소를 받아 최신 상태(다른 작업이 올린 것)로 맞추고, 돌린 뒤 바뀐 기록을 올립니다.
늦게 시작했으면 지난 시각은 봇마다 가장 최근 것 한 번만 바로 돌립니다(봇이 밀린 봉을 차례로 처리함).
python intraday_runner.py 0855 1300   — 그 창(한국 시각) 안의 시각만 맡음(오전 · 오후 작업이 나눠 맡음)
환경변수: HOURLY_PAPER_TRADING(기본 off) · M15_PAPER_TRADING(기본 on) — 예전 작업 파일과 같은 값
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")
HOURLY = ["0901", "1001", "1101", "1201", "1301", "1401", "1531"]
M15 = [f"{h:02d}{m:02d}" for h in range(9, 16) for m in (3, 18, 33, 48)]
RUN_LIMIT = 13 * 60          # 한 번 돌리기 최대(초) — 예전 작업 제한(14 · 20분)보다 짧게
DIRS = "hourly-live idle-live m15-live"


def plan(start, end):
    """[(시각 HHMM, 봇)] — 창 [start, end) 안에서 시각 순. 같은 시각이면 1시간봉 먼저."""
    jobs = [(t, "hourly") for t in HOURLY] + [(t, "m15") for t in M15]
    return sorted((t, b) for t, b in jobs if start <= t < end)


def due(jobs, now_hhmm):
    """지금 돌릴 것 · 앞으로 기다릴 것. 지난 시각은 봇마다 가장 최근 것 하나만 남김(늦게 시작했을 때 한 번만 따라잡기)."""
    past = [(t, b) for t, b in jobs if t <= now_hhmm]
    latest = {}
    for t, b in past:
        latest[b] = (t, b)
    catch_up = sorted(latest.values())
    later = [(t, b) for t, b in jobs if t > now_hhmm]
    return catch_up, later


def _sh(cmd, check=False, timeout=300):
    return subprocess.run(cmd, shell=True, check=check, timeout=timeout)


def sync():
    """다른 작업이 올린 최신 상태로 맞춤(실패해도 이번 판단은 돌림)."""
    _sh("git pull -q --rebase origin main")


def push(message):
    _sh(f"mkdir -p {DIRS} && git add -A {DIRS}")
    if _sh("git diff --cached --quiet").returncode == 0:
        return True
    _sh(f'git commit -q -m "{message}"')
    for t in range(1, 6):
        if _sh("git pull -q --rebase origin main && git push -q").returncode == 0:
            return True
        print(f"올리기 다시 시도 {t}", flush=True)
        time.sleep(t * 7)
    return False


def run_bot(bot):
    env = dict(os.environ)
    if bot == "hourly":
        env["PAPER_TRADING"] = os.getenv("HOURLY_PAPER_TRADING", "off")
        cmd, message = [sys.executable, "hourly_a.py", "live"], "Hourly A group live"
    else:
        env["PAPER_TRADING"] = os.getenv("M15_PAPER_TRADING", "on")
        env["M15_PAPER"] = os.getenv("M15_PAPER", "on")
        cmd, message = [sys.executable, "m15_live.py"], "M15 live"
    sync()
    try:
        code = subprocess.run(cmd, env=env, timeout=RUN_LIMIT).returncode
    except subprocess.TimeoutExpired:
        print(f"{bot}: {RUN_LIMIT // 60}분 안에 끝나지 않아 멈춤", flush=True)
        code = 124
    ok = push(message)
    return code == 0 and ok


def main(start="0855", end="1300", clock=lambda: datetime.now(KST), sleep=time.sleep):
    jobs = plan(start, end)
    now = clock().strftime("%H%M")
    if now >= end:
        print(f"맡은 창({start}~{end})이 이미 지나 끝냅니다.")
        return 0
    catch_up, later = due(jobs, now)
    failed = []
    for t, bot in catch_up:
        print(f"[{clock():%H:%M:%S}] 늦게 시작 — {t} {bot} 따라잡기", flush=True)
        if not run_bot(bot):
            failed.append(f"{t} {bot}")
    for t, bot in later:
        today = clock()
        at = today.replace(hour=int(t[:2]), minute=int(t[2:]), second=0, microsecond=0)
        wait = (at - today).total_seconds()
        if wait > 0:
            sleep(wait)
        print(f"[{clock():%H:%M:%S}] {t} {bot}", flush=True)
        if not run_bot(bot):
            failed.append(f"{t} {bot}")
    print("끝 · 말썽 난 회차:", failed or "없음", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(*(sys.argv[1:3])))
