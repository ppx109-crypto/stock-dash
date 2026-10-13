"""KMF-0020 탐색 1 — KMF-0017이 잃는 날의 모양(진단 · 날이 끝난 뒤 값이라 규칙에는 바로 못 씀).
사용자 2026-10-13 "신규봇에서 mdd를 메꿔줄 새로운 봇개발을 해보자".
날마다: 범위(고-저) · 효율(|종-시|/범위) · 아침 1시간 범위 비율 · 시가 갭 · 앞날 범위 · 오후 되돌림(오전 방향과 반대로 움직인 몫)."""
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "research"))
import numpy as np  # noqa: E402
import kmf as K  # noqa: E402
import kmf17 as M17  # noqa: E402

K.DAY_STOP = -25.0


def day_feats(rows):
    by = defaultdict(list)
    for r in rows:
        if 540 <= r[1] <= 930:
            by[r[0]].append(r)
    out, prev = {}, None
    for d in sorted(by):
        x = by[d]; o = x[0][2]; c = x[-1][5]
        hi = max(r[3] for r in x); lo = min(r[4] for r in x); rng = hi - lo
        am = [r for r in x if r[1] < 600]; amr = (max(r[3] for r in am) - min(r[4] for r in am)) if am else 0
        mid = [r for r in x if r[1] <= 720]; mc = mid[-1][5] if mid else c
        amdir = np.sign(mc - o) if mid else 0
        pm_back = (-(c - mc) * amdir) / rng if rng else 0
        out[d] = {"범위": rng, "효율": abs(c - o) / rng if rng else 0, "아침비": amr / rng if rng else 0,
                  "갭": (o - prev["c"]) if prev else 0, "앞날범위": prev["rng"] if prev else None, "오후되돌림": pm_back}
        prev = {"c": c, "rng": rng}
    return out


def q_table(f, pnl, key, nq=4):
    ds = [d for d in pnl if d in f and f[d][key] is not None]
    v = np.array([f[d][key] for d in ds]); p = np.array([pnl[d] for d in ds])
    qs = np.quantile(v, np.linspace(0, 1, nq + 1))
    rows = []
    for i in range(nq):
        m = (v >= qs[i]) & ((v <= qs[i + 1]) if i == nq - 1 else (v < qs[i + 1]))
        rows.append([round(float(qs[i]), 3), round(float(qs[i + 1]), 3), int(m.sum()), round(float(p[m].sum()), 1), round(float(p[m].mean()), 2), int((p[m] < 0).sum())])
    return rows


if __name__ == "__main__":
    rows = K._rows_before(M17.END)
    b = M17.prep(rows)
    days, _ = K.simulate(b, M17.signals(b, M17.grid()[0]))
    f = day_feats(rows)
    out = {}
    for key in ("범위", "효율", "아침비", "갭", "앞날범위", "오후되돌림"):
        out[key] = q_table(f, days, key)
    print("칸: [구간 아래, 위, 날 수, 손익 합, 날 평균, 손해 날 수]")
    print(json.dumps(out, ensure_ascii=False, indent=1))
    # 효율 낮고 범위 큰 날
    big = np.median([f[d]["범위"] for d in days]); eff = np.median([f[d]["효율"] for d in days])
    for a in (0, 1):
        for e in (0, 1):
            ds = [d for d in days if (f[d]["범위"] >= big) == bool(a) and (f[d]["효율"] >= eff) == bool(e)]
            print("범위", "큼" if a else "작음", "· 효율", "높음" if e else "낮음", len(ds), round(sum(days[d] for d in ds), 1), "손해 날", sum(1 for d in ds if days[d] < 0))
