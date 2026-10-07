"""P3 — 전문 트레이더 갈래(docs/RL-PRO.md): P1의 '피할 쪽'을 1일봉 엔진(nrl · 새 82 · 씨앗 8) **거르기**로.
최근 n거래일 안에 '반응 나쁜'(공시 날 종가가 전날보다 대상 가운데값 대비 −2% 아래) 자사주 처분 · 전환사채 · 유상증자 · 잠정실적 등이
있었던 후보는 안 삼. 공시 날(t0 = 접수일 또는 그 뒤 첫 거래일)이 **신호 날보다 앞**인 것만(공시는 다음 날부터) · 반응은 t0 종가까지 값.
엔진 잣대: 앞(2017 ~ 20) · 뒤(2021 ~) 연 · 골 · 행운뺌 · 큰2건뺌 · 바뀐 매매.
Z_PART=check: 자르기 · 더럽히기 — 가격 · 공시를 T까지만(또는 T 뒤 엉터리) 남겨도 T 이하 신호 날의 거름 값이 같은가 · 검사 눈(신호 날 당일 공시를 쓰는 거름)은 걸려야.
python research/z015.py · Z_PART=check python research/z015.py
"""
import bisect
import json
import os
import sys

import numpy as np

sys.path.insert(0, "/home/user/stock-dash/research")
sys.path.insert(0, "/home/user/stock-dash")
import nrl  # noqa: E402
import ntools as T  # noqa: E402

HOLD = nrl.BASE_HOLD
BAD4 = ("자사주처분", "전환사채", "유상증자", "잠정실적")
BAD_ALL = BAD4 + ("최대주주변경", "조회공시")


def build(prices, events, peek=False):
    """종목 → [(t0, 갈래, 반응)] · 반응 = t0 하루 등락 − 그날 모든 종목 가운데값."""
    cal = sorted({d for v in prices.values() for d, _ in v["rows"]})
    ret = {}
    for c, v in prices.items():
        rows = v["rows"]
        ret[c] = {rows[i][0]: rows[i][1] / rows[i - 1][1] - 1 for i in range(1, len(rows)) if rows[i - 1][1]}
    med = {}
    by = {}
    for c, m in ret.items():
        for d, x in m.items():
            by.setdefault(d, []).append(x)
    med = {d: float(np.median(v)) for d, v in by.items()}
    out = {}
    for c, evs in events.items():
        got = []
        for d, k in evs:
            j = bisect.bisect_left(cal, d)
            if j >= len(cal):
                continue
            t0 = cal[j]
            x = ret.get(c, {}).get(t0)
            if x is None or t0 not in med:
                continue
            got.append((t0, k, x - med[t0]))
        out[c] = sorted(got)
    return out, cal


def load_events(codes, cut="", poison=""):
    ev = {}
    for c in codes:
        try:
            rows = json.load(open(f"/home/user/stock-dash/event-data/{c}.json", encoding="utf-8")).get("rows") or []
        except (OSError, ValueError):
            rows = []
        got = []
        for r in rows:
            d, k = str(r.get("date", "")), r.get("kind")
            if not d or (cut and d > cut):
                continue
            if poison and d > poison:
                k = "자사주처분"                             # 엉터리: 뒤 공시를 모두 나쁜 갈래로
            got.append((d, k))
        ev[c] = got
    return ev


def make_bad(table, cal, kinds, n, thr=-0.02, same_day=False):
    pos = {d: i for i, d in enumerate(cal)}

    def bad(r):
        i = pos.get(r["date"])
        if i is None:
            return False
        for t0, k, x in reversed(table.get(r["code"], [])):
            if t0 > r["date"] or (t0 == r["date"] and not same_day):
                continue
            if i - pos[t0] > n:
                break
            if k in kinds and x < thr:
                return True
        return False
    return bad


def run():
    codes = {r["code"] for r in nrl.inside}
    table, cal = build(nrl.prices, load_events(codes))
    print("== P3: 반응 나쁜 공시 뒤 후보 거르기 ==", flush=True)
    base = T.once("지금(새 82)", holds=HOLD)
    tries = [("넷(자사주처분·전환사채·유상증자·잠정실적) 20일", BAD4, 20), ("넷 60일", BAD4, 60),
             ("잠정실적만 60일", ("잠정실적",), 60), ("희석(유상증자·전환사채)만 60일", ("유상증자", "전환사채"), 60),
             ("여섯(+최대주주변경·조회공시) 20일", BAD_ALL, 20)]
    for tag, kinds, n in tries:
        bad = make_bad(table, cal, kinds, n)
        got = T.once("거름: " + tag, holds=lambda r, bad=bad: HOLD(r) and not bad(r))
        T.diff_check(base, got)


def make_peek(table, cal, kinds, n=20, thr=-0.02):
    """검사 눈: 일부러 신호 날 **뒤** n거래일 안의 나쁜 공시를 보는 거름(미래) — 자르기 · 더럽히기에 반드시 걸려야 함."""
    pos = {d: i for i, d in enumerate(cal)}

    def peek(r):
        i = pos.get(r["date"])
        if i is None:
            return False
        return any(t0 > r["date"] and pos[t0] - i <= n and k in kinds and x < thr for t0, k, x in table.get(r["code"], []))
    return peek


def check(cuts=("20190315", "20220615", "20250902")):
    codes = sorted({r["code"] for r in nrl.inside})
    full, cal = build(nrl.prices, load_events(codes))
    rows = list(nrl.inside)
    f_bad, f_peek = make_bad(full, cal, BAD4, 60), make_peek(full, cal, BAD4)
    full_v = {(r["code"], r["date"]): f_bad(r) for r in rows}
    full_p = {(r["code"], r["date"]): f_peek(r) for r in rows}
    ok = True
    for cut in cuts:
        for mode in ("cut", "poison"):
            px = {}
            for c, v in nrl.prices.items():
                px[c] = dict(v, rows=[(d, x if d <= cut else x * 1.7) for d, x in v["rows"] if mode == "poison" or d <= cut])
            ev = load_events(codes, cut=cut if mode == "cut" else "", poison=cut if mode == "poison" else "")
            t2, cal2 = build(px, ev)
            b2, p2 = make_bad(t2, cal2, BAD4, 60), make_peek(t2, cal2, BAD4)
            keys = [k for k in full_v if k[1] <= cut]
            diff = [k for k in keys if full_v[k] != b2({"code": k[0], "date": k[1]})]
            caught = any(full_p[k] != p2({"code": k[0], "date": k[1]}) for k in keys)
            print(f"[{mode} {cut}] 거름 값 {len(keys)}행: {'합격' if not diff else f'불합격 {len(diff)}건 예 {diff[:3]}'}"
                  f" · 검사 눈(뒤 20일 공시 엿보기) {'걸림' if caught else '안 걸림(고장)'}", flush=True)
            ok &= (not diff) and caught
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(check() if os.environ.get("Z_PART") == "check" else run())
