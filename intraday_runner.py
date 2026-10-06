"""장중 상주 실행기(사용자 2026-10-06 "1번으로 진행" — GitHub 예약이 10~20분 늦고 15분봉 예약의 1/3이 빠지던 것을 막음).

GitHub 예약(schedule)은 정각 무렵 붐비면 늦게 시작하거나 회차를 건너뜁니다(10-02 · 10-05: 15분봉 28번 중 17~19번만 · 1시간봉 늘 9~13분 늦음).
그래서 작업 하나를 장 시작 전에 일찍 띄워 두고, 그 안에서 시각을 직접 재며 정해진 때에 봇을 돌립니다.
- 15분봉(m15_live.py · 모의 주문함): 09:03부터 15:48까지 :03 · :18 · :33 · :48
- 1시간봉(hourly_a.py live · 알림만): 같은 :03 회차에 15분봉 다음 차례(09:03 … 14:03 · 15:33) — 주문하는 15분봉을 먼저
돌리기 전마다 저장소를 받아 최신 상태로 맞추고, 돌린 뒤 바뀐 기록을 올립니다.
- 받아 합치기가 실패하면 되돌리고(rebase --abort) 그 회차는 건너뜀 — 낡거나 엉킨 기록으로 판단 · 주문하지 않게(다음 회차가 밀린 봉을 처리).
- 시간 초과로 멈춘 봇이 남긴 깨진 JSON은 올리지 않고 되돌림.
- 맡은 창(end)이 지나면 더 돌리지 않음 · 늦게 시작했으면 지난 회차는 봇마다 가장 최근 것 한 번만 따라잡음.
(2026-10-06 검토 반영: 합치기 실패 · 창 겹침 · 깨진 기록 · 순서)
python intraday_runner.py 0855 1200   — 그 창(한국 시각) 안의 회차만 맡음(오전 · 오후 작업이 나눠 맡고, 같은 줄에 서서 겹치지 않음)
환경변수: HOURLY_PAPER_TRADING(기본 off) · M15_PAPER_TRADING(기본 on) — 예전 작업 파일과 같은 값
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")
M15 = [f"{h:02d}{m:02d}" for h in range(9, 16) for m in (3, 18, 33, 48)]
HOURLY = ["0903", "1003", "1103", "1203", "1303", "1403", "1533"]
ORDER = {"m15": 0, "hourly": 1}          # 같은 회차면 15분봉(주문함) 먼저
RUN_LIMIT = 13 * 60                       # 한 번 돌리기 최대(초)
DIRS = ("hourly-live", "idle-live", "m15-live")


def plan(start, end):
    """[(시각 HHMM, 봇)] — 창 [start, end) 안에서 시각 순 · 같은 시각이면 15분봉 먼저."""
    jobs = [(t, "hourly") for t in HOURLY] + [(t, "m15") for t in M15]
    return sorted(((t, b) for t, b in jobs if start <= t < end), key=lambda j: (j[0], ORDER[j[1]]))


def due(jobs, now_hhmm):
    """지금 돌릴 것 · 앞으로 기다릴 것. 지난 회차는 봇마다 가장 최근 것 하나만 남김(늦게 시작했을 때 한 번만 따라잡기)."""
    latest = {}
    for t, b in jobs:
        if t <= now_hhmm:
            latest[b] = (t, b)
    catch_up = sorted(latest.values(), key=lambda j: (j[0], ORDER[j[1]]))
    later = [(t, b) for t, b in jobs if t > now_hhmm]
    return catch_up, later


def _sh(cmd, timeout=300):
    try:
        return subprocess.run(cmd, shell=True, timeout=timeout).returncode
    except subprocess.TimeoutExpired:
        print(f"명령이 {timeout}초 안에 끝나지 않음: {cmd.split()[0:3]}", flush=True)
        return 124


def _undo_rebase():
    if Path(".git/rebase-merge").exists() or Path(".git/rebase-apply").exists():
        _sh("git rebase --abort")


def sync():
    """다른 작업이 올린 최신 상태로 맞춤. 실패하면 되돌리고 False(그 회차는 건너뜀)."""
    for t in range(1, 4):
        if _sh("git pull -q --rebase origin main") == 0:
            return True
        _undo_rebase()
        time.sleep(t * 5)
    return False


def _broken_json():
    """세 폴더에서 바뀐 JSON 가운데 읽히지 않는 것(시간 초과로 쓰다 멈춘 파일)."""
    out = subprocess.run(["git", "status", "--porcelain", "--", *DIRS], capture_output=True, text=True).stdout
    bad = []
    for line in out.splitlines():
        path = line[3:].strip()
        if path.endswith(".json") and Path(path).exists():
            try:
                json.loads(Path(path).read_text(encoding="utf-8"))
            except (OSError, ValueError):
                bad.append(path)
    return bad


def push(message):
    for path in _broken_json():
        print(f"깨진 기록이라 올리지 않고 되돌림: {path}", flush=True)
        _sh(f"git checkout -- '{path}' 2>/dev/null || rm -f '{path}'")
    _sh("mkdir -p " + " ".join(DIRS) + " && git add -A " + " ".join(DIRS))
    if _sh("git diff --cached --quiet") == 0:
        return True
    _sh(f'git commit -q -m "{message}"')
    for t in range(1, 6):
        if _sh("git pull -q --rebase origin main && git push -q") == 0:
            return True
        _undo_rebase()
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
    if not sync():
        print(f"{bot}: 저장소를 최신으로 맞추지 못해 이번 회차는 건너뜀(다음 회차가 밀린 봉을 처리)", flush=True)
        return False
    started = time.time()
    try:
        code = subprocess.run(cmd, env=env, timeout=RUN_LIMIT).returncode
    except subprocess.TimeoutExpired:
        print(f"{bot}: {RUN_LIMIT // 60}분 안에 끝나지 않아 멈춤", flush=True)
        code = 124
    ok = push(message)
    print(f"{bot}: {time.time() - started:.0f}초 · 종료 {code} · 올림 {'됨' if ok else '실패'}", flush=True)
    return code == 0 and ok


def main(start="0855", end="1200", clock=lambda: datetime.now(KST), sleep=time.sleep):
    jobs = plan(start, end)
    if clock().strftime("%H%M") >= end:
        print(f"맡은 창({start}~{end})이 이미 지나 끝냅니다.")
        return 0
    catch_up, later = due(jobs, clock().strftime("%H%M"))
    failed = []

    def one(t, bot):
        if clock().strftime("%H%M") >= end:          # 창이 끝났으면 다음 작업 몫(겹치지 않게)
            return False
        try:
            if not run_bot(bot):
                failed.append(f"{t} {bot}")
        except Exception as e:                          # 한 회차가 터져도 남은 회차는 돎
            print(f"{t} {bot}: 뜻밖의 오류 {type(e).__name__}", flush=True)
            failed.append(f"{t} {bot}")
        return True

    for t, bot in catch_up:
        print(f"[{clock():%H:%M:%S}] 늦게 시작 — {t} {bot} 따라잡기", flush=True)
        if not one(t, bot):
            break
    for t, bot in later:
        now = clock()
        at = now.replace(hour=int(t[:2]), minute=int(t[2:]), second=0, microsecond=0)
        wait = (at - now).total_seconds()
        if wait > 0:
            sleep(wait)
        print(f"[{clock():%H:%M:%S}] {t} {bot}", flush=True)
        if not one(t, bot):
            print("맡은 창이 끝나 멈춥니다(다음 작업이 이어 맡음).", flush=True)
            break
    print("끝 · 말썽 난 회차:", failed or "없음", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(*(sys.argv[1:3])))
