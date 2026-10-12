"""키움 KMF 미래 참조 막기 검사(사용자 2026-10-12 "개발시 미래참조는 여러가지 방법으로 차단해줘").
모든 KMF 과제에서 실행 전에 돌림. 개발 기간(06-01 앞) 자료만 씀 · 손익 판정에 쓰지 않음.
  ① 처음부터 안 읽기: load()는 KMF_CUT 뒤 줄을 읽지 않음(kmf.py) — 과제마다 cut 시험이 따로 확인
  ② 무작위 지점(아무 분 200곳 + 신호 난 분 200곳): 그 분 k에서 rows[:k+1]만 준 신호 = 전체를 준 신호의 k번째
  ③ 뒤 자료 뒤섞기: 어느 날 뒤 값을 엉터리(무작위 걸음)로 바꿔도 그 날 앞 날별 손익 · 거래가 한 칸도 안 바뀜
  ③-2 장중 뒤섞기: 어느 날 12:00부터 뒤 값을 엉터리로 바꿔도 그 분 앞의 신호가 한 칸도 안 바뀜(그날 안 미래 참조 잡기)
  ④ 체결 값: 모든 들기 값은 판단 다음 분 시가, 모든 정리 값은 다음 분 시가 · 멈춤 값 · 그 분 종가(15:30 정리) 가운데 하나
python3 research/kmf_guard.py kmf2   (또는 kmf)"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kmf as K  # noqa: E402


def prefix_points(sig, rows, cfg, n=200, seed=0):
    rng = np.random.default_rng(seed)
    full = sig(rows, cfg)
    bad = 0
    hits = [i for i, x in enumerate(full) if x is not None]          # 신호가 난 분도 따로 뽑음(드문 신호 놓치지 않게)
    pts = set(rng.integers(0, len(rows), n).tolist())
    if hits:
        pts |= set(rng.choice(hits, min(n, len(hits)), replace=False).tolist())
    for k in sorted(pts):
        if sig(rows[:k + 1], cfg)[k] != full[k]:
            bad += 1
    return bad


def scramble(sig, rows, cfg, cut, seed=0):
    rng = np.random.default_rng(seed)
    out, px = [], None
    for r in rows:
        if r[0] < cut:
            out.append(r); continue
        px = (px or r[5]) + rng.normal(0, 3.0)
        o, c = px, px + rng.normal(0, 1.0)
        out.append((r[0], r[1], o, max(o, c) + 0.5, min(o, c) - 0.5, c, int(rng.integers(1, 999))))
    a_days, a_tr = K.simulate(rows, sig(rows, cfg))
    b_days, b_tr = K.simulate(out, sig(out, cfg))
    dd = sum(1 for d in a_days if d < cut and abs(a_days[d] - b_days[d]) > 1e-9)
    dt = sum(1 for x, y in zip([t for t in a_tr if t[0] < cut], [t for t in b_tr if t[0] < cut]) if x != y)
    return dd + dt + abs(len([t for t in a_tr if t[0] < cut]) - len([t for t in b_tr if t[0] < cut]))


def scramble_intraday(sig, rows, cfg, days=("20260115", "20260310", "20260420"), minute=720, seed=0):
    rng = np.random.default_rng(seed)
    bad = 0
    full = sig(rows, cfg)
    for d in days:
        k0 = next(i for i, r in enumerate(rows) if (r[0], r[1]) >= (d, minute))
        out = list(rows[:k0])
        px = rows[k0][5]
        for r in rows[k0:]:
            px += rng.normal(0, 3.0)
            out.append((r[0], r[1], px, px + 0.5, px - 0.5, px + rng.normal(0, 1.0), 1))
        w = sig(out, cfg)
        bad += sum(1 for i in range(k0) if w[i] != full[i])
    return bad


def fill_prices(sig, rows, cfg):
    """거래 (날, 정리 판단 분, 방향, 들기 값, 정리 값)의 값이 허용된 값 가운데 하나인지."""
    want = sig(rows, cfg)
    days, trades = K.simulate(rows, want)
    opens = {(r[0], r[1]): r[2] for r in rows}
    closes = {(r[0], r[1]): r[5] for r in rows}
    entries = set()
    for i in range(1, len(rows)):
        if rows[i][0] == rows[i - 1][0] and want[i - 1] in (1, -1):
            entries.add((rows[i][0], rows[i][2]))         # 판단 다음 분 시가
    bad = 0
    for d, m, pos, entry, exit_ in trades:
        if (d, entry) not in entries:
            bad += 1
        nxt = opens.get((d, m + 1))
        ok = abs(exit_ - closes.get((d, m), 1e18)) < 1e-9 or (nxt is not None and abs(exit_ - nxt) < 1e-9)
        if not ok:                                         # 멈춤 값: 그 분 고저 안 · 또는 그 분 시가(갭)
            r = next((x for x in rows if x[0] == d and x[1] == m), None)
            ok = r is not None and (r[4] - 1e-9 <= exit_ <= r[3] + 1e-9)
        bad += 0 if ok else 1
    return bad, len(trades)


def main(which):
    if which == "kmf2":
        import kmf2 as M
    elif which == "kmf3":
        import kmf3 as M
    else:
        M = K
    rows = K._rows_before(K.VAL[0])
    cuts = ("20260302", "20260401", "20260504")
    res = []
    for cfg in M.grid():
        r = {"cfg": M.name(cfg), "prefix_bad": prefix_points(M.signals, rows, cfg),
             "scramble_bad": sum(scramble(M.signals, rows, cfg, c, seed=i) for i, c in enumerate(cuts)),
             "intraday_bad": scramble_intraday(M.signals, rows, cfg)}
        r["fill_bad"], r["trades"] = fill_prices(M.signals, rows, cfg)
        res.append(r)
    print(json.dumps({"pass": all(x["prefix_bad"] == 0 and x["scramble_bad"] == 0 and x["intraday_bad"] == 0 and x["fill_bad"] == 0 for x in res),
                      "period": "2026-01 ~ 05(개발)만", "runs": res}, ensure_ascii=False))


def selftest():
    """검사가 일부러 만든 미래 참조 신호를 잡는지(잡아야 통과)."""
    rows = K._rows_before("20260501")

    def leak_next(rows, cfg):
        w = [None] * len(rows)
        for i in range(len(rows) - 1):
            if rows[i + 1][0] == rows[i][0] and K.ENTRY_FROM <= rows[i][1] <= K.ENTRY_TO:
                w[i] = 1 if rows[i + 1][5] > rows[i][5] else -1
        return w

    def leak_day_end(rows, cfg):
        w, last = [None] * len(rows), {}
        for r in rows:
            last[r[0]] = r[5]
        for i, r in enumerate(rows):
            if r[1] == 600:
                w[i] = 1 if last[r[0]] > r[5] else -1
        return w
    out = {}
    for nm, f in (("다음 분 몰래 보기", leak_next), ("그날 끝 몰래 보기", leak_day_end)):
        out[nm] = {"prefix_bad": prefix_points(f, rows, {}), "intraday_bad": scramble_intraday(f, rows, {})}
    print(json.dumps({"caught_all": all(v["prefix_bad"] > 0 and v["intraday_bad"] > 0 for v in out.values()), "leaky": out}, ensure_ascii=False))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "selftest":
        selftest(); sys.exit()
    main(sys.argv[1] if len(sys.argv) > 1 else "kmf2")
