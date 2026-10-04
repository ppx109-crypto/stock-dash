"""1시간봉 자료 출처 실험(docs/RL-1HY.md 1단계 · 사용자 2026-10-04 "야후에서 장 마감 동시호가 빠진 값 빼고 1시간봉 연구 · 1 · 2 · 3단계 RL로").
같은 규칙(1시간봉 94회차 = 운영 hourly_a · h101 entry_f 기본) · 같은 엔진(hlab._one_run) · 같은 종목(한투 ∩ 야후) · 같은 기간에서 **자료만** 바꿈:
  H1_SRC=yahoo     야후 60분봉(15시 봉 없음 · 14시 봉 종가 ≈ 15:00 값)
  H1_SRC=kis       한투(15시 봉을 14시 봉에 합침 = 운영과 같음 · 14시 봉 종가 = 실제 종가)
  H1_SRC=kis_no15  한투에서 15시 봉을 버림(야후처럼 14시 봉 종가 ≈ 15:00 값) — '동시호가가 빠진 탓'만 따로 봄
  H1_SRC=kis_y09   kis_no15 + 09시 봉 시가만 야후 값으로 — '아침 시가(체결 값) 차이' 몫을 봄
  H1_SRC=y_k09     야후 + 09시 봉 시가만 한투 값으로
  H1_ALL=1         종목을 야후가 1시간봉을 제대로 주는 종목으로 줄이지 않음(한투 종목 모두 · 운영과 같음)
매매 목록을 scratchpad h1src_{SRC}.json으로(종목 · 산 때 · 판 때 · 손익 · 칸) · 한 줄 요약."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, "/home/user/stock-dash")
sys.path.insert(0, "/home/user/stock-dash/research")
os.chdir("/home/user/stock-dash")
import numpy as np
import hlab as H
import kis1h

SRC = os.environ.get("H1_SRC", "yahoo")
OUT = "/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/h1src_"
LO, HI = "2025091700", "2026090100"
_yload = H.load


def _kis_raw(name, drop15):
    """한투 1시간봉(hourly-kis + m15-kis 묶음) · drop15면 15시 봉(15:00 ~ 15:30)을 버리고, 아니면 14시 봉에 합침."""
    got = {}
    rows = []
    for base, step in ((kis1h.HOME / name, "h"), (kis1h.M15 / name, "m")):
        for f in (sorted(base.glob("*.csv")) if base.is_dir() else []):
            for ln in f.read_text(encoding="utf-8").splitlines():
                p = ln.split(",")
                if len(p) == 6 and p[0][:1].isdigit():
                    rows.append((p[0], step, [float(x) for x in p[1:]]))
    m_hours = {r[0][:10] for r in rows if r[1] == "m"}
    for t, step, (o, h, l, c, v) in sorted(rows, key=lambda r: r[0]):
        if step == "h" and t[:10] in m_hours:
            continue                              # 15분봉에서 만든 시각이 있으면 그것을 씀(kis1h와 같게)
        hh = t[8:10]
        if hh == "15" and drop15:
            continue
        key = t[:8] + ("14" if hh == "15" else hh)
        if key in got:
            po, ph, pl, pc, pv = got[key]
            got[key] = (po, max(ph, h), min(pl, l), c, pv + v)
        else:
            got[key] = (o, h, l, c, v)
    return got


def load(codes=None):
    ys = _yload(codes)
    if SRC in ("yahoo", "y_k09"):
        out = {c: b for c, b in ys.items() if c in COMMON or c not in KCODES}
    else:
        out = {}
        lim = H.bar_limit()
        for c in (codes or sorted(COMMON)):
            if c not in COMMON:
                if c in ys:
                    out[c] = ys[c]                # 지수 등 한투에 없는 것은 야후 그대로
                continue
            g = _kis_raw(c, SRC != "kis")
            ts = sorted(t for t in g if not lim or t <= lim)
            if len(ts) < 200:
                continue
            arr = np.array([g[t] for t in ts])
            out[c] = {"t": ts, "o": arr[:, 0], "h": arr[:, 1], "l": arr[:, 2], "c": arr[:, 3], "v": arr[:, 4]}
    if SRC in ("kis_y09", "y_k09"):
        other = {c: (ys.get(c) if SRC == "kis_y09" else None) for c in out}
        if SRC == "y_k09":
            for c in out:
                if c in COMMON:
                    g = _kis_raw(c, True)
                    other[c] = {"t": sorted(g), "o": np.array([g[t][0] for t in sorted(g)])}
        for c, b in out.items():
            ob = other.get(c)
            if not ob or c not in COMMON:
                continue
            at = {t: i for i, t in enumerate(ob["t"])}
            o = b["o"].copy()
            for i, t in enumerate(b["t"]):
                if t[8:10] == "09" and t in at:
                    o[i] = ob["o"][at[t]]
            b["o"] = o
    return out


KCODES = {f.name for base in (kis1h.HOME, kis1h.M15) if base.is_dir() for f in base.iterdir() if f.is_dir()}
YCODES = {f.name for f in H.HOME.iterdir() if f.is_dir()}
COMMON = KCODES & YCODES
_YOK = set(_yload(sorted(COMMON)))              # 야후가 1시간봉을 제대로 주는 종목(hlab.load 거르기 통과)만
if os.environ.get("H1_ALL") != "1":             # H1_ALL=1: 한투가 가진 종목 모두(운영과 같음 · 야후 거르기 안 함)
    COMMON = {c for c in COMMON if c in _YOK}
else:
    SRC_TAG = SRC + "_all"
H.load = load
exec(open("research/h101.py", encoding="utf-8").read().split('print(f"== 1시간봉 101회차')[0])
data = {c: b for c, b in data.items() if c in COMMON}
sigs = {c: np.asarray(entry_f()(c, b), bool) for c, b in data.items()}
r = H._one_run(data, sigs, EX, size, LO, HI, 10, 0, None, rk_of(tiers(20, 5, 3)), H.COST, None, None, stale90)
T = [(t["code"], t["산 때"], t["판 때"].lstrip("끝"), t["손익"], t["칸"]) for t in r["목록"]]
json.dump(T, open(OUT + globals().get("SRC_TAG", SRC) + ".json", "w"))
p = np.array([t[3] for t in T])
print(f"{SRC:9s} 종목 {len(data)} · 매매 {len(T)} · 이김 {np.mean(p > 0) * 100:.0f}% · 평균 {p.mean():+.2f}% · 칸 반영 합 {sum(t[3] * t[4] / 10 for t in T):+.1f}%p", flush=True)
