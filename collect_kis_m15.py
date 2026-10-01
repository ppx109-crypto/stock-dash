"""한국투자증권 1분봉을 모아 15분봉 만들기(15분봉 RL 재료, 조회 전용 · collect_kis_hourly와 같은 조회 · 같은 이어 받기).

주식일별분봉조회(FHKST03010230)는 약 1년 전까지 1분봉을 줍니다. 하루를 네 번(15:30 · 13:30 · 11:30 · 09:30 끝) 물어
15분 칸(09:00 · 09:15 · … · 15:15 — 15:15 칸은 15:15~15:30, 마감 동시호가 포함)으로 묶습니다.
저장: m15-kis/{종목코드}/{해}.csv — "YYYYMMDDHHMM,시가,고가,저가,종가,거래량"(HHMM = 그 칸이 시작한 시각).
종목: hourly-data/universe.json의 top100(2023-09 뒤 하루라도 시총 100위 안에 든 종목).
python collect_kis_m15.py [종목코드,...]   · 환경변수 KIS_HOURLY_MAX_CALLS(한 번에 부를 최대 수, 기본 40000)
"""
import json
import sys
from pathlib import Path

import collect_kis_hourly as K

HOME = Path("m15-kis")
SIZE = 15


def slot(hhmmss, size=SIZE):
    """1분봉 시각(그 분이 끝난 시각)을 그 칸의 시작 분(하루 0시부터)으로. 090100 → 540(09:00) · 091500 → 540 · 091600 → 555."""
    h, m = int(hhmmss[:2]), int(hhmmss[2:4])
    return (h * 60 + m - 1) // size * size


def to_bars(rows, day, size=SIZE):
    """그날 1분봉 줄들 → [(YYYYMMDDHHMM, o, h, l, c, v)] (시각 순). 09:00 앞 · 15:30 뒤는 버림."""
    mins = []
    for r in rows:
        if str(r.get("stck_bsop_date", "")) != day:
            continue
        t = str(r.get("stck_cntg_hour", ""))
        try:
            o, hi, lo, c = (float(r[k]) for k in ("stck_oprc", "stck_hgpr", "stck_lwpr", "stck_prpr"))
            v = float(r.get("cntg_vol") or 0)
        except (KeyError, TypeError, ValueError):
            continue
        if len(t) != 6 or min(o, hi, lo, c) <= 0:
            continue
        mins.append((t, o, hi, lo, c, v))
    by = {}
    for t, o, hi, lo, c, v in sorted(set(mins)):
        s = slot(t, size)
        if not 9 * 60 <= s <= 15 * 60 + 15:
            continue
        if s not in by:
            by[s] = [o, hi, lo, c, v]
        else:
            x = by[s]
            x[1] = max(x[1], hi); x[2] = min(x[2], lo); x[3] = c; x[4] += v
    return [(f"{day}{s // 60:02d}{s % 60:02d}", *[round(x, 2) for x in by[s][:4]], int(by[s][4])) for s in sorted(by)]


def main(codes=None):
    """1시간봉 수집기를 15분 칸 · m15-kis로 돌림(끝나면 되돌려 둠 — 같은 프로세스의 1시간봉 수집에 섞이지 않게)."""
    saved = K.HOME, K.to_hours
    K.HOME, K.to_hours = HOME, to_bars
    try:
        uni = json.loads(Path("hourly-data/universe.json").read_text(encoding="utf-8"))
        return K.main(codes or list(uni["top100"]))
    finally:
        K.HOME, K.to_hours = saved


if __name__ == "__main__":
    sys.exit(main(sys.argv[1].split(",") if len(sys.argv) > 1 else None))
