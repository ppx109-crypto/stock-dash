"""한투 1시간봉(hourly-kis, collect_kis_hourly.py가 모음)을 1시간봉 연구 엔진(hlab) 모양으로 읽음 — K2(사용자 2026-10-02 "한투 데이터로 받아서 연구하자").
운영(hourly_a.kis_history)과 같게 15시 봉(15:00 ~ 15:30 마감 동시호가)은 14시 봉에 합침(시가는 14시 · 고가/저가는 둘 중 · 종가는 15시 · 거래량은 더함).
한투 분봉은 약 1년 전까지만 줌(2025-09-17 ~) → 두 반은 15분봉 연구와 같게 앞 2025-09-17 ~ 2026-03-31 · 뒤 2026-04-01 ~ 2026-09-29.
1시간봉 시험지(hlab.HOLDOUT 2026-09-30 ~)는 그대로 잠금(bar_limit).
쓰는 법: import kis1h; kis1h.use() → H.load가 한투 자료를 읽고, PERIODS를 simulate(periods=...)에 넘김."""
from pathlib import Path

import numpy as np

import hlab as H

HOME = Path("/home/user/stock-dash/hourly-kis")
PERIODS = (("앞", ("2025091700", "2026040100")), ("뒤", ("2026040100", "2026093000")))


def load(codes=None):
    found = {}
    lim = H.bar_limit()
    for folder in sorted(HOME.iterdir()):
        if not folder.is_dir() or (codes and folder.name not in codes):
            continue
        got = {}
        for f in sorted(folder.glob("*.csv")):
            for ln in f.read_text(encoding="utf-8").splitlines():
                p = ln.split(",")
                if len(p) != 6 or not p[0][:1].isdigit():
                    continue
                t = p[0][:8] + ("14" if p[0][8:] == "15" else p[0][8:])
                o, h, l, c, v = (float(x) for x in p[1:])
                if t in got:
                    po, ph, pl, pc, pv = got[t]
                    got[t] = (po, max(ph, h), min(pl, l), c, pv + v) if p[0][8:] == "15" else (o, max(ph, h), min(pl, l), pc, pv + v)
                else:
                    got[t] = (o, h, l, c, v)
        ts = sorted(t for t in got if not lim or t <= lim)
        if len(ts) < 200:
            continue
        arr = np.array([got[t] for t in ts])
        found[folder.name] = {"t": ts, "o": arr[:, 0], "h": arr[:, 1], "l": arr[:, 2], "c": arr[:, 3], "v": arr[:, 4]}
    return found


def use():
    H.load = load
    return PERIODS
