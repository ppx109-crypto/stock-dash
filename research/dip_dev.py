"""DIP-DEEP-0042 개발 도구 — 잘린 스냅샷(/tmp/dip-d.pkl · research/dip_build.py가 원자료에서 '자르기 → 파생'으로 구움)만 읽음.
(계획: research-exchange/claude-to-gpt/DIP-DEEP-0042/PLAN.md)
- round 3(GPT #193 6095756125):
  1. 1일봉 캐시 · 표 · nrl 모듈을 읽지도 import하지도 않음. 시작 때 스냅샷 sha256을 snapshot.json 값과 견주고, 다르면 멈춤.
  2. 토막(D1 · D2)마다 일봉을 그 토막 끝 날까지로 잘라 엔진에 줌. 끝 날에는 새로 사지 않고(holds 감쌈), 열린 매매는 끝 날 종가에 팖
     (연구용 가상 정산 · 정지 · 결측은 엔진 방식대로 종목 자기 줄의 다음 칸 · 줄이 먼저 끝나면 그 마지막 종가).
  3. 평가는 셈 **전에** STARTED를 적고, 끝나면 DONE · 실패면 FAILED를 같은 번호로 적음. 상한은 STARTED 수로 셈(중단 · 다시 돌리기 포함).
  2-1. 엔진 lab.run(settle_end=True)로 끝 날 하한가 · 보유 한도(130) 넘음 · 줄 끝 · 기간 끝 열린 매매도 버리지 않고 가상 정산(GPT #194 지적과 같은 빈틈).
  4. accept()에서 최대낙폭 조건을 뺌(낙폭은 측정 · 보고만 · 사용자 기준은 계좌 하루 · 달력 달 TWR −15%).
쓰는 법: import dip_dev as D → D.evaluate(tag, holds, exits, size=..., rank=..., note=...) → {"D1": {...}, "D2": {...}}"""
import bisect
import hashlib
import json
import os
import pickle
import sys
import time
from pathlib import Path

ROOT = Path("/home/user/stock-dash")
sys.path.insert(0, str(ROOT))
BOX = ROOT / "research-exchange/claude-to-gpt/DIP-DEEP-0042"
SNAP = Path(os.getenv("DIP_SNAP", "/tmp/dip-d.pkl"))
CUT = "20221229"
D1 = ("20170102", "20191230")
D2 = ("20200102", "20221229")
COST, SLOTS, CAP = 0.25, 10, 130
EVAL_CAP = 300
EVAL_LOG = Path(os.getenv("DIP_EVAL_LOG", str(BOX / "evals.jsonl")))


def _load():
    blob = SNAP.read_bytes()
    want = json.loads((BOX / "snapshot.json").read_text())["snapshot_sha256"]
    if os.getenv("DIP_SNAP_CHECK", "1") == "1" and hashlib.sha256(blob).hexdigest() != want:
        sys.exit("스냅샷 해시 다름 — 셈하지 않음")
    return pickle.loads(blob)


import lab  # noqa: E402
import rule  # noqa: E402

_s = _load()
assert _s["cut"] == CUT
prices = _s["prices"]
rows = _s["rows"]
BR = _s["br"]
FLOW = _s["flow"]
IX = _s["ix"]
IXD = sorted(IX)
del _s


def _guard():
    assert max(d for b in prices.values() for d, _ in b["rows"]) <= CUT
    assert max(r["date"] for r in rows) <= CUT and max(BR) <= CUT and IXD[-1] <= CUT
    assert all(not v[0] or v[0][-1] <= CUT for v in FLOW.values())
    assert not any("ahead" in r or "met" in r for r in rows)


_guard()


def _seg(hi):
    """토막 끝 날까지 자른 일봉 · lanes · 같이 움직이는 표(토막마다 한 번 만들어 둠)."""
    p = {c: {**b, "rows": [x for x in b["rows"] if x[0] <= hi]} for c, b in prices.items()}
    p = {c: b for c, b in p.items() if b["rows"]}
    return p, lab.lanes(p), rule.apart(p)


SEG = {}


def seg(tag):
    if tag not in SEG:
        SEG[tag] = _seg((D1 if tag == "D1" else D2)[1])
    return SEG[tag]


def lane_of(code):
    """부품 셈용 lanes(CUT까지 · 신호는 그날까지만 보므로 토막 끝과 무관)."""
    return LANES[code]


LANES = lab.lanes(prices)


# ── 부품(모두 그날까지 · 수급은 전날까지) ──────────────────────
def flow_sum(row, n, col, lag=1):
    got = FLOW.get(row["code"])
    if not got:
        return None
    days, acc, ok = got
    k = bisect.bisect_left(days, row["date"]) - (lag - 1)
    if lag == 0:
        k = bisect.bisect_right(days, row["date"])
    lo = k - n
    if lo < 0 or ok[k] - ok[lo] < n:
        return None
    return acc[col][k] - acc[col][lo]


def ret(row, n):
    c = LANES[row["code"]]["closes"]
    i = row["i"]
    return None if i < n or i >= len(c) else (c[i] / c[i - n] - 1) * 100


def ma_gap(row, n):
    c = LANES[row["code"]]["closes"]
    i = row["i"]
    if i < n - 1 or i >= len(c):
        return None
    return (c[i] / (sum(c[i - n + 1:i + 1]) / n) - 1) * 100


def ix_ret(day, n):
    k = bisect.bisect_right(IXD, day) - 1
    if k < n:
        return None
    return (IX[IXD[k]] / IX[IXD[k - n]] - 1) * 100


