"""15분봉 연구 엔진 — 1시간봉 엔진(hlab)의 계좌 모의 · 일봉 재료 · 종목 모음 · 시험지 잠금을 그대로 쓰고, 자료만 15분봉(m15-kis).

hlab의 계좌 모의(simulate · _one_run)는 봉 시각을 글자로만 다룹니다(날은 앞 8자리, 하루 끝 평가는 날이 바뀔 때). 그래서
15분봉 시각(YYYYMMDDHHMM, 12자리)도 그대로 받습니다. 체결 감사(사는 · 파는 체결은 그 종목의 바로 앞 봉이 닫힌 뒤 정한 것인지)도 같음.

- 하루 26칸: 09:00 · 09:15 · … · 15:15(15:15 칸 = 15:15 ~ 15:30, 마감 동시호가 포함).
- 신호는 봉이 닫힌 뒤 그 봉까지 값으로만 · 체결은 다음 봉 시가(hlab과 같음).
- 일봉 재료(정배열 · 추세 문 · 수급 · 시장 폭 · 공시)는 hlab.daily_context → hlab.attach로 **전 거래일 것만**.
- 시험지 잠금 · 잘라내기 · 더럽히기: hlab.bar_limit · poison_at(HLAB_CUT · HLAB_POISON, 10자리 'YYYYMMDDHH')를 따름.
  10자리 시각 T로 자르면 T시가 시작하는 15분봉부터 없는 것으로 봄(글자 비교: '202601161400' > '2026011614').
- 두 반: 자료가 약 1년(2025-09-17 ~)뿐이라 앞 2025-09-17 ~ 2026-03-31 · 뒤 2026-04-01 ~ 2026-09-29.
"""
from pathlib import Path

import numpy as np

import hlab as H

import os

HOME = Path(os.environ.get("M15_HOME", "m15-kis"))      # 시험 · 점검용으로 다른 폴더를 줄 수 있음
EARLY = ("202509170000", "202604010000")
LATE = ("202604010000", "202609300000")
PERIODS = (("앞", EARLY), ("뒤", LATE))
PER_DAY = 26
SCALE = 4            # 1시간봉 봉 수 × 4 = 15분봉 봉 수(보유 · 자리 바꾸기 봉 수를 옮길 때)


def load(codes=None, home=None, min_per_day=20, min_bars=500):
    """{code: {'t': [YYYYMMDDHHMM], 'o','h','l','c','v': np.array}} — 시각 순.
    봉이 min_per_day칸보다 적은 날(거래 정지 · 반쪽 자료)은 뺌. 시험지 잠금 · 잘라내기 · 더럽히기는 hlab과 같은 환경변수를 따름."""
    home = Path(home or HOME)
    found = {}
    if not home.exists():
        return found
    lim = H.bar_limit()
    pz = H.poison_at()
    for folder in sorted(home.iterdir()):
        if not folder.is_dir() or (codes and folder.name not in codes):
            continue
        lines = []
        for f in sorted(folder.glob("*.csv")):
            lines += [ln.split(",") for ln in f.read_text(encoding="utf-8").splitlines() if ln.count(",") == 5]
        lines = [p for p in lines if len(p[0]) == 12 and p[0].isdigit()]
        per_day = {}
        for p in lines:
            per_day[p[0][:8]] = per_day.get(p[0][:8], 0) + 1
        lines = sorted((p for p in lines if per_day[p[0][:8]] >= min_per_day), key=lambda p: p[0])
        if lim:
            lines = [p for p in lines if p[0] <= lim]
        if len(lines) < min_bars:
            continue
        arr = np.array([[float(x) for x in p[1:]] for p in lines])
        ts = [p[0] for p in lines]
        if pz:
            arr = H._poison_bars(ts, arr, pz, folder.name)
        found[folder.name] = {"t": ts, "o": arr[:, 0], "h": arr[:, 1], "l": arr[:, 2], "c": arr[:, 3], "v": arr[:, 4]}
    return found


def hhmm(b):
    return np.array([t[8:12] for t in b["t"]])


def at(b, when):
    """그 시각(HHMM)에 시작한 봉인가."""
    return hhmm(b) == when


def daystart(b):
    return np.r_[True, np.array([b["t"][i][:8] != b["t"][i - 1][:8] for i in range(1, len(b["t"]))])]


def setup(codes=None, home=None, top=100):
    """1시간봉 연구 준비(research/h003.py 앞부분)와 같은 것을 15분봉으로: 자료 · 일봉 재료(전 거래일) · 종목 모음(전 거래일 시총 순위)."""
    data = load(codes, home)
    names = [c for c in data if not c.startswith("K")]
    ranks, trend = H.cached_tables("20220101")
    ctx = H.daily_context(names, ranks, trend)
    att = {c: H.attach(data[c], ctx[c], sorted(ctx[c])) for c in names if c in ctx}
    uni = H.Universe({d: v for d, v in ranks.items() if d >= "20250101"}, top=top)
    data = {c: data[c] for c in att}
    inside = {c: np.array([uni.ok(c, t) for t in data[c]["t"]]) for c in data}
    return {"data": data, "ATT": att, "IN": inside, "ranks": ranks, "trend": trend, "CTX": ctx}


def simulate(data, entry, exit_rule, size, **kw):
    """hlab.simulate를 15분봉 두 반으로."""
    kw.setdefault("periods", PERIODS)
    return H.simulate(data, entry, exit_rule, size, **kw)


def coverage(home=None):
    """수집 상황: (종목 수, 종목마다 날 수의 가운데, 첫 날, 끝 날)."""
    home = Path(home or HOME)
    if not home.exists():
        return 0, 0, None, None
    days_per, first, last = [], None, None
    for folder in home.iterdir():
        if not folder.is_dir():
            continue
        ds = set()
        for f in folder.glob("*.csv"):
            ds.update(ln[:8] for ln in f.read_text(encoding="utf-8").splitlines() if ln[:8].isdigit())
        if ds:
            days_per.append(len(ds))
            first = min(first or min(ds), min(ds))
            last = max(last or max(ds), max(ds))
    if not days_per:
        return 0, 0, None, None
    return len(days_per), int(np.median(days_per)), first, last


def to_hours(data):
    """15분봉 → 1시간봉(같은 자료로 1시간봉 규칙과 견주려고). 09 ~ 14시 봉, 15:00 · 15:15 칸은 14시 봉에 합침(장중 알림 hourly_a와 같음).
    시각은 'YYYYMMDDHH00'(12자리)로 둬서 m15lab · hlab에 그대로 넣음."""
    out = {}
    for c, b in data.items():
        t, o, h, l, cl, v = [], [], [], [], [], []
        for k, s in enumerate(b["t"]):
            hh = min(int(s[8:10]), 14)
            key = f"{s[:8]}{hh:02d}00"
            if t and t[-1] == key:
                h[-1] = max(h[-1], b["h"][k]); l[-1] = min(l[-1], b["l"][k]); cl[-1] = b["c"][k]; v[-1] += b["v"][k]
            else:
                t.append(key); o.append(b["o"][k]); h.append(b["h"][k]); l.append(b["l"][k]); cl.append(b["c"][k]); v.append(b["v"][k])
        out[c] = {"t": t, "o": np.array(o), "h": np.array(h), "l": np.array(l), "c": np.array(cl), "v": np.array(v)}
    return out