def settle(exit_at):
    """종목 줄의 마지막 칸(토막 끝 · 줄 끝)에 오면 그날 종가에 팜(연구용 가상 정산)."""
    def go(lane, start, price, step, peak, row=None):
        if start + step >= len(lane["closes"]) - 1:
            return True
        return exit_at(lane, start, price, step, peak, row)
    return go


def no_last_day(holds, hi):
    return lambda r: r["date"] < hi and holds(r)


def fixed_exit(take, stop, days):
    def go(lane, start, price, step, peak, row=None):
        now = (lane["closes"][start + step] / price - 1) * 100
        return now >= take or now <= -stop or step >= days
    return go


# ── 돌리기 ───────────────────────────────────────────────────
KEYS = ("매매", "연수익", "폭", "최대낙폭", "골 폭", "가동률", "승률", "보유중앙", "해마다")
LUCK_CAP = 30.0


def luck(g, since):
    led = (g or {}).get("매매목록") or []
    if not led:
        return None, None
    years = max(1, int(max(t["판 날"] for t in led)[:4]) - int(str(since)[:4]) + 1)
    w = sorted(t["손익"] * t["자리"] for t in led)
    capped = sum(min(t["손익"], LUCK_CAP) * t["자리"] for t in led) / SLOTS / years
    return round(capped, 2), round(sum(w[:-2]) / SLOTS / years, 2)


def run_way(holds, exits, size=lambda r: 2, rank=None, tries=8):
    out = {}
    for tag, (lo, hi) in (("D1", D1), ("D2", D2)):
        p, lanes, kin = seg(tag)
        pool = [r for r in rows if lo <= r["date"] <= hi and r["code"] in lanes and r["i"] < len(lanes[r["code"]]["closes"])]
        g = lab.wobble(pool, p, no_last_day(holds, hi), settle(exits), tries=tries, rank=rank or (lambda r: 0), slots=SLOTS,
                       since=lo, per_day=None, apart=kin, realistic=True, cap=CAP, detail=True, size=size, cost=COST,
                       settle_end=True)   # 엔진 끝 정산: 끝 날 하한가 · 보유 한도 넘음 · 줄 끝 · 기간 끝도 가상 정산 기록
        if not g:
            out[tag] = None
            continue
        a, b = luck(g, lo)
        out[tag] = {k: g.get(k) for k in KEYS}
        out[tag].update({"행운뺌": a, "큰2건뺌": b})
    return out


def _started():
    if not EVAL_LOG.exists():
        return 0
    return sum(1 for ln in EVAL_LOG.read_text(encoding="utf-8").splitlines() if ln.strip() and json.loads(ln).get("status") == "STARTED")


def _write(rec):
    with EVAL_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def evaluate(tag, holds, exits, size=lambda r: 2, rank=None, note=""):
    """평가 판 하나 = run_way 한 번. 셈 전에 STARTED(번호)를 적고, 끝나면 DONE · 예외면 FAILED. 상한은 STARTED 수(300)."""
    n = _started()
    if n >= EVAL_CAP:
        sys.exit(f"평가 판 상한 {EVAL_CAP} 다 씀 — 더 셈하지 않음")
    _write({"n": n + 1, "status": "STARTED", "tag": tag, "note": note, "at": time.strftime("%Y-%m-%d %H:%M:%S")})
    try:
        res = run_way(holds, exits, size=size, rank=rank)
    except BaseException as e:
        _write({"n": n + 1, "status": "FAILED", "tag": tag, "error": f"{type(e).__name__}: {str(e)[:200]}",
                "at": time.strftime("%Y-%m-%d %H:%M:%S")})
        raise
    _write({"n": n + 1, "status": "DONE", "tag": tag, "at": time.strftime("%Y-%m-%d %H:%M:%S"), "res": res})
    return res


def accept(cand, inc, removal=False):
    """받아들이는 식(엔진 출력 둘째 자리 값 · inc = 지금 채택판 · round 3: 낙폭 조건 없음).
    보탬: D1 · D2 각각 ① 매매 ≥ 60 ② 연수익 차 > max(두 판 폭) ③ 행운뺌 ≥ inc 그리고 큰2건뺌 ≥ inc.
    덜어냄: D1 · D2 각각 ① 매매 ≥ 60 ② 연수익 차 ≥ −max(두 판 폭) ③ 행운뺌 · 큰2건뺌 ≥ inc − max(두 판 폭)."""
    why = {}
    for h in ("D1", "D2"):
        c, i = cand.get(h), inc.get(h)
        if not c or not i:
            why[h] = "결과 없음(60건 미만)"
            continue
        w = max(c["폭"], i["폭"])
        d = c["연수익"] - i["연수익"]
        slack = w if removal else 0
        why[h] = [c["매매"] >= 60, (d >= -w) if removal else (d > w),
                  c["행운뺌"] >= i["행운뺌"] - slack and c["큰2건뺌"] >= i["큰2건뺌"] - slack]
    return all(isinstance(v, list) and all(v) for v in why.values()), why


def line(tag, res):
    parts = [f"{tag:28s}"]
    for k in ("D1", "D2"):
        x = res.get(k)
        parts.append(f"{k} 60건 미만" if not x else
                     f"{k} {x['매매']:>4}건 연 {x['연수익']:>6} (폭 {x['폭']:>5}) 골 {x['최대낙폭']:>6} 가동 {x['가동률']:>5} "
                     f"승 {x['승률']} 행운뺌 {x['행운뺌']} 큰2뺌 {x['큰2건뺌']}")
    return " | ".join(parts)
